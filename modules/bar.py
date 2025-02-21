from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Workspaces, WorkspaceButton, ActiveWindow  # Added ActiveWindow
from fabric.utils.helpers import get_relative_path, exec_shell_command_async, FormattedString, truncate  # Added FormattedString and truncate
from gi.repository import GLib, Gdk, Gtk
from modules.systemtray import SystemTray
from config.config import open_config
import modules.icons as icons
import modules.data as data
import subprocess
import re
from modules.window_title_widget import WINDOW_TITLE_MAP

# New custom formatter for ActiveWindow
class WindowFormatter:
    def format(self, win_title, win_class):
        for pattern, icon, display in WINDOW_TITLE_MAP:
            if re.search(pattern, win_class, re.IGNORECASE):
                return f"{icon}  {display}"  # Modified: 2 spaces between icon and text
        return f"󰣆  {win_class.lower()}"  # Modified: 2 spaces between icon and text

class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            anchor="left top right",
            margin="-8px -4px -8px -4px",
            exclusivity="auto",
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs.get("notch", None)
        
        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h",
            spacing=10,
            buttons=[WorkspaceButton(id=i, label="") for i in range(1, 11)],
        )

        self.systray = SystemTray()
        # self.systray = SystemTray(name="systray", spacing=8, icon_size=20)

        self.date_time = DateTime(name="date-time", formatters=["%H:%M"], h_align="center", v_align="center")

        self.button_apps = Button(
            name="button-bar",
            on_clicked=lambda *_: self.search_apps(),
            child=Label(
                name="button-bar-label",
                markup=icons.apps
            )
        )
        self.button_apps.connect("enter_notify_event", self.on_button_enter)
        self.button_apps.connect("leave_notify_event", self.on_button_leave)
        
        self.button_power = Button(
            name="button-bar",
            on_clicked=lambda *_: self.power_menu(),
            child=Label(
                name="button-bar-label",
                markup=icons.shutdown
            )
        )
        self.button_power.connect("enter_notify_event", self.on_button_enter)
        self.button_power.connect("leave_notify_event", self.on_button_leave)

        self.button_overview = Button(
            name="button-bar",
            on_clicked=lambda *_: self.overview(),
            child=Label(
                name="button-bar-label",
                markup=icons.windows
            )
        )
        self.button_overview.connect("enter_notify_event", self.on_button_enter)
        self.button_overview.connect("leave_notify_event", self.on_button_leave)

        self.button_color = Button(
            name="button-bar",
            tooltip_text="Color Picker\nLeft Click: HEX\nMiddle Click: HSV\nRight Click: RGB",
            v_expand=False,
            child=Label(
                name="button-bar-label",
                markup=icons.colorpicker
            )
        )
        self.button_color.connect("enter-notify-event", self.on_button_enter)
        self.button_color.connect("leave-notify-event", self.on_button_leave)
        self.button_color.connect("button-press-event", self.colorpicker)

        self.button_config = Button(
            name="button-bar",
            on_clicked=lambda *_: exec_shell_command_async(f"python {data.HOME_DIR}/.config/Ax-Shell/config/config.py"),
            child=Label(
                name="button-bar-label",
                markup=icons.config
            )
        )

        # Remove the old single spacer button and add two new spacer buttons.
        self.button_test_left = Button(
            name="button-test-left",
#            on_clicked=lambda *_: exec_shell_command_async("notify-send 'test left'"),
            child=Label(
                name="button-test-left-label",
#                markup="<span foreground='red'>TEST LEFT</span>"
            ),
            h_expand=True,
        )
        # Add scroll event mask to receive scroll events.
        self.button_test_left.set_events(self.button_test_left.get_events() | Gdk.EventMask.SCROLL_MASK)
        # Connect scroll-event to change brightness
        self.button_test_left.connect("scroll-event", self.on_test_left_scroll)
        # Add gesture controller to support touchpad smooth scrolling
        self.gesture_left = Gtk.EventControllerScroll.new(
            self.button_test_left,
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.KINETIC
        )

        self.button_test_right = Button(
            name="button-test-right",
#            on_clicked=lambda *_: exec_shell_command_async("notify-send 'test right'"),
            child=Label(
                name="button-test-right-label",
#                markup="<span foreground='red'>TEST RIGHT</span>"
            ),
            h_expand=True,
        )
        # Add scroll event mask for volume control.
        self.button_test_right.set_events(self.button_test_right.get_events() | Gdk.EventMask.SCROLL_MASK)
        self.button_test_right.connect("scroll-event", self.on_test_right_scroll)
        self.gesture_right = Gtk.EventControllerScroll.new(
            self.button_test_right,
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.KINETIC
        )

        # Create an ActiveWindow widget with updated formatter using WindowFormatter.
        self.active_window = ActiveWindow(
            name="hyprland-window-bar",
            h_expand=True,
            formatter=WindowFormatter()
        )
        # Wrap the active_window in a Box if desired.
        active_window_box = Box(
            name="active-window-box",
            children=[self.active_window]
        )

        self.left_container = Box(
            name="start-container",
            spacing=4,
            orientation="h",
            children=[
                self.button_apps,
                Box(name="workspaces-container", children=[self.workspaces]),
                active_window_box,  # Newly added box to display the current active window.
                self.button_overview,
            ]
        )
        self.right_container = Box(
            name="end-container",
            spacing=4,
            orientation="h",
            children=[
                self.button_color,
                self.systray,
                self.button_config,
                self.date_time,
                self.button_power,
            ]
        )
        self.main_bar = Box(
            name="bar-inner",
            orientation="h",
            h_align="fill",
            v_align="center",
            children=[
                self.left_container,
                self.button_test_left,
                self.button_test_right,
                self.right_container,
            ]
        )
        self.children = self.main_bar

        self.hidden = False

        # Add scroll timers
        self.last_scroll_time_left = 0
        self.last_scroll_time_right = 0

        self.show_all()

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def on_button_clicked(self, *args):
        # Ejecuta notify-send cuando se hace clic en el botón
        exec_shell_command_async("notify-send 'Botón presionado' '¡Funciona!'")

    def search_apps(self):
        self.notch.open_notch("launcher")

    def overview(self):
        self.notch.open_notch("overview")

    def power_menu(self):
        self.notch.open_notch("power")

    def colorpicker(self, button, event):
        if event.button == 1:
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker-hex.sh')}")
        elif event.button == 2:
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker-hsv.sh')}")
        elif event.button == 3:
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker-rgb.sh')}")

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.main_bar.add_style_class("hidden")
        else:
            self.main_bar.remove_style_class("hidden")

    def on_test_left_scroll(self, widget, event):
        current_time = GLib.get_monotonic_time()
        # Add threshold of 100ms between scroll events
        if current_time - self.last_scroll_time_left < 10000:  # 100000 microseconds = 100ms
            return True
        
        self.last_scroll_time_left = current_time
        
        if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.SMOOTH]:
            success, dx, dy = event.get_scroll_deltas() if event.direction == Gdk.ScrollDirection.SMOOTH else (True, 0, -1)
            if dy < 0:
                exec_shell_command_async("brightnessctl set +5%")
            elif dy > 0:
                exec_shell_command_async("brightnessctl set 5%-")
            
        return False

    def on_test_right_scroll(self, widget, event):
        current_time = GLib.get_monotonic_time()
        # Add threshold of 100ms between scroll events
        if current_time - self.last_scroll_time_right < 10000:  # 100000 microseconds = 100ms
            return True
            
        self.last_scroll_time_right = current_time
        
        if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.SMOOTH]:
            success, dx, dy = event.get_scroll_deltas() if event.direction == Gdk.ScrollDirection.SMOOTH else (True, 0, -1)
            if dy < 0:
                exec_shell_command_async("pactl set-sink-volume @DEFAULT_SINK@ +5%")
            elif dy > 0:
                exec_shell_command_async("pactl set-sink-volume @DEFAULT_SINK@ -5%")
        
        return False
