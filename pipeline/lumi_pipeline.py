import enum
import time
from typing import Optional

from audio.wake_word_listener import WakeWordListener
from audio.vad_capture import capture_speech_vad
from audio.stt_engine import SpeechToTextEngine
from core.llm_engine import get_validated_intent
from core.lumi_schema import LumiIntent, IntentType
from security.sacl import validate_and_authorize
from actions.os_executor import execute_intent
from actions.tts_engine import TextToSpeechEngine

# Whisper hallucination stoplist
HALLUCINATION_STOPLIST = {
    "thank you", "thank you.", "thanks for watching", 
    "thanks for watching.", "okay", "bye", "you're welcome.", "you're welcome"
}

class PipelineState(enum.Enum):
    IDLE = "IDLE"
    WAKE_DETECTED = "WAKE_DETECTED"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    VALIDATING = "VALIDATING"
    CONFIRMING = "CONFIRMING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"

class LumiPipeline:
    def __init__(self):
        self.state = PipelineState.IDLE
        self.wake_listener = WakeWordListener(model_name="alexa", threshold=0.5)
        self.stt = SpeechToTextEngine(model_size="small", compute_type="int8")
        self.tts = TextToSpeechEngine()

    def run_voice_loop(self):
        self.tts.speak("LUMI voice pipeline online and ready.")
        time.sleep(0.5)

        while True:
            try:
                # State 1: IDLE
                self.state = PipelineState.IDLE
                detected = self.wake_listener.listen_for_wake_word()

                if not detected:
                    continue

                # State 2: WAKE_DETECTED
                self.state = PipelineState.WAKE_DETECTED
                self.tts.speak("Yes?")
                time.sleep(0.4)

                # State 3: LISTENING
                self.state = PipelineState.LISTENING
                audio_data = capture_speech_vad(silence_duration_ms=800, max_timeout_s=8.0)

                if audio_data.size == 0:
                    self.tts.speak("I didn't hear anything.")
                    time.sleep(0.4)
                    continue

                # State 4: TRANSCRIBING
                self.state = PipelineState.TRANSCRIBING
                transcript = self.stt.transcribe(audio_data)

                # Defense Layer: Hallucination Stoplist & Short Text Filter
                cleaned_text = transcript.strip().lower()
                if not cleaned_text or len(cleaned_text) < 3 or cleaned_text in HALLUCINATION_STOPLIST:
                    print(f"[Pipeline] Ignored empty or hallucinated transcript: '{transcript}'")
                    time.sleep(0.3)
                    continue

                # State 5: THINKING
                self.state = PipelineState.THINKING
                print(f"[Pipeline State] THINKING — Processing transcript: '{transcript}'")
                intent = get_validated_intent(transcript)

                # Defense Layer: LLM Confidence Gate
                if intent.confidence < 0.6:
                    print(f"[Pipeline] Dropped low-confidence LLM intent ({intent.confidence:.2f})")
                    intent = LumiIntent(intent=IntentType.UNKNOWN, confidence=intent.confidence)

                # State 6: VALIDATING
                self.state = PipelineState.VALIDATING
                is_authorized, status_code = validate_and_authorize(intent)

                if not is_authorized:
                    self.tts.speak(f"Sorry, I cannot do that. {status_code}")
                    time.sleep(0.4)
                    continue

                # State 7: CONFIRMING
                if status_code == "requires_confirmation":
                    self.state = PipelineState.CONFIRMING
                    target_name = intent.filename or intent.target or intent.alias_path
                    confirm_question = f"You want me to {intent.intent.value} {target_name}. Should I proceed?"
                    self.tts.speak(confirm_question)
                    time.sleep(0.3)

                    reply_audio = capture_speech_vad(silence_duration_ms=800, max_timeout_s=5.0)
                    reply_text = self.stt.transcribe(reply_audio).lower()

                    affirmative_keywords = ["yes", "yeah", "sure", "confirm", "do it", "haan", "okay"]
                    confirmed = any(word in reply_text for word in affirmative_keywords)

                    if not confirmed:
                        self.tts.speak("Okay, cancelled.")
                        time.sleep(0.4)
                        continue

                # State 8: EXECUTING
                self.state = PipelineState.EXECUTING
                print(f"[Pipeline State] EXECUTING — Action: {intent.intent.value}")
                result_spoken = execute_intent(intent)

                # State 9: SPEAKING
                self.state = PipelineState.SPEAKING
                self.tts.speak(result_spoken)
                time.sleep(0.5)

            except KeyboardInterrupt:
                print("\nShutting down LUMI Pipeline.")
                break
            except Exception as e:
                print(f"[Pipeline Error]: {e}")
                time.sleep(1)

# This is the core state machine tying all 5 phases together serially.