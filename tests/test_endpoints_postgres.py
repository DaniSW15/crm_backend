"""Flujos HTTP reales sobre PostgreSQL, en un esquema temporal por prueba.

TEST_DATABASE_URL debe apuntar a una base de pruebas con permiso CREATE SCHEMA.
No se modifican las tablas del esquema public ni se requiere un servidor HTTP.
"""
import asyncio
import json
import os
import unittest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core import tenant
from src.core.di import CoreProvider
from src.main import app
from src.modules.crm.infrastructure.di import CrmProvider
from src.modules.crm.infrastructure.models import PipelineModel, PipelineStageModel
from src.modules.identity.infrastructure.di import IdentityProvider
from src.modules.identity.infrastructure.session_models import RevokedTokenModel
from src.modules.identity.infrastructure.token_revocation import SqlAlchemyTokenRevocationRepository
from src.shared.infrastructure.base_model import Base


class TestDatabaseProvider(Provider):
    def __init__(self, factory):
        super().__init__()
        self.factory = factory

    @provide(scope=Scope.APP, override=True)
    def sessions(self) -> async_sessionmaker[AsyncSession]:
        return self.factory


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "Requiere TEST_DATABASE_URL de PostgreSQL")
class EndpointPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "crm_test_" + uuid4().hex
        self.engine = create_async_engine(os.environ["TEST_DATABASE_URL"], connect_args={
            "server_settings": {"search_path": self.schema},
        })
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            await connection.run_sync(Base.metadata.create_all)
        self.addAsyncCleanup(self.drop_schema)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        self.container = make_async_container(
            CoreProvider(), IdentityProvider(), CrmProvider(), TestDatabaseProvider(self.factory),
        )
        self.addAsyncCleanup(self.container.close)
        self.original_container = app.state.dishka_container
        app.state.dishka_container = self.container
        self.original_debug = tenant.settings.DEBUG
        tenant.settings.DEBUG = False
        self.addCleanup(self.restore_app)

    def restore_app(self):
        app.state.dishka_container = self.original_container
        tenant.settings.DEBUG = self.original_debug

    async def drop_schema(self):
        async with self.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def request(self, path, method="GET", token=None, body=None):
        parsed = urlsplit(path)
        messages = []
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": json.dumps(body).encode() if body is not None else b""}
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        headers = [(b"content-type", b"application/json")]
        if token:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        await app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": parsed.path,
            "raw_path": parsed.path.encode(), "root_path": "", "query_string": parsed.query.encode(),
            "headers": headers, "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
        }, receive, send)
        status = next(message["status"] for message in messages if message["type"] == "http.response.start")
        payload = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return status, json.loads(payload) if payload else None

    async def register(self):
        suffix = uuid4().hex
        email = f"admin-{suffix}@example.test"
        status, auth = await self.request("/api/v1/auth/register-tenant", "POST", body={
            "company_name": "Test company", "slug": suffix, "admin_full_name": "Test admin",
            "admin_email": email, "admin_password": "test-password-123",
        })
        self.assertEqual(status, 201, auth)
        auth["login_email"] = email
        return auth

    async def pipeline(self, auth):
        pipeline_id, stage_id = uuid4(), uuid4()
        async with self.factory() as session, session.begin():
            session.add(PipelineModel(id=pipeline_id, tenant_id=UUID(auth["tenant_id"]), name="Test sales"))
            await session.flush()
            session.add(PipelineStageModel(
                id=stage_id, tenant_id=UUID(auth["tenant_id"]), pipeline_id=pipeline_id, name="Initial", order=1,
            ))
        return str(pipeline_id), str(stage_id)

    async def test_customers_crud_isolation_and_patch(self):
        own, other = await self.register(), await self.register()
        token = own["access_token"]
        status, customer = await self.request("/api/v1/customers/", "POST", token, {
            "name": "Acme", "phone": "5551234", "industry": "Software", "annual_revenue": "1234.56",
            "owner_id": own["user_id"],
        })
        self.assertEqual(status, 201, customer)
        self.assertEqual(customer["annual_revenue"], "1234.56")
        detail = f'/api/v1/customers/{customer["id"]}/'
        self.assertEqual((await self.request(detail, token=token))[0], 200)
        self.assertEqual((await self.request(detail, token=other["access_token"]))[0], 404)
        self.assertEqual((await self.request(detail, "PATCH", other["access_token"], {"name": "Foreign"}))[0], 404)
        status, updated = await self.request(detail, "PATCH", token, {"phone": None, "name": "Acme updated"})
        self.assertEqual(status, 200, updated)
        self.assertIsNone(updated["phone"])
        self.assertEqual(updated["industry"], "Software")
        for path in ("/api/v1/customers/", "/api/v1/customers"):
            status, listed = await self.request(path, token=token)
            self.assertEqual(status, 200)
            self.assertEqual([row["id"] for row in listed], [customer["id"]])
            self.assertEqual(await self.request(path, token=other["access_token"]), (200, []))
            self.assertEqual((await self.request(path))[0], 401)
        self.assertEqual((await self.request(detail, "PATCH", token, {"name": None}))[0], 422)
        self.assertEqual((await self.request("/api/v1/customers/", "POST", token, {"name": "Injected", "tenant_id": other["tenant_id"]}))[0], 422)
        self.assertEqual((await self.request("/api/v1/customers/", "POST", token, {"name": "Foreign owner", "owner_id": other["user_id"]}))[0], 400)
        self.assertEqual((await self.request("/api/v1/customers/?limit=101", token=token))[0], 422)

    async def test_opportunities_aliases_and_tenant_summary(self):
        own, other = await self.register(), await self.register()
        pipeline_id, stage_id = await self.pipeline(own)
        token = own["access_token"]
        status, customer = await self.request("/api/v1/customers/", "POST", token, {"name": "Acme"})
        self.assertEqual(status, 201)
        body = {
            "title": "Annual license", "amount": "123.45", "currency": "USD",
            "pipeline_id": pipeline_id, "stage_id": stage_id,
            "owner_id": own["user_id"], "account_id": customer["id"],
        }
        status, opportunity = await self.request("/api/v1/opportunities/", "POST", token, body)
        self.assertEqual(status, 201, opportunity)
        self.assertEqual(opportunity["amount"], "123.45")
        for path in ("/api/v1/opportunities/", "/api/v1/opportunities", "/api/v1/deals"):
            status, listed = await self.request(path + "?limit=1&status=OPEN", token=token)
            self.assertEqual(status, 200, listed)
            self.assertEqual([row["id"] for row in listed], [opportunity["id"]])
        await self.request("/api/v1/opportunities", "POST", token, body | {"title": "MX license", "currency": "MXN", "amount": "500.00"})
        status, summary = await self.request("/api/v1/analytics/summary/", token=token)
        self.assertEqual(status, 200, summary)
        self.assertEqual(summary["total_customers"], 1)
        self.assertEqual(summary["total_opportunities"], 2)
        self.assertEqual(summary["open_opportunities"], 2)
        amounts = {row["currency"]: Decimal(row["total_amount"]) for row in summary["amounts_by_currency"]}
        self.assertEqual(amounts, {"USD": Decimal("123.45"), "MXN": Decimal("500.00")})
        status, summary = await self.request("/api/v1/analytics/summary", token=other["access_token"])
        self.assertEqual(status, 200)
        self.assertEqual(summary["total_customers"], 0)
        self.assertEqual(summary["total_opportunities"], 0)
        self.assertEqual(summary["amounts_by_currency"], [])
        self.assertEqual((await self.request("/api/v1/analytics/summary/"))[0], 401)

    async def test_logout_revokes_only_presented_session_and_relogin_works(self):
        own = await self.register()
        first = own["access_token"]
        status, login = await self.request("/api/v1/auth/login/", "POST", body={
            "email": own["login_email"], "password": "test-password-123",
        })
        self.assertEqual(status, 200, login)
        second = login["access_token"]
        self.assertNotEqual(first, second)
        self.assertEqual((await self.request("/api/v1/auth/me/", token=first))[0], 200)
        self.assertEqual(await self.request("/api/v1/auth/logout/", "POST", first), (204, None))
        for path in ("/api/v1/auth/me/", "/api/v1/customers/", "/api/v1/opportunities/", "/api/v1/analytics/summary/", "/api/v1/deals"):
            self.assertEqual((await self.request(path, token=first))[0], 401, path)
        self.assertEqual((await self.request("/api/v1/auth/me/", token=second))[0], 200)
        status, relogin = await self.request("/api/v1/auth/login", "POST", body={
            "email": own["login_email"], "password": "test-password-123",
        })
        self.assertEqual(status, 200, relogin)
        self.assertNotEqual(relogin["access_token"], first)
        self.assertEqual((await self.request("/api/v1/auth/me", token=relogin["access_token"]))[0], 200)
        async with self.factory() as session:
            revoked = (await session.execute(select(RevokedTokenModel))).scalar_one()
            self.assertEqual(len(revoked.token_hash), 64)
            self.assertNotEqual(revoked.token_hash, first)
        self.assertEqual((await self.request("/api/v1/auth/logout/", "POST"))[0], 401)

    async def test_concurrent_revocations_are_persistent_and_idempotent(self):
        repository = SqlAlchemyTokenRevocationRepository(self.factory)
        fingerprint = "a" * 64
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        await asyncio.gather(*(repository.revoke(fingerprint, expires_at) for _ in range(5)))
        fresh_repository = SqlAlchemyTokenRevocationRepository(self.factory)
        self.assertTrue(await fresh_repository.is_revoked(fingerprint))
        async with self.factory() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(RevokedTokenModel)), 1)
