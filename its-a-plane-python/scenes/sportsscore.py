"""
scenes/sportsscore.py

Displays live sports scores on the 64x32 LED matrix.

Layout (64 wide x 32 tall)
--------------------------
Row 0-9   : "LIVE" label (small, top-left) + league tag (top-right)
Row 10-20 : Score line  "EDM  3 - 2  OTT"  (large bold font, centred)
Row 21-31 : Period / clock line  "P2  14:23"  (small font, centred)

The scene only draws content when there is at least one live game
(self._sports_data is non-empty).  Otherwise it returns immediately,
leaving the rest of the display pipeline unaffected.
"""

import logging
import os
from utilities.animator import Animator
from setup import colours, fonts, frames, screen
from rgbmatrix import graphics

logger = logging.getLogger(__name__)

# ---- Layout constants ----
SCORE_FONT = fonts.regular_bold       # 6x13 bold  — clear at this size
LABEL_FONT = fonts.extrasmall         # 4x6        — small header labels
PERIOD_FONT = fonts.small             # 5x8        — period / clock row

SCORE_Y = 20          # baseline of the score text row
LABEL_Y = 7           # baseline of the top label row
PERIOD_Y = 30         # baseline of the period/clock row

# Colours
COLOUR_LIVE_LABEL = colours.RED
COLOUR_LEAGUE = colours.GREY
COLOUR_HOME_SCORE = colours.LIGHT_ORANGE
COLOUR_AWAY_SCORE = colours.LIGHT_BLUE
COLOUR_ABBR = colours.WHITE
COLOUR_SEPARATOR = colours.GREY
COLOUR_PERIOD = colours.LIGHT_GREY

# Vertical offset for logos on the canvas (pixels from top)
LOGO_Y_OFFSET = 8

# Default hex values matching the module-level colour constants above
_DEFAULT_HOME_HEX = "#fea727"  # colours.LIGHT_ORANGE (254, 167, 39)
_DEFAULT_AWAY_HEX = "#28b7f6"  # colours.LIGHT_BLUE  (40, 183, 246)

_USER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "user_config.json",
)


def _hex_to_colour(hex_val: str, default):
    """Convert a #RRGGBB string to a graphics.Color, returning default on failure."""
    try:
        from rgbmatrix import graphics
        r = int(hex_val[1:3], 16)
        g = int(hex_val[3:5], 16)
        b = int(hex_val[5:7], 16)
        return graphics.Color(r, g, b)
    except Exception:
        return default


def _load_sports_colour(key: str, default):
    """Load a colour override from user_config.json; return default if absent."""
    try:
        import json
        with open(_USER_CONFIG_PATH) as f:
            cfg = json.load(f)
        hex_val = cfg.get(key, "")
        if hex_val and len(hex_val) == 7 and hex_val.startswith("#"):
            return _hex_to_colour(hex_val, default)
    except Exception as exc:
        logger.debug("Could not load colour %s: %s", key, exc)
    return default


def _load_sport_logo(abbr: str):
    """Load a cached team logo as an RGB PIL Image, or return None."""
    try:
        from PIL import Image
        from utilities.sports import SPORTS_LOGOS_DIR
        path = os.path.join(SPORTS_LOGOS_DIR, f"{abbr.upper()}.png")
        if not os.path.exists(path):
            return None
        return Image.open(path).convert("RGB")
    except Exception as exc:
        logger.debug("Could not load sport logo %s: %s", abbr, exc)
        return None


# How many display frames to hold a single game before cycling to the next
# when multiple live games are present.  At frames.PERIOD = 0.1 s/frame,
# PER_SECOND * 15 == 150 frames == 15 seconds per game.
FRAMES_PER_GAME = int(frames.PER_SECOND * 15)


def _text_width(font, text: str) -> int:
    """Approximate pixel width of a string for a given font."""
    # graphics.DrawText returns the width of the last character drawn;
    # for width estimation we use a temporary canvas approach — but since
    # we don't have a scratch canvas here we fall back to a character-width
    # heuristic based on the known fonts.
    char_widths = {
        fonts.extrasmall: 4,
        fonts.small: 5,
        fonts.regular: 6,
        fonts.regular_bold: 6,
        fonts.regularplus: 7,
        fonts.regularplus_bold: 7,
        fonts.large: 8,
        fonts.large_bold: 8,
    }
    return len(text) * char_widths.get(font, 6)


