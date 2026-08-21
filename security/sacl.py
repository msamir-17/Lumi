import os
import re
from typing import Tuple, Optional

from config.lumi_config import (
    WHITELISTED_PATH_ALIASES,
    WHITELISTED_APPS,
    ALLOWED_FILE_EXTENSIONS,
    ALLOWED_MEDIA_ACTIONS,
    MAX_FILENAME_LENGTH,
    MAX_SEARCH_FILES_SCANNED,
    MAX_SEARCH_DEPTH,
    FORCE_CONFIRM_INTENTS,
    BLOCKED_INTENTS
)
from core.lumi_schema import LumiIntent, IntentType
from security.audit_log import append_audit_entry

SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.]+$")

def resolve_and_verify_path(alias: str, filename: Optional[str] = None) -> str | None:
    if alias not in WHITELISTED_PATH_ALIASES:
        return None

    alias_root = os.path.realpath(WHITELISTED_PATH_ALIASES[alias])
    if filename is None:
        return alias_root

    # Defense 1: Sanitization
    if len(filename) > MAX_FILENAME_LENGTH or not SAFE_FILENAME_PATTERN.match(filename) or filename.startswith("."):
        return None

    # Defense 2: Extension Whitelist
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        return None

    # Defense 3: Containment
    candidate = os.path.realpath(os.path.join(alias_root, filename))
    if os.path.commonpath([candidate, alias_root]) != alias_root:
        return None

    return candidate


def bounded_file_search(alias: str, target_filename: str) -> str | None:
    """
    Searches for target_filename inside the whitelisted alias root.
    Bounded by MAX_SEARCH_FILES_SCANNED and MAX_SEARCH_DEPTH.
    Every match is re-verified via commonpath containment.
    """
    root = resolve_and_verify_path(alias)
    if root is None or not os.path.exists(root):
        return None

    scanned = 0
    clean_target = target_filename.strip().lower()

    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth >= MAX_SEARCH_DEPTH:
            dirnames[:] = []
            continue

        for fname in filenames:
            scanned += 1
            if scanned > MAX_SEARCH_FILES_SCANNED:
                return None  # Reached limit -> bail out safely

            if fname.lower() == clean_target:
                candidate = os.path.realpath(os.path.join(dirpath, fname))
                if os.path.commonpath([candidate, root]) == root:
                    return candidate

    return None


def validate_and_authorize(intent: LumiIntent) -> Tuple[bool, str]:
    raw_dict = intent.model_dump()
    intent_str = intent.intent.value if hasattr(intent.intent, "value") else str(intent.intent)

    if intent_str in BLOCKED_INTENTS:
        reason = f"Blocked: Intent '{intent_str}' is permanently restricted."
        append_audit_entry(raw_dict, False, "blocked", reason)
        return False, reason

    if intent.intent == IntentType.UNKNOWN:
        reason = "Blocked: Intent is unknown or unconfident."
        append_audit_entry(raw_dict, False, "blocked", reason)
        return False, reason

    # App Whitelist
    if intent.intent in (IntentType.OPEN_APP, IntentType.CLOSE_APP):
        if not intent.target or intent.target.lower() not in WHITELISTED_APPS:
            reason = f"Blocked: Application '{intent.target}' is not in whitelist."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Create File
    elif intent.intent == IntentType.CREATE_FILE:
        if not intent.alias_path or not intent.filename:
            reason = "Blocked: create_file requires both alias_path and filename."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason
        resolved = resolve_and_verify_path(intent.alias_path, intent.filename)
        if not resolved:
            reason = f"Blocked: Filename '{intent.filename}' or path '{intent.alias_path}' failed security checks."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Media Control
    elif intent.intent == IntentType.MEDIA_CONTROL:
        if not intent.media_action or intent.media_action not in ALLOWED_MEDIA_ACTIONS:
            reason = f"Blocked: Media action '{intent.media_action}' is not in whitelist."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason
        append_audit_entry(raw_dict, True, "authorized", "Authorized: Media control action.")
        return True, "authorized"

    # Search File
    elif intent.intent == IntentType.SEARCH_FILE:
        if not intent.alias_path or not intent.filename:
            reason = "Blocked: search_file requires both alias_path and filename."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason
        if intent.alias_path not in WHITELISTED_PATH_ALIASES:
            reason = f"Blocked: Path alias '{intent.alias_path}' is not whitelisted."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Generic Path Alias
    elif intent.alias_path:
        resolved_path = resolve_and_verify_path(intent.alias_path)
        if not resolved_path:
            reason = f"Blocked: Path alias '{intent.alias_path}' is invalid or unverified."
            append_audit_entry(raw_dict, False, "blocked", reason)
            return False, reason

    # Force Confirmation Check
    if (intent_str in FORCE_CONFIRM_INTENTS) or intent.requires_confirmation:
        reason = "Authorized: Requires spoken confirmation."
        append_audit_entry(raw_dict, True, "requires_confirmation", reason)
        return True, "requires_confirmation"

    append_audit_entry(raw_dict, True, "authorized", "Authorized: Intent passed all SACL checks.")
    return True, "authorized"