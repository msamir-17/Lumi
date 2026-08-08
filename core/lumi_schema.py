   

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
    OPEN_APP = "open_app"              # Open an application (e.g., Chrome, VS Code)
    CLOSE_APP = "close_app"            # Close an application
    OPEN_FILE = "open_file"            # Open a file inside a whitelisted folder
    CREATE_FOLDER = "create_folder"    # Create a new folder
    OPEN_URL = "open_url"              # Open a specific website URL
    SEARCH_WEB = "search_web"          # Search the web on Google
    UNKNOWN = "unknown"                # Fallback if command is nonsense or unclear


class LumiIntent(BaseModel):
    """
    This is the Pydantic model enforcing the JSON structure.
    """
    intent: IntentType
    
    # target: Name of the app (e.g. "chrome") or file name
    target: Optional[str] = None       
    
    # alias_path: NEVER a raw Windows path (e.g., C:\Users\...).
    # ONLY whitelisted folder alias names like "Desktop", "Downloads".
    alias_path: Optional[str] = None   
    
    # query: Search query string for web searches
    query: Optional[str] = None        
    
    # confidence: Float between 0.0 and 1.0 indicating model confidence
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # requires_confirmation: Set True if the action creates/modifies files
    requires_confirmation: bool = False

    