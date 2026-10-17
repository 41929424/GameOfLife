import asyncio
import tempfile
from functools import wraps
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from textual.widgets import Input, Label

import main
from main import GameOfLifeApp


def textual_test(test_coroutine):
    @wraps(test_coroutine)
    def run_test(*args, **kwargs):
        asyncio.run(test_coroutine(*args, **kwargs))

    return run_test


def make_app():
    app = GameOfLifeApp(size=5)
    app.interval = 3600
    app.engine.clear()
    return app


def make_block(engine):
    for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
        engine.set_cell(x, y, True)


def make_blinker(engine):
    for x in (1, 2, 3):
        engine.set_cell(x, 2, True)


def label_text(app, widget_id):
    return app.query_one(f"#{widget_id}", Label).render().plain


@textual_test
async def test_initial_analysis_is_evolving():
    app = make_app()
    async with app.run_test():
        assert "Evolving" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("—")
        assert label_text(app, "cycle-start").endswith("—")
        for widget_id in (
            "generation", "population", "status", "speed", "grid", "pause", "step",
            "randomize", "clear", "record", "theme-select", "width-input",
            "height-input", "generation-limit", "resize", "set-limit", "record-status",
        ):
            app.query_one(f"#{widget_id}")


@textual_test
async def test_stable_state_shows_period_and_cycle_start():
    app = make_app()
    make_block(app.engine)
    app.engine.step()
    async with app.run_test():
        assert "Stable" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("1")
        assert label_text(app, "cycle-start").endswith("0")


@textual_test
async def test_oscillator_shows_detected_period_and_start():
    app = make_app()
    make_blinker(app.engine)
    app.engine.step()
    app.engine.step()
    async with app.run_test():
        assert "Oscillator" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("2")
        assert label_text(app, "cycle-start").endswith("0")


@textual_test
async def test_clear_refreshes_analysis_indicators():
    app = make_app()
    make_block(app.engine)
    app.engine.step()
    async with app.run_test():
        app.action_clear()
        assert "Evolving" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("—")
        assert label_text(app, "cycle-start").endswith("—")


@textual_test
async def test_randomize_refreshes_analysis_indicators():
    app = make_app()
    make_block(app.engine)
    app.engine.step()
    async with app.run_test():
        app.action_randomize()
        assert app.engine.generation == 0
        assert "Evolving" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("—")
        assert label_text(app, "cycle-start").endswith("—")


@textual_test
async def test_resize_refreshes_analysis_indicators():
    app = make_app()
    make_block(app.engine)
    app.engine.step()
    async with app.run_test():
        app.query_one("#width-input", Input).value = "10"
        app.query_one("#height-input", Input).value = "10"
        app.resize_board()
        assert (app.engine.width, app.engine.height) == (10, 10)
        assert "Evolving" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("—")
        assert label_text(app, "cycle-start").endswith("—")


@textual_test
async def test_pause_preserves_detected_state():
    app = make_app()
    make_block(app.engine)
    app.engine.step()
    async with app.run_test():
        app.action_toggle()
        assert "Paused" in label_text(app, "status")
        assert "Stable" in label_text(app, "state-status")
        assert label_text(app, "cycle-period").endswith("1")


@textual_test
async def test_detected_stable_state_does_not_stop_simulation():
    app = make_app()
    make_block(app.engine)
    async with app.run_test():
        app.advance()
        assert app.engine.status == "stable"
        assert "Stable" in label_text(app, "state-status")
        assert app.running is True


@textual_test
async def test_detected_oscillator_does_not_stop_simulation():
    app = make_app()
    make_blinker(app.engine)
    async with app.run_test():
        app.advance()
        app.advance()
        assert app.engine.status == "oscillating"
        assert "Oscillator" in label_text(app, "state-status")
        assert app.running is True


@textual_test
async def test_empty_stable_field_does_not_stop_simulation():
    app = make_app()
    async with app.run_test():
        app.advance()
        assert app.engine.status == "stable"
        assert "Stable" in label_text(app, "state-status")
        assert app.running is True


