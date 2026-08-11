# mdp.py -- the MDP definition: states, actions, get_state(), reward().
#
# PURE LOGIC ONLY. No hardware imports (no ev3dev2). Everything here must be
# unit-testable on the laptop with mocked sensor values.
#
# IMPORTANT (see CLAUDE.md section 2): nothing in this file maps a state to a
# chosen action. get_state() only *classifies* the sensor reading; reward()
# only *scores* an outcome. Which action to take in which state is learned by
# Q-learning -- never decided here.

import config

# --- Brightness classes -----------------------------------------------------
WHITE = 'WHITE'   # drifted onto the tape
EDGE = 'EDGE'     # on the tape boundary -- this is where we want to be
BLACK = 'BLACK'   # drifted onto the background
LOST = 'LOST'     # stuck at an extreme for >= k steps

# --- Direction bit ----------------------------------------------------------
CW = 'CW'
ACW = 'ACW'

# --- Actions (primitives; defining these is allowed) ------------------------
FORWARD = 'FORWARD'
LEFT = 'LEFT'
RIGHT = 'RIGHT'
REVERSE = 'REVERSE'
ACTIONS = [FORWARD, LEFT, RIGHT, REVERSE]

# All eight states: 4 brightness x 2 direction.
BRIGHTNESS_LEVELS = [WHITE, EDGE, BLACK, LOST]
DIRECTIONS = [CW, ACW]
STATES = [(b, d) for d in DIRECTIONS for b in BRIGHTNESS_LEVELS]


def classify_brightness(value):
    """Map a raw reflected-light value (0-100) to WHITE / EDGE / BLACK.

    LOST is not decided here -- it depends on history (see get_state), not on a
    single reading.
    """
    if value <= config.BLACK_MAX:
        return BLACK
    if value >= config.WHITE_MIN:
        return WHITE
    return EDGE


def get_state(value, direction, off_edge_streak):
    """Return the (brightness, dir) state tuple.

    value            : raw reflected-light reading (0-100)
    direction        : CW or ACW (set by button at episode start)
    off_edge_streak  : how many consecutive prior steps were off the edge
                       (WHITE or BLACK). If >= LOST_K we are LOST.

    This only classifies -- it does not pick an action.
    """
    brightness = classify_brightness(value)
    if brightness != EDGE and off_edge_streak >= config.LOST_K:
        brightness = LOST
    return (brightness, direction)


def update_off_edge_streak(value, streak):
    """Increment the off-edge counter while off the line, reset it on EDGE."""
    if classify_brightness(value) == EDGE:
        return 0
    return streak + 1


def reward(state, action):
    """Shaped, dense reward for landing in `state` (after taking `action`).

    Design (see CLAUDE.md section 5):
      EDGE  -> high positive (the goal state)
      WHITE / BLACK -> small / zero (off the edge but not yet lost)
      LOST  -> negative (only REVERSE should let it escape)
      + small bonus for FORWARD while on the edge (rewards progress,
        discourages wiggling in place)

    Note this rewards the *outcome state*; it never says "REVERSE is correct".
    The robot discovers that REVERSE is what leads out of LOST because staying
    LOST keeps paying the negative reward.
    """
    brightness = state[0]

    if brightness == EDGE:
        base = config.REWARD_EDGE
        if action == FORWARD:
            base += config.REWARD_FORWARD_BONUS   # progress bonus along the line
        return base
    if brightness == WHITE:
        return config.REWARD_OFF
    if brightness == BLACK:
        return config.REWARD_OFF
    if brightness == LOST:
        return config.REWARD_LOST
    return config.REWARD_OFF
