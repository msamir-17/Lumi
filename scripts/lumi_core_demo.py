import sys
import os

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.llm_engine import get_validated_intent
from security.sacl import validate_and_authorize

def main():
    print("==================================================")
    print("   LUMI CORE DEMO — Text-Only Security Pipeline   ")
    print("   (Phases 1–3: Brain + Schema + SACL Firewall)   ")
    print("==================================================")
    print("Type your commands below (type 'exit' or 'quit' to stop):\n")

    while True:
        try:
            user_input = input("\nUser > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Exiting LUMI Core Demo. Goodbye!")
                break

            print("[1/3] Converting text to validated JSON intent (LLM)...")
            intent = get_validated_intent(user_input)
            print(f"      Parsed Intent: {intent}")

            print("[2/3] Checking SACL Security Sandbox & Whitelists...")
            is_authorized, status_msg = validate_and_authorize(intent)

            print("[3/3] Final Decision:")
            if not is_authorized:
                print(f"      🛑 BLOCKED: {status_msg}")
            elif status_msg == "requires_confirmation":
                print(f"      ⚠️ WOULD EXECUTE (REQUIRES SPOKEN CONFIRMATION): {intent.intent.value} on '{intent.target or intent.alias_path}'")
            else:
                print(f"      ✅ WOULD EXECUTE: {intent.intent.value} on '{intent.target or intent.alias_path}'")

        except KeyboardInterrupt:
            print("\nExiting LUMI Core Demo. Goodbye!")
            break
        except Exception as e:
            print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()


# How this script works:
# You type a command in terminal (e.g., "open chrome", "create a folder called notes on desktop", "delete C drive").
# Phase 2 (get_validated_intent): Llama converts your command to a structured LumiIntent Pydantic object.
# Phase 3 (validate_and_authorize): SACL checks the intent against safe whitelists and path rules.
# Audit Log: Saves the full decision details to logs/lumi_audit.log.
# Output: Displays whether the system would execute, require confirmation, or block the action.