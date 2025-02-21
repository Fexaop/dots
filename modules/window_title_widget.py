import re
from fabric.hyprland.widgets import ActiveWindow
from fabric.widgets.box import Box

WINDOW_TITLE_MAP = [
    ["firefox", "󰈹", "Firefox"],
    ["microsoft-edge", "󰇩", "Edge"],
    ["discord", "", "Discord"],
    ["vesktop", "", "Vesktop"],
    ["org.kde.dolphin", "", "Dolphin"],
    ["plex", "󰚺", "Plex"],
    ["steam", "", "Steam"],
    ["spotify", "󰓇", "Spotify"],
    ["ristretto", "󰋩", "Ristretto"],
    ["obsidian", "󱓧", "Obsidian"],
    ["google-chrome", "", "Google Chrome"],
    ["brave-browser", "󰖟", "Brave Browser"],
    ["chromium", "", "Chromium"],
    ["opera", "", "Opera"],
    ["vivaldi", "󰖟", "Vivaldi"],
    ["waterfox", "󰖟", "Waterfox"],
    ["zen", "󰖟", "Zen Browser"],
    ["thorium", "󰖟", "Thorium"],
    ["tor-browser", "", "Tor Browser"],
    ["floorp", "󰈹", "Floorp"],
    ["gnome-terminal", "", "GNOME Terminal"],
    ["kitty", "󰄛", "Kitty Terminal"],
    ["konsole", "", "Konsole"],
    ["alacritty", "", "Alacritty"],
    ["wezterm", "", "Wezterm"],
    ["foot", "󰽒", "Foot Terminal"],
    ["tilix", "", "Tilix"],
    ["xterm", "", "XTerm"],
    ["urxvt", "", "URxvt"],
    ["st", "", "st Terminal"],
    ["com.mitchellh.ghostty", "󰊠", "Ghostty"],
    ["code", "󰨞", "Visual Studio Code"],
    ["vscode", "󰨞", "VS Code"],
    ["sublime-text", "", "Sublime Text"],
    ["atom", "", "Atom"],
    ["android-studio", "󰀴", "Android Studio"],
    ["intellij-idea", "", "IntelliJ IDEA"],
    ["pycharm", "󱃖", "PyCharm"],
    ["webstorm", "󱃖", "WebStorm"],
    ["phpstorm", "󱃖", "PhpStorm"],
    ["eclipse", "", "Eclipse"],
    ["netbeans", "", "NetBeans"],
    ["docker", "", "Docker"],
    ["vim", "", "Vim"],
    ["neovim", "", "Neovim"],
    ["neovide", "", "Neovide"],
    ["emacs", "", "Emacs"],
    ["slack", "󰒱", "Slack"],
    ["telegram-desktop", "", "Telegram"],
    ["org.telegram.desktop", "", "Telegram"],
    ["whatsapp", "󰖣", "WhatsApp"],
    ["teams", "󰊻", "Microsoft Teams"],
    ["skype", "󰒯", "Skype"],
    ["thunderbird", "", "Thunderbird"],
    ["nautilus", "󰝰", "Files (Nautilus)"],
    ["thunar", "󰝰", "Thunar"],
    ["pcmanfm", "󰝰", "PCManFM"],
    ["nemo", "󰝰", "Nemo"],
    ["ranger", "󰝰", "Ranger"],
    ["doublecmd", "󰝰", "Double Commander"],
    ["krusader", "󰝰", "Krusader"],
    ["vlc", "󰕼", "VLC Media Player"],
    ["mpv", "", "MPV"],
    ["rhythmbox", "󰓃", "Rhythmbox"],
    ["gimp", "", "GIMP"],
    ["inkscape", "", "Inkscape"],
    ["krita", "", "Krita"],
    ["blender", "󰂫", "Blender"],
    ["kdenlive", "", "Kdenlive"],
    ["lutris", "󰺵", "Lutris"],
    ["heroic", "󰺵", "Heroic Games Launcher"],
    ["minecraft", "󰍳", "Minecraft"],
    ["csgo", "󰺵", "CS:GO"],
    ["dota2", "󰺵", "Dota 2"],
    ["evernote", "", "Evernote"],
    ["sioyek", "", "Sioyek"],
    ["dropbox", "󰇣", "Dropbox"],
    ["^$", "󰇄", "Desktop"],
]

class WindowTitleWidget(Box):
    """A widget that displays the title of the active window."""
    def __init__(self, **kwargs):
        super().__init__(name="window-title-widget", **kwargs)
        # Create an ActiveWindow widget with a lambda callback for formatting.
        self.window = ActiveWindow(
            name="window-title",
            formatter=lambda win_title, win_class: self.get_title(win_title, win_class)
        )
        self.add(self.window)

    def get_title(self, win_title, win_class):
        # Truncate the window title to 50 characters.
        if len(win_title) > 50:
            win_title = win_title[:50]
        for pattern, icon, display in WINDOW_TITLE_MAP:
            if re.search(pattern, win_class, re.IGNORECASE):
                return f"{icon} {display}"
        # Default: show a generic icon and the lowercased window class.
        return f"󰣆 {win_class.lower()}"
