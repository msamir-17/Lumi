import json
import time
import requests
from typing import Dict, Any, List

# Switched to /api/chat endpoint for Llama 3.2 Instruct model
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"

BENCHMARK_PROMPTS: List[str] = [
    "open chrome and go to gmail",
    "create a new folder called project X on desktop",
    "close vs code",
    "search the web for python tutorials",
    "open downloads folder",
    "create folder named budget in documents",
    "open chrome",
    "search for weather today",
    "close chrome",
    "open desktop"
]

def warm_up_model():
    print("Warming up Llama 3.2 in RAM...")
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False
    }
    try:
        requests.post(OLLAMA_URL, json=payload, timeout=15)
        print("Model loaded into RAM successfully!\n")
    except Exception as e:
        print(f"Warmup warning: {e}\n")

def benchmark_single_prompt(prompt: str) -> Dict[str, Any]:
    system_instruction = (
        "You are LUMI automation assistant. "
        "Respond ONLY with a valid JSON object. No explanation, no markdown. "
        "Example: {\"intent\": \"open_app\", \"target\": \"chrome\"}"
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "format": "json",  # Ollama JSON mode
        "stream": False,
        "options": {
            "num_ctx": 512,
            "num_thread": 4,  # Capped at 4 P-cores for i5-12500H
            "temperature": 0.1
        }
    }

    start_time = time.perf_counter()
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        response.raise_for_status()
        end_time = time.perf_counter()
        
        latency = end_time - start_time
        res_data = response.json()
        
        # /api/chat returns message.content
        raw_output = res_data.get("message", {}).get("content", "").strip()
        
        is_valid_json = True
        try:
            json.loads(raw_output)
        except json.JSONDecodeError:
            is_valid_json = False

        return {
            "prompt": prompt, 
            "latency": latency, 
            "is_valid_json": is_valid_json, 
            "raw_output": raw_output, 
            "error": None
        }

    except Exception as e:
        return {
            "prompt": prompt, 
            "latency": time.perf_counter() - start_time, 
            "is_valid_json": False, 
            "raw_output": "", 
            "error": str(e)
        }

def run_benchmark():
    print("==================================================")
    print(f" Starting LUMI LLM Benchmark on {MODEL_NAME}")
    print("==================================================\n")

    warm_up_model()

    total_latency = 0.0
    valid_json_count = 0

    for idx, prompt in enumerate(BENCHMARK_PROMPTS, 1):
        res = benchmark_single_prompt(prompt)
        total_latency += res["latency"]
        
        if res["is_valid_json"]:
            valid_json_count += 1
            print(f"[{idx}/10] Latency: {res['latency']:.3f}s | Status: VALID JSON | Command: '{prompt}'")
            print(f"       Received: {res['raw_output']}")
        else:
            print(f"[{idx}/10] Latency: {res['latency']:.3f}s | Status: FAILED JSON | Command: '{prompt}'")
            print(f"       Raw Output: '{res['raw_output']}'")
            if res['error']:
                print(f"       Error: {res['error']}")
        print("-" * 50)

    avg_latency = total_latency / len(BENCHMARK_PROMPTS)
    json_success_rate = (valid_json_count / len(BENCHMARK_PROMPTS)) * 100

    print("\n==================================================")
    print(" BENCHMARK SUMMARY")
    print("==================================================")
    print(f" Avg Latency     : {avg_latency:.3f} seconds")
    print(f" JSON Success    : {json_success_rate:.1f}% ({valid_json_count}/10)")
    print("==================================================")

    if avg_latency <= 2.0 and json_success_rate == 100.0:
        print("\nRESULT: PASS — Proceed to Phase 2!")
    else:
        print("\nRESULT: Check summary metrics above.")

if __name__ == "__main__":
    run_benchmark()