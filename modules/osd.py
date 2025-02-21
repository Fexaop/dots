from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import GLib
import modules.icons as icons
import subprocess, re
from fabric.widgets.eventbox import EventBox  # Add this import

def create_progress_bar(percentage, width=150, height=None):
    """Return a Box widget that looks like a progress bar"""
    container = Box(orientation='v', name="progress-container", v_align="center")
    style = f"min-width: {percentage * width / 100}px;"
    bg_style = f"min-width: {width}px;"
    
    if height is not None:
        style += f" min-height: {height}px; margin: 0;"
        bg_style += f" min-height: {height}px; margin: 0;"
    
    progress = Box(name="progress-fill", style=style)
    background = Box(name="progress-background", style=bg_style)
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

class OSDMenu(Box):  # Change back to Box
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
        )
        
        self.notch = kwargs["notch"]
        self.is_hovered = False
        self.timeout_id = None
        self.hover_timer_id = None
        self.hover_activated = False
        
        # Create eventbox for hover detection
        self.event_area = EventBox(
            v_expand=True,
            h_expand=True
        )
        # Disable focus on event_area so scroll events are not intercepted.
        self.event_area.set_can_focus(False)
        
        # Prevent OSDMenu from gaining focus by intercepting focus-in events.
        self.set_can_focus(False)
        self.connect("focus-in-event", self._on_focus_in)
        
        # Create inner container
        self.inner_box = Box(
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            v_expand=True,
            h_expand=True,
        )
        
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

        # Build widget hierarchy
        self.inner_box.add(self.brightness_container)
        self.inner_box.add(self.volume_container)
        self.event_area.add(self.inner_box)
        self.add(self.event_area)

        # Initialize state with current values
        self.last_volume = get_volume_percentage() or 0  # Ensure we have a default value
        self.displayed_brightness = get_brightness() or 0  # Ensure we have a default value
        
        # Update displays immediately
        self.volume_label.set_markup(f"Volume: {self.last_volume}%")
        self.volume_progress.children = create_progress_bar(self.last_volume)
        self.brightness_label.set_markup(f"Brightness: {self.displayed_brightness}%")
        self.brightness_progress.children = create_progress_bar(self.displayed_brightness)
        
        # Setup monitoring
        self._start_monitoring()
        GLib.timeout_add(150, self._check_brightness)

        # Connect events
        self.event_area.connect('enter-notify-event', self._on_hover_enter)
        self.event_area.connect('leave-notify-event', self._on_hover_leave)

    # New handler to consume focus events.
    def _on_focus_in(self, widget, event):
        return True  # Consume the event, preventing focus.

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
        if not self.is_hovered:
            self.timeout_id = GLib.timeout_add(1500, self._delayed_close)

    def _delayed_close(self):
        if not self.is_hovered:
            self.close_menu()
        return False

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
        
        # Use existing values if new ones can't be fetched
        if current_vol is None:
            current_vol = self.last_volume
        if current_bri is None:
            current_bri = self.displayed_brightness
            
        # Update if either value changed
        if current_vol != self.last_volume or current_bri != self.displayed_brightness:
            self.last_volume = current_vol
            self.displayed_brightness = current_bri
            self.notch.open_notch("osd")
            self.update_volume(current_vol)
            self.update_brightness(current_bri)

    def _on_hover_enter(self, widget, event):
        self.is_hovered = True
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None
        
        # Start hover duration timer
        self.hover_timer_id = GLib.timeout_add(1500, self._on_hover_duration_reached)

    def _on_hover_leave(self, widget, event):
        self.is_hovered = False
        
        # Cancel hover timer if it exists
        if self.hover_timer_id:
            GLib.source_remove(self.hover_timer_id)
            self.hover_timer_id = None
        
        # If hover was long enough, use shorter close delay
        if self.hover_activated:
            self.timeout_id = GLib.timeout_add(500, self._delayed_close)
            self.hover_activated = False
        else:
            self._reset_timeout()

    def _on_hover_duration_reached(self):
        if self.is_hovered:
            self.hover_activated = True
        self.hover_timer_id = None
        return False
