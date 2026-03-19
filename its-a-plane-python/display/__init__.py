import json as _json
import os
import sys
from datetime import datetime, timedelta

# Transient file written by the web UI to temporarily suppress sports display
_SPORTS_PAUSE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sports_pause.json",
)


def _sports_is_paused() -> bool:
    try:
        with open(_SPORTS_PAUSE_FILE) as f:
            data = _json.load(f)
        return datetime.now().timestamp() < data.get("expires_at", 0)
    except Exception:
        return False
from setup import frames
from utilities.animator import Animator
from utilities.overhead import Overhead
from utilities.sports import SportsPoller

from scenes.temperature import TemperatureScene
from scenes.flightdetails import FlightDetailsScene
from scenes.flightlogo import FlightLogoScene
from scenes.journey import JourneyScene
from scenes.loadingpulse import LoadingPulseScene
from scenes.clock import ClockScene
from scenes.planedetails import PlaneDetailsScene
from scenes.daysforecast import DaysForecastScene
from scenes.date import DateScene
from scenes.sportsscore import SportsScoreScene

from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions


def flight_updated(flights_a, flights_b):
    get_callsigns = lambda flights: [(f["callsign"], f["direction"]) for f in flights]
    updatable_a = set(get_callsigns(flights_a))
    updatable_b = set(get_callsigns(flights_b))

    return updatable_a == updatable_b


try:
    # Attempt to load config data
    from config import (
        BRIGHTNESS,
        GPIO_SLOWDOWN,
        HAT_PWM_ENABLED,
        BRIGHTNESS_NIGHT,
        NIGHT_START,
        NIGHT_END,
        NIGHT_BRIGHTNESS,
    )
    # Parse NIGHT_START and NIGHT_END from strings to datetime objects
    NIGHT_START = datetime.strptime(NIGHT_START, "%H:%M")
    NIGHT_END = datetime.strptime(NIGHT_END, "%H:%M")

except (ModuleNotFoundError, NameError):
    # If there's no config data
    BRIGHTNESS = 100
    GPIO_SLOWDOWN = 1
    HAT_PWM_ENABLED = True
    NIGHT_BRIGHTNESS = False

# Sports config (optional — gracefully disabled if absent)
try:
    from config import SPORTS_ENABLED, SPORTS_DISPLAY_INTERVAL, SPORTS_TEAMS, SPORTS_SCORE_DELAY
except (ImportError, ModuleNotFoundError, NameError):
    SPORTS_ENABLED = False
    SPORTS_DISPLAY_INTERVAL = 30
    SPORTS_SCORE_DELAY = 10
    SPORTS_TEAMS = []

def adjust_brightness(matrix):
    if NIGHT_BRIGHTNESS is False:
        return  # Do nothing if NIGHT_BRIGHTNESS is False
        
    # Redraw screen every frame
    now = datetime.now().time().replace(second=0, microsecond=0)  # Extract only hours and minutes
    night_start_time = NIGHT_START.time().replace(second=0, microsecond=0)
    night_end_time = NIGHT_END.time().replace(second=0, microsecond=0)

    # Check if current time is after NIGHT_END and before NIGHT_START
    if night_end_time <= now < night_start_time:
        new_brightness = BRIGHTNESS
    else:
        new_brightness = BRIGHTNESS_NIGHT
        
    # Check if the brightness has changed
    if matrix.brightness != new_brightness:
        # Update the brightness
        matrix.brightness = new_brightness
        
