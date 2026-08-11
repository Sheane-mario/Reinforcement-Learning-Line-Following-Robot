# config.py -- ports, calibration thresholds, hyperparameters.
# Edit these to match your hardware and lighting. No hardware imports here so
# this file can be read on the laptop too.

# ---------------------------------------------------------------------------
# Ports  (TODO: confirm on the brick -- see CLAUDE.md section 12)
# ---------------------------------------------------------------------------
# Motors: DETECTED 2026-08-07 by smoke_test --
#   outA = MEDIUM motor (lego-ev3-m-motor)
#   outC = LARGE  motor (lego-ev3-l-motor)
#   outB = empty
# CONFIRMED 2026-08-07 by physical pulse test:
#   outC (large)  drives the LEFT  wheel, +speed = forward
#   outA (medium) drives the RIGHT wheel, +speed = forward
#   both +speed => robot goes straight forward (no inversion needed)
MOTOR_LEFT_PORT = 'outC'    # OUTPUT_C (large)  -> left wheel
MOTOR_RIGHT_PORT = 'outA'   # OUTPUT_A (medium) -> right wheel

# Sensors: DETECTED 2026-08-07 --
COLOR_SENSOR_PORT = 'in2'   # INPUT_2 (was assumed in1)
IR_SENSOR_PORT = 'in4'      # INPUT_4 (confirmed)

# ---------------------------------------------------------------------------
# Colour calibration (reflected light intensity, 0-100)
# ---------------------------------------------------------------------------
# White tape reads high, black paper reads low. The EDGE band sits between.
# Recalibrate at the start of a session if lighting changed (robot.calibrate()).
#
# CALIBRATED 2026-08-07 (repeatable over several runs):
#   tape (white/bright) ~= 54,  background (black/dark) ~= 16,  midpoint ~= 35.
# The tape boundary is sharp (few intermediate readings), so the EDGE band is
# deliberately WIDENED around the 35 midpoint rather than a narrow 33/66 split.
# This catches more transition samples and gives smoother following.
# If line-following is still twitchy, raise the sensor a few mm (wider spot ->
# more gradual transitions) and recalibrate.
BLACK_MAX = 25      # <= this  -> BLACK  (clearly off the tape)
WHITE_MIN = 45      # >= this  -> WHITE  (clearly on the tape)
# EDGE band = (BLACK_MAX, WHITE_MIN)   i.e. 26..44 -> EDGE (the good state)

# LOST detection: how many consecutive steps stuck at an extreme (all WHITE or
# all BLACK, i.e. off the edge) before we declare the LOST state. Raised 8->15
# so LOST means TRULY stuck (gives arc-turns time to recover first, and stops
# LOST from being entered so often that it becomes an absorbing sink).
LOST_K = 15

# ---------------------------------------------------------------------------
# Reward shaping magnitudes (see mdp.reward). These score the OUTCOME STATE --
# they never name which action is "right" (that stays learned, not hardcoded).
# ---------------------------------------------------------------------------
REWARD_EDGE = 10.0          # on the edge -- the goal state (highest)
REWARD_FORWARD_BONUS = 2.0  # extra for FORWARD while on the edge (progress)
REWARD_OFF = 0.0            # WHITE/BLACK: off the edge but not yet lost
REWARD_LOST = -4.0          # stuck. Softened -10 -> -4 so LOST stops being an
                            # absorbing sink the robot can never climb out of.

# ---------------------------------------------------------------------------
# IR obstacle detection (proximity 0-100, low = close)
# ---------------------------------------------------------------------------
# Baseline (nothing ahead) measured ~77-83 on 2026-08-07. Obstacles read lower.
# This threshold is an untuned starting point -- confirm during the obstacle
# phase by noting ir.proximity at your intended trigger distance.
IR_OBSTACLE_THRESHOLD = 30   # <= this -> something is close
IR_CONFIRM_READS = 3         # require this many consecutive close reads

# ---------------------------------------------------------------------------
# Motor speeds (percent)
# ---------------------------------------------------------------------------
TRAIN_SPEED = 25    # slow during training -> better discrete-time approximation
DEMO_SPEED = 45     # faster once the policy is frozen
# Turns are gentle forward-ARCS, not in-place pivots: the inner wheel runs at
# this fraction of drive speed while the outer wheel runs full. This lets the
# robot correct while still moving forward so it can ride a thin edge (in-place
# pivots overshoot a sharp edge and lose the line). Also makes REVERSE the only
# action that moves backward -> the unique escape from a dead-end (helps LOST).
TURN_INNER_FRAC = 0.25   # 0 = sharp pivot-ish, 1 = straight; 0.25 = gentle arc

# ---------------------------------------------------------------------------
# Q-learning hyperparameters
# ---------------------------------------------------------------------------
ALPHA = 0.3         # learning rate (moderate; sensors are noisy)
GAMMA = 0.9         # discount (slight lookahead helps smoothness)
EPSILON_START = 0.9
EPSILON_END = 0.05
# Decay is per-episode. Real-world runs only manage ~20-40 hand-reset episodes,
# so 0.995 (tuned for hundreds) leaves epsilon near 0.9 the whole run -> the
# robot never exploits. 0.90 reaches the 0.05 floor by ~episode 30: explores
# the first third, then exploits. (Was 0.995; changed 2026-08-07 after a run
# where epsilon only fell 0.900 -> 0.818 over 20 episodes.)
EPSILON_DECAY = 0.90    # multiplied per episode

# ---------------------------------------------------------------------------
# Control loop timing
# ---------------------------------------------------------------------------
DT = 0.10           # seconds each action runs before re-deciding (0.08-0.12)

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
QTABLE_PATH = 'qtable.json'
