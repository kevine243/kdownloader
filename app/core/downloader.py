import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import psutil

from app.core.ytdlp import get_base_yt_dlp_cmd
from app.core.parser import parse_progress_line, ProgressData
from app.core.utils import find_latest_file_in_dir


@dataclass
class DownloadOptions:
    url: str
    download_path: str
    is_audio: bool = False
    quality: str = "Meilleure qualité"
    audio_format: str = "mp3"
    audio_bitrate: str = "Meilleure qualité (V0 / ~320k)"
    embed_metadata: bool = True
    subtitles: bool = False
    split_chapters: bool = False
    playlist_range: str = ""


class DownloadProcess:
    def __init__(self, options: DownloadOptions):
        self.options = options
        self.process: subprocess.Popen | None = None
        self.cancelled = False
        self.detected_filepath: str | None = None

    def build_command(self) -> list[str]:
        opts = self.options
        target_height = None
        if not opts.is_audio and "Meilleure" not in opts.quality:
            match = re.search(r'(\d+)p', opts.quality)
            if match:
                target_height = int(match.group(1))

        progress_template = (
            "KPARSER|%(progress.status)s|%(progress._percent_str)s|"
            "%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s|"
            "%(progress._speed_str)s|%(progress._eta_str)s|%(progress.filename)s"
        )

        cmd = get_base_yt_dlp_cmd() + [
            "--newline",
            "--progress",
            "--progress-template", progress_template,
            "--paths", opts.download_path,
            "--retries", "10",
            "--fragment-retries", "10",
        ]

        if opts.embed_metadata:
            cmd += ["--embed-metadata", "--embed-thumbnail"]

        if opts.subtitles and not opts.is_audio:
            cmd += [
                "--write-subs", "--write-auto-subs",
                "--sub-langs", "fr.*,en.*,-live_chat",
                "--embed-subs"
            ]

        if opts.playlist_range:
            cmd += ["--playlist-items", opts.playlist_range]

        url = opts.url
        if opts.split_chapters:
            parsed = urlparse(url)
            q = parse_qs(parsed.query)
            if "list" in q:
                del q["list"]
                new_query = urlencode(q, doseq=True)
                url = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                 parsed.params, new_query, parsed.fragment))
            cmd += [
                "--no-playlist",
                "--split-chapters",
                "-o", "%(title)s.%(ext)s",
                "-o", "chapter:%(title)s/%(chapter_number)03d - %(chapter)s.%(ext)s"
            ]
        else:
            cmd += ["-o", "%(title)s.%(ext)s"]

        if opts.is_audio:
            fmt = opts.audio_format.lower()
            cmd += ["-x", "--audio-format", fmt]
            bitrate = opts.audio_bitrate
            if "320" in bitrate:
                cmd += ["--audio-quality", "320K"]
            elif "256" in bitrate:
                cmd += ["--audio-quality", "256K"]
            elif "192" in bitrate:
                cmd += ["--audio-quality", "192K"]
            elif "128" in bitrate:
                cmd += ["--audio-quality", "128K"]
            else:
                cmd += ["--audio-quality", "0"]
        else:
            if target_height is not None:
                cmd += ["-f", f"bestvideo[height<={target_height}]+bestaudio/best"]
            else:
                cmd += ["-f", "bestvideo+bestaudio/best"]

        cmd.append(url)
        return cmd

    def run(
        self,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[ProgressData], None] | None = None,
        on_file_found: Callable[[str], None] | None = None
    ) -> bool:
        """
        Execute the download synchronously within the calling thread.
        Returns True on success, False otherwise.
        """
        cmd = self.build_command()
        self.cancelled = False
        self.detected_filepath = None

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )

            while True:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    stripped = line.strip()
                    progress_data, file_from_line = parse_progress_line(stripped)

                    if file_from_line:
                        self.detected_filepath = file_from_line
                        if on_file_found:
                            on_file_found(file_from_line)

                    if progress_data:
                        if on_progress:
                            on_progress(progress_data)
                    else:
                        if on_log and (
                            "ERROR:" in stripped
                            or "WARNING:" in stripped
                            or "[download]" in stripped
                            or "[ExtractAudio]" in stripped
                            or "[Merger]" in stripped
                            or "[info]" in stripped
                        ):
                            on_log(stripped)

            self.process.wait()
            return_code = self.process.returncode

            if return_code == 0:
                if not self.detected_filepath or not os.path.exists(self.detected_filepath):
                    self.detected_filepath = find_latest_file_in_dir(self.options.download_path)
                return True
            return False

        except Exception as e:
            if on_log:
                on_log(f"Error: {str(e)}")
            return False
        finally:
            self.process = None

    def cancel(self):
        """Terminate the active download process tree."""
        self.cancelled = True
        if self.process is not None:
            try:
                pid = self.process.pid
                if pid and psutil.pid_exists(pid):
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    gone, still_alive = psutil.wait_procs(children, timeout=2)
                    for child in still_alive:
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    parent.terminate()
                    parent.wait(timeout=2)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                pass
