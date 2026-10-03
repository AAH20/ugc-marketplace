"""Agent implementations for rights management."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ugc_marketplace.agents.rights_management.base import BaseAgent
from ugc_marketplace.agents.rights_management.infringement_detector import InfringementDetectorAgent
from ugc_marketplace.agents.rights_management.license_detector import LicenseDetectorAgent
from ugc_marketplace.agents.rights_management.rights_validator import RightsValidatorAgent
from ugc_marketplace.agents.rights_management.takedown import TakedownAgent
from ugc_marketplace.agents.rights_management.usage_tracker import UsageTrackerAgent

# Load the rights_management.py module (shadowed by this package)
_module_path = Path(__file__).parent.parent / "rights_management.py"
_spec = importlib.util.spec_from_file_location("_rights_management_module", _module_path)
_rights_management_module = importlib.util.module_from_spec(_spec)
sys.modules["_rights_management_module"] = _rights_management_module
_spec.loader.exec_module(_rights_management_module)

# Re-export data classes and functions from the module
AccessCheckResult = _rights_management_module.AccessCheckResult
AccessDecision = _rights_management_module.AccessDecision
GrantResult = _rights_management_module.GrantResult
RightType = _rights_management_module.RightType
RightsManagementAgent = _rights_management_module.RightsManagementAgent
RightsRecord = _rights_management_module.RightsRecord
check_content_rights = _rights_management_module.check_content_rights
check_rights = _rights_management_module.check_rights
grant_rights = _rights_management_module.grant_rights
license_content = _rights_management_module.license_content
revoke_license = _rights_management_module.revoke_license

__all__ = [
    "BaseAgent",
    "InfringementDetectorAgent",
    "LicenseDetectorAgent",
    "RightsValidatorAgent",
    "TakedownAgent",
    "UsageTrackerAgent",
    "AccessCheckResult",
    "AccessDecision",
    "GrantResult",
    "RightType",
    "RightsManagementAgent",
    "RightsRecord",
    "check_content_rights",
    "check_rights",
    "grant_rights",
    "license_content",
    "revoke_license",
]
