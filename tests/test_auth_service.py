import json
import os
import unittest
from io import BytesIO
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from auth_service import FirebaseAuthUnavailable, verify_firebase_id_token


class FirebaseTokenVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(
            os.environ,
            {
                "FIREBASE_PROJECT_ID": "test-project",
                "FIREBASE_API_KEY": "test-api-key",
            },
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_token_is_verified_by_firebase_and_user_claims_are_returned(self) -> None:
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(
            {"users": [{"localId": "student-123", "email": "student@example.com", "emailVerified": True}]}
        ).encode()

        with patch("auth_service.urlopen", return_value=response) as urlopen:
            claims = verify_firebase_id_token("test-id-token")

        self.assertEqual(
            claims,
            {"uid": "student-123", "email": "student@example.com", "email_verified": True},
        )
        request = urlopen.call_args.args[0]
        self.assertIn("accounts:lookup", request.full_url)
        self.assertEqual(json.loads(request.data), {"idToken": "test-id-token"})

    def test_invalid_token_is_rejected(self) -> None:
        response = BytesIO(b'{"error":{"message":"INVALID_ID_TOKEN"}}')
        error = HTTPError("https://firebase.test", 400, "Bad request", {}, response)

        with patch("auth_service.urlopen", side_effect=error):
            with self.assertRaisesRegex(ValueError, "invalid or expired"):
                verify_firebase_id_token("invalid")
        error.close()

    def test_firebase_network_error_is_reported_as_unavailable(self) -> None:
        with patch("auth_service.urlopen", side_effect=TimeoutError):
            with self.assertRaises(FirebaseAuthUnavailable):
                verify_firebase_id_token("test-id-token")


if __name__ == "__main__":
    unittest.main()
