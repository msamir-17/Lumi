import ctypes
from config.lumi_config import ALLOWED_MEDIA_ACTIONS

def send_media_key(action: str) -> bool:
    """
    Sends a fixed OS-level virtual media key via ctypes.
    Equivalent to pressing physical keyboard media buttons.
    """
    if action not in ALLOWED_MEDIA_ACTIONS:
        return False

    vk_code = ALLOWED_MEDIA_ACTIONS[action]
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002

    # Key down
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    # Key up
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    return True