def _draw_centred(canvas, font, y: int, colour, text: str):
    """Draw text centred horizontally on the 64-pixel-wide canvas."""
    w = _text_width(font, text)
    x = max(0, (screen.WIDTH - w) // 2)
    graphics.DrawText(canvas, font, x, y, colour, text)


class SportsScoreScene(object):
    def __init__(self):
        super().__init__()
        # Live game list — populated by Display._check_sports_data
        self._sports_data: list = []
        self._sports_index: int = 0
        self._sports_frame_count: int = 0
        self._last_drawn_game_id: str = ""
        # Colour overrides from user_config.json (fall back to module defaults)
        self._colour_home_score = _load_sports_colour("sports_home_colour", COLOUR_HOME_SCORE)
        self._colour_away_score = _load_sports_colour("sports_away_colour", COLOUR_AWAY_SCORE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_sports_area(self):
        """Wipe the full 64x32 canvas area used by the sports scene."""
        self.draw_square(0, 0, screen.WIDTH, screen.HEIGHT, colours.BLACK)

    def _draw_game(self, game: dict):
        """Render a single live game onto self.canvas."""
        self._clear_sports_area()

        home = game.get("home_abbr", "HOM")
        away = game.get("away_abbr", "AWY")
        home_score = game.get("home_score", 0)
        away_score = game.get("away_score", 0)
        period = game.get("period", 0)
        clock = game.get("clock", "")
        league = game.get("league", "").upper()

        # --- Top label row ---
        graphics.DrawText(
            self.canvas, LABEL_FONT, 0, LABEL_Y, COLOUR_LIVE_LABEL, "LIVE"
        )
        league_w = _text_width(LABEL_FONT, league)
        graphics.DrawText(
            self.canvas,
            LABEL_FONT,
            screen.WIDTH - league_w,
            LABEL_Y,
            COLOUR_LEAGUE,
            league,
        )

        # --- Try to load team logos ---
        away_logo = _load_sport_logo(away)
        home_logo = _load_sport_logo(home)

        if away_logo and home_logo:
            # With logos: place them at the sides, show score numbers in the
            # centre of the remaining space (x=12 to x=52 = 40px).
            from utilities.sports import SPORTS_LOGO_SIZE
            logo_x_home = screen.WIDTH - SPORTS_LOGO_SIZE

            # Draw logos directly onto the matrix (same pattern as FlightLogoScene)
            self.matrix.SetImage(away_logo, 0, LOGO_Y_OFFSET)
            self.matrix.SetImage(home_logo, logo_x_home, LOGO_Y_OFFSET)

            # Score: colour-coded numbers only, centred in the middle column
            score_segments = [
                (str(away_score), self._colour_away_score),
                (" - ",           COLOUR_SEPARATOR),
                (str(home_score), self._colour_home_score),
            ]
            full_score = "".join(s for s, _ in score_segments)
            score_w = _text_width(SCORE_FONT, full_score)
            left_bound = SPORTS_LOGO_SIZE
            centre_area = screen.WIDTH - 2 * SPORTS_LOGO_SIZE
            x = left_bound + max(0, (centre_area - score_w) // 2)
            for seg_text, seg_colour in score_segments:
                graphics.DrawText(self.canvas, SCORE_FONT, x, SCORE_Y, seg_colour, seg_text)
                x += _text_width(SCORE_FONT, seg_text)

        else:
            # Fallback: text-only layout  "AWY X - X HOM"
            separator = " - "
            segments = [
                (away,            COLOUR_ABBR),
                (" ",             COLOUR_SEPARATOR),
                (str(away_score), self._colour_away_score),
                (separator,       COLOUR_SEPARATOR),
                (str(home_score), self._colour_home_score),
                (" ",             COLOUR_SEPARATOR),
                (home,            COLOUR_ABBR),
            ]
            full_text = "".join(s for s, _ in segments)
            total_w = _text_width(SCORE_FONT, full_text)
            x = max(0, (screen.WIDTH - total_w) // 2)
            for seg_text, seg_colour in segments:
                graphics.DrawText(self.canvas, SCORE_FONT, x, SCORE_Y, seg_colour, seg_text)
                x += _text_width(SCORE_FONT, seg_text)

        # --- Period / clock row ---
        if period:
            period_str = f"P{period}"
            if clock:
                period_str = f"{period_str}  {clock}"
        else:
            period_str = game.get("status_detail", "")

        _draw_centred(self.canvas, PERIOD_FONT, PERIOD_Y, COLOUR_PERIOD, period_str)

    # ------------------------------------------------------------------
    # KeyFrame callbacks
    # ------------------------------------------------------------------

    @Animator.KeyFrame.add(1)
    def sports_score(self, count):
        """
        Runs every frame.  Only draws when live sports data is present.

        The Display class populates self._sports_data via its own KeyFrame
        that checks the SportsPoller.  This scene is entirely passive —
        it just renders whatever is in _sports_data.
        """
        if not self._sports_data:
            return

        # Planes take priority — wait until the current scroll cycle finishes
        # before taking over the display
        if self._data and not self._data_all_looped:
            return

        # Cycle through multiple live games
        self._sports_frame_count += 1
        if self._sports_frame_count >= FRAMES_PER_GAME:
            self._sports_frame_count = 0
            self._sports_index = (self._sports_index + 1) % len(self._sports_data)

        game = self._sports_data[self._sports_index % len(self._sports_data)]
        self._draw_game(game)

    @Animator.KeyFrame.add(0)
    def reset_sports(self):
        """Called by reset_scene().  Reset per-cycle state."""
        self._sports_frame_count = 0
        # Don't reset _sports_index so we don't restart mid-game-cycle
