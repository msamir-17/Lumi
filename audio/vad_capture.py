import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # ~32ms blocks at 16kHz

def capture_speech_vad(silence_duration_ms: int = 700, max_timeout_s: float = 8.0) -> np.ndarray:
    """
    Captures spoken audio segment using RMS energy silence detection.
    Stops automatically after silence_duration_ms of continuous silence or max_timeout_s.
    Returns PCM float32 audio array normalized for Whisper STT.
    """
    print("[VAD Capture] 🎤 Listening for spoken command...")
    
    audio_frames = []
    silence_start_time = None
    start_time = time.time()
    
    # Silence energy threshold (RMS)
    SILENCE_THRESHOLD = 0.005 
    silence_limit_s = silence_duration_ms / 1000.0

    recording = True

    def audio_callback(indata, frames, time_info, status):
        nonlocal silence_start_time, recording
        
        chunk = indata[:, 0]
        audio_frames.append(chunk.copy())
        
        # Calculate Root Mean Square (RMS) energy level
        rms = np.sqrt(np.mean(chunk**2))
        
        if rms < SILENCE_THRESHOLD:
            if silence_start_time is None:
                silence_start_time = time.time()
            elif time.time() - silence_start_time >= silence_limit_s:
                # Stop recording after silence limit reached
                recording = False
                raise sd.CallbackStop()
        else:
            silence_start_time = None

        # Check hard timeout limit
        if time.time() - start_time >= max_timeout_s:
            recording = False
            raise sd.CallbackStop()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                         blocksize=CHUNK_SIZE, callback=audio_callback):
        while recording:
            sd.sleep(50)

    print("[VAD Capture] 🛑 Recording finished (Silence or timeout reached).")
    
    if len(audio_frames) == 0:
        return np.array([], dtype=np.float32)
        
    full_audio = np.concatenate(audio_frames, axis=0)
    return full_audio

# Right after the wake word triggers, this file records your command speech and automatically stops recording after ~700ms of silence (or a maximum timeout of 8 seconds).