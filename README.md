# Gothog Music Player

A modern, playlist-focused music player built with GTK4 and Python.

## Features

- **Playlist-Centric Design**: Organize your music into folder-based playlists
- **Streaming Service Integration**: Download playlists from Spotify and YouTube Music
- **Modern GTK4 Interface**: Clean and responsive UI with dark mode support
- **Smart Playlist Management**: Each playlist has its own settings stored in JSON
- **Advanced Playback**: Crossfade, gapless playback, shuffle, and repeat modes
- **Metadata Management**: Automatic metadata fetching and editing

## Requirements

- Python 3.8+
- GTK 4.0+
- libadwaita 1.0+
- GStreamer 1.0+
- FFmpeg (for audio conversion)

## Installation

### Dependencies (Fedora)

```bash
sudo dnf install gtk4-devel libadwaita-devel gstreamer1-devel \
    gstreamer1-plugins-base-devel gstreamer1-plugins-good \
    gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free \
    python3-pip ffmpeg
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
./run.py
```

### Playlist Structure

Playlists are stored as folders in `~/Music/Playlists/`:

```
~/Music/Playlists/
├── My Favorites/
│   ├── playlist.json    # Playlist metadata and settings
│   ├── song1.mp3
│   ├── song2.mp3
│   └── cover.jpg
└── Workout Mix/
    ├── playlist.json
    └── *.mp3
```

### Downloading Playlists

1. Click the "+" button in the sidebar
2. Select "Download from URL"
3. Paste a Spotify or YouTube Music playlist URL
4. The app will download all tracks with metadata

### Spotify Integration

To download from Spotify, you'll need to set up API credentials:

1. Go to https://developer.spotify.com/dashboard
2. Create an app
3. Get your Client ID and Client Secret
4. Set them as environment variables:

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```

## Development

### Project Structure

```
src/
├── main.py              # Application entry point
├── core/                # Backend logic
│   ├── playlist_manager.py
│   ├── audio_player.py
│   └── downloader.py
├── ui/                  # GTK4 UI components
│   ├── main_window.py
│   ├── playlist_sidebar.py
│   ├── track_list.py
│   └── player_controls.py
└── utils/               # Utility functions
    ├── file_utils.py
    └── metadata_utils.py
```

### Building

```bash
meson setup builddir
meson compile -C builddir
```

## License

GPL-3.0 License

## TODO

- [ ] Playlist settings dialog
- [ ] Download progress dialog
- [ ] Preferences dialog
- [ ] Keyboard shortcuts dialog
- [ ] Visualizer
- [ ] Lyrics display
- [ ] Smart playlist creation UI
- [ ] Batch metadata editing
- [ ] Export playlists to streaming services
