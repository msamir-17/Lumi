# This file handles calling Ollama, validating the JSON with Pydantic, and retrying if Llama makes a formatting error


import json
import requests
from typing import Tuple ,Optional
from pydantic import ValidationError
import re
from core.lumi_schema import LumiIntent, IntentType
from config.lumi_config import ALLOWED_MEDIA_ACTIONS
from core.system_prompt import LUMI_SYSTEM_PROMPT

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"


def fast_path_router(text: str) -> Optional[LumiIntent]:
    """
    Deterministic Python Pre-Router.
    Bypasses LLM for unambiguous commands (YouTube, Web search, Media keys).
    Saves ~1.5s latency and eliminates LLM misclassification.
    """
    clean = text.strip()
    lower = clean.lower()

    # Rule 1: YouTube Searches ("search X on youtube", "play X on youtube", "youtube X")
    yt_patterns = [
        r"^search\s+(?:for\s+)?(.+?)\s+on\s+youtube$",
        r"^search\s+youtube\s+for\s+(.+)$",
        r"^play\s+(.+?)\s+on\s+youtube$",
        r"^play\s+(.+)$",
        r"^youtube\s+(.+)$",
    ]
    for pattern in yt_patterns:
        match = re.match(pattern, lower)
        if match:
            query = match.group(1).strip()
            # If query is not a bare media command like "music" or "song"
            if query and query not in ("music", "song", "audio"):
                return LumiIntent(intent=IntentType.SEARCH_YOUTUBE, query=query, confidence=1.0)

    # Rule 2: Web / Google Searches ("search google for X", "search X on web", "google X")
    web_patterns = [
        r"^search\s+google\s+for\s+(.+)$",
        r"^search\s+(?:for\s+)?(.+?)\s+on\s+(?:google|the\s+web|web)$",
        r"^google\s+(.+)$",
    ]
    for pattern in web_patterns:
        match = re.match(pattern, lower)
        if match:
            return LumiIntent(intent=IntentType.SEARCH_WEB, query=match.group(1).strip(), confidence=1.0)

    # Rule 3: Media Control Shortcuts
    if lower in ("pause", "pause music", "pause song", "stop music", "resume", "unpause", "play music"):
        return LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="play_pause", confidence=1.0)
    if lower in ("volume up", "increase volume", "louder"):
        return LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="volume_up", confidence=1.0)
    if lower in ("volume down", "decrease volume", "quieter"):
        return LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="volume_down", confidence=1.0)
    if lower in ("mute", "silence", "unmute"):
        return LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="mute", confidence=1.0)
    if lower in ("next song", "skip track", "next track"):
        return LumiIntent(intent=IntentType.MEDIA_CONTROL, media_action="next_track", confidence=1.0)

    # No fast-path match -> pass to LLM
    return None

def get_validated_intent(user_text: str, max_retries: int = 2) -> LumiIntent:
    """
    Sends user text to Llama, validates output with LumiIntent schema.
    If validation fails, re-prompts once with the error message.
    """

        # Check deterministic fast-path pre-router first
    fast_intent = fast_path_router(user_text)
    if fast_intent:
        print(f"[Fast-Path Router] Matched deterministic intent: {fast_intent.intent.value}")
        return fast_intent
    
    messages = [
        {"role": "system", "content": LUMI_SYSTEM_PROMPT},
        {"role": "user", "content": user_text}
    ]

    for attempt in range(max_retries):
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {
                "num_ctx": 512,
                "temperature": 0.1
            }
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=20)
            response.raise_for_status()
            
            raw_text = response.json().get("message", {}).get("content", "").strip()
            
            # Step 1: Parse JSON string
            json_data = json.loads(raw_text)
            
            # Step 2: Validate against Pydantic schema
            validated_intent = LumiIntent(**json_data)
            return validated_intent

        except (json.JSONDecodeError, ValidationError) as err:
            # If validation fails, append the error and retry once with feedback
            print(f"[LLM Engine] Validation attempt {attempt + 1} failed: {err}")
            messages.append({"role": "assistant", "content": raw_text if 'raw_text' in locals() else ""})
            messages.append({
                "role": "user", 
                "content": f"Your output failed validation: {err}. Respond again with ONLY valid JSON matching the schema."
            })
        except Exception as req_err:
            print(f"[LLM Engine] Request error: {req_err}")
            break

    # Safe Fallback if all retries fail
    print("[LLM Engine] Failed to get valid intent after retries. Returning safe UNKNOWN fallback.")
    return LumiIntent(intent=IntentType.UNKNOWN, confidence=0.0)