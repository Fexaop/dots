from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import GLib
import modules.icons as icons
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
    try:
        current = int(subprocess.check_output(["brightnessctl", "g"], encoding="utf-8").strip())
        maximum = int(subprocess.check_output(["brightnessctl", "m"], encoding="utf-8").strip())
        return int((current / maximum) * 100)
    except Exception as e:
        print("Error getting brightness:", e)
    return None

def get_volume_percentage():
    try:
        out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], universal_newlines=True)
        m = re.search(r"(\d+)%", out)
        if m:
            return int(m.group(1))
    except Exception:
        return None

class OSDMenu(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="osd-menu",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            v_expand=True,
            h_expand=True,
            visible=True,
            **kwargs,
        )

        self.notch = kwargs["notch"]
        
        # Volume section
        self.volume_label = Label(name="osd-label", markup="Volume: --%")
        self.volume_progress = Box(name="osd-progress")
        
        # Brightness section
        self.brightness_label = Label(name="osd-label", markup="Brightness: --%")
        self.brightness_progress = Box(name="osd-progress")

        # Create containers
        self.volume_container = Box(
            name="control-section",
            orientation='v',
            spacing=8,
            children=[self.volume_label, self.volume_progress]
        )

        self.brightness_container = Box(
            name="control-section",
            orientation='v',
            spacing=8,
            children=[self.brightness_label, self.brightness_progress]
        )

        # Add containers to main box
        self.add(self.brightness_container)
        self.add(self.volume_container)

        self.timeout_id = None
        self.last_volume = get_volume_percentage()
        self.displayed_brightness = get_brightness()
        self._start_monitoring()
        GLib.timeout_add(150, self._check_brightness)

    def update_volume(self, percentage):
        self.volume_label.set_markup(f"Volume: {percentage}%")
        self.volume_progress.children = create_progress_bar(percentage)
        self._reset_timeout()

    def update_brightness(self, percentage):
        self.brightness_label.set_markup(f"Brightness: {percentage}%")
        self.brightness_progress.children = create_progress_bar(percentage)
        self._reset_timeout()

    def _reset_timeout(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
        self.timeout_id = GLib.timeout_add(1500, self.close_menu)

    def close_menu(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None
        self.notch.close_notch()
        return False

    def _start_monitoring(self):
        # Start pactl subscribe and attach a GLib IO watch to its stdout
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
        line = source.readline()
        if "sink" in line.lower():
            self._check_changes()
        return True

    def _check_brightness(self):
        current = get_brightness()
        if current is not None:
            self._check_changes()
        return True

    def _check_changes(self):
        current_vol = get_volume_percentage()
        current_bri = get_brightness()
        
        if current_vol is None:
            current_vol = self.last_volume
            
        # Only update if either value has changed
        if current_vol != self.last_volume or current_bri != self.displayed_brightness:
            self.last_volume = current_vol
            self.displayed_brightness = current_bri
            self.notch.open_notch("osd")
            self.update_volume(current_vol or 0)
            self.update_brightness(current_bri or 0)
