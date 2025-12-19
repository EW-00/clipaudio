# ClipAudio

A macOS menu bar app to extract audio from video URLs across platforms (YouTube, Bilibili, Vimeo, etc.).

## Features

- One-click audio download from clipboard
- Supports YouTube, Bilibili, Vimeo, Dailymotion, SoundCloud, Twitter/X
- Custom filename before download
- Real-time download progress in menu bar
- Configurable output folder and audio format (MP3, AAC, FLAC, WAV, M4A)
- Native macOS notifications

## Installation

### Build from Source

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone https://github.com/yourusername/clipaudio.git
cd clipaudio

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .

# Build the app
pyinstaller ClipAudio.spec

# Install to Applications
cp -r dist/ClipAudio.app /Applications/
```

### Launch

Open **ClipAudio** from Spotlight (Cmd+Space), Launchpad, or the Applications folder.

## Usage

1. **Copy** a video URL from your browser
2. **Click** the music note icon in the menu bar
3. **Click** "Download from Clipboard"
4. **Edit** the filename if desired, then click "Download"
5. **Done** - audio file saved to your output folder

## Menu Options

| Option | Description |
|--------|-------------|
| Download from Clipboard | Download audio from copied URL |
| Output: ~/... | Click to change output folder |
| Format | Select audio format (MP3, AAC, FLAC, WAV, M4A) |
| Open Output Folder | Open the output folder in Finder |
| Quit | Exit the app |

## Auto-start on Login

1. Open **System Settings** → **General** → **Login Items**
2. Click **+** and select **ClipAudio.app**

## License

MIT License - see [LICENSE](LICENSE) for details.
