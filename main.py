from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from PIL import Image
from rich.text import Text
from engine import GameEngine
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static


THEMES = {
    "midnight": Theme(
        name="midnight", primary="#58E6A1", secondary="#58B8E6", accent="#F4C76B",
        foreground="#E7EEF5", background="#0B1118", surface="#263746", panel="#111B25",
        success="#58E6A1", warning="#F4C76B", error="#FF6B6B", dark=True,
        variables={"text-muted": "#9AABBA", "grid-live": "#58E6A1", "grid-dead": "#293846"},
    ),
    "forest": Theme(
        name="forest", primary="#A3D977", secondary="#64BFA5", accent="#E7C66A",
        foreground="#E8F0E4", background="#101812", surface="#34483A", panel="#1A261D",
        success="#A3D977", warning="#E7C66A", error="#E88772", dark=True,
        variables={"text-muted": "#A9B9A5", "grid-live": "#A3D977", "grid-dead": "#354338"},
    ),
    "sunset": Theme(
        name="sunset", primary="#FF9B73", secondary="#D78BC7", accent="#FFD166",
        foreground="#F8E9E2", background="#1B1118", surface="#513342", panel="#291A24",
        success="#86D6A4", warning="#FFD166", error="#FF7777", dark=True,
        variables={"text-muted": "#C3A9B8", "grid-live": "#FF9B73", "grid-dead": "#49303C"},
    ),
    "light": Theme(
        name="light", primary="#087F5B", secondary="#2368A0", accent="#9A6500",
        foreground="#1C2733", background="#F1F5F8", surface="#B8C7D2", panel="#FFFFFF",
        success="#087F5B", warning="#9A6500", error="#B42318", dark=False,
        variables={"text-muted": "#526474", "grid-live": "#087F5B", "grid-dead": "#C9D4DC"},
    ),
    "ocean": Theme(
        name="ocean", primary="#4DD0E1", secondary="#64B5F6", accent="#80CBC4",
        foreground="#E0F7FA", background="#071923", surface="#164052", panel="#0D2A38",
        success="#80CBC4", warning="#FFD180", error="#FF8A80", dark=True,
        variables={"text-muted": "#91B7C3", "grid-live": "#4DD0E1", "grid-dead": "#1C3B49"},
    ),
    "dracula": Theme(
        name="dracula", primary="#BD93F9", secondary="#8BE9FD", accent="#FFB86C",
        foreground="#F8F8F2", background="#191A21", surface="#49465B", panel="#252631",
        success="#50FA7B", warning="#FFB86C", error="#FF5555", dark=True,
        variables={"text-muted": "#B6B3C6", "grid-live": "#BD93F9", "grid-dead": "#41404D"},
    ),
    "amber": Theme(
        name="amber", primary="#FFC857", secondary="#F29E4C", accent="#F9DC5C",
        foreground="#FFF3D6", background="#21180B", surface="#594321", panel="#30220F",
        success="#A8C66C", warning="#FFC857", error="#EF6461", dark=True,
        variables={"text-muted": "#C8B68E", "grid-live": "#FFC857", "grid-dead": "#4B3A20"},
    ),
}
SETTINGS_PATH = Path(__file__).with_name(".gol-settings.json")


class LifeGrid(Static):
    """Compact colored renderer for the cell field."""

    def show_field(self, field: list[list[bool]], live_color: str, dead_color: str) -> None:
        lines = []
        for row in field:
            line = Text()
            for alive in row:
                line.append("██" if alive else "··", style=f"bold {live_color}" if alive else dead_color)
            lines.append(line)
        self.update(Text("\n").join(lines))

