import os
from typing import Tuple

from config.lumi_config import (
    WHITELISTED_PATH_ALIASES,
    WHITELISTED_APPS,
    FORCE_CONFIRM_INTENTS,
    BLOCKED_INTENTS
)
from core.lumi_schema import LumiIntent, IntentType
from security.audit_log import append_audit_entry

def resolve_and_verify_path(alias: str) -> str | None:
    """
    Hinglish Comment:
    'abspath' sirf string ko saf karta hai, par symlinks ko ignore kar sakta hai.
    'realpath' real physical disk path resolve karta hai. Isse agar koi hack karke
    symlink ya '../' se whitelist ke bahar jaane ki koshish kare, realpath use pakad leta hai.
    """
    if alias not in WHITELISTED_PATH_ALIASES:
        return None  # Alias not in whitelist config -> reject

    base_path = os.path.realpath(WHITELISTED_PATH_ALIASES[alias])
    resolved_path = os.path.realpath(base_path)

    # Ensure resolved path stays inside base directory (prevents path traversal)
    if os.path.commonpath([resolved_path, base_path]) != base_path:
        return None  # Escaped whitelist root -> reject

    return resolved_path


def validate_and_authorize(intent: LumiIntent) -> Tuple[bool, str]:
    """
    Main SACL decision gate.
    Returns: (is_authorized, status_code/reason)
    Status codes: 'authorized', 'requires_confirmation', 'blocked: <reason>'
    """
    raw_dict = intent.model_dump()

    # Extract intent string safely
    intent_str = intent.intent.value if hasattr(intent.intent, "value") else str(intent.intent)

    # Rule 1: Check hard-blocked intent types
    if intent_str in BLOCKED_INTENTS:
        reason = f"Blocked: Intent '{intent_str}' is permanently restricted."
        append_audit_entry(raw_dict, False, "blocked", reason)
        return False, reason

    # Rule 2: Check unknown intent
    if intent.intent == IntentType.UNKNOWN:
        reason = "Blocked: Intent is unknown or unconfident."
        append_audit_entry(raw_dict, False, "blocked", reason)
        return False, reason

    # Rule 3: App whitelist check
    if intent.intent in (IntentType.OPEN_APP, IntentType.CLOSE_APP):
        if not intent.target or intent.target.lower() not in WHITELISTED_APPS:
            reason = f"Blocked: Application '{intent.target}' is not in whitelist."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Rule 4: Path alias check (if path specified)
    if intent.alias_path:
        resolved_path = resolve_and_verify_path(intent.alias_path)
        if not resolved_path:
            reason = f"Blocked: Path alias '{intent.alias_path}' is invalid or unverified."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Rule 5: Force confirmation check
    if (intent_str in FORCE_CONFIRM_INTENTS) or intent.requires_confirmation:
        reason = "Authorized: Requires spoken confirmation."
        append_audit_entry(raw_dict, True, "requires_confirmation", reason)
        return True, "requires_confirmation"

    # All checks passed
    reason = "Authorized: Intent passed all SACL security checks."
    append_audit_entry(raw_dict, True, "authorized", reason)
    return True, "authorized"