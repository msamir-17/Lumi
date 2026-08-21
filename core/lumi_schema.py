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


# Line-by-Line Explanation:
# ---------------------------------------------------------------------
# IntentType is an Enum (a fixed list of allowed choices).
# Llama can ONLY pick one of these exact values. If it invents anything else,
# Pydantic will reject it immediately.
from pydantic import BaseModel, field_validator, model_validator, ValidationInfo
from typing import Optional, Any
from enum import Enum

class IntentType(str, Enum):
    OPEN_APP = 'open_app'
    CLOSE_APP = 'close_app'
    OPEN_FILE = 'open_file'
    SEARCH_FILE = 'search_file'
    CREATE_FOLDER = 'create_folder'
    CREATE_FILE = 'create_file'
    MEDIA_CONTROL = 'media_control'
    OPEN_URL = 'open_url'
    SEARCH_WEB = 'search_web'
    SEARCH_YOUTUBE = 'search_youtube'
    UNKNOWN = 'unknown'

class LumiIntent(BaseModel):
    intent: IntentType
    target: Optional[str] = None
    alias_path: Optional[str] = None
    filename: Optional[str] = None
    query: Optional[str] = None           # <-- ADDED THIS!
    media_action: Optional[str] = None
    confidence: float = 1.0
    requires_confirmation: bool = False

    @field_validator('intent', mode='before')
    @classmethod
    def structural_intent_guard(cls, v: Any) -> Any:
        if not isinstance(v, str):
            return v
        
        normalized = v.lower().strip()
        synonym_map = {
            'play_music': 'search_youtube',
            'play_song': 'search_youtube',
            'youtube_search': 'search_youtube',
            'find_file': 'search_file',
            'search_document': 'search_file',
            'make_file': 'create_file',
            'new_file': 'create_file',
            'make_folder': 'create_folder',
            'new_folder': 'create_folder',
            'web_search': 'search_web'
        }
        return synonym_map.get(normalized, normalized)

    @model_validator(mode='before')
    @classmethod
    def auto_redirect_youtube_app(cls, data: Any) -> Any:
        if isinstance(data, dict):
            intent = str(data.get('intent', '')).lower()
            target = str(data.get('target', '')).lower()
            query = str(data.get('query', '')).lower()

            # If search_file was mistakenly chosen for YouTube search
            if intent in ('open_app', 'search_file') and ('youtube' in target or 'youtube' in query or not data.get('alias_path')):
                if 'youtube' in target or 'youtube' in query:
                    data['intent'] = 'search_youtube'
                    if not data.get('query'):
                        data['query'] = data.get('target', 'trending music').replace('youtube', '').strip()
        return data