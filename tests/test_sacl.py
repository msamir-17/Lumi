import pytest
from core.lumi_schema import LumiIntent, IntentType
from security.sacl import validate_and_authorize

def test_valid_app_open():
    intent = LumiIntent(intent=IntentType.OPEN_APP, target="chrome", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is True
    assert status == "authorized"

def test_unwhitelisted_app_blocked():
    intent = LumiIntent(intent=IntentType.OPEN_APP, target="unknown_app_xyz", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "not in whitelist" in status

def test_blocked_intent():
    # Attempting a blocked intent directly
    intent = LumiIntent(intent=IntentType.UNKNOWN, confidence=0.0)
    intent.intent = "delete_file"  # Simulating blocked intent
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "restricted" in status or "blocked" in status

def test_force_confirmation_intent():
    intent = LumiIntent(intent=IntentType.CREATE_FOLDER, target="new_folder", alias_path="Desktop", confidence=0.9)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is True
    assert status == "requires_confirmation"

def test_invalid_path_alias_blocked():
    intent = LumiIntent(intent=IntentType.OPEN_FILE, target="test.txt", alias_path="SecretFolder", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "invalid or unverified" in status

def test_create_file_valid():
    intent = LumiIntent(intent=IntentType.CREATE_FILE, filename="notes.txt", alias_path="Desktop", confidence=0.95)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is True
    assert status == "requires_confirmation"

def test_create_file_path_traversal_rejected():
    intent = LumiIntent(intent=IntentType.CREATE_FILE, filename="../../evil.py", alias_path="Desktop", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "failed security checks" in status

def test_create_file_disallowed_extension_rejected():
    intent = LumiIntent(intent=IntentType.CREATE_FILE, filename="script.exe", alias_path="Desktop", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "failed security checks" in status

def test_create_file_leading_dot_rejected():
    intent = LumiIntent(intent=IntentType.CREATE_FILE, filename=".hidden.py", alias_path="Desktop", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "failed security checks" in status

def test_core_apps_whitelist():
    for app in ["explorer", "notepad", "calculator", "taskmanager"]:
        intent = LumiIntent(intent=IntentType.OPEN_APP, target=app, confidence=1.0)
        is_auth, status = validate_and_authorize(intent)
        assert is_auth is True
        assert status == "authorized"

def test_media_control_valid():
    intent = LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="play_pause", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is True
    assert status == "authorized"

def test_media_control_invalid_rejected():
    intent = LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="eject_cd", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is False
    assert "not in whitelist" in status

def test_search_file_valid():
    intent = LumiIntent(intent=IntentType.SEARCH_FILE, filename="test.txt", alias_path="Desktop", confidence=1.0)
    is_auth, status = validate_and_authorize(intent)
    assert is_auth is True
    assert status == "authorized"