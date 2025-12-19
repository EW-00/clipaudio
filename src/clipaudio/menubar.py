"""macOS menu bar application for downloading audio from video URLs."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

import rumps
import yt_dlp
from AppKit import NSPasteboard, NSStringPboardType

from clipaudio import DEFAULT_OUTPUT_DIR, download_audio, is_valid_video_url


def get_resource_path(relative_path: str) -> str:
    """Get the path to a bundled resource file."""
    if hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    # Running in development
    base_path = Path(__file__).parent.parent.parent
    return str(base_path / relative_path)


def fetch_video_title(url: str) -> str:
    """Fetch video title from URL using yt-dlp.

    Args:
        url: The video URL to fetch title from.

    Returns:
        The video title, or a fallback ID if fetching fails.
    """
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "")
            if title:
                # Sanitize title for filename (remove problematic characters)
                sanitized = re.sub(r'[<>:"/\\|?*]', "", title)
                return sanitized.strip()
    except Exception:
        pass
    # Fallback to video ID extraction
    return _extract_video_id(url)


def _extract_video_id(url: str) -> str:
    """Extract a video ID or slug from the URL as fallback."""
    # Bilibili: extract BV ID
    if match := re.search(r"bilibili\.com/video/(BV\w+)", url):
        return match.group(1)
    # YouTube: extract video ID
    if match := re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)", url):
        return match.group(1)
    # Vimeo: extract numeric ID
    if match := re.search(r"vimeo\.com/(\d+)", url):
        return match.group(1)
    # SoundCloud: extract track slug
    if match := re.search(r"soundcloud\.com/[\w-]+/([\w-]+)", url):
        return match.group(1)
    # Twitter/X: extract tweet ID
    if match := re.search(r"(?:twitter|x)\.com/.*/status/(\d+)", url):
        return match.group(1)
    # Fallback: use "audio" as default
    return "audio"


def get_clipboard_text() -> Optional[str]:
    """Get the current text content from the clipboard."""
    pasteboard = NSPasteboard.generalPasteboard()
    text = pasteboard.stringForType_(NSStringPboardType)
    return text if text else None


def format_bytes(num_bytes: float) -> str:
    """Format bytes into human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes:.0f} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_eta(seconds: float) -> str:
    """Format ETA seconds into human-readable string."""
    if not seconds or seconds < 0:
        return "--:--"
    minutes, secs = divmod(int(seconds), 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class ClipAudioApp(rumps.App):
    """Menu bar application for downloading audio from video URLs."""

    def __init__(self) -> None:
        # Get the menu bar icon path (use high-res, macOS will scale)
        icon_path = get_resource_path("assets/menubar_icon.png")
        if not os.path.exists(icon_path):
            icon_path = None  # Fall back to text if icon not found

        super().__init__(
            name="ClipAudio",
            icon=icon_path,
            title=None,  # Use icon instead of text
            quit_button=None,  # We'll add our own quit button
            template=True,  # Auto-adjust color for light/dark menu bar
        )
        self._default_icon = icon_path
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.audio_format = "mp3"
        self._is_downloading = False
        self._progress_item: Optional[rumps.MenuItem] = None
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the menu structure."""
        download_item = rumps.MenuItem(
            "Download from Clipboard", callback=self.download_from_clipboard
        )
        self._progress_item = rumps.MenuItem("", callback=None)
        self._progress_item.hidden = True
        output_title = f"Output: {self._short_path(self.output_dir)}"
        output_item = rumps.MenuItem(output_title, callback=self.change_output_dir)
        self.menu = [
            download_item,
            self._progress_item,
            None,  # Separator
            output_item,
            self._build_format_menu(),
            None,  # Separator
            rumps.MenuItem("Open Output Folder", callback=self.open_output_folder),
            None,  # Separator
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

    def _build_format_menu(self) -> rumps.MenuItem:
        """Build the audio format submenu."""
        format_menu = rumps.MenuItem("Format")
        formats = ["mp3", "aac", "flac", "wav", "m4a"]
        for fmt in formats:
            item = rumps.MenuItem(fmt, callback=self.set_format)
            if fmt == self.audio_format:
                item.state = 1  # Checkmark
            format_menu.add(item)
        return format_menu

    def _short_path(self, path: Path) -> str:
        """Return a shortened path for display."""
        home = Path.home()
        try:
            return f"~/{path.relative_to(home)}"
        except ValueError:
            return str(path)

    def _update_output_menu_title(self) -> None:
        """Update the output folder menu item title."""
        for key in self.menu.keys():
            if key and key.startswith("Output:"):
                self.menu[key].title = f"Output: {self._short_path(self.output_dir)}"
                break

    @rumps.clicked("Download from Clipboard")
    def download_from_clipboard(self, _: rumps.MenuItem) -> None:
        """Download audio from the URL in clipboard."""
        # Prevent multiple simultaneous downloads
        if self._is_downloading:
            rumps.notification(
                title="ClipAudio",
                subtitle="Download in Progress",
                message="Please wait for the current download to finish.",
            )
            return

        url = get_clipboard_text()

        if not url:
            rumps.notification(
                title="ClipAudio",
                subtitle="No URL Found",
                message="Clipboard is empty or doesn't contain text.",
            )
            return

        url = url.strip()

        if not is_valid_video_url(url):
            rumps.notification(
                title="ClipAudio",
                subtitle="Invalid URL",
                message="Clipboard doesn't contain a supported video URL.",
            )
            return

        # Fetch video title for default filename
        rumps.notification(
            title="ClipAudio",
            subtitle="Fetching Video Info",
            message="Getting video title...",
        )
        default_name = fetch_video_title(url)
        url_preview = url[:60] + ("..." if len(url) > 60 else "")
        window = rumps.Window(
            message=f"Enter filename for the audio file:\n\n{url_preview}",
            title="ClipAudio - Save As",
            default_text=default_name,
            ok="Download",
            cancel="Cancel",
            dimensions=(320, 24),
        )
        response = window.run()

        # Check if user clicked Cancel or closed the dialog
        if response.clicked != 1:
            return

        # Get the filename (use default if empty)
        file_name = response.text.strip() if response.text.strip() else None

        # Run download in background thread to keep UI responsive
        thread = threading.Thread(
            target=self._download_thread,
            args=(url, file_name),
            daemon=True,
        )
        thread.start()

        display_name = file_name if file_name else "(auto from title)"
        rumps.notification(
            title="ClipAudio",
            subtitle="Download Started",
            message=f"Saving as: {display_name}.{self.audio_format}",
        )

    def _update_progress(self, progress_info: dict) -> None:
        """Update the menu bar and progress item with download progress."""
        status = progress_info.get("status", "")
        percent = progress_info.get("percent", 0)
        downloaded = progress_info.get("downloaded_bytes", 0)
        total = progress_info.get("total_bytes", 0)
        eta = progress_info.get("eta", 0)
        speed = progress_info.get("speed", 0)

        if status == "downloading":
            # Update menu bar: show percentage text alongside icon
            self.title = f"{percent:.0f}%"

            # Update progress menu item
            if self._progress_item:
                size_info = f"{format_bytes(downloaded)} / {format_bytes(total)}"
                speed_info = f"{format_bytes(speed)}/s" if speed else ""
                eta_info = f"ETA: {format_eta(eta)}" if eta else ""
                details = " • ".join(filter(None, [size_info, speed_info, eta_info]))
                self._progress_item.title = f"⏳ {percent:.0f}% — {details}"
                self._progress_item.hidden = False

        elif status == "finished":
            # Download finished, converting audio
            self.title = "Converting..."
            if self._progress_item:
                self._progress_item.title = "🔄 Converting audio..."

    def _reset_progress(self) -> None:
        """Reset progress display to normal state."""
        self._is_downloading = False
        self.title = None  # Remove text, show only icon
        if self._progress_item:
            self._progress_item.hidden = True
            self._progress_item.title = ""

    def _download_thread(self, url: str, file_name: Optional[str] = None) -> None:
        """Background thread for downloading audio."""
        self._is_downloading = True
        try:
            download_audio(
                url=url,
                audio_format=self.audio_format,
                quality="0",
                output_dir=self.output_dir,
                file_name=file_name,
                progress_callback=self._update_progress,
            )
            self._reset_progress()
            rumps.notification(
                title="ClipAudio",
                subtitle="Download Complete",
                message=f"Audio saved to {self._short_path(self.output_dir)}",
            )
        except Exception as exc:
            self._reset_progress()
            rumps.notification(
                title="ClipAudio",
                subtitle="Download Failed",
                message=str(exc)[:100],
            )

    def set_format(self, sender: rumps.MenuItem) -> None:
        """Set the audio format."""
        # Uncheck all format items
        format_menu = self.menu["Format"]
        for item in format_menu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = 0

        # Check the selected format
        sender.state = 1
        self.audio_format = sender.title

    def change_output_dir(self, _: rumps.MenuItem) -> None:
        """Open a dialog to change the output directory."""
        # Use osascript to show a folder selection dialog
        script = """
        tell application "System Events"
            activate
            set selectedFolder to choose folder with prompt "Select output folder:"
            return POSIX path of selectedFolder
        end tell
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
            )
            new_path = result.stdout.strip()
            if new_path:
                self.output_dir = Path(new_path)
                # Update menu title
                self._update_output_menu_title()
                rumps.notification(
                    title="ClipAudio",
                    subtitle="Output Folder Changed",
                    message=f"New folder: {self._short_path(self.output_dir)}",
                )
        except subprocess.CalledProcessError:
            # User cancelled the dialog
            pass

    def open_output_folder(self, _: rumps.MenuItem) -> None:
        """Open the output folder in Finder."""
        subprocess.run(["open", str(self.output_dir)], check=False)


def main() -> None:
    """Run the menu bar application."""
    app = ClipAudioApp()
    app.run()


if __name__ == "__main__":
    main()
