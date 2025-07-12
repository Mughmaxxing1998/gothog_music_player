"""Main window implementation for Gothog Music Player."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import logging
from pathlib import Path

from ..core import PlaylistManager, AudioPlayer
from .playlist_sidebar import PlaylistSidebar
from .track_list import TrackList
from .player_controls import PlayerControls

logger = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    """Main application window."""
    
    def __init__(self, app):
        """Initialize the main window."""
        super().__init__(application=app)
        
        # Window properties
        self.set_title("Gothog Music Player")
        self.set_default_size(1200, 700)
        
        # Core components
        self.playlist_manager = PlaylistManager()
        self.audio_player = AudioPlayer()
        
        # Current playlist state
        self.current_playlist = None
        self.current_track_index = -1
        
        # Build UI
        self._build_ui()
        
        # Set up audio player callbacks
        self.audio_player.set_callbacks(
            on_end=self._on_track_end,
            on_error=self._on_playback_error,
            on_position=self._on_position_update
        )
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # Header bar
        self._create_header_bar()
        
        # Content area (horizontal split)
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.set_vexpand(True)
        main_box.append(content_box)
        
        # Sidebar with playlists
        self.playlist_sidebar = PlaylistSidebar(self.playlist_manager)
        self.playlist_sidebar.set_size_request(300, -1)
        self.playlist_sidebar.connect('playlist-selected', self._on_playlist_selected)
        self.playlist_sidebar.connect('playlist-action', self._on_playlist_action)
        content_box.append(self.playlist_sidebar)
        
        # Main content area
        main_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_content.set_hexpand(True)
        content_box.append(main_content)
        
        # Track list
        self.track_list = TrackList()
        self.track_list.set_vexpand(True)
        self.track_list.connect('track-activated', self._on_track_activated)
        self.track_list.connect('track-reordered', self._on_track_reordered)
        
        # Scrolled window for track list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.track_list)
        main_content.append(scrolled)
        
        # Player controls at bottom
        self.player_controls = PlayerControls(self.audio_player)
        self.player_controls.connect('control-action', self._on_control_action)
        main_box.append(self.player_controls)
        
        # Right panel (optional) - initially hidden
        self.right_panel = self._create_right_panel()
        self.right_panel.set_visible(False)
        content_box.append(self.right_panel)
    
    def _create_header_bar(self):
        """Create the header bar."""
        header = Adw.HeaderBar()
        self.set_titlebar(header)
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        header.pack_end(menu_button)
        
        # Create menu
        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("Keyboard Shortcuts", "app.shortcuts")
        menu.append("About", "app.about")
        menu_button.set_menu_model(menu)
        
        # Settings button for current playlist
        self.playlist_settings_btn = Gtk.Button()
        self.playlist_settings_btn.set_icon_name("emblem-system-symbolic")
        self.playlist_settings_btn.set_tooltip_text("Playlist Settings")
        self.playlist_settings_btn.connect("clicked", self._on_playlist_settings)
        self.playlist_settings_btn.set_sensitive(False)
        header.pack_end(self.playlist_settings_btn)
    
    def _create_right_panel(self):
        """Create the right panel for metadata/lyrics."""
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.set_size_request(250, -1)
        panel.add_css_class("sidebar")
        
        # Panel header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.set_margin_top(12)
        header.set_margin_bottom(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        panel.append(header)
        
        label = Gtk.Label(label="Track Info")
        label.add_css_class("title-4")
        header.append(label)
        
        # Close button
        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", lambda w: panel.set_visible(False))
        header.pack_end(close_btn, False, False, 0)
        
        # Separator
        panel.append(Gtk.Separator())
        
        # Content area
        self.info_stack = Gtk.Stack()
        panel.append(self.info_stack)
        
        # Album art view
        art_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        art_box.set_margin_top(12)
        art_box.set_margin_bottom(12)
        art_box.set_margin_start(12)
        art_box.set_margin_end(12)
        
        self.album_art_image = Gtk.Picture()
        self.album_art_image.set_size_request(200, 200)
        art_box.append(self.album_art_image)
        
        self.info_stack.add_titled(art_box, "art", "Album Art")
        
        # Metadata view
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        metadata_box.set_margin_top(12)
        metadata_box.set_margin_bottom(12)
        metadata_box.set_margin_start(12)
        metadata_box.set_margin_end(12)
        
        self.metadata_label = Gtk.Label()
        self.metadata_label.set_wrap(True)
        metadata_box.append(self.metadata_label)
        
        self.info_stack.add_titled(metadata_box, "metadata", "Details")
        
        return panel
    
    def _on_playlist_selected(self, sidebar, playlist_name):
        """Handle playlist selection."""
        logger.info(f"Selected playlist: {playlist_name}")
        
        playlist = self.playlist_manager.get_playlist(playlist_name)
        if playlist:
            self.current_playlist = playlist
            self.current_track_index = -1
            self.track_list.load_playlist(playlist)
            self.playlist_settings_btn.set_sensitive(True)
            
            # Update window title
            self.set_title(f"Gothog Music Player - {playlist_name}")
    
    def _on_playlist_action(self, sidebar, action, data):
        """Handle playlist actions from sidebar."""
        logger.info(f"Playlist action: {action}, data: {data}")
        
        if action == "create":
            self._create_new_playlist()
        elif action == "download":
            self._download_playlist()
        elif action == "delete":
            self._delete_playlist(data)
        elif action == "rename":
            self._rename_playlist(data)
    
    def _on_track_activated(self, track_list, index):
        """Handle track activation (double-click)."""
        if self.current_playlist and 0 <= index < len(self.current_playlist.tracks):
            self.current_track_index = index
            self._play_current_track()
    
    def _on_track_reordered(self, track_list, old_index, new_index):
        """Handle track reordering."""
        if self.current_playlist:
            self.current_playlist.reorder_tracks(old_index, new_index)
            
            # Update current track index if needed
            if self.current_track_index == old_index:
                self.current_track_index = new_index
            elif old_index < self.current_track_index <= new_index:
                self.current_track_index -= 1
            elif new_index <= self.current_track_index < old_index:
                self.current_track_index += 1
    
    def _on_control_action(self, controls, action):
        """Handle player control actions."""
        logger.info(f"Control action: {action}")
        
        if action == "play_pause":
            if self.audio_player.is_playing():
                self.audio_player.pause()
            else:
                if self.current_track_index >= 0:
                    self._play_current_track()
                elif self.current_playlist and self.current_playlist.tracks:
                    self.current_track_index = 0
                    self._play_current_track()
        
        elif action == "previous":
            self._play_previous()
        
        elif action == "next":
            self._play_next()
        
        elif action == "shuffle":
            if self.current_playlist:
                self.current_playlist.settings.shuffle_enabled = not self.current_playlist.settings.shuffle_enabled
                self.current_playlist.save()
        
        elif action == "repeat":
            if self.current_playlist:
                modes = ["none", "track", "playlist"]
                current_mode = self.current_playlist.settings.repeat_mode
                next_index = (modes.index(current_mode) + 1) % len(modes)
                self.current_playlist.settings.repeat_mode = modes[next_index]
                self.current_playlist.save()
    
    def _play_current_track(self):
        """Play the current track."""
        if not self.current_playlist or self.current_track_index < 0:
            return
        
        track_path = self.current_playlist.get_track_path(self.current_track_index)
        if track_path and track_path.exists():
            self.audio_player.play(track_path)
            self.track_list.set_playing_track(self.current_track_index)
            
            # Update track info
            track = self.current_playlist.tracks[self.current_track_index]
            self.player_controls.set_track_info(track.title, track.artist)
            
            # Start position updater
            self.audio_player._start_position_updater()
    
    def _play_next(self):
        """Play the next track."""
        if not self.current_playlist or not self.current_playlist.tracks:
            return
        
        if self.current_playlist.settings.shuffle_enabled:
            # TODO: Implement shuffle logic
            pass
        else:
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist.tracks)
        
        self._play_current_track()
    
    def _play_previous(self):
        """Play the previous track."""
        if not self.current_playlist or not self.current_playlist.tracks:
            return
        
        # If more than 3 seconds into track, restart it
        if self.audio_player.get_position() > 3.0:
            self.audio_player.seek(0)
        else:
            self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist.tracks)
            self._play_current_track()
    
    def _on_track_end(self):
        """Handle track end event."""
        if not self.current_playlist:
            return
        
        # Update play statistics
        self.current_playlist.update_track_stats(self.current_track_index, played=True)
        
        # Handle repeat mode
        if self.current_playlist.settings.repeat_mode == "track":
            self._play_current_track()
        elif self.current_playlist.settings.repeat_mode == "playlist" or self.current_track_index < len(self.current_playlist.tracks) - 1:
            self._play_next()
        else:
            # End of playlist
            self.audio_player.stop()
            self.track_list.set_playing_track(-1)
    
    def _on_playback_error(self, error):
        """Handle playback error."""
        logger.error(f"Playback error: {error}")
        # TODO: Show error dialog
    
    def _on_position_update(self, position, duration):
        """Handle position update from audio player."""
        self.player_controls.update_position(position, duration)
    
    def _on_playlist_settings(self, button):
        """Show playlist settings dialog."""
        if self.current_playlist:
            # TODO: Implement playlist settings dialog
            logger.info("Show playlist settings")
    
    def _create_new_playlist(self):
        """Create a new playlist."""
        # TODO: Implement create playlist dialog
        logger.info("Create new playlist")
    
    def _download_playlist(self):
        """Download a playlist from URL."""
        # TODO: Implement download playlist dialog
        logger.info("Download playlist")
    
    def _delete_playlist(self, playlist_name):
        """Delete a playlist."""
        # TODO: Implement confirmation dialog
        if self.playlist_manager.delete_playlist(playlist_name):
            self.playlist_sidebar.refresh()
            if self.current_playlist and self.current_playlist.name == playlist_name:
                self.current_playlist = None
                self.track_list.clear()
    
    def _rename_playlist(self, playlist_name):
        """Rename a playlist."""
        # TODO: Implement rename dialog
        logger.info(f"Rename playlist: {playlist_name}")
