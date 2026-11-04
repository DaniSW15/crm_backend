import ast
import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from dishka import Scope
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import tenant
from src.core.di import create_container
from src.core.security import create_access_token
from src.main import app
from src.modules.crm.application.use_cases.create_deal import CreateDealUseCase
from src.modules.crm.application.use_cases.delete_deal import DeleteDealUseCase
from src.modules.crm.application.use_cases.move_deal_stage import MoveDealStageUseCase
from src.modules.crm.application.use_cases.update_deal import UpdateDealUseCase
from src.modules.crm.infrastructure.repositories import SqlAlchemyDealRepository
from src.modules.identity.application.use_cases.login import LoginUseCase
from src.modules.identity.application.use_cases.register_tenant import RegisterTenantUseCase
from src.modules.identity.infrastructure.token_revocation import SqlAlchemyTokenRevocationRepository
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def request(path, method="GET", headers=None, body=None):
    """Ejecuta ASGI directamente, sin servidor ni dependencias HTTP adicionales."""
    messages = []
    sent = False
    payload = json.dumps(body).encode() if body is not None else b""

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": payload, "more_body": False}
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path,
        "raw_path": path.encode(), "root_path": "", "query_string": b"",
        "headers": [(b"content-type", b"application/json")] + [
            (key.lower().encode(), value.encode()) for key, value in (headers or {}).items()
        ],
        "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


class ApiAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        debug = patch.object(tenant.settings, "DEBUG", False)
        debug.start()
        self.addCleanup(debug.stop)
        revocations = patch.object(SqlAlchemyTokenRevocationRepository, "is_revoked", return_value=False)
        revocations.start()
        self.addCleanup(revocations.stop)

    async def test_api_rejects_headers_without_token(self):
        headers = {"X-Tenant-ID": str(uuid4()), "X-User-ID": str(uuid4())}
        deal_id = uuid4()
        cases = [
            ("GET", "/api/v1/deals", None),
            ("GET", "/api/v1/pipelines", None),
            ("GET", "/api/v1/auth/me", None),
            ("POST", f"/api/v1/deals/{deal_id}/move-stage", {"new_stage_id": str(uuid4())}),
            ("DELETE", f"/api/v1/deals/{deal_id}", None),
        ]
        for method, path, body in cases:
            with self.subTest(path=path, method=method):
                self.assertEqual(await request(path, method, headers, body), 401)

    async def test_api_allows_signed_tenant_and_ignores_conflicting_headers(self):
        tenant_id = uuid4()
        token = create_access_token({"tenant_id": str(tenant_id), "sub": str(uuid4()), "role": "CLIENTE"})
        headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(uuid4())}
        with patch.object(SqlAlchemyDealRepository, "list", return_value=[]) as list_deals:
            self.assertEqual(await request("/api/v1/deals", headers=headers), 200)
        self.assertEqual(list_deals.call_args.kwargs["tenant_id"], tenant_id)

    async def test_private_routes_require_a_jwt_even_in_debug(self):
        paths = ["/api/v1/auth/me", "/api/v1/deals", "/api/v1/pipelines",
                 "/api/v1/customers/", "/api/v1/analytics/summary/", "/api/v1/opportunities/"]
        attempts = [{}, {"Authorization": "Bearer"}, {"Authorization": "Bearer invalid-token"},
                    {"X-Tenant-ID": str(uuid4()), "X-User-ID": str(uuid4())}]
        with patch.object(tenant.settings, "DEBUG", True):
            for path in paths:
                for headers in attempts:
                    with self.subTest(path=path, headers=headers):
                        self.assertEqual(await request(path, headers=headers), 401)

    async def test_debug_never_authenticates_writes_without_a_jwt(self):
        deal_id = uuid4()
        cases = [
            ("POST", "/api/v1/deals", {"title": "Unauthorized", "amount": "10.00",
                "pipeline_id": str(uuid4()), "stage_id": str(uuid4()), "owner_id": str(uuid4())}),
            ("POST", f"/api/v1/deals/{deal_id}/move-stage", {"new_stage_id": str(uuid4())}),
            ("PUT", f"/api/v1/deals/{deal_id}", {"title": "Unauthorized edit"}),
            ("DELETE", f"/api/v1/deals/{deal_id}", None),
            ("POST", "/api/v1/customers/", {"name": "Unauthorized customer"}),
        ]
        with patch.object(tenant.settings, "DEBUG", True):
            for method, path, body in cases:
                with self.subTest(method=method, path=path):
                    self.assertEqual(await request(path, method, body=body), 401)

    async def test_api_blocks_delete_for_client_role(self):
        token = create_access_token({"tenant_id": str(uuid4()), "sub": str(uuid4()), "role": "CLIENTE"})
        self.assertEqual(await request(
            f"/api/v1/deals/{uuid4()}", "DELETE", {"Authorization": f"Bearer {token}"}
        ), 403)


class WiringTests(unittest.IsolatedAsyncioTestCase):
    async def test_write_use_cases_share_the_request_transaction(self):
        container = create_container()
        try:
            async with container(scope=Scope.REQUEST) as request_container:
                uow = await request_container.get(UnitOfWork)
                for cls in (CreateDealUseCase, MoveDealStageUseCase, UpdateDealUseCase,
                            DeleteDealUseCase, RegisterTenantUseCase):
                    with self.subTest(use_case=cls.__name__):
                        use_case = await request_container.get(cls)
                        repo = getattr(use_case, "deal_repo", getattr(use_case, "identity_repo", None))
                        self.assertIs(use_case.uow, uow)
                        self.assertIs(repo.session, uow.session)
                        if hasattr(use_case, "pipeline_repo"):
                            self.assertIs(use_case.pipeline_repo.session, uow.session)
                self.assertIsInstance(await request_container.get(LoginUseCase), LoginUseCase)
        finally:
            await container.close()

    async def test_real_async_session_transaction_lifecycle(self):
        # Comprueba el ciclo async real sin necesitar una conexión a PostgreSQL.
        async with AsyncSession() as session:
            uow = SqlAlchemyUnitOfWork(session)
            async with uow:
                self.assertTrue(session.in_transaction())
            self.assertFalse(session.in_transaction())
            with self.assertRaises(RuntimeError):
                async with uow:
                    raise RuntimeError("operation failed")
            self.assertFalse(session.in_transaction())


class ArchitectureTests(unittest.TestCase):
    def test_inner_layers_do_not_import_frameworks_or_infrastructure(self):
        root = Path(__file__).resolve().parents[1] / "src"
        violations = []
        for path in root.rglob("*.py"):
            if not {"domain", "application"}.intersection(path.parts):
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                imports = []
                if isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""]
                elif isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                for name in imports:
                    if (name.split(".")[0] in {"fastapi", "sqlalchemy", "dishka", "pydantic"}
                            or name.startswith("src.core")
                            or ".infrastructure" in name or ".presentation" in name
                            or ("domain" in path.parts and ".application" in name)):
                        violations.append(f"{path.relative_to(root)}:{node.lineno}: {name}")
        self.assertEqual(violations, [])