class GameOfLifeApp(App[None]):
    TITLE = "GAME OF LIFE"
    SUB_TITLE = "Conway's cellular automaton"
    CSS = """
    Screen { background: $background; color: $foreground; }
    #main { height: 1fr; min-height: 0; padding: 1 2; }
    #top { height: 6; margin-bottom: 1; }
    #stats { width: 1fr; height: 6; border: round $surface; padding: 0 1; background: $panel; }
    #stats Label { height: 1; }
    #workspace { height: 1fr; min-height: 0; }
    #grid-wrap { width: 1fr; height: 1fr; min-height: 0; border: round $surface; align: center middle; overflow: auto; }
    #grid { width: auto; height: auto; padding: 1 2; }
    #side { width: 30; height: 1fr; min-height: 0; margin-left: 1; overflow-y: scroll; }
    .card { border: round $surface; padding: 1; height: auto; margin-bottom: 1; background: $panel; }
    .card-title { color: $accent; text-style: bold; margin-bottom: 1; }
    #controls Button { width: 100%; margin-bottom: 1; }
    #controls Input { width: 100%; margin-bottom: 1; }
    #help { color: $text-muted; }
    #message { color: $warning; height: auto; min-height: 2; }
    """
    BINDINGS = [
        ("space", "toggle", "Pause / resume"),
        ("n", "step", "Next generation"),
        ("r", "randomize", "Randomize"),
        ("c", "clear", "Clear"),
        ("+", "faster", "Faster"),
        ("-,_", "slower", "Slower"),
        ("ctrl+down", "controls_down", "Scroll controls down"),
        ("ctrl+up", "controls_up", "Scroll controls up"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, size: int = 30) -> None:
        super().__init__()
        self.engine = GameEngine(size, size)
        self.max_generations: int | None = None
        self.running = True
        self.interval = 0.35
        self.timer = None
        self.recording = False
        self.recording_frames: list[Image.Image] = []
        self.recording_durations: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main"):
            with Horizontal(id="top"):
                with Vertical(id="stats"):
                    yield Label("GENERATION   0", id="generation")
                    yield Label("POPULATION   0", id="population")
                    yield Label("STATUS       Running", id="status")
                    yield Label("SPEED        0.35 s / step", id="speed")
            with Horizontal(id="workspace"):
                with Vertical(id="grid-wrap"):
                    yield LifeGrid(id="grid")
                with Vertical(id="side"):
                    with Vertical(id="controls", classes="card"):
                        yield Label("CONTROLS", classes="card-title")
                        yield Button("⏸  Pause", id="pause", variant="primary")
                        yield Button("⏭  Step", id="step")
                        yield Button("↻  Randomize", id="randomize")
                        yield Button("◻  Clear", id="clear")
                        yield Button("●  Start GIF recording", id="record")
                        yield Button("📁  Open GIF folder", id="open-recordings")
                        yield Label("Recorder idle", id="record-status")
                        yield Label("Color theme", classes="card-title")
                        yield Select(
                            [
                                ("Midnight", "midnight"), ("Forest", "forest"),
                                ("Sunset", "sunset"), ("Light", "light"),
                                ("Ocean", "ocean"), ("Dracula", "dracula"), ("Amber", "amber"),
                            ],
                            value="midnight", id="theme-select", allow_blank=False,
                        )
                        yield Label("Board dimensions", classes="card-title")
                        yield Input(str(self.engine.width), id="width-input", type="integer", placeholder="Width (10-80)")
                        yield Input(str(self.engine.height), id="height-input", type="integer", placeholder="Height (10-80)")
                        yield Button("Apply dimensions", id="resize")
                        yield Label("Generation limit (blank = unlimited)", classes="card-title")
                        yield Input("", id="generation-limit", type="integer", placeholder="e.g. 100")
                        yield Button("Set limit", id="set-limit")
                    with Vertical(classes="card"):
                        yield Label("KEYBOARD", classes="card-title")
                        yield Static("Ctrl+Down / Up  Scroll panel\nSpace            Pause / resume\nN                Next step\nR                Randomize\nC                Clear\n+ / −            Change speed\nQ                Quit", id="help")
                    yield Label("", id="message")
        yield Footer()

    def on_mount(self) -> None:
        for theme in THEMES.values():
            self.register_theme(theme)
        try:
            saved_theme = json.loads(SETTINGS_PATH.read_text(encoding="utf-8")).get("theme")
        except (OSError, ValueError, AttributeError):
            saved_theme = None
        if saved_theme in THEMES:
            self.theme = saved_theme
            self.query_one("#theme-select", Select).value = saved_theme
        self.timer = self.set_interval(self.interval, self.tick)
        self.refresh_view()
        self.call_after_refresh(self.warn_if_board_exceeds_view)

    def tick(self) -> None:
        if self.running:
            self.advance()

    def advance(self) -> None:
        if self.max_generations is not None and self.engine.generation >= self.max_generations:
            self.running = False
            self.query_one("#message", Label).update(f"Generation limit reached ({self.max_generations}).")
            self.refresh_view()
            return
        self.engine.step()
        self.capture_recording_frame()
        if self.max_generations is not None and self.engine.generation >= self.max_generations:
            self.running = False
            self.query_one("#message", Label).update(f"Generation limit reached ({self.max_generations}).")
        self.refresh_view()
        if not self.running:
            return
        if self.engine.is_empty:
            self.running = False
            self.query_one("#message", Label).update("All cells are dead. Randomize to start again.")
            self.refresh_view()

    def refresh_view(self) -> None:
        field = self.engine.get_field()
        colors = THEMES.get(self.theme, THEMES["midnight"]).variables
        self.query_one("#grid", LifeGrid).show_field(
            field, colors["grid-live"], colors["grid-dead"]
        )
        self.query_one("#generation", Label).update(f"GENERATION   {self.engine.generation:,}")
        self.query_one("#population", Label).update(
            f"POPULATION   {self.engine.population:,} / {self.engine.width * self.engine.height:,}"
        )
        self.query_one("#status", Label).update(f"STATUS       {'Running' if self.running else 'Paused'}")
        self.query_one("#speed", Label).update(f"SPEED        {self.interval:.2f} s / step")
        self.query_one("#pause", Button).label = "⏸  Pause" if self.running else "▶  Resume"
        self.query_one("#record-status", Label).update(
            f"Recording · {len(self.recording_frames)} frames" if self.recording else "Recorder idle"
        )

    def action_toggle(self) -> None:
        self.running = not self.running
        self.query_one("#message", Label).update("")
        self.refresh_view()

    def action_step(self) -> None:
        self.running = False
        self.advance()

    def action_randomize(self) -> None:
        self.engine.randomize()
        self.running = True
        self.query_one("#message", Label).update("")
        self.refresh_view()

    def action_clear(self) -> None:
        self.engine.clear()
        self.running = False
        self.query_one("#message", Label).update("Board cleared. Randomize or resize to begin.")
        self.refresh_view()

    def action_faster(self) -> None:
        self.set_speed(max(0.05, self.interval - 0.05))

    def action_slower(self) -> None:
        self.set_speed(min(2.0, self.interval + 0.05))

    def action_controls_down(self) -> None:
        panel = self.query_one("#side", Vertical)
        panel.scroll_to(y=min(panel.max_scroll_y, panel.scroll_y + max(1, panel.size.height - 2)), animate=False)

    def action_controls_up(self) -> None:
        panel = self.query_one("#side", Vertical)
        panel.scroll_to(y=max(0, panel.scroll_y - max(1, panel.size.height - 2)), animate=False)

    def set_speed(self, interval: float) -> None:
        self.interval = interval
        if self.timer:
            self.timer.stop()
            self.timer = self.set_interval(self.interval, self.tick)
        self.refresh_view()

    def toggle_recording(self) -> None:
        if self.recording:
            self.save_recording()
            return
        self.recording = True
        self.recording_frames = []
        self.recording_durations = []
        self.capture_recording_frame()
        self.query_one("#record", Button).label = "■  Stop and save GIF"
        self.query_one("#message", Label).update("GIF recording started.")
        self.refresh_view()

    def capture_recording_frame(self) -> None:
        if not self.recording:
            return
        colors = THEMES.get(self.theme, THEMES["midnight"]).variables
        dead = tuple(int(colors["grid-dead"][i:i + 2], 16) for i in (1, 3, 5))
        live = tuple(int(colors["grid-live"][i:i + 2], 16) for i in (1, 3, 5))
        field = self.engine.get_field()
        height, width = len(field), len(field[0])
        frame = Image.new("RGB", (width, height), dead)
        pixels = frame.load()
        for y, row in enumerate(field):
            for x, alive in enumerate(row):
                if alive:
                    pixels[x, y] = live
        self.recording_frames.append(
            frame.resize((width * 8, height * 8), Image.Resampling.NEAREST)
        )
        self.recording_durations.append(max(50, int(self.interval * 1000)))
        self.query_one("#record-status", Label).update(
            f"Recording · {len(self.recording_frames)} frames"
        )

    def save_recording(self) -> None:
        self.recording = False
        self.query_one("#record", Button).label = "●  Start GIF recording"
        if not self.recording_frames:
            self.query_one("#message", Label).update("No frames were recorded.")
            self.refresh_view()
            return
        output_dir = Path(__file__).with_name("recordings")
        output_path = output_dir / f"game-of-life-{datetime.now():%Y%m%d-%H%M%S-%f}.gif"
        try:
            output_dir.mkdir(exist_ok=True)
            self.recording_frames[0].save(
                output_path,
                save_all=True,
                append_images=self.recording_frames[1:],
                duration=self.recording_durations,
                loop=0,
                optimize=False,
            )
        except OSError as error:
            self.query_one("#message", Label).update(f"Could not save GIF: {error}")
        else:
            self.query_one("#message", Label).update(f"GIF saved: recordings/{output_path.name}")
        finally:
            self.recording_frames = []
            self.recording_durations = []
        self.refresh_view()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "pause": self.action_toggle,
            "step": self.action_step,
            "randomize": self.action_randomize,
            "clear": self.action_clear,
        }
        if event.button.id in actions:
            actions[event.button.id]()
        elif event.button.id == "record":
            self.toggle_recording()
        elif event.button.id == "open-recordings":
            self.open_recordings_folder()
        elif event.button.id == "resize":
            self.resize_board()
        elif event.button.id == "set-limit":
            self.set_generation_limit()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "theme-select" or event.value is Select.BLANK:
            return
        theme_name = str(event.value)
        if theme_name not in THEMES:
            return
        self.theme = theme_name
        try:
            SETTINGS_PATH.write_text(json.dumps({"theme": theme_name}), encoding="utf-8")
        except OSError:
            self.query_one("#message", Label).update("Theme changed, but its setting could not be saved.")
        self.refresh_view()

    def set_generation_limit(self) -> None:
        value = self.query_one("#generation-limit", Input).value.strip()
        if not value:
            self.max_generations = None
            self.query_one("#message", Label).update("Generation limit removed.")
            return
        try:
            limit = int(value)
        except ValueError:
            self.query_one("#message", Label).update("Enter a positive whole number, or leave blank.")
            return
        if limit < 1:
            self.query_one("#message", Label).update("Generation limit must be at least 1.")
            return
        self.max_generations = limit
        self.query_one("#message", Label).update(f"Simulation will stop at generation {limit}.")

    def resize_board(self) -> None:
        try:
            width = int(self.query_one("#width-input", Input).value.strip())
            height = int(self.query_one("#height-input", Input).value.strip())
        except ValueError:
            self.show_warning("Enter whole numbers for width and height.")
            return
        if not 10 <= width <= 80 or not 10 <= height <= 80:
            self.show_warning("Width and height must each be between 10 and 80 cells.")
            return
        self.engine.resize(width, height)
        self.running = True
        self.query_one("#message", Label).update("")
        self.refresh_view()
        self.call_after_refresh(self.warn_if_board_exceeds_view)

    def show_warning(self, message: str) -> None:
        self.query_one("#message", Label).update(message)
        self.notify(message, title="Check board settings", severity="warning")

    def warn_if_board_exceeds_view(self) -> None:
        grid_wrap = self.query_one("#grid-wrap", Vertical)
        visible_width = max(1, (grid_wrap.size.width - 6) // 2)
        visible_height = max(1, grid_wrap.size.height - 4)
        if self.engine.width > visible_width or self.engine.height > visible_height:
            message = (
                f"Field is {self.engine.width}×{self.engine.height}; this window shows about "
                f"{visible_width}×{visible_height} cells at once. Scroll inside the board to see the rest."
            )
            self.query_one("#message", Label).update(message)
            self.notify(message, title="Field is larger than the visible area", severity="warning")

    def open_recordings_folder(self) -> None:
        folder = Path(__file__).with_name("recordings")
        try:
            folder.mkdir(exist_ok=True)
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError as error:
            self.notify(f"Could not open the folder: {error}", title="Open GIF folder", severity="error")


if __name__ == "__main__":
    GameOfLifeApp().run()
