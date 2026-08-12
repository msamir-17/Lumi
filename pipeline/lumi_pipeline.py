import enum
import time
from typing import Optional

from audio.wake_word_listener import WakeWordListener
from audio.vad_capture import capture_speech_vad
from audio.stt_engine import SpeechToTextEngine
from core.llm_engine import get_validated_intent
from security.sacl import validate_and_authorize
from actions.os_executor import execute_intent
from actions.tts_engine import TextToSpeechEngine

class PipelineState(enum.Enum):
    IDLE = "IDLE"                     # Listening for wake word
    WAKE_DETECTED = "WAKE_DETECTED"   # Wake word triggered
    LISTENING = "LISTENING"           # Recording speech with VAD
    TRANSCRIBING = "TRANSCRIBING"     # Whisper transcribing audio to text
    THINKING = "THINKING"             # Llama model creating JSON intent
    VALIDATING = "VALIDATING"         # SACL verifying whitelists
    CONFIRMING = "CONFIRMING"         # Asking spoken Yes/No confirmation
    EXECUTING = "EXECUTING"           # Windows executing authorized action
    SPEAKING = "SPEAKING"             # TTS speaking output

class LumiPipeline:
    """
    Strict serial state machine managing LUMI's voice execution loop.
    Resource Discipline: Releases audio resources before starting LLM inference.
    """
    def __init__(self):
        self.state = PipelineState.IDLE
        self.wake_listener = WakeWordListener(model_name="alexa", threshold=0.5)
        self.stt = SpeechToTextEngine(model_size="small", compute_type="int8")
        self.tts = TextToSpeechEngine()

    def run_voice_loop(self):
        """
        Main execution loop. Runs indefinitely until interrupted.
        """
        self.tts.speak("LUMI voice pipeline online and ready.")

        while True:
            try:
                # State 1: IDLE - Wait for wake word
                self.state = PipelineState.IDLE
                detected = self.wake_listener.listen_for_wake_word()

                if not detected:
                    continue

                # State 2: WAKE_DETECTED
                self.state = PipelineState.WAKE_DETECTED
                self.tts.speak("Yes?")
                time.sleep(0.3)

                # State 3: LISTENING - Capture speech with VAD
                self.state = PipelineState.LISTENING
                audio_data = capture_speech_vad(silence_duration_ms=700, max_timeout_s=8.0)

                if audio_data.size == 0:
                    self.tts.speak("I didn't hear anything.")
                    continue

                # State 4: TRANSCRIBING - Whisper Speech-to-Text
                # Microphone stream is completely closed here!
                self.state = PipelineState.TRANSCRIBING
                transcript = self.stt.transcribe(audio_data)

                if not transcript or len(transcript.strip()) < 2:
                    self.tts.speak("Could you please repeat that?")
                    continue

                # State 5: THINKING - LLM JSON Intent Generation
                self.state = PipelineState.THINKING
                print(f"[Pipeline State] THINKING — Processing transcript: '{transcript}'")
                intent = get_validated_intent(transcript)

                # State 6: VALIDATING - SACL Whitelist Sandbox Check
                self.state = PipelineState.VALIDATING
                is_authorized, status_code = validate_and_authorize(intent)

                if not is_authorized:
                    self.tts.speak(f"Sorry, I cannot do that. {status_code}")
                    continue

                # State 7: CONFIRMING (if required by SACL or Intent)
                if status_code == "requires_confirmation":
                    self.state = PipelineState.CONFIRMING
                    confirm_question = f"You want me to {intent.intent.value} on {intent.target or intent.alias_path}. Should I proceed?"
                    self.tts.speak(confirm_question)

                    # Quick VAD capture for Yes/No answer (No wake word needed)
                    reply_audio = capture_speech_vad(silence_duration_ms=700, max_timeout_s=5.0)
                    reply_text = self.stt.transcribe(reply_audio).lower()

                    affirmative_keywords = ["yes", "yeah", "sure", "confirm", "do it", "haan", "okay"]
                    confirmed = any(word in reply_text for word in affirmative_keywords)

                    if not confirmed:
                        self.tts.speak("Okay, cancelled.")
                        continue

                # State 8: EXECUTING - Run Windows Action
                self.state = PipelineState.EXECUTING
                print(f"[Pipeline State] EXECUTING — Action: {intent.intent.value}")
                result_spoken = execute_intent(intent)

                # State 9: SPEAKING - Speak Result
                self.state = PipelineState.SPEAKING
                self.tts.speak(result_spoken)

            except KeyboardInterrupt:
                print("\nShutting down LUMI Pipeline.")
                break
            except Exception as e:
                print(f"[Pipeline Error]: {e}")
                self.tts.speak("An unexpected error occurred.")
                time.sleep(1)

# This is the core state machine tying all 5 phases together serially.