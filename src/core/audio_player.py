"""Audio player engine using GStreamer for playback capabilities."""

import logging
from pathlib import Path
from typing import Optional, Callable, Dict
import gi
import threading

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Audio player class that leverages GStreamer for media playback."""
    
    def __init__(self):
        """Initialize the audio player."""
        Gst.init(None)
        self.pipeline = Gst.ElementFactory.make('playbin', 'playbin')
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_message)

        self._current_track: Optional[Path] = None
        self._volume: float = 0.8
        self._is_paused: bool = False
        self._duration: float = 0.0
        self._position_thread: Optional[threading.Thread] = None
        self._update_position: bool = False

        self._callbacks: Dict[str, Callable] = {
            'on_start': None,
            'on_end': None,
            'on_error': None,
            'on_position': None,
            'on_state_changed': None
        }

    def on_message(self, bus, message):
        """Handle GStreamer bus messages."""
        msg_type = message.type

        if msg_type == Gst.MessageType.EOS:
            logger.info('End-of-stream reached')
            self.pipeline.set_state(Gst.State.NULL)
            if self._callbacks['on_end']:
                self._callbacks['on_end']()

        elif msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f'Error: {err}, Debug Info: {debug}')
            if self._callbacks['on_error']:
                self._callbacks['on_error'](err)

        elif msg_type == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            if old_state == Gst.State.READY and new_state == Gst.State.PAUSED:
                if self._callbacks['on_start']:
                    self._callbacks['on_start'](self._current_track)

    def set_callbacks(self, on_start=None, on_end=None, on_error=None, on_position=None):
        """Set callbacks for player events."""
        self._callbacks['on_start'] = on_start
        self._callbacks['on_end'] = on_end
        self._callbacks['on_error'] = on_error
        self._callbacks['on_position'] = on_position

    def play(self, track_path: Path):
        """Play the specified track."""
        logger.info(f'Playing track: {track_path}')
        self._current_track = track_path
        self.pipeline.set_property('uri', track_path.as_uri())
        self.pipeline.set_state(Gst.State.PLAYING)

    def pause(self):
        """Pause the playback."""
        logger.info('Pausing playback')
        self.pipeline.set_state(Gst.State.PAUSED)

    def stop(self):
        """Stop the playback."""
        logger.info('Stopping playback')
        self.pipeline.set_state(Gst.State.NULL)

    def set_volume(self, level: float):
        """Set the playback volume."""
        logger.info(f'Setting volume to: {level}')
        if 0 <= level <= 1:
            self._volume = level
            self.pipeline.set_property('volume', self._volume)

    def get_position(self) -> float:
        """Get the current playback position in seconds."""
        success, position = self.pipeline.query_position(Gst.Format.TIME)
        if success:
            return position / Gst.SECOND
        return 0.0

    def seek(self, position_seconds: float):
        """Seek to a specific position in the track in seconds."""
        logger.info(f'Seeking to position: {position_seconds} seconds')
        self.pipeline.seek_simple(Gst.Format.TIME,
                                  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                  int(position_seconds * Gst.SECOND))

    def is_playing(self) -> bool:
        """Check if there is an active playback."""
        state = self.pipeline.get_state(1)[1]  # 1 second timeout
        return state == Gst.State.PLAYING
    
    def get_duration(self) -> float:
        """Get the duration of the current track in seconds."""
        success, duration = self.pipeline.query_duration(Gst.Format.TIME)
        if success:
            return duration / Gst.SECOND
        return 0.0
    
    def toggle_play_pause(self):
        """Toggle between play and pause states."""
        if self.is_playing():
            self.pause()
            self._is_paused = True
        else:
            if self._is_paused and self._current_track:
                self.pipeline.set_state(Gst.State.PLAYING)
                self._is_paused = False
    
    def get_volume(self) -> float:
        """Get the current volume level."""
        return self._volume
    
    def _start_position_updater(self):
        """Start the position update thread."""
        if self._position_thread and self._position_thread.is_alive():
            return
        
        self._update_position = True
        self._position_thread = threading.Thread(target=self._update_position_worker)
        self._position_thread.daemon = True
        self._position_thread.start()
    
    def _stop_position_updater(self):
        """Stop the position update thread."""
        self._update_position = False
        if self._position_thread:
            self._position_thread.join(timeout=1)
    
    def _update_position_worker(self):
        """Worker thread to update position."""
        import time
        while self._update_position:
            if self.is_playing() and self._callbacks['on_position']:
                position = self.get_position()
                duration = self.get_duration()
                GLib.idle_add(self._callbacks['on_position'], position, duration)
            time.sleep(0.1)
