"""Compatibility facade for the split authentication modules."""
import sys
from . import auth_common as _core

# Register all auth routes before exposing the legacy module surface.
from . import auth_tunnel_registration as _auth_tunnel_registration
from . import auth_login_session as _auth_login_session
from . import auth_devices as _auth_devices

# Preserve legacy imports and monkeypatch behavior: routes.api_auth is the
# same module object as auth_common, where shared auth state now lives.
sys.modules[__name__] = _core
