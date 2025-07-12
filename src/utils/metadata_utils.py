"""Metadata utilities for managing music file tags and information."""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TCON, APIC
from mutagen.mp4 import MP4Cover
import logging

logger = logging.getLogger(__name__)


class MetadataUtils:
    """Utility class for audio metadata operations."""
    
    @staticmethod
    def read_metadata(filepath: Path) -> Dict[str, Any]:
        """Read metadata from an audio file."""
        try:
            audio_file = File(filepath)
            if audio_file is None:
                return MetadataUtils._parse_from_filename(filepath)
            
            metadata = {
                'title': None,
                'artist': None,
                'album': None,
                'year': None,
                'track_number': None,
                'genre': None,
                'duration': audio_file.info.length if hasattr(audio_file.info, 'length') else 0,
                'bitrate': getattr(audio_file.info, 'bitrate', 0),
                'sample_rate': getattr(audio_file.info, 'sample_rate', 0)
            }
            
            # Extract common tags based on format
            if isinstance(audio_file, MP3):
                metadata.update(MetadataUtils._read_id3_tags(audio_file))
            elif isinstance(audio_file, MP4):
                metadata.update(MetadataUtils._read_mp4_tags(audio_file))
            elif isinstance(audio_file, (FLAC, OggVorbis)):
                metadata.update(MetadataUtils._read_vorbis_tags(audio_file))
            
            # Clean up metadata
            for key, value in metadata.items():
                if isinstance(value, list) and value:
                    metadata[key] = value[0]
                elif value == '':
                    metadata[key] = None
                    
            # Use filename if title is missing
            if not metadata['title']:
                metadata['title'] = filepath.stem
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error reading metadata from {filepath}: {e}")
            return MetadataUtils._parse_from_filename(filepath)
    
    @staticmethod
    def _read_id3_tags(audio_file: MP3) -> Dict[str, Any]:
        """Read ID3 tags from MP3 files."""
        tags = {}
        if audio_file.tags:
            tags['title'] = str(audio_file.tags.get('TIT2', [''])[0])
            tags['artist'] = str(audio_file.tags.get('TPE1', [''])[0])
            tags['album'] = str(audio_file.tags.get('TALB', [''])[0])
            
            # Year
            year_tag = audio_file.tags.get('TDRC')
            if year_tag:
                tags['year'] = int(str(year_tag[0])[:4]) if str(year_tag[0])[:4].isdigit() else None
            
            # Track number
            track_tag = audio_file.tags.get('TRCK')
            if track_tag:
                track_str = str(track_tag[0]).split('/')[0]
                tags['track_number'] = int(track_str) if track_str.isdigit() else None
            
            tags['genre'] = str(audio_file.tags.get('TCON', [''])[0])
            
        return tags
    
    @staticmethod
    def _read_mp4_tags(audio_file: MP4) -> Dict[str, Any]:
        """Read tags from MP4/M4A files."""
        tags = {}
        if audio_file.tags:
            tags['title'] = audio_file.tags.get('\xa9nam', [''])[0]
            tags['artist'] = audio_file.tags.get('\xa9ART', [''])[0]
            tags['album'] = audio_file.tags.get('\xa9alb', [''])[0]
            
            # Year
            year_tag = audio_file.tags.get('\xa9day', [''])
            if year_tag and year_tag[0]:
                year_str = str(year_tag[0])[:4]
                tags['year'] = int(year_str) if year_str.isdigit() else None
            
            # Track number
            track_tag = audio_file.tags.get('trkn', [(None, None)])
            if track_tag and track_tag[0][0]:
                tags['track_number'] = track_tag[0][0]
            
            tags['genre'] = audio_file.tags.get('\xa9gen', [''])[0]
            
        return tags
    
    @staticmethod
    def _read_vorbis_tags(audio_file) -> Dict[str, Any]:
        """Read Vorbis comments from FLAC/OGG files."""
        tags = {}
        if audio_file.tags:
            tags['title'] = audio_file.tags.get('title', [''])[0]
            tags['artist'] = audio_file.tags.get('artist', [''])[0]
            tags['album'] = audio_file.tags.get('album', [''])[0]
            
            # Year
            year_tag = audio_file.tags.get('date', [''])
            if year_tag and year_tag[0]:
                year_str = str(year_tag[0])[:4]
                tags['year'] = int(year_str) if year_str.isdigit() else None
            
            # Track number
            track_tag = audio_file.tags.get('tracknumber', [''])
            if track_tag and track_tag[0]:
                track_str = str(track_tag[0]).split('/')[0]
                tags['track_number'] = int(track_str) if track_str.isdigit() else None
            
            tags['genre'] = audio_file.tags.get('genre', [''])[0]
            
        return tags
    
    @staticmethod
    def _parse_from_filename(filepath: Path) -> Dict[str, Any]:
        """Parse metadata from filename when tags are not available."""
        filename = filepath.stem
        
        # Common patterns: "Artist - Title", "01. Artist - Title", "01 - Title"
        patterns = [
            r'^(\d+)[\.\-\s]+(.+?)\s*-\s*(.+)$',  # "01. Artist - Title" or "01 - Artist - Title"
            r'^(.+?)\s*-\s*(.+)$',                  # "Artist - Title"
            r'^(\d+)[\.\-\s]+(.+)$',                # "01. Title" or "01 - Title"
        ]
        
        metadata = {
            'title': filename,
            'artist': None,
            'album': None,
            'year': None,
            'track_number': None,
            'genre': None,
            'duration': 0
        }
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 3 and groups[0].isdigit():
                    # Pattern: "01. Artist - Title"
                    metadata['track_number'] = int(groups[0])
                    metadata['artist'] = groups[1].strip()
                    metadata['title'] = groups[2].strip()
                elif len(groups) == 2 and groups[0].isdigit():
                    # Pattern: "01. Title"
                    metadata['track_number'] = int(groups[0])
                    metadata['title'] = groups[1].strip()
                elif len(groups) == 2:
                    # Pattern: "Artist - Title"
                    metadata['artist'] = groups[0].strip()
                    metadata['title'] = groups[1].strip()
                break
        
        return metadata
    
    @staticmethod
    def write_metadata(filepath: Path, metadata: Dict[str, Any]) -> bool:
        """Write metadata to an audio file."""
        try:
            audio_file = File(filepath)
            if audio_file is None:
                logger.error(f"Unsupported file format: {filepath}")
                return False
            
            # Create tags if they don't exist
            if audio_file.tags is None:
                audio_file.add_tags()
            
            if isinstance(audio_file, MP3):
                MetadataUtils._write_id3_tags(audio_file, metadata)
            elif isinstance(audio_file, MP4):
                MetadataUtils._write_mp4_tags(audio_file, metadata)
            elif isinstance(audio_file, (FLAC, OggVorbis)):
                MetadataUtils._write_vorbis_tags(audio_file, metadata)
            
            audio_file.save()
            return True
            
        except Exception as e:
            logger.error(f"Error writing metadata to {filepath}: {e}")
            return False
    
    @staticmethod
    def _write_id3_tags(audio_file: MP3, metadata: Dict[str, Any]) -> None:
        """Write ID3 tags to MP3 files."""
        if metadata.get('title'):
            audio_file.tags['TIT2'] = TIT2(encoding=3, text=metadata['title'])
        if metadata.get('artist'):
            audio_file.tags['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
        if metadata.get('album'):
            audio_file.tags['TALB'] = TALB(encoding=3, text=metadata['album'])
        if metadata.get('year'):
            audio_file.tags['TDRC'] = TDRC(encoding=3, text=str(metadata['year']))
        if metadata.get('track_number'):
            audio_file.tags['TRCK'] = TRCK(encoding=3, text=str(metadata['track_number']))
        if metadata.get('genre'):
            audio_file.tags['TCON'] = TCON(encoding=3, text=metadata['genre'])
    
    @staticmethod
    def _write_mp4_tags(audio_file: MP4, metadata: Dict[str, Any]) -> None:
        """Write tags to MP4/M4A files."""
        if metadata.get('title'):
            audio_file.tags['\xa9nam'] = metadata['title']
        if metadata.get('artist'):
            audio_file.tags['\xa9ART'] = metadata['artist']
        if metadata.get('album'):
            audio_file.tags['\xa9alb'] = metadata['album']
        if metadata.get('year'):
            audio_file.tags['\xa9day'] = str(metadata['year'])
        if metadata.get('track_number'):
            audio_file.tags['trkn'] = [(int(metadata['track_number']), 0)]
        if metadata.get('genre'):
            audio_file.tags['\xa9gen'] = metadata['genre']
    
    @staticmethod
    def _write_vorbis_tags(audio_file, metadata: Dict[str, Any]) -> None:
        """Write Vorbis comments to FLAC/OGG files."""
        if metadata.get('title'):
            audio_file.tags['title'] = metadata['title']
        if metadata.get('artist'):
            audio_file.tags['artist'] = metadata['artist']
        if metadata.get('album'):
            audio_file.tags['album'] = metadata['album']
        if metadata.get('year'):
            audio_file.tags['date'] = str(metadata['year'])
        if metadata.get('track_number'):
            audio_file.tags['tracknumber'] = str(metadata['track_number'])
        if metadata.get('genre'):
            audio_file.tags['genre'] = metadata['genre']
    
    @staticmethod
    def embed_album_art(filepath: Path, image_path: Path) -> bool:
        """Embed album art into audio file."""
        try:
            audio_file = File(filepath)
            if audio_file is None:
                return False
            
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            if isinstance(audio_file, MP3):
                if audio_file.tags is None:
                    audio_file.add_tags()
                audio_file.tags.add(
                    APIC(
                        encoding=3,
                        mime='image/jpeg' if image_path.suffix.lower() in ['.jpg', '.jpeg'] else 'image/png',
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=image_data
                    )
                )
            elif isinstance(audio_file, MP4):
                cover_format = MP4Cover.FORMAT_JPEG if image_path.suffix.lower() in ['.jpg', '.jpeg'] else MP4Cover.FORMAT_PNG
                audio_file.tags['covr'] = [MP4Cover(image_data, imageformat=cover_format)]
            elif isinstance(audio_file, FLAC):
                import mutagen.flac
                picture = mutagen.flac.Picture()
                picture.type = 3  # Cover (front)
                picture.mime = 'image/jpeg' if image_path.suffix.lower() in ['.jpg', '.jpeg'] else 'image/png'
                picture.desc = 'Cover'
                picture.data = image_data
                audio_file.clear_pictures()
                audio_file.add_picture(picture)
            
            audio_file.save()
            return True
            
        except Exception as e:
            logger.error(f"Error embedding album art in {filepath}: {e}")
            return False
    
    @staticmethod
    def extract_album_art(filepath: Path, output_path: Path) -> bool:
        """Extract album art from audio file."""
        try:
            audio_file = File(filepath)
            if audio_file is None:
                return False
            
            image_data = None
            
            if isinstance(audio_file, MP3) and audio_file.tags:
                for tag in audio_file.tags.values():
                    if isinstance(tag, APIC):
                        image_data = tag.data
                        break
            elif isinstance(audio_file, MP4) and audio_file.tags:
                covers = audio_file.tags.get('covr', [])
                if covers:
                    image_data = bytes(covers[0])
            elif isinstance(audio_file, FLAC):
                if audio_file.pictures:
                    image_data = audio_file.pictures[0].data
            
            if image_data:
                with open(output_path, 'wb') as img_file:
                    img_file.write(image_data)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error extracting album art from {filepath}: {e}")
            return False
