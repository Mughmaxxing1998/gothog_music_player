project('gothog-music-player',
  version: '0.1.0',
  meson_version: '>= 0.59.0'
)

# Find Python installation
python = import('python').find_installation('python3')

# Define paths
prefix = get_option('prefix')
datadir = join_paths(prefix, get_option('datadir'))
pkgdatadir = join_paths(datadir, meson.project_name())

# Configuration data
conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('PKGDATADIR', pkgdatadir)

# Install Python modules
python_sources = [
  'src/__init__.py',
  'src/main.py',
  'src/ui/__init__.py',
  'src/ui/main_window.py',
  'src/ui/playlist_sidebar.py',
  'src/ui/track_list.py',
  'src/ui/player_controls.py',
  'src/core/__init__.py',
  'src/core/playlist_manager.py',
  'src/core/audio_player.py',
  'src/core/downloader.py',
  'src/utils/__init__.py',
  'src/utils/file_utils.py',
  'src/utils/metadata_utils.py',
]

# Install the main executable
configure_file(
  input: 'gothog-music-player.in',
  output: 'gothog-music-player',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

# Install desktop file
desktop_file = 'data/gothog-music-player.desktop'
if host_machine.system() == 'linux'
  install_data(desktop_file,
    install_dir: join_paths(datadir, 'applications')
  )
endif

# Install icon
icon_file = 'resources/icons/gothog-music-player.svg'
if host_machine.system() == 'linux'
  install_data(icon_file,
    install_dir: join_paths(datadir, 'icons', 'hicolor', 'scalable', 'apps')
  )
endif
