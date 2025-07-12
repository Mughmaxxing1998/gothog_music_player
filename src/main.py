#!/usr/bin/env python3
"""Main entry point for Gothog Music Player."""

import sys
import gi
import logging

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from .ui.main_window import MainWindow

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GothogMusicPlayer(Adw.Application):
    """Main application class."""
    
    def __init__(self):
        super().__init__(
            application_id='org.gothog.MusicPlayer',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self.window = None
    
    def do_activate(self):
        """Called when the application is activated."""
        if not self.window:
            self.window = MainWindow(self)
        self.window.present()
    
    def do_startup(self):
        """Called on application startup."""
        Adw.Application.do_startup(self)
        
        # Set up actions
        self._setup_actions()
        
        # Apply custom CSS if needed
        self._setup_css()
    
    def _setup_actions(self):
        """Set up application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        
        # Preferences action
        pref_action = Gio.SimpleAction.new("preferences", None)
        pref_action.connect("activate", self._on_preferences)
        self.add_action(pref_action)
        
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)
        
        # Keyboard shortcuts
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._on_shortcuts)
        self.add_action(shortcuts_action)
    
    def _setup_css(self):
        """Set up custom CSS styling."""
        css_provider = Gtk.CssProvider()
        css_data = """
        .accent {
            color: @accent_color;
        }
        
        .track-playing {
            font-weight: bold;
            color: @accent_color;
        }
        
        .player-controls {
            padding: 12px;
            background-color: @headerbar_bg_color;
        }
        """
        css_provider.load_from_data(css_data.encode())
        
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
    
    def _on_preferences(self, action, param):
        """Show preferences dialog."""
        logger.info("Show preferences")
        # TODO: Implement preferences dialog
    
    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name="Gothog Music Player",
            application_icon="org.gothog.MusicPlayer",
            developer_name="Gothog Music Player",
            version="0.1.0",
            developers=["Gothog Music Player"],
            copyright="© 2025 Gothog Music Player",
            license_type=Gtk.License.GPL_3_0,
            comments="A modern, playlist-focused music player built with GTK4",
            website="https://github.com/gothog/music-player"
        )
        about.present()
    
    def _on_shortcuts(self, action, param):
        """Show keyboard shortcuts."""
        logger.info("Show keyboard shortcuts")
        # TODO: Implement shortcuts dialog


def main():
    """Main entry point."""
    if not Gtk.init_check():
        logger.critical("Gtk couldn't be initialized.")
        return 1
    app = GothogMusicPlayer()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
