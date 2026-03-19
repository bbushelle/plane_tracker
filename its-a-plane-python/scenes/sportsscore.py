"""
scenes/sportsscore.py

Displays live sports scores on the 64x32 LED matrix.

Layout (64 wide x 32 tall)
--------------------------
Row 0-7   : "LIVE" (red, left) + period/clock (grey, right)  e.g. "LIVE    P2 14:23"
Row 9-20  : Team logos at each side (12x12) — score numbers centred between them
Row 24-28 : Team abbreviations centred under each logo
Row 29-31 : League name centred

Text-only fallback (logos unavailable):
Row 0-7   : "LIVE" + period/clock header
Row 13-16 : Team abbreviations at left/right edges
Row 22-27 : Score centred
Row 29-31 : League name

The scene only draws content when self._sports_data is non-empty.
"""

import logging
import os
from utilities.animator import Animator
from setup import colours, fonts, frames, screen, theme
from rgbmatrix import graphics

logger = logging.getLogger(__name__)

# ---- Fonts ----
SCORE_FONT        = fonts.regular_bold   # logo mode score
FALLBACK_SCORE_FONT = fonts.small        # text-only mode score (narrower)
LABEL_FONT        = fonts.extrasmall     # header labels + abbreviations

# ---- Layout: logo mode ----
HEADER_Y          = 7    # "LIVE" + period/clock baseline
LOGO_Y_OFFSET     = 9    # logo top edge (logos are 12px tall → bottom at y=20)
SCORE_Y           = 21   # score numbers baseline (regular_bold, top of chars ~y=9)
ABBR_Y            = 28   # abbreviations baseline (below logos, top of chars ~y=24)
LEAGUE_Y          = 31   # league name baseline

# ---- Layout: text-only fallback ----
FALLBACK_ABBR_Y   = 14   # team abbreviations row
FALLBACK_SCORE_Y  = 25   # score row (small font, 8px tall → top ~y=18)

# ---- Colours ----
COLOUR_LIVE_LABEL = colours.RED
COLOUR_PERIOD     = colours.GREY
COLOUR_LEAGUE     = colours.GREY
COLOUR_HOME_SCORE = theme.SPORTS_HOME
COLOUR_AWAY_SCORE = theme.SPORTS_AWAY
COLOUR_ABBR       = colours.WHITE
COLOUR_SEPARATOR  = colours.GREY

# How many display frames to hold a single game before cycling to the next
FRAMES_PER_GAME = int(frames.PER_SECOND * 15)


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


