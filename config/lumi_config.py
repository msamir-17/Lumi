# What is SACL? (System Access Control Layer & Security Sandbox)!
# Even if Llama gives us a valid JSON object, we NEVER trust the AI directly.
# SACL is a strict, deterministic Python firewall. It checks the JSON against hardcoded rules before anything is allowed to execute on your Windows machine.

# [ LumiIntent JSON from LLM ]
#             ↓
#       [ SACL Firewall ]
#   - Is intent blocked?        → REJECT ❌
#   - Is app in whitelist?      → REJECT ❌
#   - Is path outside root?     → REJECT ❌ (Path Traversal Protection)
#   - Requires confirmation?   → Flag for Voice "Yes/No" Confirmation ⚠️
#   - Passed all checks?       → AUTHORIZE ✅
#             ↓
#    [ Append to Audit Log ]

import os

# 1. Properly expand user home directory (~ expands to C:\Users\<username>)
USER_HOME = os.path.expanduser("~")

WHITELISTED_PATH_ALIASES = {
    "Desktop": os.path.join(USER_HOME, "Desktop"),
    "Downloads": os.path.join(USER_HOME, "Downloads"),
    "ProjectFolder": os.path.join(USER_HOME, "Projects"),
    "Documents": os.path.join(USER_HOME, "Documents"),
}

# Find dynamic VS Code executable path in AppData or Program Files
default_vscode_path = os.path.join(USER_HOME, r"AppData\Local\Programs\Microsoft VS Code\Code.exe")
if not os.path.exists(default_vscode_path):
    default_vscode_path = r"C:\Program Files\Microsoft VS Code\Code.exe"

# Whitelisted Applications (Full absolute paths to .exe)
WHITELISTED_APPS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vscode": default_vscode_path,
    "code": default_vscode_path,
}

# Only these extensions can ever be created on disk.
# Executables/scripts (.exe, .bat, .ps1, .dll, .lnk) are strictly forbidden.
ALLOWED_FILE_EXTENSIONS = {".py", ".txt", ".html", ".md", ".json", ".css", ".js"}

# Maximum filename length (defensive limit)
MAX_FILENAME_LENGTH = 100

# Intents that ALWAYS require a spoken "Yes/No" confirmation from the user
FORCE_CONFIRM_INTENTS = {"create_folder", "create_file", "ui_action"}

# Intents that are hard-blocked entirely in v1 - zero path to execution
BLOCKED_INTENTS = {
    "delete_file", 
    "delete_folder", 
    "move_file", 
    "format_drive", 
    "run_shell"
}

# Whitelisted UI actions for pywinauto (App, Action) pairs
WHITELISTED_UI_ACTIONS = {
    ("vscode", "new_file"): {"menu_path": ["File", "New File"]},
    ("chrome", "new_tab"): {"shortcut": "^t"},
}