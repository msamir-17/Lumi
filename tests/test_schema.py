from core.llm_engine import get_validated_intent
from core.lumi_schema import IntentType
def run_phase2_tests():
    test_inputs = [
        "open chrome",
        "create a new folder called project X on desktop",
        "search the web for weather today",
        "delete all system files from C drive",  # Ambiguous/Dangerous -> should yield unknown
        "open downloads folder"
    ]

    print("==================================================")
    print(" TESTING PHASE 2: SCHEMA VALIDATION & RETRY ENGINE")
    print("==================================================\n")

    for text in test_inputs:
        print(f"User Said : '{text}'")
        intent_obj = get_validated_intent(text)
        print(f"Parsed    : {intent_obj}")
        print(f"Intent    : {intent_obj.intent.value}")
        print(f"Alias Path: {intent_obj.alias_path}")
        print("-" * 50)

if __name__ == "__main__":
    run_phase2_tests()