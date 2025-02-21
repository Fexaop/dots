import setproctitle
import os
import shutil  # New import
from fabric import Application
from fabric.utils import get_relative_path
from modules.bar import Bar
from modules.notch import Notch
from modules.corners import Corners
from config.config import open_config

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

config_path = os.path.expanduser("~/.config/Ax-Shell/config/config.json")

def monitor_file(path):
    file = Gio.File.new_for_path(path)
    monitor = file.monitor(Gio.FileMonitorFlags.WATCH_MOVES, None)
    return monitor

def monitor_directory_recursive(directory, callback):
    monitors = []
    
    for root, dirs, files in os.walk(directory):
        # Monitor the directory itself
        dir_monitor = monitor_file(root)
        dir_monitor.connect("changed", callback)
        monitors.append(dir_monitor)
        
        # Monitor CSS files in this directory
        for file in files:
            if file.endswith('.css'):
                file_path = os.path.join(root, file)
                file_monitor = monitor_file(file_path)
                file_monitor.connect("changed", callback)
                monitors.append(file_monitor)
    
    return monitors

if __name__ == "__main__":
    setproctitle.setproctitle("ax-shell")
    
    # Clear the cache directory
    cache_path = os.path.expanduser("~/.config/Ax-Shell/cache")
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path)
    os.makedirs(cache_path, exist_ok=True)
    
    if not os.path.isfile(config_path):
        open_config()
    corners = Corners()
    bar = Bar()
    notch = Notch()
    bar.notch = notch
    app = Application("ax-shell", bar, notch)

    def apply_css(*_):
        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
            exposed_functions={
                "overview_width": lambda: f"min-width: {CURRENT_WIDTH * 0.1 * 5}px;",
                "overview_height": lambda: f"min-height: {CURRENT_HEIGHT * 0.1 * 2}px;",
            },
        )

    # Set up recursive file monitoring for CSS changes
    styles_dir = get_relative_path("styles")
    style_monitors = monitor_directory_recursive(styles_dir, apply_css)
    
    # Apply initial styling
    apply_css()

    app.run()
