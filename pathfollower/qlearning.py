# qlearning.py -- tabular Q-learning: the Q-table, action selection, the update
# rule, and JSON persistence.
#
# PURE LOGIC ONLY. No hardware imports. Unit-testable off-brick.
# Python 3.5 compatible: no f-strings, no numpy.

import json
import random

import config
from mdp import STATES, ACTIONS


def _key(state):
    """Encode a (brightness, dir) tuple as a JSON-friendly string, e.g.
    ('EDGE', 'CW') -> 'EDGE|CW'."""
    return state[0] + '|' + state[1]


def _unkey(s):
    """Inverse of _key: 'EDGE|CW' -> ('EDGE', 'CW')."""
    parts = s.split('|')
    return (parts[0], parts[1])


class QTable(object):
    def __init__(self):
        # Nested dict: q[state_key][action] = value. Initialised to 0.0.
        self.q = {}
        for state in STATES:
            self.q[_key(state)] = {}
            for action in ACTIONS:
                self.q[_key(state)][action] = 0.0

    # --- access -------------------------------------------------------------
    def get(self, state, action):
        return self.q[_key(state)][action]

    def actions_for(self, state):
        return self.q[_key(state)]

    def best_action(self, state):
        """Greedy action for a state, ties broken randomly."""
        vals = self.q[_key(state)]
        best = max(vals.values())
        candidates = [a for a in ACTIONS if vals[a] == best]
        return random.choice(candidates)

    def max_value(self, state):
        return max(self.q[_key(state)].values())

    # --- learning -----------------------------------------------------------
    def choose_action(self, state, epsilon):
        """Epsilon-greedy: explore with prob epsilon, else exploit."""
        if random.random() < epsilon:
            return random.choice(ACTIONS)
        return self.best_action(state)

    def learn(self, s, a, r, s2):
        """Standard Q-learning update:
        Q(s,a) <- Q(s,a) + alpha * (r + gamma * max_a' Q(s2,a') - Q(s,a))"""
        old = self.q[_key(s)][a]
        td_target = r + config.GAMMA * self.max_value(s2)
        self.q[_key(s)][a] = old + config.ALPHA * (td_target - old)

    # --- persistence --------------------------------------------------------
    def save(self, path=None):
        if path is None:
            path = config.QTABLE_PATH
        with open(path, 'w') as f:
            json.dump(self.q, f, indent=2, sort_keys=True)

    def load(self, path=None):
        if path is None:
            path = config.QTABLE_PATH
        with open(path, 'r') as f:
            loaded = json.load(f)
        # Merge into the fully-initialised table so missing keys stay at 0.0.
        for sk in loaded:
            if sk in self.q:
                for a in loaded[sk]:
                    if a in self.q[sk]:
                        self.q[sk][a] = loaded[sk][a]
        return self

    # --- reporting (evidence for the report/demo) ---------------------------
    def pretty(self):
        """Human-readable dump of the table -- used as marking evidence that the
        robot learned each behaviour (e.g. REVERSE wins in LOST states)."""
        lines = []
        header = 'STATE'.ljust(14)
        for a in ACTIONS:
            header += a.rjust(10)
        header += '   ->best'
        lines.append(header)
        lines.append('-' * len(header))
        for state in STATES:
            row = _key(state).ljust(14)
            for a in ACTIONS:
                row += ('%.2f' % self.q[_key(state)][a]).rjust(10)
            row += '   ' + self.best_action(state)
            lines.append(row)
        return '\n'.join(lines)


def epsilon_for_episode(episode):
    """Decayed epsilon for a given (0-based) episode index, floored at END."""
    eps = config.EPSILON_START * (config.EPSILON_DECAY ** episode)
    if eps < config.EPSILON_END:
        eps = config.EPSILON_END
    return eps
