   

        # [ Spoken Text: "open chrome" ]
        #             ↓
        #     [ Llama 3.2 3B ]
        #             ↓
        # [ Pydantic Schema Validation ] 
        # - Valid?   → Return LumiIntent object
        # - Invalid? → Retry 1 time with error message
        # - Failed?  → Fallback safely to UNKNOWN intent

# Why do we use named alias_path instead of raw paths?
# We tell Llama it only knows 4 folder names: Desktop, Downloads, ProjectFolder, Documents.
# Llama is never allowed to output C:\Windows\System32 or raw file paths. This makes it impossible for Llama to attack system files!


from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

# Line-by-Line Explanation:
# ---------------------------------------------------------------------
# IntentType is an Enum (a fixed list of allowed choices).
# Llama can ONLY pick one of these exact values. If it invents anything else,
# Pydantic will reject it immediately.

class IntentType(str, Enum):
    OPEN_APP = "open_app"              # Open an application
    CLOSE_APP = "close_app"            # Close an application
    OPEN_FILE = "open_file"            # Open a file inside a whitelisted folder
    CREATE_FOLDER = "create_folder"    # Create a new folder
    CREATE_FILE = "create_file"        # Create a new file safely on disk
    OPEN_URL = "open_url"              # Open a specific URL
    SEARCH_WEB = "search_web"          # Search Google
    SEARCH_YOUTUBE = "search_youtube"  # Search YouTube directly
    UI_ACTION = "ui_action"            # Safe in-app UI automation via pywinauto
    UNKNOWN = "unknown"                # Fallback if command is unconfident or restricted


class LumiIntent(BaseModel):
    intent: IntentType
    target: Optional[str] = None       # Name of app or folder
    alias_path: Optional[str] = None   # Whitelisted folder alias ("Desktop", "Downloads", etc.)
    filename: Optional[str] = None     # Filename for create_file (e.g. "script.py")
    query: Optional[str] = None        # Search query string
    app: Optional[str] = None          # App name for UI automation ("vscode", "chrome")
    action: Optional[str] = None       # Pre-approved UI action name ("new_file", "new_tab")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    requires_confirmation: bool = False