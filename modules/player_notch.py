#!/usr/bin/env python3
import subprocess, random, hashlib, requests
from gi.repository import GLib, Gdk, Gtk, GdkPixbuf
import cairo
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.revealer import Revealer
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button
from modules.osd import OSDMenu, create_progress_bar
import modules.icons as icons

def get_player_icon_markup_by_name(player_name):
    if player_name:
        pn = player_name.lower()
        if pn == "firefox":
            return icons.firefox
        elif pn == "spotify":
            return icons.spotify
        elif pn in ("chromium", "brave"):
            return icons.chromium
    return icons.disc

class PlayerNotch:
    def __init__(self, parent):
        self.parent = parent  # reference to Notch if needed
        # --- Create Media Stack UI Widgets ---
        self.media_box = Box(name="media-view", orientation="v", spacing=4, v_align="center", h_align="center")
        self.media_content_box = Box(orientation="h", spacing=10, v_align="center", h_align="fill", h_expand=True)
        
        # Left box: switcher label, track image and title
        self.media_left_box = Box(name="media-left-box", orientation="h", spacing=4, v_align="center", h_align="start", width=200)
        # NEW: create switcher label using spotify as default
        self.switcher_label = Label(name="media-switcher-label", markup=get_player_icon_markup_by_name("spotify"))
        
        self.track_image = Gtk.DrawingArea()
        self.track_image.set_size_request(64, 64)
        self.track_image.connect("draw", self.on_track_image_draw)
        self.current_track_size = 64
        self.track_image_large = True
        self.media_title = Label(text="Loading Title...")
        # Insert switcher label at beginning of children list
        self.media_left_box.children = [self.switcher_label, self.track_image, self.media_title]
        
        # Right box: waveform
        self.media_right_box = Box(orientation="h", spacing=4, v_align="center", h_align="end")
        self.waveform = Gtk.DrawingArea()
        self.waveform.set_size_request(20, 30)
        self.waveform.set_valign(Gtk.Align.CENTER)
        self.waveform.connect("draw", self.draw_waveform)
        self.bar_heights = [0, 0, 0, 0, 0]
        self.is_animating = False
        self.media_right_box.children = [self.waveform]
        
        # Pack left and right boxes
        self.media_content_box.pack_start(self.media_left_box, False, False, 0)
        self.media_content_box.pack_end(self.media_right_box, False, False, 0)
        
        # --- Media Controls (Buttons & Progress) ---
        self.media_buttons_box = Box(orientation="h", spacing=4, v_align="center", h_align="center")
        prev_icon = Gtk.Image.new_from_icon_name("media-skip-backward-symbolic", Gtk.IconSize.DND)
        prev_icon.set_pixel_size(20)
        play_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.DND)
        play_icon.set_pixel_size(26)
        pause_icon = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.DND)
        pause_icon.set_pixel_size(26)
        next_icon = Gtk.Image.new_from_icon_name("media-skip-forward-symbolic", Gtk.IconSize.DND)
        next_icon.set_pixel_size(20)
        
        self.media_previous_button = Button()
        self.media_previous_button.set_image(prev_icon)
        self.media_previous_button.set_always_show_image(True)
        self.media_previous_button.add_style_class("media-button")
        self.media_previous_button.connect("clicked", self.on_media_previous_clicked)
        
        self.play_icon = play_icon
        self.pause_icon = pause_icon
        self.media_button = Button()
        self.media_button.set_image(self.play_icon)
        self.media_button.set_always_show_image(True)
        self.media_button.add_style_class("media-button")
        self.media_button.connect("clicked", self.on_media_button_clicked)
        
        self.media_next_button = Button()
        self.media_next_button.set_image(next_icon)
        self.media_next_button.set_always_show_image(True)
        self.media_next_button.add_style_class("media-button")
        self.media_next_button.connect("clicked", self.on_media_next_clicked)
        
        self.media_buttons_box.children = [
            self.media_previous_button,
            self.media_button,
            self.media_next_button
        ]
        
        self.media_progress_box = Box(orientation="h", spacing=4, v_align="center", h_align="center", name="media-progress-box")
        self.media_progress = Box()
        self.media_progress_eventbox = EventBox(child=self.media_progress)
        self.media_progress_eventbox.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON1_MOTION_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK
        )
        self.media_progress_eventbox.connect("button-press-event", self.on_progress_press)
        self.media_progress_eventbox.connect("motion-notify-event", self.on_progress_motion)
        self.media_progress_eventbox.connect("button-release-event", self.on_progress_release)
        
        self.media_current_time = Label(text="0:00")
        self.media_time = Label(text="Loading Time...")
        self.media_progress_box.children = [
            self.media_current_time,
            self.media_progress_eventbox,
            self.media_time
        ]
        
        self.media_controls_box = Box(orientation="v", spacing=4, v_align="center", h_align="center")
        self.media_controls_box.children = [
            self.media_buttons_box,
            self.media_progress_box
        ]
        
        self.media_revealer = Revealer(child=self.media_controls_box, child_revealed=False, transition_type="slide-up", transition_duration=150)
        self.media_box.children = [
            self.media_content_box,
            self.media_revealer
        ]
        
        # Other media-related attributes
        self.full_pixbuf = None
        self.scaled_pixbufs = {}
        self.current_track_length = 0
        self.is_dragging_progress = False

        # Setup periodic media updates
        GLib.timeout_add(500, self.refresh_media_info)
        GLib.timeout_add(100, self.animate_waveform)

    # --- Media-Related Methods ---
    def on_track_image_draw(self, widget, cr):
        if not self.full_pixbuf:
            return
        alloc = widget.get_allocation()
        size = alloc.width
        if size not in self.scaled_pixbufs:
            self.scaled_pixbufs[size] = self.full_pixbuf.scale_simple(
                size, size, GdkPixbuf.InterpType.BILINEAR
            )
        radius = 10
        cr.move_to(radius, 0)
        cr.arc(size - radius, radius, radius, -90 * (3.14159 / 180), 0)
        cr.arc(size - radius, size - radius, radius, 0, 90 * (3.14159 / 180))
        cr.arc(radius, size - radius, radius, 90 * (3.14159 / 180), 180 * (3.14159 / 180))
        cr.arc(radius, radius, radius, 180 * (3.14159 / 180), 270 * (3.14159 / 180))
        cr.close_path()
        cr.clip()
        Gdk.cairo_set_source_pixbuf(cr, self.scaled_pixbufs[size], 0, 0)
        cr.paint()

    def animate_track_image_resize(self, target_size, duration=150, steps=5):
        start_size = self.current_track_size
        diff = target_size - start_size
        if diff == 0:
            return
        step_duration = int(duration / steps)
        step = 0

        def update_size():
            nonlocal step
            step += 1
            new_size = int(start_size + (diff * step / steps))
            self.track_image.set_size_request(new_size, new_size)
            self.current_track_size = new_size
            self.track_image.queue_draw()
            if step >= steps:
                self.current_track_size = target_size
                return False
            return True

        GLib.timeout_add(step_duration, update_size)

    def draw_waveform(self, widget, cr):
        cr.set_source_rgb(*self.get_average_color(self.full_pixbuf) if self.full_pixbuf else (1,1,1))
        bar_width = 2
        spacing = 2
        total_width = 2 * bar_width + 4 * spacing
        start_x = (widget.get_allocated_width() - total_width) / 2
        max_height = 20
        center_y = (widget.get_allocated_height() - max_height) / 2
        for i, height in enumerate(self.bar_heights):
            x = start_x + i * (bar_width + spacing)
            half_height = height / 2
            top_y = center_y + (max_height / 2 - half_height)
            bottom_y = center_y + (max_height / 2 + half_height)
            radius = bar_width / 2 
            if height >= max_height:
                cr.rectangle(x, center_y, bar_width, max_height)
                cr.fill()
            else:
                cr.arc(x + radius, top_y, radius, 180 * (3.14159 / 180), 360 * (3.14159 / 180))
                cr.arc(x + radius, bottom_y, radius, 0, 180 * (3.14159 / 180))
                cr.move_to(x, top_y)
                cr.line_to(x, bottom_y)
                cr.move_to(x + bar_width, top_y)
                cr.line_to(x + bar_width, bottom_y)
                cr.fill()

    def animate_waveform(self):
        if self.is_animating:
            self.bar_heights = [random.randint(5, 20) for _ in range(5)]
            self.waveform.queue_draw()
        return True

    def on_media_button_clicked(self, _):
        try:
            subprocess.Popen(["playerctl", "--player=spotify", "play-pause"])
            status = subprocess.check_output(
                ["playerctl", "--player=spotify", "status"],
                encoding="utf-8"
            ).strip().lower()
            if status == "playing":
                self.media_button.set_image(self.pause_icon)
                self.is_animating = True
            else:
                self.media_button.set_image(self.play_icon)
                self.is_animating = False
                self.bar_heights = [0, 0, 0, 0, 0]
                self.waveform.queue_draw()
        except Exception as e:
            print("Error executing playerctl command:", e)
            self.is_animating = False
            self.bar_heights = [0, 0, 0, 0, 0]
            self.waveform.queue_draw()

    def on_media_previous_clicked(self, _):
        try:
            subprocess.Popen(["playerctl", "--player=spotify", "previous"])
        except Exception as e:
            print("Error executing previous command:", e)
    
    def on_media_next_clicked(self, _):
        try:
            subprocess.Popen(["playerctl", "--player=spotify", "next"])
        except Exception as e:
            print("Error executing next command:", e)

    def on_progress_press(self, widget, event):
        self.is_dragging_progress = True
        self._update_track_position_from_event(widget, event, seek=False)
        return True

    def on_progress_motion(self, widget, event):
        if self.is_dragging_progress:
            self._update_track_position_from_event(widget, event, seek=False)
        return True

    def on_progress_release(self, widget, event):
        self._update_track_position_from_event(widget, event, seek=True)
        self.is_dragging_progress = False
        return True

    def _update_track_position_from_event(self, widget, event, seek=False):
        allocation = widget.get_allocation()
        width = allocation.width if allocation.width > 0 else 1
        new_percentage = min(max(event.x / width, 0), 1)
        self.media_progress.children = [create_progress_bar(new_percentage * 100, width=200, height=5)]
        if seek:
            try:
                subprocess.Popen(["playerctl", "--player=spotify", "position", str(new_percentage * self.current_track_length)])
            except Exception as e:
                print("Error seeking track:", e)

    def get_average_color(self, pixbuf):
        if not pixbuf:
            return (1, 1, 1)
        pixels = pixbuf.get_pixels()
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        n_channels = pixbuf.get_n_channels()
        rowstride = pixbuf.get_rowstride()
        total_r = total_g = total_b = count = 0
        for y in range(height):
            for x in range(width):
                offset = y * rowstride + x * n_channels
                r = pixels[offset]
                g = pixels[offset + 1]
                b = pixels[offset + 2]
                if pixbuf.get_has_alpha():
                    a = pixels[offset + 3]
                    if a > 0:
                        total_r += r
                        total_g += g
                        total_b += b
                        count += 1
                else:
                    total_r += r
                    total_g += g
                    total_b += b
                    count += 1
        if count:
            return (total_r/count/255.0, total_g/count/255.0, total_b/count/255.0)
        return (1, 1, 1)

    def create_rounded_pixbuf(self, pixbuf):
        size = min(pixbuf.get_width(), pixbuf.get_height())
        radius = 10
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surface)
        cr.move_to(radius, 0)
        cr.arc(size - radius, radius, radius, -90 * (3.14159 / 180), 0)
        cr.arc(size - radius, size - radius, radius, 0, 90 * (3.14159 / 180))
        cr.arc(radius, size - radius, radius, 90 * (3.14159 / 180), 180 * (3.14159 / 180))
        cr.arc(radius, radius, radius, 180 * (3.14159 / 180), 270 * (3.14159 / 180))
        cr.close_path()
        cr.clip()
        Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
        cr.paint()
        return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)

    def get_cached_image(self, art_url):
        import os
        cache_dir = "/home/gunit/.config/Ax-Shell/cache"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        hash_name = hashlib.md5(art_url.encode("utf-8")).hexdigest() + ".png"
        file_path = os.path.join(cache_dir, hash_name)
        if not os.path.exists(file_path):
            try:
                response = requests.get(art_url)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
            except Exception:
                return None
        return file_path

    def refresh_media_info(self):
        try:
            title = subprocess.check_output(
                ["playerctl", "--player=spotify", "metadata", "title"],
                encoding="utf-8"
            ).strip()
            position = float(subprocess.check_output(
                ["playerctl", "--player=spotify", "position"],
                encoding="utf-8"
            ).strip())
            length = float(subprocess.check_output(
                ["playerctl", "--player=spotify", "metadata", "mpris:length"],
                encoding="utf-8"
            ).strip()) / 1000000
            progress_percentage = (position / length) * 100 if length > 0 else 0
            self.current_track_length = length
            if len(title) > 20:
                title = title[:20] + "..."
            cur_m = int((position % 3600) // 60)
            cur_s = int(position % 60)
            tot_m = int((length % 3600) // 60)
            tot_s = int(length % 60)
            current = f"{cur_m}:{cur_s:02d}"
            total = f"{tot_m}:{tot_s:02d}"
            self.media_title.set_text(title)
            self.media_current_time.set_text(current)
            self.media_time.set_text(total)
            if not self.is_dragging_progress:
                self.media_progress.children = [create_progress_bar(progress_percentage, width=200, height=5)]
            try:
                art_url = subprocess.check_output(
                    ["playerctl", "--player=spotify", "metadata", "mpris:artUrl"],
                    encoding="utf-8"
                ).strip()
                if art_url:
                    if art_url.startswith("file://"):
                        file_path = art_url.replace("file://", "")
                    else:
                        file_path = self.get_cached_image(art_url)
                    if file_path:
                        original_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(file_path, 64, 64, True)
                        rounded_pixbuf = self.create_rounded_pixbuf(original_pixbuf)
                        self.full_pixbuf = rounded_pixbuf
                        self.scaled_pixbufs = {}
                        self.track_image.set_size_request(self.current_track_size, self.current_track_size)
                        self.track_image.queue_draw()
            except Exception:
                pass
            status = subprocess.check_output(
                ["playerctl", "--player=spotify", "status"],
                encoding="utf-8"
            ).strip().lower()
            if status == "playing":
                self.media_button.set_image(self.pause_icon)
                self.is_animating = True
            else:
                self.media_button.set_image(self.play_icon)
                self.is_animating = False
                self.bar_heights = [0, 0, 0, 0, 0]
                self.waveform.queue_draw()
        except Exception:
            self.media_title.set_text("No track")
            self.media_progress.children = [create_progress_bar(0, width=80, height=5)]
            self.media_button.set_image(self.play_icon)
            self.is_animating = False
            self.bar_heights = [0, 0, 0, 0, 0]
            self.waveform.queue_draw()
        return True

# ...possible extra helper methods...
