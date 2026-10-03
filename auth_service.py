import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any


class FirebaseAuthUnavailable(Exception):
    """Firebase Authentication could not be reached or is misconfigured."""


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    api_key = os.getenv("FIREBASE_API_KEY", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if not api_key or not project_id:
        raise FirebaseAuthUnavailable("Firebase Authentication is not configured.")

    endpoint = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
    request = Request(
        f"{endpoint}?{urlencode({'key': api_key})}",
        data=json.dumps({"idToken": id_token}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except HTTPError as exc:
        try:
            error_payload = json.loads(exc.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_payload = {}
        error_detail = error_payload.get("error")
        error_message = error_detail.get("message", "") if isinstance(error_detail, dict) else ""
        if error_message in {
            "INVALID_ID_TOKEN",
            "TOKEN_EXPIRED",
            "INVALID_ARGUMENT",
            "USER_DISABLED",
            "USER_NOT_FOUND",
        }:
            raise ValueError("Sign-in is invalid or expired. Please sign in again.") from exc
        raise FirebaseAuthUnavailable(
            "Firebase Authentication could not verify this sign-in. Check its project settings."
        ) from exc
    except (TimeoutError, URLError) as exc:
        raise FirebaseAuthUnavailable(
            "Could not reach Firebase Authentication. Check your internet connection and try again."
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FirebaseAuthUnavailable("Firebase Authentication returned an invalid response.") from exc

    users = payload.get("users")
    if not isinstance(users, list) or not users or not isinstance(users[0], dict):
        raise ValueError("Sign-in is invalid or expired. Please sign in again.")

    user = users[0]
    uid = user.get("localId")
    if not isinstance(uid, str) or not uid:
        raise ValueError("Sign-in is invalid or expired. Please sign in again.")

    return {
        "uid": uid,
        "email": user.get("email"),
        "email_verified": user.get("emailVerified") is True,
    }
