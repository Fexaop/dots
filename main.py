import setproctitle
import os
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
    monitor = file.monitor(Gio.FileMonitorFlags.NONE, None)
    return monitor

if __name__ == "__main__":
    setproctitle.setproctitle("ax-shell")
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

    app.set_css = apply_css

    # Set up file monitoring for CSS changes
    css_path = get_relative_path("main.css")
    style_monitor = monitor_file(css_path)
    style_monitor.connect("changed", apply_css)
    
    # Apply initial styling
    apply_css()

    app.run()
