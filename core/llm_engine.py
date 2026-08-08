# This file handles calling Ollama, validating the JSON with Pydantic, and retrying if Llama makes a formatting error


import json
import requests
from typing import Tuple
from pydantic import ValidationError

from core.lumi_schema import LumiIntent, IntentType
from core.system_prompt import LUMI_SYSTEM_PROMPT

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"

def get_validated_intent(user_text: str, max_retries: int = 2) -> LumiIntent:
    """
    Sends user text to Llama, validates output with LumiIntent schema.
    If validation fails, re-prompts once with the error message.
    """
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