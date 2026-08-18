import json
import subprocess
import urllib.request
from typing import NamedTuple

from app.core.ytdlp import get_base_yt_dlp_cmd
from app.core.parser import parse_available_qualities
from app.core.utils import format_duration


class MediaMetadata(NamedTuple):
    url: str
    title: str
    uploader: str
    duration_sec: int
    duration_str: str
    thumbnail_bytes: bytes | None
    qualities: list[str]
    available_names: list[str]
    is_playlist: bool
    count: int


def fetch_metadata(url: str) -> MediaMetadata:
    """Fetch video or playlist metadata and thumbnail asynchronously/synchronously."""
    cmd = get_base_yt_dlp_cmd() + ["--dump-single-json", "--flat-playlist", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    title = data.get("title") or "Sans titre"
    uploader = data.get("uploader") or data.get("channel") or data.get("artist") or "Inconnu"
    duration = data.get("duration") or 0
    thumbnail_url = data.get("thumbnail") or ""

    qualities, available_names = parse_available_qualities(data)

    thumb_bytes = None
    if thumbnail_url:
        try:
            req = urllib.request.Request(
                thumbnail_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                thumb_bytes = response.read()
        except Exception:
            pass

    _type = data.get("_type")
    entries = data.get("entries")
    is_playlist = (_type in ("playlist", "multi_video") or isinstance(entries, list))
    count = len(entries) if entries is not None else data.get("playlist_count", 0)

    return MediaMetadata(
        url=url,
        title=title,
        uploader=uploader,
        duration_sec=duration,
        duration_str=format_duration(duration),
        thumbnail_bytes=thumb_bytes,
        qualities=qualities,
        available_names=available_names,
        is_playlist=is_playlist,
        count=count
    )


def fetch_playlist_info(url: str) -> tuple[bool, str, int]:
    """Inspect if URL is a playlist. Returns (is_playlist, title, item_count)."""
    cmd = get_base_yt_dlp_cmd() + ["--flat-playlist", "--dump-single-json", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    _type = data.get("_type")
    entries = data.get("entries")

    if _type in ("playlist", "multi_video") or isinstance(entries, list):
        title = data.get("title", "Sans titre")
        count = len(entries) if entries is not None else data.get("playlist_count", 0)
        return True, title, count
    else:
        title = data.get("title", "Sans titre")
        return False, title, 1


def fetch_chapters_info(url: str) -> tuple[list[dict], list[str], int]:
    """Inspect chapters and qualities. Returns (chapters_list, qualities, total_duration)."""
    cmd = get_base_yt_dlp_cmd() + ["--no-playlist", "--dump-json", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    qualities, _ = parse_available_qualities(data)
    chapters = data.get("chapters", [])
    total_duration = data.get("duration") or (
        chapters[-1].get("end_time", chapters[-1].get("start_time", 0)) if chapters else 0
    )

    return chapters, qualities, total_duration
