"""Player controls for playback actions."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Pango

from ..utils.file_utils import FileUtils


class PlayerControls(Gtk.Box):
    """Control bar for playback actions."""

    __gsignals__ = {
        'control-action': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, audio_player):
        """Initialize player controls."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("toolbar")
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.audio_player = audio_player

        # Progress bar section
        progress_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        progress_box.set_margin_bottom(6)
        self.append(progress_box)

        # Current time label
        self.time_label = Gtk.Label(label="0:00")
        self.time_label.add_css_class("dim-label")
        self.time_label.add_css_class("caption")
        self.time_label.set_size_request(45, -1)
        progress_box.append(self.time_label)

        # Progress bar
        self.progress_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.progress_bar.set_range(0, 100)
        self.progress_bar.set_hexpand(True)
        self.progress_bar.set_draw_value(False)
        self.progress_bar.connect("value-changed", self._on_seek)
        self._seeking = False
        progress_box.append(self.progress_bar)

        # Duration label
        self.duration_label = Gtk.Label(label="0:00")
        self.duration_label.add_css_class("dim-label")
        self.duration_label.add_css_class("caption")
        self.duration_label.set_size_request(45, -1)
        progress_box.append(self.duration_label)

        # Controls section
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        controls_box.set_halign(Gtk.Align.CENTER)
        controls_box.set_spacing(6)
        self.append(controls_box)

        # Track info section (left side)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        info_box.set_size_request(250, -1)
        info_box.set_halign(Gtk.Align.START)
        info_box.set_margin_end(24)
        controls_box.append(info_box)

        self.track_title_label = Gtk.Label()
        self.track_title_label.set_halign(Gtk.Align.START)
        self.track_title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.track_title_label.add_css_class("heading")
        info_box.append(self.track_title_label)

        self.track_artist_label = Gtk.Label()
        self.track_artist_label.set_halign(Gtk.Align.START)
        self.track_artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.track_artist_label.add_css_class("dim-label")
        info_box.append(self.track_artist_label)

        # Playback controls (center)
        playback_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls_box.append(playback_box)

        # Previous button
        self.prev_button = Gtk.Button()
        self.prev_button.set_icon_name('media-skip-backward-symbolic')
        self.prev_button.add_css_class("circular")
        self.prev_button.connect('clicked', lambda w: self.emit('control-action', 'previous'))
        playback_box.append(self.prev_button)

        # Play/Pause button
        self.play_pause_button = Gtk.Button()
        self.play_pause_button.set_icon_name('media-playback-start-symbolic')
        self.play_pause_button.add_css_class("circular")
        self.play_pause_button.add_css_class("suggested-action")
        self.play_pause_button.set_size_request(48, 48)
        self.play_pause_button.connect('clicked', self._on_play_pause_clicked)
        playback_box.append(self.play_pause_button)

        # Next button
        self.next_button = Gtk.Button()
        self.next_button.set_icon_name('media-skip-forward-symbolic')
        self.next_button.add_css_class("circular")
        self.next_button.connect('clicked', lambda w: self.emit('control-action', 'next'))
        playback_box.append(self.next_button)

        # Additional controls (right side)
        extra_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        extra_controls.set_halign(Gtk.Align.END)
        extra_controls.set_size_request(250, -1)
        extra_controls.set_margin_start(24)
        controls_box.append(extra_controls)

        # Shuffle button
        self.shuffle_button = Gtk.ToggleButton()
        self.shuffle_button.set_icon_name('media-playlist-shuffle-symbolic')
        self.shuffle_button.add_css_class("flat")
        self.shuffle_button.connect('toggled', lambda w: self.emit('control-action', 'shuffle'))
        extra_controls.append(self.shuffle_button)

        # Repeat button
        self.repeat_button = Gtk.Button()
        self.repeat_button.set_icon_name('media-playlist-repeat-symbolic')
        self.repeat_button.add_css_class("flat")
        self.repeat_button.connect('clicked', lambda w: self.emit('control-action', 'repeat'))
        extra_controls.append(self.repeat_button)

        # Volume control
        self.volume_button = Gtk.VolumeButton()
        self.volume_button.set_value(self.audio_player.get_volume())
        self.volume_button.connect('value-changed', self._on_volume_changed)
        extra_controls.append(self.volume_button)

    def _on_play_pause_clicked(self, button):
        """Handle play/pause button press."""
        self.emit('control-action', 'play_pause')
        if self.audio_player.is_playing():
            button.set_icon_name('media-playback-start-symbolic')
        else:
            button.set_icon_name('media-playback-pause-symbolic')

    def _on_volume_changed(self, button, value):
        """Handle volume change."""
        self.audio_player.set_volume(value)

    def _on_seek(self, scale):
        """Handle seeking in the track."""
        if not self._seeking:
            value = scale.get_value()
            duration = self.audio_player.get_duration()
            if duration > 0:
                position = (value / 100.0) * duration
                self.audio_player.seek(position)

    def set_track_info(self, title, artist):
        """Update track info labels."""
        self.track_title_label.set_text(title or "No track playing")
        self.track_artist_label.set_text(artist or "Unknown artist")

    def update_position(self, position, duration):
        """Update position of the track in UI."""
        if duration > 0:
            # Update progress bar
            self._seeking = True
            self.progress_bar.set_value((position / duration) * 100)
            self._seeking = False
            
            # Update time labels
            self.time_label.set_text(FileUtils.format_duration(position))
            self.duration_label.set_text(FileUtils.format_duration(duration))
    
    def update_play_state(self, is_playing):
        """Update play/pause button icon."""
        if is_playing:
            self.play_pause_button.set_icon_name('media-playback-pause-symbolic')
        else:
            self.play_pause_button.set_icon_name('media-playback-start-symbolic')
    
    def set_shuffle_state(self, enabled):
        """Update shuffle button state."""
        self.shuffle_button.set_active(enabled)
    
    def set_repeat_mode(self, mode):
        """Update repeat button icon based on mode."""
        if mode == "none":
            self.repeat_button.set_icon_name('media-playlist-repeat-symbolic')
            self.repeat_button.remove_css_class("accent")
        elif mode == "track":
            self.repeat_button.set_icon_name('media-playlist-repeat-song-symbolic')
            self.repeat_button.add_css_class("accent")
        elif mode == "playlist":
            self.repeat_button.set_icon_name('media-playlist-repeat-symbolic')
            self.repeat_button.add_css_class("accent")

