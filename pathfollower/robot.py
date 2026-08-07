# robot.py -- hardware wrapper: sensors, motors, action primitives, calibration.
#
# THIS RUNS ON THE BRICK ONLY. It imports ev3dev2, which cannot be imported on
# the laptop. Keep all hardware I/O in here so mdp.py / qlearning.py stay pure.
# Python 3.5 on ev3dev-stretch: no f-strings.

import time

from ev3dev2.motor import Motor, OUTPUT_A, OUTPUT_C, SpeedPercent
from ev3dev2.sensor.lego import ColorSensor, InfraredSensor
from ev3dev2.button import Button
from ev3dev2.sound import Sound

import config
from mdp import FORWARD, LEFT, RIGHT, REVERSE, CW, ACW


class Robot(object):
    def __init__(self, speed=None):
        # Mixed motor types (confirmed by smoke_test 2026-08-07):
        #   outC = LARGE  motor -> LEFT  wheel
        #   outA = MEDIUM motor -> RIGHT wheel
        # MoveTank can't mix a large + medium, so drive two independent Motor
        # objects. Positive speed = forward for both (no inversion needed).
        self.left = Motor(OUTPUT_C)    # large motor, left wheel
        self.right = Motor(OUTPUT_A)   # medium motor, right wheel

        self.cs = ColorSensor()
        self.cs.mode = 'COL-REFLECT'      # reflected light intensity, 0-100

        self.ir = InfraredSensor()
        self.ir.mode = 'IR-PROX'          # proximity, 0-100, low = close

        self.btn = Button()
        self.snd = Sound()

        self.speed = config.TRAIN_SPEED if speed is None else speed

    # --- sensing ------------------------------------------------------------
    def brightness(self):
        """Raw reflected-light reading, 0-100."""
        return self.cs.reflected_light_intensity

    def proximity(self):
        """Raw IR proximity, 0-100 (low = close)."""
        return self.ir.proximity

    def obstacle_ahead(self):
        """Confirmed obstacle: require several consecutive close reads to
        reject IR noise. Scripted (non-RL) -- explicitly allowed."""
        for _ in range(config.IR_CONFIRM_READS):
            if self.proximity() > config.IR_OBSTACLE_THRESHOLD:
                return False
            time.sleep(0.01)
        return True

    # --- action primitives (allowed: only the mechanics, not the policy) ----
    def _drive(self, left_pct, right_pct):
        """Set both motors (non-blocking). Convention: +ve = forward."""
        self.left.on(SpeedPercent(left_pct))
        self.right.on(SpeedPercent(right_pct))

    def act(self, action):
        """Execute one action primitive (non-blocking motor set)."""
        s = self.speed
        t = config.TURN_DIFF
        if action == FORWARD:
            self._drive(s, s)
        elif action == REVERSE:
            self._drive(-s, -s)
        elif action == LEFT:
            self._drive(-t, t)     # left wheel back, right fwd -> pivot left
        elif action == RIGHT:
            self._drive(t, -t)     # left wheel fwd, right back -> pivot right

    def stop(self):
        self.left.off()
        self.right.off()

    # --- direction bit ------------------------------------------------------
    def read_direction(self):
        """Block until a button picks the run direction: LEFT->CW, RIGHT->ACW.
        This is the one thing we *tell* the robot (see CLAUDE.md section 5);
        it still learns which turn recovers the line."""
        self.snd.beep()
        while True:
            if self.btn.left:
                self._wait_release()
                return CW
            if self.btn.right:
                self._wait_release()
                return ACW
            time.sleep(0.02)

    def wait_enter(self):
        """Block until ENTER -- used to advance episodes after a manual reset."""
        while not self.btn.enter:
            time.sleep(0.02)
        self._wait_release()

    def _wait_release(self):
        while self.btn.any():
            time.sleep(0.02)

    # --- calibration --------------------------------------------------------
    def _sample(self, n=15, gap=0.03):
        """Average n reflected-light reads to smooth sensor noise. Returns
        (mean, lo, hi) as ints."""
        vals = []
        for _ in range(n):
            vals.append(self.brightness())
            time.sleep(gap)
        mean = sum(vals) / float(len(vals))
        return (int(round(mean)), min(vals), max(vals))

    def calibrate(self):
        """Interactive calibration: sample the TAPE, the BACKGROUND, then the
        EDGE (straddling the boundary). Order-agnostic about which surface is
        brighter -- the two off-edge states are symmetric. Averages each sample
        to beat noise, derives thresholds, sanity-checks them, and prints values
        to paste into config.py. Returns (tape, background, edge)."""
        print('Calibration. Keep the sensor at its FIXED mounted height throughout.')

        print('1/3: sensor FULLY ON the tape, then press ENTER.')
        self.wait_enter()
        tape, tlo, thi = self._sample()
        print('  tape       mean=%d (spread %d-%d)' % (tape, tlo, thi))

        print('2/3: sensor FULLY OFF the tape (background), then press ENTER.')
        self.wait_enter()
        bg, glo, ghi = self._sample()
        print('  background mean=%d (spread %d-%d)' % (bg, glo, ghi))

        # Order-agnostic: BLACK = dark extreme, WHITE = bright extreme, whichever
        # physical surface each turns out to be. EDGE = the middle band.
        lo = min(tape, bg)
        hi = max(tape, bg)
        span = hi - lo
        black_max = lo + int(span * 0.33)
        white_min = lo + int(span * 0.66)

        print('')
        print('  (bright surface reads %d, dark surface reads %d, span %d)'
              % (hi, lo, span))
        print('=== Suggested config.py values ===')
        print('  BLACK_MAX = %d' % black_max)
        print('  WHITE_MIN = %d' % white_min)
        if span < 20:
            print('  WARN: contrast span is only %d -- weak. Lower the sensor'
                  ' (closer to surface) or improve lighting.' % span)

        # Sweep test: instead of a fiddly static straddle, drag the sensor across
        # the boundary while we log continuously, and check the EDGE band is
        # actually visited during motion (it only helps if the sensor passes
        # through it while driving).
        print('')
        print('SWEEP: press ENTER, then slowly drag the sensor back and forth')
        print('across the tape edge a few times for ~6 seconds.')
        self.wait_enter()
        samples = self._sweep(secs=6.0)
        n_black = len([v for v in samples if v <= black_max])
        n_edge = len([v for v in samples if black_max < v < white_min])
        n_white = len([v for v in samples if v >= white_min])
        total = len(samples)
        print('  swept %d samples: dark=%d  EDGE=%d  bright=%d  (range %d-%d)'
              % (total, n_black, n_edge, n_white, min(samples), max(samples)))
        edge_pct = 100.0 * n_edge / total if total else 0.0
        print('  EDGE band was occupied %.0f%% of the sweep.' % edge_pct)
        if n_edge == 0:
            print('  WARN: EDGE band NEVER hit -- boundary too sharp for this')
            print('        sensor height. Raise the sensor a few mm (wider spot)')
            print('        so transitions are gradual, then recalibrate.')
        elif edge_pct < 10:
            print('  NOTE: EDGE band is thin. Line-following will work but the')
            print('        EDGE reward is sparse; raising the sensor slightly helps.')
        else:
            print('  CHECK: EDGE band is reachable during motion -- good.')
        return (tape, bg, samples)

    def _sweep(self, secs=6.0, gap=0.03):
        """Log reflected-light continuously for `secs` while the user drags the
        sensor across the boundary. Returns the list of readings."""
        samples = []
        t_end = time.time() + secs
        while time.time() < t_end:
            samples.append(self.brightness())
            time.sleep(gap)
        return samples
