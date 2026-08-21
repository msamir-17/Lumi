import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHUNK_SIZE = 512

# default silence_duration_ms ko 800 se badha kar 1500 kiya
def capture_speech_vad(silence_duration_ms: int = 1500, max_timeout_s: float = 10.0) -> np.ndarray:
    print("[VAD Capture] 🎤 Listening for spoken command...")

    audio_frames = []
    silence_start_time = None
    start_time = time.time()
    
    has_speech_started = False
    consecutive_speech_chunks = 0
    
    # SENIOR ML ENGINEER TUNING:
    # Lowered slightly so it captures faint speech but ignores fan hiss.
    SILENCE_THRESHOLD = 0.012   
    MIN_SPEECH_CHUNKS = 2      # ~64ms of sustained speech to trigger
    
    silence_limit_s = silence_duration_ms / 1000.0
    recording = True

    def audio_callback(indata, frames, time_info, status):
        nonlocal silence_start_time, recording, has_speech_started, consecutive_speech_chunks

        chunk = indata[:, 0]
        audio_frames.append(chunk.copy())

        # RMS volume energy calculation
        rms = np.sqrt(np.mean(chunk**2))

        if rms >= SILENCE_THRESHOLD:
            consecutive_speech_chunks += 1
            if consecutive_speech_chunks >= MIN_SPEECH_CHUNKS:
                has_speech_started = True
                silence_start_time = None  # Reset silence timer since user is speaking
        else:
            consecutive_speech_chunks = 0
            if has_speech_started:
                if silence_start_time is None:
                    silence_start_time = time.time()
                elif time.time() - silence_start_time >= silence_limit_s:
                    recording = False
                    raise sd.CallbackStop()
            elif time.time() - start_time >= 3.5: # 2.5s se badha kar 3.5s kiya
                # No sustained speech within 3.5s after wake word -> timeout
                recording = False
                raise sd.CallbackStop()

        if time.time() - start_time >= max_timeout_s:
            recording = False
            raise sd.CallbackStop()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                         blocksize=CHUNK_SIZE, callback=audio_callback):
        while recording:
            sd.sleep(50)

    print("[VAD Capture] 🛑 Recording finished.")
    if len(audio_frames) == 0:
        return np.array([], dtype=np.float32)

    return np.concatenate(audio_frames, axis=0)

    
# Right after the wake word triggers, this file records your command speech and automatically stops recording after ~700ms of silence (or a maximum timeout of 8 seconds).