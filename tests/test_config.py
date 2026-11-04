import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from src.core.config import Settings


class SecuritySettingsTests(unittest.TestCase):
    def settings(self, **values):
        # Isolate both the shell environment and the developer's private .env.
        with patch.dict(os.environ, {}, clear=True):
            return Settings(_env_file=None, **values)

    def test_local_defaults_disable_debug(self):
        settings = self.settings()
        self.assertFalse(settings.DEBUG)
        self.assertEqual(settings.ENVIRONMENT, "development")

    def test_production_requires_a_private_signing_key(self):
        for key in (None, "", "too-short", "changeme-in-production-super-secret-key",
                    "super-secret-key-change-in-production-1234567890"):
            values = {} if key is None else {"SECRET_KEY": key}
            with self.subTest(key=key), self.assertRaises(ValidationError):
                self.settings(ENVIRONMENT="production", **values)

    def test_production_rejects_debug_and_sql_logging(self):
        for flag in ("DEBUG", "DB_ECHO"):
            with self.subTest(flag=flag), self.assertRaises(ValidationError):
                self.settings(ENVIRONMENT="production", SECRET_KEY="a-test-only-key-with-at-least-32-characters", **{flag: True})

    def test_production_accepts_explicit_safe_settings(self):
        settings = self.settings(
            ENVIRONMENT="production", DEBUG=False, DB_ECHO=False,
            SECRET_KEY="a-test-only-key-with-at-least-32-characters",
        )
        self.assertFalse(settings.DEBUG)
        self.assertFalse(settings.DB_ECHO)

    def test_only_the_supported_jwt_algorithm_is_accepted(self):
        for algorithm in ("none", "HS512", "RS256"):
            with self.subTest(algorithm=algorithm), self.assertRaises(ValidationError):
                self.settings(ALGORITHM=algorithm)

    def test_token_lifetime_must_be_positive(self):
        for minutes in (0, -1):
            with self.subTest(minutes=minutes), self.assertRaises(ValidationError):
                self.settings(ACCESS_TOKEN_EXPIRE_MINUTES=minutes)