class Display(
    SportsScoreScene,
    TemperatureScene,
    FlightDetailsScene,
    FlightLogoScene,
    JourneyScene,
    LoadingPulseScene,
    PlaneDetailsScene,
    ClockScene,
    DaysForecastScene,
    DateScene,
    Animator,
):
    def __init__(self):
        # Setup Display
        options = RGBMatrixOptions()
        options.hardware_mapping = "adafruit-hat-pwm" if HAT_PWM_ENABLED else "adafruit-hat"
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.row_address_type = 0
        options.multiplexing = 0
        options.pwm_bits = 11
        options.brightness = BRIGHTNESS
        options.pwm_lsb_nanoseconds = 130
        options.led_rgb_sequence = "RGB"
        options.pixel_mapper_config = ""
        options.show_refresh_rate = 0
        options.gpio_slowdown = GPIO_SLOWDOWN
        options.disable_hardware_pulsing = True
        options.drop_privileges = True
        self.matrix = RGBMatrix(options=options)

        # Setup canvas
        self.canvas = self.matrix.CreateFrameCanvas()
        self.canvas.Clear()

        # Data to render
        self._data_index = 0
        self._data = []

        # Start Looking for planes
        self.overhead = Overhead()
        self.overhead.grab_data()

        # Start looking for live sports scores
        if SPORTS_ENABLED and SPORTS_TEAMS:
            self.sports_poller = SportsPoller(teams_config=SPORTS_TEAMS)
            self.sports_poller.grab_data()
            # Pre-download team logos in the background so they are ready
            # before any game starts.  Skips logos that are already cached.
            from utilities.sports import download_team_logos
            from threading import Thread
            Thread(
                target=download_team_logos,
                args=(SPORTS_TEAMS,),
                daemon=True,
            ).start()
        else:
            self.sports_poller = None

        # Track how long we have been showing sports so we can time-limit it
        self._sports_display_frames = 0
        # frames.PER_SECOND is 1/PERIOD; SPORTS_DISPLAY_INTERVAL is in seconds
        self._sports_display_max_frames = int(
            frames.PER_SECOND * SPORTS_DISPLAY_INTERVAL
        )
        # Timestamp after which a pending score-change display should fire;
        # None means no score change is queued.
        self._sports_score_show_at = None

        # Initalise animator and scenes
        super().__init__()

        # Overwrite any default settings from
        # Animator or Scenes
        self.delay = frames.PERIOD

    def draw_square(self, x0, y0, x1, y1, colour):
        for x in range(x0, x1):
            _ = graphics.DrawLine(self.canvas, x, y0, x, y1, colour)

    # ------------------------------------------------------------------
    # Sports polling and display-gating
    # ------------------------------------------------------------------

    # Poll the sports API every 60 seconds (live) or every 5 minutes (idle).
    # The KeyFrame divisor here is based on the faster rate; the poller
    # itself decides whether to re-fetch or skip based on its own timer.
    # We use frames.PER_SECOND * 60 == once per 60 seconds of wall-clock
    # time (at the 0.1 s frame period that equals 600 frames).
    @Animator.KeyFrame.add(int(frames.PER_SECOND * 60))
    def poll_sports_data(self, count):
        """Periodically re-fetch live game data from ESPN."""
        if self.sports_poller is None:
            return
        # Only fetch when not already processing
        if not self.sports_poller.processing:
            # Decide poll rate: live game -> 60 s, idle -> 5 min
            # count resets to 0 each time the keyframe divisor fires, so
            # we use a simple flag derived from current data.
            if self.sports_poller.has_live_game:
                # Already set to fire every 60 s — always fetch
                self.sports_poller.grab_data()
            else:
                # Only re-fetch on every 5th cycle (5 x 60 s = 5 min)
                if count % 5 == 0:
                    self.sports_poller.grab_data()

    @Animator.KeyFrame.add(int(frames.PER_SECOND * 5))
    def check_sports_data(self, count):
        """
        Consume new data from the SportsPoller and decide whether to show
        the sports scene.

        Logic
        -----
        * If SPORTS_ENABLED is False or no poller exists, clear sports data.
        * If a score change is detected, immediately show the sports scene by
          resetting the display and populating self._sports_data.
        * If there is live game data, populate self._sports_data so
          SportsScoreScene can render it.
        * After SPORTS_DISPLAY_INTERVAL seconds of sports, clear self._sports_data
          so the plane/clock scenes reclaim the display.
        """
        if self.sports_poller is None:
            self._sports_data = []
            return

        # Consume new data from poller
        if self.sports_poller.new_data:
            fresh_games = self.sports_poller.data  # clears new_data flag
            score_changed = self.sports_poller.score_changed

            if fresh_games and not _sports_is_paused():
                self._sports_data = fresh_games
                self._sports_display_frames = 0  # restart display timer

                # On a score change, queue a delayed display instead of
                # switching immediately — gives the TV broadcast time to catch up
                if score_changed and self._sports_score_show_at is None:
                    self._sports_score_show_at = datetime.now() + timedelta(seconds=SPORTS_SCORE_DELAY)
            else:
                # No live games (or sports paused) — stop showing sports
                self._sports_data = []
                self._sports_score_show_at = None

        # If pause was activated mid-display, clear sports immediately
        if self._sports_data and _sports_is_paused():
            self._sports_data = []
            self._sports_score_show_at = None

        # Fire delayed score-change display once the delay has elapsed.
        # Only reset the scene if planes aren't mid-scroll — sports_score will
        # start drawing naturally on the next completed plane cycle if we skip this.
        if self._sports_score_show_at is not None and datetime.now() >= self._sports_score_show_at:
            self._sports_score_show_at = None
            if not self._data or self._data_all_looped:
                self.reset_scene()

        # Enforce the display-interval time limit
        if self._sports_data:
            self._sports_display_frames += 1
            if self._sports_display_frames >= self._sports_display_max_frames:
                # Time is up; stop showing sports until next data arrives
                self._sports_data = []
                self._sports_display_frames = 0

    @Animator.KeyFrame.add(0)
    def clear_screen(self):
        # First operation after
        # a screen reset
        self.canvas.Clear()

    @Animator.KeyFrame.add(frames.PER_SECOND * 5)
    def check_for_loaded_data(self, count):
        if self.overhead.new_data:
            # Check if there's data
            there_is_data = len(self._data) > 0 or not self.overhead.data_is_empty

            # this marks self.overhead.data as no longer new
            new_data = self.overhead.data

            # See if this matches the data already on the screen
            # This test only checks if it's 2 lists with the same
            # callsigns, regardless or order
            data_is_different = not flight_updated(self._data, new_data)

            if data_is_different:
                self._data_index = 0
                self._data_all_looped = False
                self._data = new_data

            # Only reset if there's flight data already
            # on the screen, of if there's some new
            # data available to draw which is different
            # from the current data
            reset_required = there_is_data and data_is_different

            if reset_required:
                self.reset_scene()

    @Animator.KeyFrame.add(1)
    def sync(self, count):
        # Redraw screen every frame
        _ = self.matrix.SwapOnVSync(self.canvas)
        
    
        # Adjust brightness
        adjust_brightness(self.matrix)

    @Animator.KeyFrame.add(frames.PER_SECOND * 30)
    def grab_new_data(self, count):
        # Only grab data if we're not already searching
        # for planes, or if there's new data available
        # which hasn't been displayed.
        #
        # We also need wait until all previously grabbed
        # data has been looped through the display.
        #
        # Last, if our internal store of the data
        # is empty, try and grab data
        if not (self.overhead.processing and self.overhead.new_data) and (
            self._data_all_looped or len(self._data) <= 1
        ):
            self.overhead.grab_data()

    def run(self):
        try:
            # Start loop
            print("Press CTRL-C to stop")
            self.play()

        except KeyboardInterrupt:
            print("Exiting\n")
            sys.exit(0)
