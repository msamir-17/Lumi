import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80ms chunks at 16kHz

class WakeWordListener:
    # Default threshold lowered from 0.5 to 0.42 for better distance sensitivity
    def __init__(self, model_name: str = "alexa", threshold: float = 0.42):
        openwakeword.utils.download_models()
        # Explicit inference framework definition
        self.model = Model(wakeword_models=[model_name], inference_framework="onnx")
        self.model_name = model_name
        self.threshold = threshold
        self.detected = False

    def listen_for_wake_word(self) -> bool:
        self.detected = False
        print(f"\n[WakeWord] Listening for wake word ('{self.model_name}')...")

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[WakeWord Status Warning]: {status}")
            
            # Convert audio chunk to 16-bit PCM integer format safely
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            
            # Feed audio data to openWakeWord model
            prediction = self.model.predict(audio_data)
            
            # openWakeWord prediction format handler
            for m in prediction:
                if prediction[m] >= self.threshold:
                    print(f"\n[WakeWord] >>> Wake Word Detected! (Score: {prediction[m]:.2f})")
                    self.detected = True
                    raise sd.CallbackStop()

        # Input stream with safe resource handling
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                                 blocksize=CHUNK_SIZE, callback=audio_callback):
                while not self.detected:
                    sd.sleep(100)
        except Exception as e:
            # Catch stream terminations safely
            pass

        return self.detected



# This file runs a lightweight background audio stream using openwakeword and sounddevice. It listens for a wake word (e.g., "alexa" / "hey_jarvis" as pre-trained ONNX models).
# When detected, it immediately stops the microphone stream to free CPU resources