# test_logic.py -- off-brick unit tests for the PURE logic (mdp + qlearning).
# Runs on the laptop -- no ev3dev2 needed. Run:  python3 test_logic.py
# Python 3.5 compatible.

import os
import tempfile

import config
import mdp
from qlearning import QTable, epsilon_for_episode


def _check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_classify_brightness():
    _check(mdp.classify_brightness(0) == mdp.BLACK, 'low -> BLACK')
    _check(mdp.classify_brightness(100) == mdp.WHITE, 'high -> WHITE')
    mid = (config.BLACK_MAX + config.WHITE_MIN) // 2
    _check(mdp.classify_brightness(mid) == mdp.EDGE, 'mid -> EDGE')


def test_lost_requires_streak():
    # Off the edge but streak below k -> not LOST yet.
    s = mdp.get_state(0, mdp.CW, config.LOST_K - 1)
    _check(s == (mdp.BLACK, mdp.CW), 'below k stays BLACK, got %s' % str(s))
    # Streak at k -> LOST.
    s = mdp.get_state(0, mdp.CW, config.LOST_K)
    _check(s == (mdp.LOST, mdp.CW), 'at k -> LOST, got %s' % str(s))
    # On the edge is never LOST regardless of streak.
    mid = (config.BLACK_MAX + config.WHITE_MIN) // 2
    s = mdp.get_state(mid, mdp.CW, 999)
    _check(s == (mdp.EDGE, mdp.CW), 'edge never LOST, got %s' % str(s))


def test_streak_update():
    mid = (config.BLACK_MAX + config.WHITE_MIN) // 2
    _check(mdp.update_off_edge_streak(mid, 5) == 0, 'edge resets streak')
    _check(mdp.update_off_edge_streak(0, 5) == 6, 'off-edge increments streak')


def test_reward_ordering():
    edge_fwd = mdp.reward((mdp.EDGE, mdp.CW), mdp.FORWARD)
    edge_turn = mdp.reward((mdp.EDGE, mdp.CW), mdp.LEFT)
    lost = mdp.reward((mdp.LOST, mdp.CW), mdp.REVERSE)
    white = mdp.reward((mdp.WHITE, mdp.CW), mdp.FORWARD)
    _check(edge_fwd > edge_turn, 'FORWARD on edge beats turning on edge')
    _check(edge_turn > white, 'edge beats white')
    _check(lost < 0, 'LOST is negative')


def test_qlearning_converges_lost_to_reverse():
    """With the shaped reward, REVERSE should become the best action out of a
    LOST state. This is the key 'reverse is learned' evidence, off-brick."""
    qt = QTable()
    lost = (mdp.LOST, mdp.CW)
    edge = (mdp.EDGE, mdp.CW)
    # Simulate: REVERSE from LOST reaches EDGE; other actions stay LOST.
    for _ in range(500):
        for a in mdp.ACTIONS:
            if a == mdp.REVERSE:
                nxt = edge
            else:
                nxt = lost
            r = mdp.reward(nxt, a)
            qt.learn(lost, a, r, nxt)
        # keep EDGE valuable
        qt.learn(edge, mdp.FORWARD, mdp.reward(edge, mdp.FORWARD), edge)
    best = qt.best_action(lost)
    _check(best == mdp.REVERSE,
           'expected REVERSE learned in LOST, got %s' % best)


def test_save_load_roundtrip():
    qt = QTable()
    qt.learn((mdp.EDGE, mdp.CW), mdp.FORWARD, 10.0, (mdp.EDGE, mdp.CW))
    path = os.path.join(tempfile.gettempdir(), 'qtable_test.json')
    qt.save(path)
    qt2 = QTable()
    qt2.load(path)
    _check(qt2.get((mdp.EDGE, mdp.CW), mdp.FORWARD) ==
           qt.get((mdp.EDGE, mdp.CW), mdp.FORWARD), 'roundtrip preserves value')
    os.remove(path)


def test_epsilon_decay():
    _check(epsilon_for_episode(0) == config.EPSILON_START, 'ep0 = start')
    _check(epsilon_for_episode(10000) == config.EPSILON_END, 'floors at end')


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    passed = 0
    for t in tests:
        t()
        print('ok   %s' % t.__name__)
        passed += 1
    print('\n%d/%d tests passed' % (passed, len(tests)))


if __name__ == '__main__':
    main()
