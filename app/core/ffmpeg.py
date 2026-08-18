import os
import shutil


def get_ffmpeg_path() -> str | None:
    """Find FFmpeg binary via imageio_ffmpeg or system PATH."""
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    
    # Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg and os.path.exists(system_ffmpeg):
        return system_ffmpeg
    return None


def is_ffmpeg_available() -> bool:
    """Check if FFmpeg is available on the system."""
    return get_ffmpeg_path() is not None
