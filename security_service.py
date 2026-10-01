import base64
import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone

from storage_utils import atomic_write_json
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
CREDENTIALS_FILE = os.path.join(DATA_DIR, "credentials.json")
LEGACY_CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
RP_NAME = "My Cinema Secure"
CHALLENGE_TTL_SECONDS = 120
MAX_ACTIVE_CHALLENGES = 512


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _safe_device_name(value):
    name = " ".join(str(value or "").strip().split())
    return name[:80] or "Thiết bị không tên"


class SecurityService:
    def __init__(self):
        self.credentials = self._load_credentials()
        self.challenges = {}
        self._challenge_lock = threading.RLock()

    def _normalize_credential(self, credential):
        item = dict(credential or {})
        item.setdefault("device_id", uuid.uuid4().hex)
        item["device_name"] = _safe_device_name(
            item.get("device_name") or "Thiết bị đã đăng ký"
        )
        created_at = item.get("created_at")
        try:
            datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except Exception:
            item["created_at"] = _utc_now()
        item.setdefault("last_used_at", None)
        return item

    def _load_credentials(self):
        source_file = (
            CREDENTIALS_FILE
            if os.path.exists(CREDENTIALS_FILE)
            else LEGACY_CREDENTIALS_FILE
        )
        if not os.path.exists(source_file):
            return {}

        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        normalized = {}
        for user_id, raw_credentials in data.items():
            if isinstance(raw_credentials, dict):
                raw_credentials = [raw_credentials]
            normalized[user_id] = [
                self._normalize_credential(item)
                for item in raw_credentials or []
            ]

        if source_file == LEGACY_CREDENTIALS_FILE:
            atomic_write_json(CREDENTIALS_FILE, normalized)
        return normalized

    def _save_credentials(self):
        atomic_write_json(CREDENTIALS_FILE, self.credentials)

    def _cleanup_challenges_unlocked(self):
        now = time.time()
        expired = [
            challenge_id
            for challenge_id, item in self.challenges.items()
            if item["expires_at"] <= now
        ]
        for challenge_id in expired:
            self.challenges.pop(challenge_id, None)

        if len(self.challenges) > MAX_ACTIVE_CHALLENGES:
            overflow = len(self.challenges) - MAX_ACTIVE_CHALLENGES
            oldest = sorted(
                self.challenges.items(),
                key=lambda pair: pair[1]["created_at"],
            )[:overflow]
            for challenge_id, _ in oldest:
                self.challenges.pop(challenge_id, None)

    def _store_challenge(self, user_id, purpose, challenge):
        with self._challenge_lock:
            self._cleanup_challenges_unlocked()
            challenge_id = secrets.token_urlsafe(24)
            now = time.time()
            self.challenges[challenge_id] = {
                "user_id": user_id,
                "purpose": purpose,
                "challenge": challenge,
                "created_at": now,
                "expires_at": now + CHALLENGE_TTL_SECONDS,
            }
            self._cleanup_challenges_unlocked()
            return challenge_id

    def _take_challenge(self, challenge_id, user_id, purpose):
        with self._challenge_lock:
            self._cleanup_challenges_unlocked()
            item = self.challenges.pop(str(challenge_id or ""), None)
            if not item:
                raise ValueError("Challenge không tồn tại hoặc đã hết hạn")
            if item["user_id"] != user_id or item["purpose"] != purpose:
                raise ValueError("Challenge không hợp lệ")
            if item["expires_at"] <= time.time():
                raise ValueError("Challenge đã hết hạn")
            return item["challenge"]

    @staticmethod
    def _rp_id_from_origin(origin):
        return origin.split("//")[-1].split(":")[0]

    def has_credentials(self, user_id):
        return bool(self.credentials.get(user_id))

    def has_device(self, user_id, device_id):
        return any(
            item.get("device_id") == device_id
            for item in self.credentials.get(user_id, [])
        )

    def get_registration_options(self, user_id, username, origin):
        rp_id = self._rp_id_from_origin(origin)
        user_id_bytes = (
            user_id.encode("utf-8")
            if isinstance(user_id, str)
            else user_id
        )
        existing = [
            PublicKeyCredentialDescriptor(id=base64.b64decode(cred["id"]))
            for cred in self.credentials.get(user_id, [])
        ]

        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=RP_NAME,
            user_id=user_id_bytes,
            user_name=username,
            exclude_credentials=existing,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        challenge_id = self._store_challenge(
            user_id, "register", options.challenge
        )
        return {
            "publicKey": json.loads(options_to_json(options)),
            "challenge_id": challenge_id,
            "expires_in": CHALLENGE_TTL_SECONDS,
        }

    def verify_registration(
        self,
        user_id,
        origin,
        credential_json,
        challenge_id,
        device_name=None,
    ):
        rp_id = self._rp_id_from_origin(origin)
        challenge = self._take_challenge(
            challenge_id, user_id, "register"
        )
        parsed_credential = parse_registration_credential_json(
            credential_json
        )

        verification = verify_registration_response(
            credential=parsed_credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
            require_user_verification=True,
        )

        if user_id not in self.credentials:
            self.credentials[user_id] = []

        credential_id = base64.b64encode(
            verification.credential_id
        ).decode("utf-8")
        now = _utc_now()
        new_cred = {
            "id": credential_id,
            "public_key": base64.b64encode(
                verification.credential_public_key
            ).decode("utf-8"),
            "sign_count": verification.sign_count,
            "device_id": uuid.uuid4().hex,
            "device_name": _safe_device_name(device_name),
            "created_at": now,
            "last_used_at": now,
        }

        existing_idx = next(
            (
                i
                for i, item in enumerate(self.credentials[user_id])
                if item["id"] == credential_id
            ),
            None,
        )
        if existing_idx is not None:
            previous = self.credentials[user_id][existing_idx]
            new_cred["device_id"] = (
                previous.get("device_id") or new_cred["device_id"]
            )
            new_cred["created_at"] = (
                previous.get("created_at") or now
            )
            self.credentials[user_id][existing_idx] = new_cred
        else:
            self.credentials[user_id].append(new_cred)

        self._save_credentials()
        return {
            "device_id": new_cred["device_id"],
            "device_name": new_cred["device_name"],
        }

    def get_authentication_options(self, user_id, origin):
        rp_id = self._rp_id_from_origin(origin)
        user_creds = self.credentials.get(user_id, [])
        if not user_creds:
            raise ValueError(
                f"No credentials found for user: {user_id}"
            )

        allow_credentials = [
            PublicKeyCredentialDescriptor(id=base64.b64decode(cred["id"]))
            for cred in user_creds
        ]
        options = generate_authentication_options(
            rp_id=rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        challenge_id = self._store_challenge(
            user_id, "login", options.challenge
        )
        return {
            "publicKey": json.loads(options_to_json(options)),
            "challenge_id": challenge_id,
            "expires_in": CHALLENGE_TTL_SECONDS,
        }

    def verify_authentication(
        self,
        user_id,
        origin,
        credential_json,
        challenge_id,
    ):
        rp_id = self._rp_id_from_origin(origin)
        user_creds = self.credentials.get(user_id, [])
        challenge = self._take_challenge(
            challenge_id, user_id, "login"
        )
        if not user_creds:
            raise ValueError("Không có Passkey đã đăng ký")

        parsed_credential = parse_authentication_credential_json(
            credential_json
        )
        credential_id_b64 = base64.b64encode(
            parsed_credential.raw_id
        ).decode("utf-8")
        matching_cred = next(
            (
                c
                for c in user_creds
                if c["id"] == credential_id_b64
            ),
            None,
        )
        if not matching_cred:
            raise ValueError("Passkey không được nhận diện")

        verification = verify_authentication_response(
            credential=parsed_credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
            credential_public_key=base64.b64decode(
                matching_cred["public_key"]
            ),
            credential_current_sign_count=matching_cred["sign_count"],
            require_user_verification=True,
        )

        matching_cred["sign_count"] = verification.new_sign_count
        matching_cred["last_used_at"] = _utc_now()
        self._save_credentials()
        return {
            "device_id": matching_cred["device_id"],
            "device_name": matching_cred["device_name"],
        }

    def list_devices(self, user_id):
        devices = []
        for item in self.credentials.get(user_id, []):
            devices.append({
                "device_id": item.get("device_id"),
                "device_name": (
                    item.get("device_name")
                    or "Thiết bị đã đăng ký"
                ),
                "created_at": item.get("created_at"),
                "last_used_at": item.get("last_used_at"),
            })
        return devices

    def rename_device(self, user_id, device_id, device_name):
        for item in self.credentials.get(user_id, []):
            if item.get("device_id") == device_id:
                item["device_name"] = _safe_device_name(device_name)
                self._save_credentials()
                return item["device_name"]
        raise ValueError("Không tìm thấy thiết bị")

    def revoke_device(self, user_id, device_id):
        devices = self.credentials.get(user_id, [])
        if len(devices) <= 1:
            raise ValueError(
                "Không thể thu hồi Passkey cuối cùng"
            )
        remaining = [
            item
            for item in devices
            if item.get("device_id") != device_id
        ]
        if len(remaining) == len(devices):
            raise ValueError("Không tìm thấy thiết bị")
        self.credentials[user_id] = remaining
        self._save_credentials()
        return True


security_manager = SecurityService()
