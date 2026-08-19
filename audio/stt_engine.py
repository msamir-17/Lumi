import time
import numpy as np
from faster_whisper import WhisperModel

class SpeechToTextEngine:
    """
    Wrapper around Faster-Whisper using CPU int8 quantization and Silero VAD filtering.
    """
    def __init__(self, model_size: str = "small", compute_type: str = "int8"):
        print(f"[STT Engine] Loading Faster-Whisper model ('{model_size}', compute_type='{compute_type}')...")
        self.model = WhisperModel(model_size, device="cpu", compute_type=compute_type, cpu_threads=4)
        print("[STT Engine] Faster-Whisper model loaded successfully!")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribes PCM audio array into text with strict no-speech and VAD filtering.
        """
        if audio_data.size == 0:
            return ""

        start_time = time.perf_counter()

        # Whisper Silero VAD filtering + disable previous text conditioning to stop loops
        segments, info = self.model.transcribe(
            audio_data,
            beam_size=1,
            language="en",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            no_speech_threshold=0.6,
            condition_on_previous_text=False,  # Stops hallucination-loop drift
        )

        segments = list(segments)
        if not segments:
            return ""

        # Drop transcript if average no-speech probability is high
        avg_no_speech = float(np.mean([s.no_speech_prob for s in segments]))
        if avg_no_speech > 0.6:
            print(f"[STT Engine] Dropped low-confidence / near-silence audio (no_speech_prob: {avg_no_speech:.2f})")
            return ""

        transcribed_text = " ".join([s.text for s in segments]).strip()
        latency = time.perf_counter() - start_time
        print(f"[STT Engine] Transcribed in {latency:.3f}s: '{transcribed_text}'")

        return transcribed_text

# This file wraps faster-whisper using the quantized small model with compute_type="int8" on CPU for fast offline transcription.