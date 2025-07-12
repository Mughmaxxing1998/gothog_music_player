"""File system utilities for managing playlists and music files."""

import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class FileUtils:
    """Utility class for file system operations."""
    
    @staticmethod
    def get_playlists_directory() -> Path:
        """Get the default playlists directory."""
        default_path = os.path.expanduser("~/Music/Playlists")
        os.makedirs(default_path, exist_ok=True)
        return Path(default_path)
    
    @staticmethod
    def create_playlist_folder(name: str) -> Path:
        """Create a new playlist folder."""
        base_dir = FileUtils.get_playlists_directory()
        playlist_dir = base_dir / FileUtils.sanitize_filename(name)
        
        # Handle duplicate names
        counter = 1
        original_dir = playlist_dir
        while playlist_dir.exists():
            playlist_dir = base_dir / f"{FileUtils.sanitize_filename(name)}_{counter}"
            counter += 1
            
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return playlist_dir
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
            
        return filename or "Untitled"
    
    @staticmethod
    def get_file_hash(filepath: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def load_json(filepath: Path) -> Optional[Dict[str, Any]]:
        """Load JSON file with error handling."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            return None
    
    @staticmethod
    def save_json(filepath: Path, data: Dict[str, Any], backup: bool = True) -> bool:
        """Save JSON file with atomic write and optional backup."""
        try:
            # Create backup if requested and file exists
            if backup and filepath.exists():
                backup_path = filepath.with_suffix('.json.bak')
                shutil.copy2(filepath, backup_path)
            
            # Write to temporary file first
            temp_path = filepath.with_suffix('.json.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(filepath)
            return True
            
        except Exception as e:
            logger.error(f"Error saving JSON to {filepath}: {e}")
            return False
    
    @staticmethod
    def get_supported_audio_files(directory: Path) -> List[Path]:
        """Get all supported audio files in a directory."""
        supported_extensions = {'.mp3', '.flac', '.m4a', '.opus', '.ogg', '.wav'}
        audio_files = []
        
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in supported_extensions:
                audio_files.append(file)
                
        return sorted(audio_files)
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS."""
        if seconds < 0:
            return "0:00"
            
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    @staticmethod
    def get_file_size_mb(filepath: Path) -> float:
        """Get file size in megabytes."""
        return filepath.stat().st_size / (1024 * 1024)
    
    @staticmethod
    def cleanup_empty_folders(base_dir: Path) -> None:
        """Remove empty playlist folders."""
        for folder in base_dir.iterdir():
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
                logger.info(f"Removed empty folder: {folder}")
    
    @staticmethod
    def validate_playlist_structure(playlist_dir: Path) -> bool:
        """Validate that a playlist folder has the required structure."""
        playlist_json = playlist_dir / "playlist.json"
        return playlist_json.exists() and playlist_json.is_file()
    
    @staticmethod
    def copy_with_progress(src: Path, dst: Path, callback=None) -> bool:
        """Copy file with progress callback."""
        try:
            total_size = src.stat().st_size
            copied = 0
            
            with open(src, 'rb') as fsrc:
                with open(dst, 'wb') as fdst:
                    while True:
                        buf = fsrc.read(1024 * 1024)  # 1MB chunks
                        if not buf:
                            break
                        fdst.write(buf)
                        copied += len(buf)
                        
                        if callback:
                            callback(copied, total_size)
                            
            return True
        except Exception as e:
            logger.error(f"Error copying file {src} to {dst}: {e}")
            return False
