# KDownloader

A modern **PyQt6** graphical user interface for the **yt-dlp** video & audio downloader.

## Features
- 🎥 **Video & Audio Downloads**: Download highest available quality or cap resolution (4K, 2K, 1080p, 720p, etc.), or extract audio as MP3.
- 📑 **Chapter Splitting & Inspection**: Inspect video chapters and split downloads into chapter files.
- 📋 **Playlist Support**: Verify and download video playlists.
- ⚡ **Real-Time Metrics**: Live progress bar, download speed, size counter, and ETA display.
- 🎨 **Modern Dark Theme**: Polished dark UI with responsive controls.
- 📁 **Folder Memory**: Remembers last chosen destination folder automatically.

## Requirements
- **Python 3.8+**
- **yt-dlp** (added to system PATH)
- Python packages: `PyQt6`, `psutil`

## Setup & Execution

1. Install dependencies:
   ```bash
   pip install PyQt6 yt-dlp psutil
   ```

2. Run the application:
   ```bash
   python main.py
   ```
