"""Playlist sidebar component for displaying and managing playlists."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gdk, Pango
import logging

logger = logging.getLogger(__name__)


class PlaylistSidebar(Gtk.Box):
    """Sidebar widget for displaying playlists."""
    
    __gsignals__ = {
        'playlist-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'playlist-action': (GObject.SignalFlags.RUN_FIRST, None, (str, str))
    }
    
    def __init__(self, playlist_manager):
        """Initialize the playlist sidebar."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.playlist_manager = playlist_manager
        
        self.add_css_class("sidebar")
        
        # Header
        self._create_header()
        
        # Search entry
        self._create_search_entry()
        
        # Playlist list
        self._create_playlist_list()
        
        # Load playlists
        self.refresh()
    
    def _create_header(self):
        """Create the sidebar header."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(6)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        self.append(header_box)
        
        # Title
        title = Gtk.Label(label="Playlists")
        title.add_css_class("title-4")
        title.set_halign(Gtk.Align.START)
        header_box.append(title)
        
        # Add button
        add_button = Gtk.MenuButton()
        add_button.set_icon_name("list-add-symbolic")
        add_button.add_css_class("flat")
        add_button.set_tooltip_text("Add Playlist")
        header_box.append(add_button)
        
        # Create add menu
        menu = Gtk.PopoverMenu()
        add_button.set_popover(menu)
        
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        menu_box.set_spacing(3)
        menu.set_child(menu_box)
        
        # Create playlist button
        create_btn = Gtk.Button(label="Create New Playlist")
        create_btn.add_css_class("flat")
        create_btn.set_halign(Gtk.Align.START)
        create_btn.connect("clicked", lambda w: self._on_action("create", None))
        menu_box.append(create_btn)
        
        # Download playlist button
        download_btn = Gtk.Button(label="Download from URL")
        download_btn.add_css_class("flat")
        download_btn.set_halign(Gtk.Align.START)
        download_btn.connect("clicked", lambda w: self._on_action("download", None))
        menu_box.append(download_btn)
    
    def _create_search_entry(self):
        """Create the search entry."""
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search playlists...")
        self.search_entry.set_margin_start(12)
        self.search_entry.set_margin_end(12)
        self.search_entry.set_margin_bottom(6)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.append(self.search_entry)
    
    def _create_playlist_list(self):
        """Create the playlist list view."""
        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.append(scrolled)
        
        # List box
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-activated", self._on_row_activated)
        scrolled.set_child(self.listbox)
        
        # Set up filtering
        self.listbox.set_filter_func(self._filter_func)
        
        # Context menu
        self._setup_context_menu()
    
    def _setup_context_menu(self):
        """Set up right-click context menu."""
        gesture = Gtk.GestureClick()
        gesture.set_button(3)  # Right mouse button
        gesture.connect("pressed", self._on_right_click)
        self.listbox.add_controller(gesture)
        
        # Create popover menu
        self.context_menu = Gtk.PopoverMenu()
        
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        menu_box.set_spacing(3)
        self.context_menu.set_child(menu_box)
        
        # Menu items
        rename_btn = Gtk.Button(label="Rename")
        rename_btn.add_css_class("flat")
        rename_btn.set_halign(Gtk.Align.START)
        rename_btn.connect("clicked", self._on_rename_clicked)
        menu_box.append(rename_btn)
        
        delete_btn = Gtk.Button(label="Delete")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("destructive-action")
        delete_btn.set_halign(Gtk.Align.START)
        delete_btn.connect("clicked", self._on_delete_clicked)
        menu_box.append(delete_btn)
        
        self.context_menu_row = None
    
    def _on_right_click(self, gesture, n_press, x, y):
        """Handle right-click on playlist."""
        row = self.listbox.get_row_at_y(y)
        if row:
            self.context_menu_row = row
            self.context_menu.set_parent(row)
            self.context_menu.popup()
    
    def _on_rename_clicked(self, button):
        """Handle rename menu item."""
        self.context_menu.popdown()
        if self.context_menu_row:
            playlist_name = self.context_menu_row.get_child().playlist_name
            self.emit('playlist-action', 'rename', playlist_name)
    
    def _on_delete_clicked(self, button):
        """Handle delete menu item."""
        self.context_menu.popdown()
        if self.context_menu_row:
            playlist_name = self.context_menu_row.get_child().playlist_name
            self.emit('playlist-action', 'delete', playlist_name)
    
    def _create_playlist_row(self, playlist):
        """Create a row for a playlist."""
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row_box.set_margin_top(6)
        row_box.set_margin_bottom(6)
        row_box.set_margin_start(12)
        row_box.set_margin_end(12)
        row_box.set_spacing(12)
        
        # Store playlist name for later reference
        row_box.playlist_name = playlist.name
        
        # Icon
        icon = Gtk.Image()
        icon.set_from_icon_name("folder-music-symbolic")
        icon.set_pixel_size(24)
        row_box.append(icon)
        
        # Text box
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_box.set_hexpand(True)
        row_box.append(text_box)
        
        # Playlist name
        name_label = Gtk.Label(label=playlist.name)
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class("body")
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(name_label)
        
        # Track count and duration
        info_text = f"{playlist.track_count} tracks"
        if playlist.total_duration > 0:
            from ..utils.file_utils import FileUtils
            duration_str = FileUtils.format_duration(playlist.total_duration)
            info_text += f" • {duration_str}"
        
        info_label = Gtk.Label(label=info_text)
        info_label.set_halign(Gtk.Align.START)
        info_label.add_css_class("dim-label")
        info_label.add_css_class("caption")
        text_box.append(info_label)
        
        return row_box
    
    def refresh(self):
        """Refresh the playlist list."""
        # Clear existing items
        while True:
            row = self.listbox.get_row_at_index(0)
            if row:
                self.listbox.remove(row)
            else:
                break
        
        # Add playlists
        self.playlist_manager.refresh()
        for playlist in self.playlist_manager.get_all_playlists():
            row_content = self._create_playlist_row(playlist)
            self.listbox.append(row_content)
    
    def _filter_func(self, row):
        """Filter function for search."""
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        
        playlist_name = row.get_child().playlist_name.lower()
        return search_text in playlist_name
    
    def _on_search_changed(self, entry):
        """Handle search text change."""
        self.listbox.invalidate_filter()
    
    def _on_row_activated(self, listbox, row):
        """Handle playlist selection."""
        if row:
            playlist_name = row.get_child().playlist_name
            self.emit('playlist-selected', playlist_name)
    
    def _on_action(self, action, data):
        """Handle sidebar actions."""
        self.emit('playlist-action', action, data or "")
