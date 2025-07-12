"""Track list component for displaying playlist tracks."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gdk, Pango, Gio
import logging

from ..utils.file_utils import FileUtils

logger = logging.getLogger(__name__)


class TrackList(Gtk.ListView):
    """Track list widget for displaying playlist tracks."""
    
    __gsignals__ = {
        'track-activated': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'track-reordered': (GObject.SignalFlags.RUN_FIRST, None, (int, int))
    }
    
    def __init__(self):
        """Initialize the track list."""
        super().__init__()
        
        self.playlist = None
        self.playing_index = -1
        
        # Set up the model using Gio.ListStore with custom objects
        self.store = Gio.ListStore()
        
        # Create selection model
        self.selection = Gtk.SingleSelection(model=self.store)
        self.set_model(self.selection)
        
        # Create the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        self.set_factory(factory)
        
        # Connect signals
        self.connect("activate", self._on_row_activated)
    
    def _on_factory_setup(self, factory, list_item):
        """Set up the factory for list items."""
        # Create a box for the track row
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Track number
        track_label = Gtk.Label()
        track_label.set_size_request(30, -1)
        track_label.add_css_class("dim-label")
        box.append(track_label)
        
        # Title and artist box
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        info_box.set_hexpand(True)
        box.append(info_box)
        
        title_label = Gtk.Label()
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.add_css_class("body")
        info_box.append(title_label)
        
        artist_label = Gtk.Label()
        artist_label.set_halign(Gtk.Align.START)
        artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        artist_label.add_css_class("dim-label")
        artist_label.add_css_class("caption")
        info_box.append(artist_label)
        
        # Duration
        duration_label = Gtk.Label()
        duration_label.add_css_class("dim-label")
        box.append(duration_label)
        
        # Store references
        box.track_label = track_label
        box.title_label = title_label
        box.artist_label = artist_label
        box.duration_label = duration_label
        
        list_item.set_child(box)
    
    def _on_factory_bind(self, factory, list_item):
        """Bind data to the factory."""
        track_data = list_item.get_item()
        box = list_item.get_child()
        
        # Update labels
        box.track_label.set_text(str(track_data.track_number))
        box.title_label.set_text(track_data.title)
        box.artist_label.set_text(f"{track_data.artist or 'Unknown Artist'} • {track_data.album or 'Unknown Album'}")
        box.duration_label.set_text(track_data.duration_str)
        
        # Highlight playing track
        if track_data.is_playing:
            box.add_css_class("accent")
        else:
            box.remove_css_class("accent")
    
    def load_playlist(self, playlist):
        """Load a playlist into the track list."""
        self.playlist = playlist
        self.store.remove_all()
        
        for i, track in enumerate(playlist.tracks):
            track_item = TrackItem(
                index=i,
                track_number=track.track_number or (i + 1),
                title=track.title,
                artist=track.artist,
                album=track.album,
                duration=track.duration,
                duration_str=FileUtils.format_duration(track.duration),
                is_playing=False
            )
            self.store.append(track_item)
    
    def clear(self):
        """Clear the track list."""
        self.playlist = None
        self.store.remove_all()
        self.playing_index = -1
    
    def set_playing_track(self, index):
        """Set the currently playing track."""
        # Clear previous playing state
        if 0 <= self.playing_index < self.store.get_n_items():
            item = self.store.get_item(self.playing_index)
            item.is_playing = False
        
        # Set new playing state
        self.playing_index = index
        if 0 <= index < self.store.get_n_items():
            item = self.store.get_item(index)
            item.is_playing = True
    
    def _on_row_activated(self, view, position):
        """Handle row activation (double-click)."""
        if 0 <= position < self.store.get_n_items():
            item = self.store.get_item(position)
            self.emit('track-activated', item.index)


class TrackItem(GObject.Object):
    """Data model for a track item."""
    
    def __init__(self, index, track_number, title, artist, album, duration, duration_str, is_playing):
        super().__init__()
        self.index = index
        self.track_number = track_number
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.duration_str = duration_str
        self.is_playing = is_playing
