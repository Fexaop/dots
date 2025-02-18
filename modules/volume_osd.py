from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from gi.repository import GLib, Gdk
import subprocess, re

def create_progress_bar(percentage, width=150):
    """Return a Box widget that looks like a progress bar"""
    container = Box(orientation='h', name="progress-container")
    progress = Box(name="progress-fill", style=f"min-width: {percentage * width / 100}px;")
    background = Box(name="progress-background", style=f"min-width: {width}px;")
    background.children = [progress]
    container.children = [background]
    return container

def get_brightness():
    # Uses brightnessctl to get current and max brightness, then computes percentage.
    try:
        current = int(subprocess.check_output(["brightnessctl", "g"], encoding="utf-8").strip())
        maximum = int(subprocess.check_output(["brightnessctl", "m"], encoding="utf-8").strip())
        return int((current / maximum) * 100)
    except Exception as e:
        print("Error getting brightness:", e)
    return None

def get_volume_percentage():
    # Get current volume percentage from pactl output.
    try:
        out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], universal_newlines=True)
        m = re.search(r"(\d+)%", out)
        if m:
            return int(m.group(1))
    except Exception:
        return None

class VolumeOSD(Window):
    def __init__(self):
        super().__init__(
            name="volume-osd",
            layer="overlay",
            anchor="top center",
            margin="5px 0 0 0",
            exclusivity="none",
            visible=False,
        )
        
        self.brightness_label = Label(name="brightness-label", markup="Brightness: --%")
        self.brightness_progress = Box(name="brightness-progress")
        self.volume_label = Label(name="volume-label", markup="Volume: --%")
        self.volume_progress = Box(name="volume-progress")
        
        # Create a horizontal box as main container
        self.children = Box(
            orientation='h',
            spacing=0,
            children=[
                # Brightness section
                Box(name="control-section", orientation='v', spacing=8, children=[
                    self.brightness_label,
                    self.brightness_progress
                ]),
                # Separator
                # Box(name="osd-separator"),
                # Volume section
                Box(name="control-section", orientation='v', spacing=8, children=[
                    self.volume_label,
                    self.volume_progress
                ])
            ]
        )
        
        self.hide_timeout_id = None
        self.last_volume = get_volume_percentage()
        self.displayed_brightness = get_brightness()
        self._start_monitoring()
        GLib.timeout_add(150, self._check_brightness)

    def _start_monitoring(self):
        # Start pactl subscribe and attach a GLib IO watch to its stdout.
        self.subscribe_proc = subprocess.Popen(
            ["pactl", "subscribe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            universal_newlines=True,
        )
        if self.subscribe_proc.stdout:
            GLib.io_add_watch(self.subscribe_proc.stdout, GLib.IO_IN, self._on_volume_event)

    def _on_volume_event(self, source, condition):
        # Read one line from pactl subscribe output.
        line = source.readline()
        if "sink" in line.lower():
            self.update_osd()
        return True

    def _check_brightness(self):
        # Periodically check brightness and update.
        current = get_brightness()
        if current is not None:
            self.update_osd()
        return True

    def update_osd(self):
        current_vol = get_volume_percentage()
        current_bri = get_brightness()
        # Fallback to stored volume if None
        if current_vol is None:
            current_vol = self.last_volume
        # Only update if either volume or brightness has changed.
        if current_vol == self.last_volume and current_bri == self.displayed_brightness:
            return
        self.last_volume = current_vol
        self.displayed_brightness = current_bri
        
        self.brightness_label.set_markup(f"<span font='14'>Brightness: {current_bri}%</span>")
        self.volume_label.set_markup(f"<span font='14'>Volume: {current_vol}%</span>")
        
        self.brightness_progress.children = create_progress_bar(current_bri or 0)
        self.volume_progress.children = create_progress_bar(current_vol or 0)
        
        self.show_all()
        if self.hide_timeout_id is not None:
            GLib.source_remove(self.hide_timeout_id)
        self.hide_timeout_id = GLib.timeout_add(1500, self.hide_osd)

    def show_volume(self):
        # Alias for update_osd to support existing calls.
        self.update_osd()

    def hide_osd(self):
        self.hide()
        self.hide_timeout_id = None
        return False

