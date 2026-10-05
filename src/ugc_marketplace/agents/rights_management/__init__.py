"""Rights Management agent."""

from ugc_marketplace.agents._rights_management import *  # noqa: F401,F403
from ugc_marketplace.agents._rights_management import (  # noqa: F401
    AccessCheckResult,
    AccessDecision,
    GrantResult,
    RightType,
    RightsManagementAgent,
    RightsRecord,
    _default_agent,
    check_content_rights,
    check_rights,
    grant_rights,
    license_content,
    revoke_license,
)
from ugc_marketplace.agents.rights_management.infringement_detector import InfringementDetectorAgent  # noqa: F401
from ugc_marketplace.agents.rights_management.license_detector import LicenseDetectorAgent  # noqa: F401
from ugc_marketplace.agents.rights_management.rights_validator import RightsValidatorAgent  # noqa: F401
from ugc_marketplace.agents.rights_management.takedown import TakedownAgent  # noqa: F401
from ugc_marketplace.agents.rights_management.usage_tracker import UsageTrackerAgent  # noqa: F401

# Alias for backward compatibility with tests that import the old module name
import sys as _sys
import types as _types
_rights_management_module = _types.ModuleType("ugc_marketplace.agents._rights_management")
_rights_management_module.__dict__.update(globals())
_sys.modules[__name__ + "._rights_management_module"] = _rights_management_module
_sys.modules["ugc_marketplace.agents._rights_management"] = _rights_management_module
