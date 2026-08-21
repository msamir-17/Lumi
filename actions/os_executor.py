import os
import subprocess
import webbrowser
import urllib.parse
import psutil
from typing import Optional

from config.lumi_config import WHITELISTED_APPS, WHITELISTED_PATH_ALIASES
from core.lumi_schema import LumiIntent, IntentType
from security.sacl import resolve_and_verify_path
from security.audit_log import append_audit_entry


def _build_youtube_search_url(query: str) -> str:
    """
    URL-encodes search query text safely into a direct YouTube search URL.
    """
    clean_query = query.strip() if query else "trending"
    safe_query = urllib.parse.quote_plus(clean_query)
    return f"https://www.youtube.com/results?search_query={safe_query}"


def _build_google_search_url(query: str) -> str:
    """
    URL-encodes search query text safely into a Google search URL.
    """
    clean_query = query.strip() if query else "news"
    safe_query = urllib.parse.quote_plus(clean_query)
    return f"https://www.google.com/search?q={safe_query}"


def _execute_create_file(resolved_path: str) -> str:
    """
    Creates an empty file at resolved_path and opens it in VS Code.
    Assumes resolved_path was ALREADY verified by SACL.
    """
    filename = os.path.basename(resolved_path)
    code_exe = WHITELISTED_APPS.get("code") or WHITELISTED_APPS.get("vscode")

    # If file already exists, don't overwrite it — just open it
    if os.path.exists(resolved_path):
        if code_exe and os.path.exists(code_exe):
            subprocess.Popen([code_exe, resolved_path])
        return f"File {filename} already exists. Opened it in VS Code."

    # Create safe empty file on disk
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write("")

    # Launch VS Code pointing directly to the new file
    if code_exe and os.path.exists(code_exe):
        subprocess.Popen([code_exe, resolved_path])

    return f"Created {filename} and opened it in VS Code."


def execute_intent(intent: LumiIntent) -> str:
    """
    Executes authorized intents on the Windows OS.
    Returns human-friendly response string for TTS voice engine.
    """
    intent_val = intent.intent.value if hasattr(intent.intent, "value") else str(intent.intent)
    raw_dict = intent.model_dump()

    try:
        # Action 1: Open Application
        if intent_val == "open_app":
            app_key = (intent.target or "").strip().lower()
            if app_key in WHITELISTED_APPS:
                app_path = WHITELISTED_APPS[app_key]
                if not os.path.exists(app_path):
                    msg = f"Executable for {intent.target} not found on disk."
                    append_audit_entry(raw_dict, False, "not_found", msg)
                    return msg

                if app_key == "chrome":
                    subprocess.Popen([app_path, "--profile-directory=Default"])
                else:
                    subprocess.Popen([app_path])

                msg = f"Opened {intent.target}."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return f"Application {intent.target} is not in whitelist."

        # Action 2: Close Application
        elif intent_val == "close_app":
            app_key = (intent.target or "").strip().lower()
            if app_key in WHITELISTED_APPS:
                exe_name = os.path.basename(WHITELISTED_APPS[app_key]).lower()
                terminated = False
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and proc.info['name'].lower() == exe_name:
                        proc.terminate()
                        terminated = True
                if terminated:
                    msg = f"Closed {intent.target}."
                    append_audit_entry(raw_dict, True, "executed", msg)
                    return msg
                return f"{intent.target} was not running."
            return f"Application {intent.target} is not in whitelist."

        # Action 3: Create File
        elif intent_val == "create_file":
            alias = intent.alias_path or "Desktop"
            fname = intent.filename or "notes.txt"
            resolved_file = resolve_and_verify_path(alias, fname)
            if resolved_file:
                msg = _execute_create_file(resolved_file)
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return "Failed to verify file path authorization."

        # Action 4: Create Folder
        elif intent_val == "create_folder":
            folder_alias = intent.alias_path or "Desktop"
            folder_name = intent.target or "New_Folder"
            parent_dir = resolve_and_verify_path(folder_alias)
            if parent_dir:
                new_folder_path = os.path.join(parent_dir, folder_name)
                os.makedirs(new_folder_path, exist_ok=True)
                msg = f"Created folder {folder_name} in {folder_alias}."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return "Failed to resolve folder path."

        # Action 5: Search YouTube
        elif intent_val == "search_youtube":
            search_text = (intent.query or intent.target or "").strip()
            if not search_text:
                search_text = "trending music"
            url = _build_youtube_search_url(search_text)
            webbrowser.open(url)
            msg = f"Searching YouTube for {search_text}."
            append_audit_entry(raw_dict, True, "executed", msg)
            return msg

        # Action 6: Search Web / Open URL
        elif intent_val in ("search_web", "open_url"):
            query_str = (intent.query or intent.target or "").strip()
            if not query_str:
                query_str = "latest news"

            if query_str.startswith("http://") or query_str.startswith("https://"):
                webbrowser.open(query_str)
            else:
                url = _build_google_search_url(query_str)
                webbrowser.open(url)

            msg = f"Searching web for {query_str}."
            append_audit_entry(raw_dict, True, "executed", msg)
            return msg

        # Action 7: Open Folder
        elif intent_val == "open_file":
            alias = intent.alias_path or "Downloads"
            target_dir = resolve_and_verify_path(alias)
            if target_dir and os.path.exists(target_dir):
                os.startfile(target_dir)
                msg = f"Opened {alias}."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return f"Could not open {alias}."

        return "Command was not recognized or permitted."

    except Exception as e:
        error_msg = f"Execution error: {str(e)}"
        append_audit_entry(raw_dict, False, "execution_error", error_msg)
        return f"Error executing command: {str(e)}"

    
# This file receives SACL-authorized intents and maps them to real Windows actions using subprocess, os, psutil, and webbrowser.