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

# Line-by-Line Explanation:
# ---------------------------------------------------------------------
# These are the ONLY folders LUMI is allowed to access.
# Replace <username> with your actual Windows username (or use os.path.expanduser).

USER_HOME = os.path.expanduser("aamir")

WHITELISTED_PATH_ALIASES = {
    "Desktop": os.path.join(USER_HOME, "Desktop"),
    "Downloads": os.path.join(USER_HOME, "Downloads"),
    "ProjectFolder": os.path.join(USER_HOME, "Projects"),
    "Documents": os.path.join(USER_HOME, "Documents"),
}

# Whitelisted Applications (Full absolute paths to .exe)
WHITELISTED_APPS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vscode": os.path.join(USER_HOME, r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
    "code": os.path.join(USER_HOME, r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
}

# Intents that ALWAYS require a spoken "Yes/No" confirmation from the user
FORCE_CONFIRM_INTENTS = {"create_folder"}

# Intents that are hard-blocked entirely in v1 - zero path to execution
BLOCKED_INTENTS = {
    "delete_file", 
    "delete_folder", 
    "move_file", 
    "format_drive", 
    "run_shell"
}