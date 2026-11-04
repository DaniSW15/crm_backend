import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core import tenant
from src.core.security import create_access_token, hash_password, verify_password


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.debug = patch.object(tenant.settings, "DEBUG", False)
        self.debug.start()
        self.addCleanup(self.debug.stop)

    def resolve(self, token=None, tenant_id=None, user_id=None):
        bearer = (
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            if token else None
        )
        return tenant.resolve_tenant_context(bearer, tenant_id, user_id)

    def test_headers_do_not_authenticate_in_production(self):
        for headers in ((None, None), (str(uuid4()), None), (str(uuid4()), str(uuid4()))):
            with self.subTest(headers=headers), self.assertRaises(HTTPException) as error:
                self.resolve(tenant_id=headers[0], user_id=headers[1])
            self.assertEqual(error.exception.status_code, 401)

    def test_signed_identity_overrides_headers(self):
        tenant_id, user_id = uuid4(), uuid4()
        token = create_access_token({
            "tenant_id": str(tenant_id), "sub": str(user_id), "role": "CLIENTE"
        })
        context = self.resolve(token, str(uuid4()), str(uuid4()))
        self.assertEqual((context.tenant_id, context.user_id), (tenant_id, user_id))
        with self.assertRaises(HTTPException) as error:
            tenant.require_roles("ADMIN", "DEV")(context)
        self.assertEqual(error.exception.status_code, 403)

    def test_invalid_token_cannot_fall_back_to_demo(self):
        with patch.object(tenant.settings, "DEBUG", True):
            with self.assertRaises(HTTPException) as error:
                self.resolve("invalid-token", str(uuid4()), str(uuid4()))
        self.assertEqual(error.exception.status_code, 401)

    def test_missing_identity_claims_are_rejected(self):
        with self.assertRaises(HTTPException) as error:
            self.resolve(create_access_token({"role": "ADMIN"}))
        self.assertEqual(error.exception.status_code, 401)

    def test_debug_never_authenticates_demo_defaults_or_headers(self):
        with patch.object(tenant.settings, "DEBUG", True):
            for headers in ((None, None), (str(uuid4()), str(uuid4())), ("invalid", "invalid")):
                with self.subTest(headers=headers), self.assertRaises(HTTPException) as error:
                    self.resolve(tenant_id=headers[0], user_id=headers[1])
                self.assertEqual(error.exception.status_code, 401)
                self.assertEqual(error.exception.headers, {"WWW-Authenticate": "Bearer"})

    def test_password_round_trip_and_mock_hash_rejection(self):
        hashed = hash_password("test-password")
        self.assertTrue(verify_password("test-password", hashed))
        self.assertFalse(verify_password("wrong-password", hashed))
        self.assertFalse(verify_password("admin123", "mock-password-hash"))
