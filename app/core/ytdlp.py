import shutil
import subprocess
from app.core.ffmpeg import get_ffmpeg_path


def check_yt_dlp() -> tuple[bool, str]:
    """
    Check if yt-dlp is installed and runnable.
    Returns (is_available, version_or_error_string).
    """
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        return True, version
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        return False, str(e)


def get_base_yt_dlp_cmd() -> list[str]:
    """Construct base yt-dlp command with optimal client args and FFmpeg path."""
    cmd = ["yt-dlp", "--extractor-args", "youtube:player_client=web_embedded,android_vr,mweb,web"]
    if shutil.which("node"):
        cmd += ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        cmd += ["--ffmpeg-location", ffmpeg_path]
    return cmd
