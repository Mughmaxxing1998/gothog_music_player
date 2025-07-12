"""Downloader module for fetching playlists from streaming services."""

import os
import re
import json
import logging
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Tuple
from datetime import datetime
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests

from ..utils.file_utils import FileUtils
from ..utils.metadata_utils import MetadataUtils

logger = logging.getLogger(__name__)


class DownloadProgress:
    """Track download progress for multiple files."""
    
    def __init__(self):
        self.total_tracks = 0
        self.completed_tracks = 0
        self.current_track = ""
        self.current_progress = 0.0
        self.errors: List[str] = []
        self.skipped: List[str] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary."""
        return {
            'total_tracks': self.total_tracks,
            'completed_tracks': self.completed_tracks,
            'current_track': self.current_track,
            'current_progress': self.current_progress,
            'overall_progress': (self.completed_tracks / self.total_tracks * 100) if self.total_tracks > 0 else 0,
            'errors': self.errors,
            'skipped': self.skipped
        }


class PlaylistDownloader:
    """Handle downloading playlists from various streaming services."""
    
    def __init__(self, download_dir: Optional[Path] = None, 
                 spotify_client_id: Optional[str] = None,
                 spotify_client_secret: Optional[str] = None):
        """Initialize the downloader."""
        self.download_dir = download_dir or FileUtils.get_playlists_directory()
        self.progress = DownloadProgress()
        self._progress_callback: Optional[Callable] = None
        
        # Initialize Spotify client if credentials provided
        self.spotify = None
        if spotify_client_id and spotify_client_secret:
            try:
                auth_manager = SpotifyClientCredentials(
                    client_id=spotify_client_id,
                    client_secret=spotify_client_secret
                )
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
            except Exception as e:
                logger.error(f"Failed to initialize Spotify client: {e}")
        
        # yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'progress_hooks': [self._ydl_progress_hook],
        }
    
    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def _ydl_progress_hook(self, d):
        """Handle yt-dlp progress updates."""
        if d['status'] == 'downloading':
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                self.progress.current_progress = (downloaded / total) * 100
                if self._progress_callback:
                    self._progress_callback(self.progress)
        elif d['status'] == 'finished':
            self.progress.current_progress = 100
            if self._progress_callback:
                self._progress_callback(self.progress)
    
    def identify_service(self, url: str) -> Optional[str]:
        """Identify the streaming service from URL."""
        if 'spotify.com' in url:
            return 'spotify'
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'music.youtube.com' in url:
            return 'youtube_music'
        return None
    
    def extract_playlist_id(self, url: str, service: str) -> Optional[str]:
        """Extract playlist ID from URL."""
        if service == 'spotify':
            # Pattern: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
            match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
            return match.group(1) if match else None
        elif service in ['youtube', 'youtube_music']:
            # Pattern: https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf
            match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
            return match.group(1) if match else None
        return None
    
    def download_spotify_playlist(self, url: str, playlist_name: Optional[str] = None) -> Optional[Path]:
        """Download a Spotify playlist."""
        if not self.spotify:
            logger.error("Spotify client not initialized. Please provide API credentials.")
            return None
        
        playlist_id = self.extract_playlist_id(url, 'spotify')
        if not playlist_id:
            logger.error(f"Invalid Spotify playlist URL: {url}")
            return None
        
        try:
            # Get playlist info
            playlist = self.spotify.playlist(playlist_id)
            name = playlist_name or playlist['name']
            
            # Create playlist directory
            playlist_dir = FileUtils.create_playlist_folder(name)
            
            # Get all tracks
            tracks = []
            results = playlist['tracks']
            tracks.extend(results['items'])
            
            while results['next']:
                results = self.spotify.next(results)
                tracks.extend(results['items'])
            
            # Download playlist cover
            if playlist['images']:
                self._download_cover_image(playlist['images'][0]['url'], playlist_dir / 'cover.jpg')
            
            # Prepare playlist metadata
            playlist_data = {
                'name': name,
                'description': playlist.get('description', ''),
                'created_date': datetime.now().isoformat(),
                'modified_date': datetime.now().isoformat(),
                'cover_image': 'cover.jpg' if playlist['images'] else None,
                'source': {
                    'type': 'spotify',
                    'url': url,
                    'last_sync': datetime.now().isoformat()
                },
                'settings': {
                    'shuffle_enabled': False,
                    'repeat_mode': 'none',
                    'volume': 0.8,
                    'equalizer_preset': 'default'
                },
                'tracks': []
            }
            
            # Download tracks
            self.progress.total_tracks = len(tracks)
            self.progress.completed_tracks = 0
            
            for i, item in enumerate(tracks):
                if not item['track']:
                    continue
                    
                track = item['track']
                artist_names = ', '.join([artist['name'] for artist in track['artists']])
                track_name = track['name']
                
                self.progress.current_track = f"{artist_names} - {track_name}"
                if self._progress_callback:
                    self._progress_callback(self.progress)
                
                # Search and download from YouTube
                search_query = f"{artist_names} {track_name} audio"
                downloaded_file = self._download_from_youtube(search_query, playlist_dir)
                
                if downloaded_file:
                    # Add to playlist
                    track_data = {
                        'filename': downloaded_file.name,
                        'title': track_name,
                        'artist': artist_names,
                        'album': track['album']['name'],
                        'duration': track['duration_ms'] / 1000,
                        'track_number': track['track_number'],
                        'downloaded_date': datetime.now().isoformat(),
                        'source_id': f"spotify:track:{track['id']}"
                    }
                    playlist_data['tracks'].append(track_data)
                    self.progress.completed_tracks += 1
                else:
                    self.progress.errors.append(f"Failed to download: {track_name}")
                
                if self._progress_callback:
                    self._progress_callback(self.progress)
            
            # Save playlist metadata
            playlist_json_path = playlist_dir / 'playlist.json'
            FileUtils.save_json(playlist_json_path, playlist_data)
            
            return playlist_dir
            
        except Exception as e:
            logger.error(f"Error downloading Spotify playlist: {e}")
            return None
    
    def download_youtube_playlist(self, url: str, playlist_name: Optional[str] = None) -> Optional[Path]:
        """Download a YouTube/YouTube Music playlist."""
        try:
            # Extract playlist info
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            
            name = playlist_name or info.get('title', 'YouTube Playlist')
            
            # Create playlist directory
            playlist_dir = FileUtils.create_playlist_folder(name)
            
            # Download thumbnail
            thumbnail_url = info.get('thumbnail')
            if thumbnail_url:
                self._download_cover_image(thumbnail_url, playlist_dir / 'cover.jpg')
            
            # Prepare playlist metadata
            playlist_data = {
                'name': name,
                'description': info.get('description', ''),
                'created_date': datetime.now().isoformat(),
                'modified_date': datetime.now().isoformat(),
                'cover_image': 'cover.jpg' if thumbnail_url else None,
                'source': {
                    'type': 'youtube_music' if 'music.youtube.com' in url else 'youtube',
                    'url': url,
                    'last_sync': datetime.now().isoformat()
                },
                'settings': {
                    'shuffle_enabled': False,
                    'repeat_mode': 'none',
                    'volume': 0.8,
                    'equalizer_preset': 'default'
                },
                'tracks': []
            }
            
            # Download tracks
            entries = info.get('entries', [])
            self.progress.total_tracks = len(entries)
            self.progress.completed_tracks = 0
            
            # Configure yt-dlp for downloading
            ydl_opts = self.ydl_opts.copy()
            ydl_opts['outtmpl'] = str(playlist_dir / '%(title)s.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for i, entry in enumerate(entries):
                    if not entry:
                        continue
                    
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    self.progress.current_track = entry.get('title', 'Unknown')
                    
                    if self._progress_callback:
                        self._progress_callback(self.progress)
                    
                    try:
                        # Download the track
                        info_dict = ydl.extract_info(video_url, download=True)
                        
                        # Get the downloaded filename
                        filename = ydl.prepare_filename(info_dict)
                        # Replace extension with mp3
                        mp3_filename = Path(filename).with_suffix('.mp3')
                        
                        if mp3_filename.exists():
                            # Read metadata from file
                            metadata = MetadataUtils.read_metadata(mp3_filename)
                            
                            track_data = {
                                'filename': mp3_filename.name,
                                'title': info_dict.get('title', mp3_filename.stem),
                                'artist': info_dict.get('artist') or info_dict.get('uploader', 'Unknown'),
                                'album': info_dict.get('album', ''),
                                'duration': info_dict.get('duration', 0),
                                'downloaded_date': datetime.now().isoformat(),
                                'source_id': f"youtube:video:{entry['id']}"
                            }
                            playlist_data['tracks'].append(track_data)
                            self.progress.completed_tracks += 1
                        
                    except Exception as e:
                        logger.error(f"Error downloading track: {e}")
                        self.progress.errors.append(f"Failed: {entry.get('title', 'Unknown')}")
                    
                    if self._progress_callback:
                        self._progress_callback(self.progress)
            
            # Save playlist metadata
            playlist_json_path = playlist_dir / 'playlist.json'
            FileUtils.save_json(playlist_json_path, playlist_data)
            
            return playlist_dir
            
        except Exception as e:
            logger.error(f"Error downloading YouTube playlist: {e}")
            return None
    
    def _download_from_youtube(self, search_query: str, output_dir: Path) -> Optional[Path]:
        """Download a single track from YouTube by search query."""
        try:
            ydl_opts = self.ydl_opts.copy()
            ydl_opts['outtmpl'] = str(output_dir / '%(title)s.%(ext)s')
            ydl_opts['default_search'] = 'ytsearch'
            ydl_opts['format'] = 'bestaudio/best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{search_query}", download=True)
                if info and 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    filename = ydl.prepare_filename(entry)
                    mp3_filename = Path(filename).with_suffix('.mp3')
                    if mp3_filename.exists():
                        return mp3_filename
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading from YouTube: {e}")
            return None
    
    def _download_cover_image(self, url: str, output_path: Path) -> bool:
        """Download cover image from URL."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading cover image: {e}")
            return False
    
    def download_playlist(self, url: str, playlist_name: Optional[str] = None) -> Optional[Path]:
        """Download a playlist from any supported service."""
        service = self.identify_service(url)
        
        if not service:
            logger.error(f"Unsupported URL: {url}")
            return None
        
        # Reset progress
        self.progress = DownloadProgress()
        
        if service == 'spotify':
            return self.download_spotify_playlist(url, playlist_name)
        elif service in ['youtube', 'youtube_music']:
            return self.download_youtube_playlist(url, playlist_name)
        
        return None
