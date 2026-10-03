from .auth_common import (
    auth_bp,
    can_register_request,
    get_origin,
    get_session_state,
    is_authenticated_unlocked,
    is_direct_local_request,
    is_recently_authenticated,
    is_token_valid,
)

# Import route modules for Blueprint registration side effects.
from . import auth_tunnel_registration as _auth_tunnel_registration
from . import auth_login_session as _auth_login_session
from . import auth_devices as _auth_devices

__all__ = [
    "auth_bp", "can_register_request", "get_origin", "get_session_state",
    "is_authenticated_unlocked", "is_direct_local_request",
    "is_recently_authenticated", "is_token_valid",
]
