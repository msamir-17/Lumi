import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model

# Sample rate required by openwakeword
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80ms chunks at 16kHz

class WakeWordListener:
    """
    Continuous low-overhead wake word detector using openWakeWord ONNX models.
    Automatically closes the audio stream once the wake word is detected.
    """
    def __init__(self, model_name: str = "alexa", threshold: float = 0.5):
        """
        Initialize openWakeWord engine with a pre-trained model.
        Note: Built-in ONNX models include 'alexa', 'hey_jarvis', 'hey_mycroft'.
        """
        openwakeword.utils.download_models()
        self.model = Model(wakeword_models=[model_name], inference_framework="onnx")
        self.model_name = model_name
        self.threshold = threshold
        self.detected = False

    def listen_for_wake_word(self) -> bool:
        """
        Listens on microphone until wake word threshold is triggered.
        Returns True immediately on detection and closes audio stream.
        """
        self.detected = False
        print(f"\n[WakeWord] Listening for wake word ('{self.model_name}')...")

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"[WakeWord Status Warning]: {status}")
            
            # Convert audio chunk to 16-bit PCM integer format
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            
            # Predict wake word score
            prediction = self.model.predict(audio_data)
            
            for m in prediction:
                if prediction[m] >= self.threshold:
                    print(f"\n[WakeWord] >>> Wake Word Detected! (Score: {prediction[m]:.2f})")
                    self.detected = True
                    raise sd.CallbackStop()

        # Start low-overhead input stream
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                             blocksize=CHUNK_SIZE, callback=audio_callback):
            while not self.detected:
                sd.sleep(100)

        return self.detected

# This file runs a lightweight background audio stream using openwakeword and sounddevice. It listens for a wake word (e.g., "alexa" / "hey_jarvis" as pre-trained ONNX models).
# When detected, it immediately stops the microphone stream to free CPU resources