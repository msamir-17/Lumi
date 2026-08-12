import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # ~32ms blocks at 16kHz

def capture_speech_vad(silence_duration_ms: int = 800, max_timeout_s: float = 8.0) -> np.ndarray:
    """
    Captures spoken audio segment using RMS energy silence detection.
    Stops automatically after silence_duration_ms of continuous silence or max_timeout_s.
    Returns PCM float32 audio array normalized for Whisper STT.
    """
    print("[VAD Capture] 🎤 Listening for spoken command...")
    
    audio_frames = []
    silence_start_time = None
    start_time = time.time()
    has_speech_started = False
    
    # Silence energy threshold (RMS)
    SILENCE_THRESHOLD = 0.005 
    silence_limit_s = silence_duration_ms / 1000.0

    recording = True

    def audio_callback(indata, frames, time_info, status):
        nonlocal silence_start_time, recording, has_speech_started
        
        chunk = indata[:, 0]
        audio_frames.append(chunk.copy())
        
        # Calculate RMS volume energy
        rms = np.sqrt(np.mean(chunk**2))
        
        # Mark speech as started once volume exceeds threshold
        if rms >= SILENCE_THRESHOLD:
            has_speech_started = True
            silence_start_time = None
        else:
            # Only count silence AFTER speech has started, or if 2.5 seconds pass with no speech
            if has_speech_started:
                if silence_start_time is None:
                    silence_start_time = time.time()
                elif time.time() - silence_start_time >= silence_limit_s:
                    recording = False
                    raise sd.CallbackStop()
            elif time.time() - start_time >= 2.5:
                # If no speech at all after 2.5s, stop
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