"""ClipAudio - Extract audio from video URLs across platforms."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable, List, Optional

import certifi
import yt_dlp

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover - runtime dependency guard
    imageio_ffmpeg = None


# Default output directory for downloaded audio files
DEFAULT_OUTPUT_DIR = Path.home() / "Music" / "ClipAudio"

# Supported video URL patterns for validation
VIDEO_URL_PATTERNS: List[str] = [
    r"https?://(?:www\.)?bilibili\.com/video/",
    r"https?://(?:www\.)?youtube\.com/watch",
    r"https?://youtu\.be/",
    r"https?://(?:www\.)?vimeo\.com/",
    r"https?://(?:www\.)?dailymotion\.com/video/",
    r"https?://(?:www\.)?soundcloud\.com/",
    r"https?://(?:www\.)?twitter\.com/.*/status/",
    r"https?://(?:www\.)?x\.com/.*/status/",
]


def is_valid_video_url(url: str) -> bool:
    """Check if the URL matches any supported video site pattern.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL matches a supported video site, False otherwise.
    """
    if not url:
        return False
    return any(re.match(pattern, url.strip()) for pattern in VIDEO_URL_PATTERNS)


def get_ffmpeg_path() -> Optional[Path]:
    """Return the bundled ffmpeg binary path if available."""
    if imageio_ffmpeg is None:
        return None
    return Path(imageio_ffmpeg.get_ffmpeg_exe())


def download_audio(
    url: str,
    audio_format: str,
    quality: str,
    output_dir: Path,
    file_name: Optional[str],
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> None:
    """Download and convert the audio stream from the given video URL.

    Args:
        url: The video URL to download audio from.
        audio_format: Output audio format (e.g., 'mp3', 'aac', 'flac').
        quality: Audio quality passed to ffmpeg (0 = best).
        output_dir: Directory to save the audio file.
        file_name: Optional custom filename (without extension).
        progress_callback: Optional callback for progress updates.
            Called with dict containing: status, downloaded_bytes,
            total_bytes, speed, eta, percent.
    """
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path is None:
        raise RuntimeError(
            "ffmpeg not found. Install imageio-ffmpeg in the virtualenv."
        )

    # Ensure Python/yt-dlp uses a valid certificate bundle.
    cert_path = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", cert_path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", cert_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    if file_name:
        base = Path(file_name).name  # drop any directory components
        base = Path(base).stem  # drop any provided extension
        output_template = output_dir / f"{base}.%(ext)s"
    else:
        output_template = output_dir / "%(title)s.%(ext)s"

    def progress_hook(d: dict) -> None:
        """Internal progress hook that normalizes yt-dlp progress data."""
        if progress_callback is None:
            return

        status = d.get("status", "")
        progress_info = {
            "status": status,
            "downloaded_bytes": d.get("downloaded_bytes", 0),
            "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate", 0),
            "speed": d.get("speed", 0),
            "eta": d.get("eta", 0),
            "percent": 0.0,
        }

        if progress_info["total_bytes"] > 0:
            progress_info["percent"] = (
                progress_info["downloaded_bytes"] / progress_info["total_bytes"] * 100
            )

        progress_callback(progress_info)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_template),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": quality,
            }
        ],
        "ffmpeg_location": str(ffmpeg_path),
        "progress_hooks": [progress_hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "VIDEO_URL_PATTERNS",
    "is_valid_video_url",
    "download_audio",
]
