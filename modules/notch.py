#!/usr/bin/env python3
from os import truncate
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.stack import Stack
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils.helpers import FormattedString, truncate
from gi.repository import GLib, Gdk, Gtk, GdkPixbuf
from modules.launcher import AppLauncher
from modules.dashboard import Dashboard
from modules.wallpapers import WallpaperSelector
from modules.notifications import NotificationContainer
from modules.power import PowerMenu
from modules.overview import Overview
from modules.bluetooth import BluetoothConnections
from modules.corners import MyCorner
import modules.icons as icons
import modules.data as data
from modules.osd import OSDMenu, create_progress_bar
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button
import subprocess
import requests
import hashlib
import random
import cairo  # Added for image rounding
from modules.player_notch import PlayerNotch  # New import

class Notch(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="notch",
            layer="top",
            anchor="top",
            margin="-40px 10px 10px 10px",
            keyboard_mode="none",
            exclusivity="normal",
            visible=True,
            all_visible=True,
        )

        self.dashboard = Dashboard(notch=self)
        self.launcher = AppLauncher(notch=self)
        self.wallpapers = WallpaperSelector(notch=self)
        self.notification = NotificationContainer(notch=self)
        self.overview = Overview()
        self.power = PowerMenu(notch=self)
        self.bluetooth = BluetoothConnections(notch=self)
        self.osd = OSDMenu(notch=self)
        
        # Instantiate our new media stack component
        self.player_notch = PlayerNotch(parent=self)
        
        # Use the media_box from the player_notch instance
        self.info_media = self.player_notch.media_box

        # --- Info Widgets (Hostname, Media, Session) ---
        self.info_hostname = Label(text="Loading...")
        self.info_session = Label(text=self.get_session_info())
        
        self.hostname_event = EventBox(
            child=self.info_hostname,
            events=["button-press-event"],
            name="hostname-event"
        )
        self.hostname_event.connect("button-press-event", self.on_hostname_click)
        
        self.session_event = EventBox(
            child=self.info_session,
            events=["button-press-event"],
            name="session-event"
        )
        self.session_event.connect("button-press-event", self.on_session_click)
        
        self.active_info_index = 0
        self.active_stack = Stack(
            name="active-info-stack",
            v_expand=True,
            h_expand=True,
            transition_type="crossfade",
            transition_duration=100,
            children=[self.hostname_event, self.info_media, self.session_event]
        )
        self.active_stack.set_visible_child(self.hostname_event)

        # Wrap active_stack in an EventBox for hover detection
        self.active_stack_eventbox = EventBox(
            child=self.active_stack,
            events=["enter-notify-event", "leave-notify-event"],
            name="active-stack-eventbox"
        )
        self.active_stack_eventbox.connect("enter-notify-event", self.on_active_stack_enter)
        self.active_stack_eventbox.connect("leave-notify-event", self.on_active_stack_leave)

        GLib.idle_add(self.initial_hostname_update)

        # Main stack for all panels
        self.stack = Stack(
            name="notch-content",
            v_expand=True,
            h_expand=True,
            transition_type="crossfade",
            transition_duration=100,
            children=[
                self.active_stack_eventbox,
                self.launcher,
                self.dashboard,
                self.wallpapers,
                self.notification,
                self.overview,
                self.power,
                self.bluetooth,
                self.osd,
            ]
        )
        self.stack.set_visible_child(self.active_stack_eventbox)
        self.average_color = (1, 1, 1)  # Default waveform bar color (white)
        GLib.timeout_add(500, self.player_notch.refresh_media_info)
        GLib.timeout_add(5000, self.refresh_hostname_info)
        GLib.timeout_add(2000, self.refresh_session_info)
        GLib.timeout_add(100, self.player_notch.animate_waveform)

        self.corner_left = Box(
            name="notch-corner-left",
            orientation="v",
            children=[MyCorner("top-right"), Box()]
        )

        self.corner_right = Box(
            name="notch-corner-right",
            orientation="v",
            children=[MyCorner("top-left"), Box()]
        )

        self.notch_box = CenterBox(
            name="notch-box",
            orientation="h",
            h_align="center",
            v_align="center",
            start_children=Box(children=[self.corner_left]),
            center_children=self.stack,
            end_children=Box(children=[self.corner_right])
        )
        
        self.event_box = EventBox(
            events=["scroll", "enter-notify-event", "leave-notify-event"],
            child=self.notch_box,
            name="notch-eventbox"
        )
        self.event_box.connect("scroll-event", self.on_notch_scroll)
        
        self.add(self.event_box)
        self.hidden = False

        for widget in [self.launcher, self.dashboard, self.wallpapers, 
                       self.notification, self.overview, self.power, 
                       self.bluetooth, self.osd]:
            widget.show_all()
        self.show_all()
        self.wallpapers.viewport.hide()

        self.add_keybinding("Escape", lambda *_: self.close_notch())
        self.add_keybinding("Ctrl Tab", lambda *_: self.dashboard.go_to_next_child())
        self.add_keybinding("Ctrl Shift ISO_Left_Tab", lambda *_: self.dashboard.go_to_previous_child())

        self.media_hide_timeout = None  # new attribute for hide timer

    # --- Hover Callbacks Updated to Delay Hiding Media after Unhover ---
    def on_active_stack_enter(self, widget, event):
        # Cancel any pending media hide
        if self.media_hide_timeout is not None:
            GLib.source_remove(self.media_hide_timeout)
            self.media_hide_timeout = None
        if self.active_stack.get_visible_child() == self.info_media:
            self.player_notch.track_image_large = True
            self.player_notch.animate_track_image_resize(64, duration=150)
            self.player_notch.media_revealer.reveal()

    def on_active_stack_leave(self, widget, event):
        if self.active_stack.get_visible_child() == self.info_media:
            # Schedule media hide after 1.5 seconds
            self.media_hide_timeout = GLib.timeout_add(1500, self._delayed_media_hide)
        return False

    def _delayed_media_hide(self):
        self.player_notch.track_image_large = False
        self.player_notch.animate_track_image_resize(32, duration=150)
        self.player_notch.media_revealer.unreveal()
        self.media_hide_timeout = None
        return False

    def on_hostname_click(self, widget, event):
        if self.active_info_index != 1:
            self.open_notch("dashboard")
        return False

    def on_session_click(self, widget, event):
        if self.active_info_index != 1:
            self.open_notch("dashboard")
        return False

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def close_notch(self):
        self.set_keyboard_mode("none")
        if self.hidden:
            self.notch_box.remove_style_class("hideshow")
            self.notch_box.add_style_class("hidden")
        for widget in [self.launcher, self.dashboard, self.wallpapers, 
                       self.notification, self.overview, self.power, 
                       self.bluetooth, self.osd]:
            widget.remove_style_class("open")
            if widget == self.wallpapers:
                self.wallpapers.viewport.hide()
                self.wallpapers.viewport.set_property("name", None)
        for style in ["launcher", "dashboard", "wallpapers", "notification", 
                      "overview", "power", "bluetooth", "osd"]:
            self.stack.remove_style_class(style)
        self.stack.set_visible_child(self.active_stack_eventbox)
        if self.active_info_index != 1:
            self.stack.remove_style_class("media")
            self.player_notch.media_box.remove_style_class("open")

    def open_notch(self, widget):
        # New approach for "osd" to avoid capturing focus
        if widget == "osd":
            # Do not change keyboard mode for osd
            # Instead, just show the osd without focus changes.
            widgets = {
                "launcher": self.launcher,
                "dashboard": self.dashboard,
                "wallpapers": self.wallpapers,
                "notification": self.notification,
                "overview": self.overview,
                "power": self.power,
                "bluetooth": self.bluetooth,
                "osd": self.osd,
            }
            # Remove any style classes from all widgets
            for style in widgets.keys():
                self.stack.remove_style_class(style)
            for w in widgets.values():
                w.remove_style_class("open")
            self.stack.add_style_class("osd")
            self.stack.set_visible_child(self.osd)
            self.osd.add_style_class("open")
            return

        # Existing behavior for other widgets.
        self.set_keyboard_mode("exclusive")
        if self.hidden:
            self.notch_box.remove_style_class("hidden")
            self.notch_box.add_style_class("hideshow")
        widgets = {
            "launcher": self.launcher,
            "dashboard": self.dashboard,
            "wallpapers": self.wallpapers,
            "notification": self.notification,
            "overview": self.overview,
            "power": self.power,
            "bluetooth": self.bluetooth,
            "osd": self.osd,
        }
        for style in widgets.keys():
            self.stack.remove_style_class(style)
        for w in widgets.values():
            w.remove_style_class("open")
        if widget in widgets:
            self.stack.add_style_class(widget)
            self.stack.set_visible_child(widgets[widget])
            widgets[widget].add_style_class("open")
            if widget == "launcher":
                self.launcher.open_launcher()
                self.launcher.search_entry.set_text("")
                self.launcher.search_entry.grab_focus()
            if widget == "notification":
                self.set_keyboard_mode("none")
            if widget == "wallpapers":
                self.wallpapers.search_entry.set_text("")
                self.wallpapers.search_entry.grab_focus()
                GLib.timeout_add(
                    500, 
                    lambda: (
                        self.wallpapers.viewport.show(), 
                        self.wallpapers.viewport.set_property("name", "wallpaper-icons")
                    )
                )
            if widget != "wallpapers":
                self.wallpapers.viewport.hide()
                self.wallpapers.viewport.set_property("name", None)
            if widget == "dashboard" and self.dashboard.stack.get_visible_child() != self.dashboard.stack.get_children()[4]:
                self.dashboard.stack.set_visible_child(self.dashboard.stack.get_children()[0])
        else:
            self.stack.set_visible_child(self.dashboard)

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.notch_box.add_style_class("hidden")
        else:
            self.notch_box.remove_style_class("hidden")

    def on_notch_scroll(self, widget, event):
        if self.stack.get_visible_child() != self.active_stack_eventbox:
            return False
        direction = "up" if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.SMOOTH] else "down"
        style_context = self.active_stack.get_style_context()
        style_context.remove_class("slide-up")
        style_context.remove_class("slide-down")
        style_context.add_class(f"slide-{direction}")
        if self.active_info_index == 1:
            # Replace get_media_info with refresh_media_info
            self.player_notch.refresh_media_info()
        if direction == "up":
            self.active_info_index = (self.active_info_index + 1) % 3
        else:
            self.active_info_index = (self.active_info_index - 1) % 3
        new_child = [self.hostname_event, self.info_media, self.session_event][self.active_info_index]
        self.active_stack.set_visible_child(new_child)
        if self.active_info_index == 1:
            self.stack.add_style_class("media")
            self.player_notch.media_box.add_style_class("open")
            GLib.idle_add(lambda: self.player_notch.media_revealer.reveal())
        else:
            self.stack.remove_style_class("media")
            self.player_notch.media_box.remove_style_class("open")
            self.player_notch.media_revealer.unreveal()
        GLib.timeout_add(300, lambda: style_context.remove_class(f"slide-{direction}"))
        return False

    def get_hostname_info(self):
        import os, socket
        try:
            username = os.getenv('USER') or os.getlogin()
            hostname = socket.gethostname()
            return f"{username}@{hostname}"
        except Exception:
            return "unknown@unknown"

    def get_session_info(self):
        try:
            desktop = subprocess.check_output(
                ["echo $XDG_CURRENT_DESKTOP"],
                shell=True,
                encoding="utf-8"
            ).strip()
            return f"Session: {desktop}"
        except Exception:
            return "Session: Unknown"

    def refresh_hostname_info(self):
        hostname = self.get_hostname_info()
        self.info_hostname.set_text(hostname)
        if self.active_info_index == 0:
            self.active_stack.set_visible_child(self.hostname_event)
        return True

    def refresh_session_info(self):
        session = self.get_session_info()
        self.info_session.set_text(session)
        if self.active_info_index == 2:
            self.active_stack.set_visible_child(self.session_event)
        return True

    def initial_hostname_update(self):
        hostname = self.get_hostname_info()
        self.info_hostname.set_text(hostname)
        return False

if __name__ == "__main__":
    notch = Notch()
    Gtk.main()
