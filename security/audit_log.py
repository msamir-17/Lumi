import json
import os
from datetime import datetime
from typing import Dict, Any

AUDIT_LOG_PATH = os.path.join("logs", "lumi_audit.log")

def append_audit_entry(raw_intent: Dict[str, Any], is_authorized: bool, status_code: str, reason: str):
    """
    Appends authorization decisions to a local JSON-line audit log file.
    """
    os.makedirs("logs", exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "raw_intent": raw_intent,
        "is_authorized": is_authorized,
        "status_code": status_code,
        "reason": reason
    }
    
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")