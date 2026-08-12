import os
import subprocess
import webbrowser
import psutil
# from typing import str

from config.lumi_config import WHITELISTED_APPS, WHITELISTED_PATH_ALIASES
from core.lumi_schema import LumiIntent, IntentType
from security.sacl import resolve_and_verify_path
from security.audit_log import append_audit_entry

def execute_intent(intent: LumiIntent) -> str:
    """
    Executes authorized intents on the Windows operating system.
    Returns a human-friendly response string for the TTS voice engine.
    Assumes intent has ALREADY passed SACL authorization checks.
    """
    intent_type = intent.intent
    raw_dict = intent.model_dump()

    try:
        # Action 1: Open Application
        if intent_type == IntentType.OPEN_APP:
            app_key = intent.target.lower() if intent.target else ""
            if app_key in WHITELISTED_APPS:
                app_path = WHITELISTED_APPS[app_key]
                
                # If opening Chrome, pass default profile flag to bypass profile picker
                if app_key == "chrome":
                    subprocess.Popen([app_path, "--profile-directory=Default"])
                else:
                    subprocess.Popen([app_path])

                msg = f"Opened {intent.target}."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg

        # Action 2: Close Application
        elif intent_type == IntentType.CLOSE_APP:
            app_key = intent.target.lower() if intent.target else ""
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

        # Action 3: Create Folder
        elif intent_type == IntentType.CREATE_FOLDER:
            folder_alias = intent.alias_path or "Desktop"
            parent_dir = resolve_and_verify_path(folder_alias)
            if parent_dir and intent.target:
                new_folder_path = os.path.join(parent_dir, intent.target)
                os.makedirs(new_folder_path, exist_ok=True)
                msg = f"Created folder {intent.target} in {folder_alias}."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return "Failed to resolve folder path."

        # Action 4: Open File or Folder
        elif intent_type == IntentType.OPEN_FILE:
            alias = intent.alias_path or "Downloads"
            target_dir = resolve_and_verify_path(alias)
            if target_dir:
                os.startfile(target_dir)  # Native Windows explorer open
                msg = f"Opened {alias}."
                append_audit_entry(raw_dict, True, "executed", msg)
                return msg
            return f"Could not open {alias}."

        # Action 5: Search Web / Open URL
        elif intent_type in (IntentType.SEARCH_WEB, IntentType.OPEN_URL):
            query_str = intent.query or intent.target or ""
            if query_str.startswith("http://") or query_str.startswith("https://"):
                webbrowser.open(query_str)
            else:
                webbrowser.open(f"https://www.google.com/search?q={query_str}")
            msg = f"Searching web for {query_str}."
            append_audit_entry(raw_dict, True, "executed", msg)
            return msg

        # Fallback for Unknown or unsupported
        return "Command was not recognized or permitted."

    except Exception as e:
        error_msg = f"Execution error: {str(e)}"
        append_audit_entry(raw_dict, False, "execution_error", error_msg)
        return "An error occurred while executing the command."

# This file receives SACL-authorized intents and maps them to real Windows actions using subprocess, os, psutil, and webbrowser.