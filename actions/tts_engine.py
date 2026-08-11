import pyttsx3

# TODO: swap for Kokoro-82M once RAM headroom is confirmed stable

class TextToSpeechEngine:
    """
    Lightweight TTS engine using Windows native SAPI5 via pyttsx3.
    """
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 175)  # Slightly faster spoken speed
        except Exception as e:
            print(f"[TTS Engine] Initialization warning: {e}")
            self.engine = None

    def speak(self, text: str):
        """
        Synthesizes and speaks text string aloud.
        """
        print(f"\n[LUMI Voice]: \"{text}\"")
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[TTS Engine Error]: {e}")


# This file uses Windows native SAPI5 voice synthesizer (pyttsx3) so it consumes zero extra RAM.
