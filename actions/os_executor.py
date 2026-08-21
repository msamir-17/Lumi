import os
import subprocess
import webbrowser
import urllib.parse
import psutil
from typing import Optional

from config.lumi_config import WHITELISTED_APPS, WHITELISTED_PATH_ALIASES
from core.lumi_schema import LumiIntent, IntentType
from security.sacl import resolve_and_verify_path, bounded_file_search
from security.audit_log import append_audit_entry
from actions.media_control import send_media_key


def _build_youtube_search_url(query: str) -> str:
    safe_query = urllib.parse.quote_plus(query.strip() if query else "trending")
    return f"https://www.youtube.com/results?search_query={safe_query}"


def _build_google_search_url(query: str) -> str:
    safe_query = urllib.parse.quote_plus(query.strip() if query else "news")
    return f"https://www.google.com/search?q={safe_query}"


def _execute_open_folder(resolved_path: str) -> str:
    """
    Opens folder in Windows File Explorer using list arguments (never shell strings).
    """
    if os.path.exists(resolved_path):
        subprocess.Popen(["explorer.exe", resolved_path])
        return f"Opened {os.path.basename(resolved_path)} in File Explorer."
    return "Target folder does not exist on disk."


def _execute_create_file(resolved_path: str) -> str:
    filename = os.path.basename(resolved_path)
    code_exe = WHITELISTED_APPS.get("code") or WHITELISTED_APPS.get("vscode")

    if os.path.exists(resolved_path):
        if code_exe and os.path.exists(code_exe):
            subprocess.Popen([code_exe, resolved_path])
        return f"File {filename} already exists. Opened it in VS Code."

    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write("")

    if code_exe and os.path.exists(code_exe):
        subprocess.Popen([code_exe, resolved_path])

    return f"Created {filename} and opened it in VS Code."


def _execute_search_file(alias_path: str, filename: str) -> str:
    """
    Searches for a file within alias_path.
    If found: highlights it in File Explorer.
    If NOT found (Safe 'Not Found' condition): explicitly informs the user
    and falls back to web search (with complete audit trail).
    """
    result = bounded_file_search(alias_path, filename)
    
    if result is not None:
        subprocess.Popen(["explorer.exe", f"/select,{result}"])
        return f"Found {filename} in {alias_path}, showing it in File Explorer."

    # Explicit Fallback for 'Not Found'
    fallback_url = _build_google_search_url(filename)
    webbrowser.open(fallback_url)
    
    msg = f"Could not find '{filename}' on your {alias_path} — searching the web instead."
    append_audit_entry({"search_file_fallback": filename, "alias": alias_path}, True, "not_found_fallback", msg)
    return msg


def execute_intent(intent: LumiIntent) -> str:
    intent_val = intent.intent.value if hasattr(intent.intent, "value") else str(intent.intent)
    raw_dict = intent.model_dump()

    try:
        # 1. Open App
        if intent_val == "open_app":
            app_key = (intent.target or "").strip().lower()
            if app_key in WHITELISTED_APPS:
                app_path = WHITELISTED_APPS[app_key]
                if not os.path.exists(app_path):
                    msg = f"Application {intent.target} not found on disk."
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

        # 2. Close App
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

        # 3. Media Control (New!)
        elif intent_val == "media_control":
            action = intent.media_action or "play_pause"
            success = send_media_key(action)
            if success:
                msg = f"Media command {action.replace('_', ' ')} executed."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return "Failed to send media key."

        # 4. Search File (New!)
        elif intent_val == "search_file":
            alias = intent.alias_path or "Desktop"
            fname = intent.filename or intent.target or ""
            msg = _execute_search_file(alias, fname)
            append_audit_entry(raw_dict, True, "executed", msg)
            return msg

        # 5. Open Folder
        elif intent_val == "open_file":
            alias = intent.alias_path or "Downloads"
            target_dir = resolve_and_verify_path(alias)
            if target_dir:
                msg = _execute_open_folder(target_dir)
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return f"Could not open {alias}."

        # 6. Create File
        elif intent_val == "create_file":
            alias = intent.alias_path or "Desktop"
            fname = intent.filename or "notes.txt"
            resolved_file = resolve_and_verify_path(alias, fname)
            if resolved_file:
                msg = _execute_create_file(resolved_file)
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return "Failed to verify file path authorization."

        # 7. Create Folder
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

        # 8. Search YouTube
        elif intent_val == "search_youtube":
            search_text = (intent.query or intent.target or "trending music").strip()
            url = _build_youtube_search_url(search_text)
            webbrowser.open(url)
            msg = f"Searching YouTube for {search_text}."
            append_audit_entry(raw_dict, True, "executed", msg)
            return msg

        # 9. Search Web
        elif intent_val in ("search_web", "open_url"):
            query_str = (intent.query or intent.target or "news").strip()
            if query_str.startswith("http://") or query_str.startswith("https://"):
                webbrowser.open(query_str)
            else:
                url = _build_google_search_url(query_str)
                webbrowser.open(url)
            msg = f"Searching web for {query_str}."
            append_audit_entry(raw_dict, True, "executed", msg)
            return msg

        return "Command was not recognized or permitted."

    except Exception as e:
        error_msg = f"Execution error: {str(e)}"
        append_audit_entry(raw_dict, False, "execution_error", error_msg)
        return f"Error executing command: {str(e)}"

# NEXT STEP IS TO IMPLEMENT THE OTHERS FEATURES LIKE PLAY PAUSE SEARCH ON YT ETC 
    
# This file receives SACL-authorized intents and maps them to real Windows actions using subprocess, os, psutil, and webbrowser.