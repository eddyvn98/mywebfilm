import json
import os
import uuid
import base64
from storage_utils import atomic_write_json
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers import (
    parse_registration_credential_json,
    parse_authentication_credential_json,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
CREDENTIALS_FILE = os.path.join(DATA_DIR, "credentials.json")
LEGACY_CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
RP_ID = "localhost" # This will need to be dynamic for tunnels
RP_NAME = "My Cinema Secure"

class SecurityService:
    def __init__(self):
        self.credentials = self._load_credentials()
        self.challenges = {} # Store challenges in memory (temporary)

    def _load_credentials(self):
        source_file = CREDENTIALS_FILE if os.path.exists(CREDENTIALS_FILE) else LEGACY_CREDENTIALS_FILE
        if os.path.exists(source_file):
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migration: Convert single credential to list for each user
                for user_id in data:
                    if isinstance(data[user_id], dict):
                        data[user_id] = [data[user_id]]
                if source_file == LEGACY_CREDENTIALS_FILE:
                    atomic_write_json(CREDENTIALS_FILE, data)
                return data
        return {}

    def _save_credentials(self):
        atomic_write_json(CREDENTIALS_FILE, self.credentials)

    def get_registration_options(self, user_id, username, origin):
        # We use the origin from the request to support Tunnels
        rp_id = origin.split("//")[-1].split(":")[0]
        
        # user_id must be bytes for pywebauthn
        user_id_bytes = user_id.encode('utf-8') if isinstance(user_id, str) else user_id

        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=RP_NAME,
            user_id=user_id_bytes,
            user_name=username,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        self.challenges[user_id] = options.challenge
        return options_to_json(options)

    def verify_registration(self, user_id, origin, credential_json):
        rp_id = origin.split("//")[-1].split(":")[0]
        challenge = self.challenges.get(user_id)
        
        if not challenge:
            raise ValueError("Challenge not found for user registration")

        # Parse the JSON credential
        parsed_credential = parse_registration_credential_json(credential_json)

        registration_verification = verify_registration_response(
            credential=parsed_credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
        )

        # Save credential
        if user_id not in self.credentials:
            self.credentials[user_id] = []
        
        new_cred = {
            "id": base64.b64encode(registration_verification.credential_id).decode('utf-8'),
            "public_key": base64.b64encode(registration_verification.credential_public_key).decode('utf-8'),
            "sign_count": registration_verification.sign_count,
            "created_at": str(uuid.uuid4()) # Traceable
        }
        
        # Check if ID already exists (to update instead of duplicate)
        existing_idx = next((i for i, c in enumerate(self.credentials[user_id]) if c["id"] == new_cred["id"]), None)
        if existing_idx is not None:
            self.credentials[user_id][existing_idx] = new_cred
        else:
            self.credentials[user_id].append(new_cred)

        self._save_credentials()
        return True

    def get_authentication_options(self, user_id, origin):
        rp_id = origin.split("//")[-1].split(":")[0]
        user_creds = self.credentials.get(user_id, [])
        
        if not user_creds:
            raise ValueError(f"No credentials found for user: {user_id}")

        allow_credentials = []
        for cred in user_creds:
            allow_credentials.append(PublicKeyCredentialDescriptor(
                id=base64.b64decode(cred["id"]),
            ))

        options = generate_authentication_options(
            rp_id=rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        self.challenges[user_id] = options.challenge
        return options_to_json(options)

    def verify_authentication(self, user_id, origin, credential_json):
        rp_id = origin.split("//")[-1].split(":")[0]
        user_creds = self.credentials.get(user_id, [])
        challenge = self.challenges.get(user_id)

        if not user_creds or not challenge:
            raise ValueError("Invalid authentication state: no credentials or challenge")

        # Parse the JSON credential to get the ID
        parsed_credential = parse_authentication_credential_json(credential_json)
        credential_id_b64 = base64.b64encode(parsed_credential.raw_id).decode('utf-8')
        
        # Find the matching credential
        matching_cred = next((c for c in user_creds if c["id"] == credential_id_b64), None)
        if not matching_cred:
            raise ValueError("Credential ID not recognized")

        # In webauthn 2.x, we can pass the parsed credential
        authentication_verification = verify_authentication_response(
            credential=parsed_credential,
            expected_challenge=challenge,
            expected_origin=origin,
            expected_rp_id=rp_id,
            credential_public_key=base64.b64decode(matching_cred["public_key"]),
            credential_current_sign_count=matching_cred["sign_count"],
        )

        # Update sign count
        matching_cred["sign_count"] = authentication_verification.new_sign_count
        self._save_credentials()
        return True

security_manager = SecurityService()
