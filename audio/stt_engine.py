import time
import numpy as np
from faster_whisper import WhisperModel

class SpeechToTextEngine:
    """
    Wrapper around Faster-Whisper using CPU int8 quantization for lightweight execution.
    """
    def __init__(self, model_size: str = "small", compute_type: str = "int8"):
        """
        Initialize Faster-Whisper model on CPU.
        """
        print(f"[STT Engine] Loading Faster-Whisper model ('{model_size}', compute_type='{compute_type}')...")
        self.model = WhisperModel(model_size, device="cpu", compute_type=compute_type, cpu_threads=4)
        print("[STT Engine] Faster-Whisper model loaded successfully!")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribes numpy float32 PCM audio array into text.
        Tracks and prints transcription latency instrumentation.
        """
        if audio_data.size == 0:
            return ""

        start_time = time.perf_counter()
        
        # Transcribe audio segment
        segments, _ = self.model.transcribe(audio_data, beam_size=1, language="en")
        transcribed_text = " ".join([segment.text for segment in segments]).strip()
        
        latency = time.perf_counter() - start_time
        print(f"[STT Engine] Transcribed in {latency:.3f}s: '{transcribed_text}'")
        
        return transcribed_text

# This file wraps faster-whisper using the quantized small model with compute_type="int8" on CPU for fast offline transcription.