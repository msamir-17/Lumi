import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.lumi_pipeline import LumiPipeline

def main():
    print("==================================================")
    print("      LUMI — Offline Voice Automation Agent       ")
    print("==================================================")
    
    pipeline = LumiPipeline()
    pipeline.run_voice_loop()

if __name__ == "__main__":
    main()

# Main Voice Entry Point