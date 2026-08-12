import os
import re
from typing import Tuple, Optional

from config.lumi_config import (
    WHITELISTED_PATH_ALIASES,
    WHITELISTED_APPS,
    ALLOWED_FILE_EXTENSIONS,
    MAX_FILENAME_LENGTH,
    FORCE_CONFIRM_INTENTS,
    BLOCKED_INTENTS
)
from core.lumi_schema import LumiIntent, IntentType
from security.audit_log import append_audit_entry

# Safe filename regex: Only alphanumeric, underscores, hyphens, and single dots allowed
SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.]+$")

def resolve_and_verify_path(alias: str, filename: Optional[str] = None) -> str | None:
    """
    Takes a whitelisted alias and an optional filename, resolves the combined path,
    and enforces 3 defense-in-depth security layers against path traversal:
    1. Filename sanitization (regex, length check, no leading dot)
    2. File extension whitelist check
    3. Combined path containment check (realpath + commonpath)
    """
    if alias not in WHITELISTED_PATH_ALIASES:
        return None

    alias_root = os.path.realpath(WHITELISTED_PATH_ALIASES[alias])

    if filename is None:
        return alias_root

    # --- Defense Layer 1: Filename Sanitization ---
    if len(filename) > MAX_FILENAME_LENGTH:
        return None
    if not SAFE_FILENAME_PATTERN.match(filename):
        return None  # Rejects "..", "/", "\\", ":", null bytes, etc.
    if filename.startswith("."):
        return None  # No hidden files or ".." disguised with a leading dot

    # --- Defense Layer 2: Extension Whitelist ---
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        return None  # Rejects disallowed file types (.exe, .bat, .ps1, etc.)

    # --- Defense Layer 3: Combined Path Containment Check ---
    candidate = os.path.realpath(os.path.join(alias_root, filename))
    if os.path.commonpath([candidate, alias_root]) != alias_root:
        return None  # Escaped whitelist root -> reject traversal attempt

    return candidate


def validate_and_authorize(intent: LumiIntent) -> Tuple[bool, str]:
    """
    Main SACL decision gate.
    Returns: (is_authorized, status_code/reason)
    """
    raw_dict = intent.model_dump()
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

    # Rule 4: Create File Validation (Alias + Filename checks)
    if intent.intent == IntentType.CREATE_FILE:
        if not intent.alias_path or not intent.filename:
            reason = "Blocked: 'create_file' requires both 'alias_path' and 'filename'."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason
        
        resolved_file_path = resolve_and_verify_path(intent.alias_path, intent.filename)
        if not resolved_file_path:
            reason = f"Blocked: Filename '{intent.filename}' or path '{intent.alias_path}' failed security checks."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Rule 5: Generic Path alias check
    elif intent.alias_path:
        resolved_path = resolve_and_verify_path(intent.alias_path)
        if not resolved_path:
            reason = f"Blocked: Path alias '{intent.alias_path}' is invalid or unverified."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Rule 6: Force confirmation check
    if (intent_str in FORCE_CONFIRM_INTENTS) or intent.requires_confirmation:
        reason = "Authorized: Requires spoken confirmation."
        append_audit_entry(raw_dict, True, "requires_confirmation", reason)
        return True, "requires_confirmation"

    # All checks passed
    reason = "Authorized: Intent passed all SACL security checks."
    append_audit_entry(raw_dict, True, "authorized", reason)
    return True, "authorized"