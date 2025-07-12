"""Playlist management system for creating, loading, and managing playlists."""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging

from ..utils.file_utils import FileUtils
from ..utils.metadata_utils import MetadataUtils

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Represents a single track in a playlist."""
    filename: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: float = 0.0
    track_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    downloaded_date: Optional[str] = None
    source_id: Optional[str] = None
    file_hash: Optional[str] = None
    play_count: int = 0
    skip_count: int = 0
    last_played: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Create track from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    @classmethod
    def from_file(cls, filepath: Path, playlist_dir: Path) -> 'Track':
        """Create track from audio file."""
        metadata = MetadataUtils.read_metadata(filepath)
        relative_path = filepath.relative_to(playlist_dir)
        
        return cls(
            filename=str(relative_path),
            title=metadata.get('title', filepath.stem),
            artist=metadata.get('artist'),
            album=metadata.get('album'),
            duration=metadata.get('duration', 0),
            track_number=metadata.get('track_number'),
            year=metadata.get('year'),
            genre=metadata.get('genre'),
            downloaded_date=datetime.now().isoformat(),
            file_hash=FileUtils.get_file_hash(filepath)
        )


@dataclass
class PlaylistSettings:
    """Playlist-specific settings."""
    shuffle_enabled: bool = False
    repeat_mode: str = "none"  # none, track, playlist
    volume: float = 0.8
    equalizer_preset: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaylistSettings':
        """Create settings from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class PlaylistSource:
    """Information about playlist source."""
    type: str  # manual, spotify, youtube_music
    url: Optional[str] = None
    last_sync: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert source to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaylistSource':
        """Create source from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class Playlist:
    """Represents a single playlist."""
    
    def __init__(self, path: Path):
        """Initialize playlist from directory path."""
        self.path = path
        self.name = path.name
        self.description = ""
        self.created_date = datetime.now().isoformat()
        self.modified_date = datetime.now().isoformat()
        self.cover_image: Optional[str] = None
        self.total_duration = 0.0
        self.track_count = 0
        self.source = PlaylistSource(type="manual")
        self.settings = PlaylistSettings()
        self.tracks: List[Track] = []
        self.tags: List[str] = []
        
        # Load existing playlist if it exists
        if self.path.exists():
            self.load()
    
    def load(self) -> bool:
        """Load playlist from JSON file."""
        json_path = self.path / "playlist.json"
        data = FileUtils.load_json(json_path)
        
        if not data:
            logger.error(f"Failed to load playlist from {json_path}")
            return False
        
        # Load basic metadata
        self.name = data.get('name', self.name)
        self.description = data.get('description', '')
        self.created_date = data.get('created_date', self.created_date)
        self.modified_date = data.get('modified_date', self.modified_date)
        self.cover_image = data.get('cover_image')
        self.total_duration = data.get('total_duration', 0)
        self.track_count = data.get('track_count', 0)
        self.tags = data.get('tags', [])
        
        # Load source info
        if 'source' in data:
            self.source = PlaylistSource.from_dict(data['source'])
        
        # Load settings
        if 'settings' in data:
            self.settings = PlaylistSettings.from_dict(data['settings'])
        
        # Load tracks
        self.tracks = []
        for track_data in data.get('tracks', []):
            self.tracks.append(Track.from_dict(track_data))
        
        return True
    
    def save(self) -> bool:
        """Save playlist to JSON file."""
        # Update metadata
        self.modified_date = datetime.now().isoformat()
        self.track_count = len(self.tracks)
        self.total_duration = sum(track.duration for track in self.tracks)
        
        # Prepare data
        data = {
            'name': self.name,
            'description': self.description,
            'created_date': self.created_date,
            'modified_date': self.modified_date,
            'cover_image': self.cover_image,
            'total_duration': self.total_duration,
            'track_count': self.track_count,
            'tags': self.tags,
            'source': self.source.to_dict(),
            'settings': self.settings.to_dict(),
            'tracks': [track.to_dict() for track in self.tracks]
        }
        
        # Save to file
        json_path = self.path / "playlist.json"
        return FileUtils.save_json(json_path, data)
    
    def add_track(self, audio_file: Path) -> bool:
        """Add a track to the playlist."""
        if not audio_file.exists():
            logger.error(f"Audio file does not exist: {audio_file}")
            return False
        
        # Copy file to playlist directory if not already there
        if audio_file.parent != self.path:
            dest_path = self.path / audio_file.name
            if dest_path.exists():
                logger.warning(f"File already exists in playlist: {dest_path}")
                return False
            
            shutil.copy2(audio_file, dest_path)
            audio_file = dest_path
        
        # Create track from file
        track = Track.from_file(audio_file, self.path)
        self.tracks.append(track)
        
        # Save playlist
        return self.save()
    
    def remove_track(self, index: int, delete_file: bool = False) -> bool:
        """Remove a track from the playlist."""
        if index < 0 or index >= len(self.tracks):
            logger.error(f"Invalid track index: {index}")
            return False
        
        track = self.tracks[index]
        
        # Delete file if requested
        if delete_file:
            file_path = self.path / track.filename
            if file_path.exists():
                file_path.unlink()
        
        # Remove from playlist
        self.tracks.pop(index)
        
        # Save playlist
        return self.save()
    
    def reorder_tracks(self, old_index: int, new_index: int) -> bool:
        """Reorder tracks in the playlist."""
        if old_index < 0 or old_index >= len(self.tracks):
            return False
        if new_index < 0 or new_index >= len(self.tracks):
            return False
        
        # Move track
        track = self.tracks.pop(old_index)
        self.tracks.insert(new_index, track)
        
        # Save playlist
        return self.save()
    
    def update_track_stats(self, index: int, played: bool = True) -> None:
        """Update play/skip statistics for a track."""
        if 0 <= index < len(self.tracks):
            track = self.tracks[index]
            if played:
                track.play_count += 1
                track.last_played = datetime.now().isoformat()
            else:
                track.skip_count += 1
            self.save()
    
    def get_track_path(self, index: int) -> Optional[Path]:
        """Get the full path to a track file."""
        if 0 <= index < len(self.tracks):
            return self.path / self.tracks[index].filename
        return None
    
    def validate_tracks(self) -> List[int]:
        """Validate all tracks and return indices of missing files."""
        missing = []
        for i, track in enumerate(self.tracks):
            file_path = self.path / track.filename
            if not file_path.exists():
                missing.append(i)
        return missing
    
    def sync_with_filesystem(self) -> bool:
        """Sync playlist with filesystem (add new files, remove missing)."""
        # Find audio files in directory
        audio_files = FileUtils.get_supported_audio_files(self.path)
        
        # Get current filenames
        current_files = {track.filename for track in self.tracks}
        
        # Add new files
        for audio_file in audio_files:
            relative_path = audio_file.relative_to(self.path)
            if str(relative_path) not in current_files:
                track = Track.from_file(audio_file, self.path)
                self.tracks.append(track)
        
        # Remove missing files
        self.tracks = [
            track for track in self.tracks 
            if (self.path / track.filename).exists()
        ]
        
        # Save changes
        return self.save()


class PlaylistManager:
    """Manages all playlists in the application."""
    
    def __init__(self, playlists_dir: Optional[Path] = None):
        """Initialize playlist manager."""
        self.playlists_dir = playlists_dir or FileUtils.get_playlists_directory()
        self.playlists: Dict[str, Playlist] = {}
        self._scan_playlists()
    
    def _scan_playlists(self) -> None:
        """Scan the playlists directory for existing playlists."""
        self.playlists.clear()
        
        for item in self.playlists_dir.iterdir():
            if item.is_dir() and FileUtils.validate_playlist_structure(item):
                playlist = Playlist(item)
                self.playlists[playlist.name] = playlist
    
    def create_playlist(self, name: str, description: str = "") -> Optional[Playlist]:
        """Create a new playlist."""
        # Create playlist directory
        playlist_dir = FileUtils.create_playlist_folder(name)
        
        # Create playlist object
        playlist = Playlist(playlist_dir)
        playlist.name = name
        playlist.description = description
        
        # Save initial playlist file
        if not playlist.save():
            # Cleanup on failure
            shutil.rmtree(playlist_dir)
            return None
        
        # Add to manager
        self.playlists[playlist.name] = playlist
        return playlist
    
    def delete_playlist(self, name: str) -> bool:
        """Delete a playlist."""
        if name not in self.playlists:
            logger.error(f"Playlist not found: {name}")
            return False
        
        playlist = self.playlists[name]
        
        # Remove directory
        try:
            shutil.rmtree(playlist.path)
            del self.playlists[name]
            return True
        except Exception as e:
            logger.error(f"Failed to delete playlist {name}: {e}")
            return False
    
    def rename_playlist(self, old_name: str, new_name: str) -> bool:
        """Rename a playlist."""
        if old_name not in self.playlists:
            logger.error(f"Playlist not found: {old_name}")
            return False
        
        playlist = self.playlists[old_name]
        new_path = self.playlists_dir / FileUtils.sanitize_filename(new_name)
        
        # Check if new name already exists
        if new_path.exists():
            logger.error(f"Playlist already exists: {new_name}")
            return False
        
        # Rename directory
        try:
            playlist.path.rename(new_path)
            playlist.path = new_path
            playlist.name = new_name
            playlist.save()
            
            # Update manager
            del self.playlists[old_name]
            self.playlists[new_name] = playlist
            return True
        except Exception as e:
            logger.error(f"Failed to rename playlist: {e}")
            return False
    
    def get_playlist(self, name: str) -> Optional[Playlist]:
        """Get a playlist by name."""
        return self.playlists.get(name)
    
    def get_all_playlists(self) -> List[Playlist]:
        """Get all playlists."""
        return list(self.playlists.values())
    
    def refresh(self) -> None:
        """Refresh the playlist list from filesystem."""
        self._scan_playlists()
    
    def import_playlist(self, source_path: Path, name: Optional[str] = None) -> Optional[Playlist]:
        """Import a playlist from M3U/PLS file or directory."""
        if source_path.is_dir():
            # Copy entire directory
            dest_name = name or source_path.name
            dest_path = FileUtils.create_playlist_folder(dest_name)
            
            try:
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                playlist = Playlist(dest_path)
                playlist.sync_with_filesystem()
                self.playlists[playlist.name] = playlist
                return playlist
            except Exception as e:
                logger.error(f"Failed to import playlist directory: {e}")
                return None
        
        # TODO: Implement M3U/PLS import
        logger.warning("M3U/PLS import not yet implemented")
        return None
    
    def export_playlist(self, name: str, dest_path: Path, format: str = "m3u") -> bool:
        """Export a playlist to M3U/PLS format."""
        if name not in self.playlists:
            logger.error(f"Playlist not found: {name}")
            return False
        
        playlist = self.playlists[name]
        
        try:
            if format.lower() == "m3u":
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    for track in playlist.tracks:
                        duration = int(track.duration)
                        artist = track.artist or "Unknown Artist"
                        title = track.title
                        file_path = playlist.path / track.filename
                        
                        f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                        f.write(f"{file_path}\n")
                return True
            
            # TODO: Implement other formats (PLS, JSON)
            logger.warning(f"Export format not implemented: {format}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to export playlist: {e}")
            return False
