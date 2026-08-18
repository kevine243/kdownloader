import os


def format_duration(seconds) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if not seconds or seconds < 0:
        return "00:00"
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bytes_human(b: float | int) -> str:
    """Format byte size into human readable string (KB, MB, GB)."""
    if not b or b <= 0:
        return ""
    if b < 1024 * 1024:
        return f" (~{b / 1024:.1f} KB)"
    elif b < 1024 * 1024 * 1024:
        return f" (~{b / (1024 * 1024):.1f} MB)"
    else:
        return f" (~{b / (1024 * 1024 * 1024):.2f} GB)"


def find_latest_file_in_dir(directory: str) -> str | None:
    """Find the most recently modified file in a directory."""
    if not directory or not os.path.exists(directory):
        return None
    try:
        files = [
            os.path.join(directory, f) for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        ]
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
    except Exception:
        pass
    return None