@textual_test
async def test_responsive_layout_and_scrolling_at_supported_terminal_sizes():
    for screen_size in ((50, 16), (80, 24), (120, 40)):
        app = GameOfLifeApp(size=30)
        app.interval = 3600
        app.engine.clear()
        async with app.run_test(size=screen_size) as pilot:
            screen = app.size
            stats = app.query_one("#stats")
            workspace = app.query_one("#workspace")
            grid_wrap = app.query_one("#grid-wrap")
            side = app.query_one("#side")

            assert stats.region.bottom <= workspace.region.y
            assert workspace.region.height >= 5
            assert grid_wrap.region.height >= 5
            assert grid_wrap.region.right <= side.region.x
            assert side.region.right <= screen.width
            assert side.region.bottom <= screen.height

            for widget_id in ("state-status", "cycle-period", "cycle-start"):
                region = app.query_one(f"#{widget_id}").region
                assert region.width > 0 and region.height == 1
                assert stats.region.x <= region.x < stats.region.right
                assert stats.region.y <= region.y < stats.region.bottom

            stats_regions = [
                app.query_one(f"#{widget_id}").region
                for widget_id in (
                    "generation", "population", "status", "speed",
                    "state-status", "cycle-period", "cycle-start",
                )
            ]
            for index, first in enumerate(stats_regions):
                for second in stats_regions[index + 1:]:
                    overlaps = (
                        first.x < second.right and second.x < first.right
                        and first.y < second.bottom and second.y < first.bottom
                    )
                    assert not overlaps

            assert grid_wrap.max_scroll_y > 0
            horizontal_scroll_available = grid_wrap.max_scroll_x > 0
            grid_wrap.scroll_to(
                x=grid_wrap.max_scroll_x,
                y=grid_wrap.max_scroll_y,
                animate=False,
            )
            await pilot.pause()
            if horizontal_scroll_available:
                assert grid_wrap.scroll_x > 0
            assert grid_wrap.scroll_y > 0

            if screen_size == (50, 16):
                await pilot.click("#pause")
                assert app.running is False
                await pilot.pause()
                await pilot.press("space")
                assert app.running is True
                await pilot.pause()
                await pilot.press("space")
                assert app.running is False

                await pilot.press("ctrl+down")
                await pilot.pause()
                assert app.query_one("#step").region.y < screen.height
                await pilot.click("#step")
                assert app.engine.generation == 1
                assert app.running is False

                side.scroll_to(y=42, animate=False)
                await pilot.pause()
                assert app.query_one("#set-limit").region.y < screen.height
                await pilot.click("#set-limit")
                assert "removed" in app.query_one("#message", Label).render().plain


@textual_test
async def test_generation_limit_stops_simulation():
    app = make_app()
    async with app.run_test():
        app.max_generations = 2
        app.advance()
        assert app.running is True
        app.advance()
        assert app.engine.generation == 2
        assert app.running is False
        assert "Generation limit reached (2)" in app.query_one("#message", Label).render().plain


@textual_test
async def test_gif_recording_saves_valid_multiframe_file_in_temporary_directory():
    project_root = Path(__file__).resolve().parents[1]
    old_settings_path = main.SETTINGS_PATH
    with tempfile.TemporaryDirectory(prefix="pilot-gif-", dir=project_root) as temp_name:
        temp_dir = Path(temp_name)
        main.SETTINGS_PATH = temp_dir / "settings.json"
        app = make_app()
        app.interval = 0.5
        make_blinker(app.engine)
        original_with_name = Path.with_name

        def redirect_recordings(path, name):
            if name == "recordings":
                return temp_dir / "recordings"
            return original_with_name(path, name)

        try:
            async with app.run_test(size=(80, 24)):
                app.toggle_recording()
                app.advance()
                app.advance()
                with patch.object(Path, "with_name", redirect_recordings):
                    app.toggle_recording()

                gif_files = list((temp_dir / "recordings").glob("*.gif"))
                assert len(gif_files) == 1
                with Image.open(gif_files[0]) as gif:
                    gif.verify()
                with Image.open(gif_files[0]) as gif:
                    assert gif.n_frames >= 3
                assert "GIF saved" in app.query_one("#message", Label).render().plain
        finally:
            main.SETTINGS_PATH = old_settings_path
