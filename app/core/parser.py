import re
from typing import NamedTuple
from app.core.utils import format_bytes_human


class ProgressData(NamedTuple):
    status: str
    percent: int
    percent_str: str
    downloaded_str: str
    total_str: str
    speed_str: str
    eta_str: str
    filename: str | None


def parse_progress_line(line: str) -> tuple[ProgressData | None, str | None]:
    """
    Parse a single stdout line from yt-dlp.
    Returns (ProgressData, detected_filepath).
    """
    detected_file = None
    progress_data = None

    if line.startswith("KPARSER|"):
        parts = line.split("|")
        if len(parts) >= 7:
            status = parts[1].strip()
            percent_str = parts[2].strip()
            downloaded_str = parts[3].strip()
            total_str = parts[4].strip()
            speed_str = parts[5].strip()
            eta_str = parts[6].strip()

            clean_percent = re.sub(r"[^\d.]", "", percent_str)
            percent_val = 0
            if clean_percent:
                try:
                    percent_val = int(float(clean_percent))
                except ValueError:
                    percent_val = 0

            if len(parts) >= 8 and parts[7].strip():
                detected_file = parts[7].strip()

            progress_data = ProgressData(
                status=status,
                percent=percent_val,
                percent_str=percent_str,
                downloaded_str=downloaded_str,
                total_str=total_str,
                speed_str=speed_str,
                eta_str=eta_str,
                filename=detected_file
            )
        return progress_data, detected_file

    # Check standard yt-dlp outputs for target filepath
    if "[download] Destination:" in line:
        detected_file = line.replace("[download] Destination:", "").strip()
    elif "[Merger] Merging formats into" in line:
        m = re.search(r'Merging formats into "([^"]+)"', line)
        if m:
            detected_file = m.group(1)
    elif "[ExtractAudio] Destination:" in line:
        detected_file = line.replace("[ExtractAudio] Destination:", "").strip()

    return progress_data, detected_file


def parse_available_qualities(data: dict) -> tuple[list[str], list[str]]:
    """
    Parse available video qualities and estimated sizes from yt-dlp JSON dump.
    Returns (qualities_list, available_names).
    """
    formats = data.get("formats", [])
    audio_formats = [
        f for f in formats 
        if f.get("vcodec") == "none" and (f.get("filesize") or f.get("filesize_approx"))
    ]
    best_audio_size = max(
        [(f.get("filesize") or f.get("filesize_approx")) for f in audio_formats],
        default=0
    )

    heights = sorted(
        list(set(f.get("height") for f in formats if f.get("height") and f.get("height") >= 144)),
        reverse=True
    )

    height_labels = {
        2160: "4K (2160p)",
        1440: "2K (1440p)",
        1080: "1080p",
        720: "720p",
        480: "480p",
        360: "360p",
        240: "240p",
        144: "144p",
    }

    max_size_str = ""
    if heights:
        max_h = heights[0]
        v_formats = [f for f in formats if f.get("height") == max_h and f.get("vcodec") != "none"]
        best_v_size = max([(f.get("filesize") or f.get("filesize_approx") or 0) for f in v_formats], default=0)
        if best_v_size > 0:
            max_size_str = format_bytes_human(best_v_size + best_audio_size)

    qualities = [f"Meilleure qualité{max_size_str}"]
    available_names = []
    for h in heights:
        label = height_labels.get(h, f"{h}p")
        v_formats = [f for f in formats if f.get("height") == h and f.get("vcodec") != "none"]
        best_v_size = max([(f.get("filesize") or f.get("filesize_approx") or 0) for f in v_formats], default=0)
        size_str = format_bytes_human(best_v_size + best_audio_size) if best_v_size > 0 else ""

        full_name = f"{label}{size_str}"
        if full_name not in qualities:
            qualities.append(full_name)
            available_names.append(full_name)

    return qualities, available_names
