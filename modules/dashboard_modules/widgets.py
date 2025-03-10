from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.stack import Stack
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import GLib, Gtk, Vte, Pango
import modules.icons as icons
from modules.dashboard_modules.buttons import Buttons
from modules.calendar import Calendar
from modules.kanban import Kanban
from modules.player import Player

class Widgets(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dash-widgets",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs["notch"]

        self.buttons = Buttons(notch=self.notch)

        self.box_1 = Box(
            name="box-1",
            h_expand=True,
            v_expand=True,
        )

        self.box_2 = Box(
            name="box-2",
            h_expand=True,
            v_expand=True,
        )

        self.box_3 = Box(
            name="box-3",
            # h_expand=True,
            v_expand=True,
        )

        self.box_4 = Box(
            name="box-4",
            orientation="h",
            spacing=4,
            children=[
                Box(
                    name="box-x",
                    h_expand=True,
                ),
                Box(
                    name="box-x",
                    h_expand=True,
                ),
                Box(
                    name="box-x",
                    h_expand=True,
                ),
            ]
        )

        self.player = Player()

        self.container_1 = Box(
            name="container-1",
            h_expand=True,
            v_expand=True,
            orientation="h",
            spacing=8,
            children=[
                Box(
                    name="container-sub-1",
                    h_expand=True,
                    v_expand=True,
                    spacing=8,
                    children=[
                        Calendar(),
                        self.box_2,
                    ]
                ),
                self.box_3,
            ]
        )

        self.container_2 = Box(
            name="container-2",
            h_expand=True,
            v_expand=True,
            orientation="v",
            spacing=8,
            children=[
                self.buttons,
                self.box_4,
                self.container_1,
            ]
        )

        self.container_3 = Box(
            name="container-3",
            h_expand=True,
            v_expand=True,
            orientation="h",
            spacing=8,
            children=[
                self.player,
                self.container_2,
            ]
        )

        self.add(self.container_3)

        self.show_all()
