import hashlib
import hmac
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.core import security, tenant
from src.core.security import create_access_token, decode_access_token
from src.modules.crm.infrastructure.repositories import SqlAlchemyDealRepository
from src.modules.identity.application.use_cases.logout import LogoutUseCase, token_fingerprint
from src.modules.identity.infrastructure.session_models import RevokedTokenModel
from src.modules.identity.infrastructure.token_revocation import SqlAlchemyTokenRevocationRepository
from test_transactions import AsyncSessionAdapter, AsyncTransactionAdapter
from test_wiring import request


class AsyncSessionContext(AsyncSessionAdapter):
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.session.close()

    def begin_nested(self):
        return AsyncTransactionAdapter(self.session.begin_nested())


def signed_token(payload, algorithm="HS256"):
    """Firma fixtures legacy y claims inválidos sin pasar por el emisor."""
    header = security._base64url_encode(json.dumps({"alg": algorithm, "typ": "JWT"}).encode())
    body = security._base64url_encode(json.dumps(payload).encode())
    data = f"{header}.{body}"
    signature = security._base64url_encode(hmac.new(
        security.settings.SECRET_KEY.encode(), data.encode(), hashlib.sha256
    ).digest())
    return f"{data}.{signature}"


class JwtExpirationTests(unittest.TestCase):
    def test_rejects_missing_or_invalid_expiration(self):
        for expiration in (None, 0, -1, "9999999999", True, float("nan"), float("inf"), 10**1000):
            with self.subTest(expiration=expiration), self.assertRaises(ValueError):
                decode_access_token(signed_token({"exp": expiration}))
        with self.assertRaises(ValueError):
            decode_access_token(signed_token({}))

    def test_rejects_expiration_at_current_second_and_past(self):
        now = int(datetime.now(timezone.utc).timestamp())
        for expiration in (now, now - 1):
            with self.subTest(expiration=expiration), self.assertRaises(ValueError):
                decode_access_token(signed_token({"exp": expiration}))

    def test_rejects_unexpected_header_algorithm(self):
        expiration = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        for algorithm in ("none", "HS512", None):
            with self.subTest(algorithm=algorithm), self.assertRaises(ValueError):
                decode_access_token(signed_token({"exp": expiration}, algorithm))

    def test_legacy_token_without_jti_remains_valid(self):
        payload = {"exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())}
        self.assertEqual(decode_access_token(signed_token(payload)), payload)

    def test_each_new_session_has_unique_server_generated_jti(self):
        claims = {"sub": str(uuid4()), "tenant_id": str(uuid4()), "role": "CLIENTE", "jti": "client-value"}
        first = create_access_token(claims)
        second = create_access_token(claims)
        self.assertNotEqual(first, second)
        self.assertNotEqual(decode_access_token(first)["jti"], "client-value")
        self.assertNotEqual(decode_access_token(first)["jti"], decode_access_token(second)["jti"])


class LogoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        RevokedTokenModel.__table__.create(self.engine)
        self.addCleanup(self.engine.dispose)
        self.session_factory = lambda: AsyncSessionContext(Session(self.engine))
        self.store = SqlAlchemyTokenRevocationRepository(self.session_factory)
        self.logout = LogoutUseCase(self.store)
        self.claims = {"sub": str(uuid4()), "tenant_id": str(uuid4()), "role": "CLIENTE"}
        self.token = create_access_token(self.claims)
        self.expires = datetime.fromtimestamp(decode_access_token(self.token)["exp"], timezone.utc)
        for mocked in (
            patch.object(tenant.settings, "DEBUG", False),
            patch.object(SqlAlchemyTokenRevocationRepository, "is_revoked", side_effect=self.store.is_revoked),
            patch.object(SqlAlchemyTokenRevocationRepository, "revoke", side_effect=self.store.revoke),
        ):
            mocked.start()
            self.addCleanup(mocked.stop)

    async def test_revocation_persists_only_fingerprint_across_repository_instances(self):
        await self.logout.execute(self.token, self.expires)
        replacement = SqlAlchemyTokenRevocationRepository(self.session_factory)
        self.assertTrue(await replacement.is_revoked(token_fingerprint(self.token)))
        with Session(self.engine) as session:
            stored = session.get(RevokedTokenModel, token_fingerprint(self.token))
            self.assertEqual(len(stored.token_hash), 64)
            self.assertNotEqual(stored.token_hash, self.token)
            self.assertIsNotNone(stored.expires_at)
            self.assertIsNotNone(stored.revoked_at)

    async def test_duplicate_revocation_is_idempotent(self):
        await self.logout.execute(self.token, self.expires)
        await self.logout.execute(self.token, self.expires)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(RevokedTokenModel)), 1)

    async def test_logout_revokes_presented_session_and_rejects_reuse(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        with patch.object(SqlAlchemyDealRepository, "list", return_value=[]):
            self.assertEqual(await request("/api/v1/deals", headers=headers), 200)
        self.assertEqual(await request("/api/v1/auth/logout/", "POST", headers), 204)
        for method, path, body in (
            ("GET", "/api/v1/auth/me/", None),
            ("GET", "/api/v1/deals", None),
            ("POST", "/api/v1/deals", {"title": "New deal"}),
            ("GET", "/api/v1/pipelines", None),
            ("POST", "/api/v1/auth/logout/", None),
        ):
            with self.subTest(path=path, method=method):
                self.assertEqual(await request(path, method, headers, body), 401)

    async def test_logout_keeps_other_and_immediate_new_sessions_valid(self):
        second = create_access_token(self.claims)
        await self.logout.execute(self.token, self.expires)
        replacement = create_access_token(self.claims)
        with patch.object(SqlAlchemyDealRepository, "list", return_value=[]):
            for token in (second, replacement):
                self.assertEqual(await request(
                    "/api/v1/deals", headers={"Authorization": f"Bearer {token}"}
                ), 200)

    async def test_logout_requires_valid_bearer_even_in_development(self):
        for debug in (False, True):
            with self.subTest(debug=debug), patch.object(tenant.settings, "DEBUG", debug):
                for headers in ({}, {"Authorization": "Bearer invalid"}):
                    self.assertEqual(await request("/api/v1/auth/logout/", "POST", headers), 401)

    async def test_legacy_session_can_be_revoked(self):
        legacy = signed_token(self.claims | {"exp": self.expires.timestamp()})
        headers = {"Authorization": f"Bearer {legacy}"}
        self.assertEqual(await request("/api/v1/auth/logout", "POST", headers), 204)
        self.assertEqual(await request("/api/v1/deals", headers=headers), 401)

    async def test_token_expiring_after_dependencies_returns_unauthorized(self):
        with patch(
            "src.modules.identity.presentation.routes.decode_access_token",
            side_effect=ValueError("El token ha expirado."),
        ):
            self.assertEqual(await request(
                "/api/v1/auth/logout/", "POST", {"Authorization": f"Bearer {self.token}"}
            ), 401)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(RevokedTokenModel)), 0)

    async def test_revocation_lookup_does_not_fail_open_if_storage_is_missing(self):
        RevokedTokenModel.__table__.drop(self.engine)
        with self.assertRaises(OperationalError):
            await request("/api/v1/deals", headers={"Authorization": f"Bearer {self.token}"})