def _text_width(font, text: str) -> int:
    """Approximate pixel width of a string for a given font."""
    char_widths = {
        fonts.extrasmall:      4,
        fonts.small:           5,
        fonts.regular:         6,
        fonts.regular_bold:    6,
        fonts.regularplus:     7,
        fonts.regularplus_bold: 7,
        fonts.large:           8,
        fonts.large_bold:      8,
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
        self._sports_data: list = []
        self._sports_index: int = 0
        self._sports_frame_count: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_sports_area(self):
        """Wipe the full 64x32 canvas."""
        self.draw_square(0, 0, screen.WIDTH, screen.HEIGHT, colours.BLACK)

    def _draw_logo_to_canvas(self, logo, offset_x: int, offset_y: int):
        """Blit a PIL RGB image onto self.canvas using SetPixel."""
        for py in range(logo.height):
            for px in range(logo.width):
                r, g, b = logo.getpixel((px, py))
                self.canvas.SetPixel(offset_x + px, offset_y + py, r, g, b)

    def _draw_game(self, game: dict):
        """Render a single live game onto self.canvas."""
        self._clear_sports_area()

        home       = game.get("home_abbr", "HOM")
        away       = game.get("away_abbr", "AWY")
        home_score = game.get("home_score", 0)
        away_score = game.get("away_score", 0)
        period     = game.get("period", 0)
        clock      = game.get("clock", "")
        league     = game.get("league", "").upper()

        # ---- Header row: "LIVE" left, period/clock right ----
        graphics.DrawText(self.canvas, LABEL_FONT, 0, HEADER_Y, COLOUR_LIVE_LABEL, "LIVE")

        if period:
            header_right = f"P{period}  {clock}" if clock else f"P{period}"
        else:
            # Pre/post-game — show a short status, truncated to avoid overflow
            detail = game.get("status_detail", "")
            header_right = detail[:10]

        if header_right:
            hw = _text_width(LABEL_FONT, header_right)
            graphics.DrawText(
                self.canvas, LABEL_FONT,
                screen.WIDTH - hw, HEADER_Y,
                COLOUR_PERIOD, header_right,
            )

        # ---- Try to load team logos ----
        away_logo = _load_sport_logo(away)
        home_logo = _load_sport_logo(home)

        if away_logo and home_logo:
            from utilities.sports import SPORTS_LOGO_SIZE
            home_logo_x = screen.WIDTH - SPORTS_LOGO_SIZE

            # Draw logos pixel-by-pixel into the canvas
            self._draw_logo_to_canvas(away_logo, 0, LOGO_Y_OFFSET)
            self._draw_logo_to_canvas(home_logo, home_logo_x, LOGO_Y_OFFSET)

            # Score numbers centred in the space between the logos
            left_bound   = SPORTS_LOGO_SIZE + 1
            centre_area  = screen.WIDTH - 2 * (SPORTS_LOGO_SIZE + 1)
            score_segs = [
                (str(away_score), COLOUR_AWAY_SCORE),
                (" - ",           COLOUR_SEPARATOR),
                (str(home_score), COLOUR_HOME_SCORE),
            ]
            full_score = "".join(s for s, _ in score_segs)
            score_w = _text_width(SCORE_FONT, full_score)
            x = left_bound + max(0, (centre_area - score_w) // 2)
            for seg_text, seg_colour in score_segs:
                graphics.DrawText(self.canvas, SCORE_FONT, x, SCORE_Y, seg_colour, seg_text)
                x += _text_width(SCORE_FONT, seg_text)

            # Abbreviations centred under each logo
            aw = _text_width(LABEL_FONT, away)
            ax = max(0, (SPORTS_LOGO_SIZE - aw) // 2)
            graphics.DrawText(self.canvas, LABEL_FONT, ax, ABBR_Y, COLOUR_ABBR, away)

            hw_a = _text_width(LABEL_FONT, home)
            hx   = home_logo_x + max(0, (SPORTS_LOGO_SIZE - hw_a) // 2)
            graphics.DrawText(self.canvas, LABEL_FONT, hx, ABBR_Y, COLOUR_ABBR, home)

        else:
            # ---- Text-only fallback ----
            # Abbreviations: away left-edge, home right-edge
            graphics.DrawText(
                self.canvas, LABEL_FONT, 0, FALLBACK_ABBR_Y,
                COLOUR_ABBR, away[:4],
            )
            home_abbr_w = _text_width(LABEL_FONT, home[:4])
            graphics.DrawText(
                self.canvas, LABEL_FONT,
                screen.WIDTH - home_abbr_w, FALLBACK_ABBR_Y,
                COLOUR_ABBR, home[:4],
            )

            # Score centred — use narrow font so double-digit scores fit
            score_segs = [
                (str(away_score), COLOUR_AWAY_SCORE),
                (" - ",           COLOUR_SEPARATOR),
                (str(home_score), COLOUR_HOME_SCORE),
            ]
            full_score = "".join(s for s, _ in score_segs)
            score_w = _text_width(FALLBACK_SCORE_FONT, full_score)
            x = max(0, (screen.WIDTH - score_w) // 2)
            for seg_text, seg_colour in score_segs:
                graphics.DrawText(
                    self.canvas, FALLBACK_SCORE_FONT, x, FALLBACK_SCORE_Y,
                    seg_colour, seg_text,
                )
                x += _text_width(FALLBACK_SCORE_FONT, seg_text)

        # ---- League name centred at bottom ----
        if league:
            _draw_centred(self.canvas, LABEL_FONT, LEAGUE_Y, COLOUR_LEAGUE, league)

    # ------------------------------------------------------------------
    # KeyFrame callbacks
    # ------------------------------------------------------------------

    @Animator.KeyFrame.add(1)
    def sports_score(self, count):
        """
        Runs every frame.  Draws sports display when live data is present.
        Planes take priority — waits for the current scroll cycle to finish.
        """
        if not self._sports_data:
            return

        if self._data and not self._data_all_looped:
            return

        self._sports_frame_count += 1
        if self._sports_frame_count >= FRAMES_PER_GAME:
            self._sports_frame_count = 0
            self._sports_index = (self._sports_index + 1) % len(self._sports_data)

        game = self._sports_data[self._sports_index % len(self._sports_data)]
        self._draw_game(game)

    @Animator.KeyFrame.add(0)
    def reset_sports(self):
        """Called by reset_scene(). Reset per-cycle state."""
        self._sports_frame_count = 0
