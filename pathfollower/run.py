# run.py -- frozen greedy policy for the demo. RUNS ON THE BRICK.
#
# Loads the learned Q-table, always exploits (epsilon = 0), and layers the
# SCRIPTED non-RL components on top: IR obstacle avoidance and path re-finding.
# Python 3.5: no f-strings.

import time

import config
from robot import Robot
from qlearning import QTable
from mdp import get_state, update_off_edge_streak, classify_brightness, EDGE


def avoid_obstacle(robot, direction):
    """Scripted obstacle maneuver (see CLAUDE.md section 7). Not learned.
    Stop -> turn ~90 deg away -> drive forward to clear -> turn back."""
    robot.stop()
    robot.snd.beep()
    # Turn away, go around, come back. Durations are rough and tunable.
    robot.act('RIGHT'); time.sleep(0.9)     # ~90 deg
    robot.act('FORWARD'); time.sleep(1.2)   # clear the obstacle
    robot.act('LEFT'); time.sleep(0.9)      # face back toward the line
    robot.act('FORWARD'); time.sleep(1.0)
    robot.stop()


def find_path(robot, direction):
    """Scripted sweep until the colour sensor sees the EDGE again, then hand
    control back to the policy. Not learned."""
    robot.snd.beep()
    for _ in range(60):
        if classify_brightness(robot.brightness()) == EDGE:
            robot.stop()
            return True
        robot.act('RIGHT')       # slow sweep to re-acquire the edge
        time.sleep(0.1)
    robot.stop()
    return False


def main():
    robot = Robot(speed=config.DEMO_SPEED)
    qt = QTable()
    qt.load()   # will raise if no qtable.json -- train first
    print('Loaded policy:')
    print(qt.pretty())

    print('Pick demo direction (LEFT=CW, RIGHT=ACW).')
    direction = robot.read_direction()
    print('Running greedy policy in %s. Ctrl-C to stop.' % direction)

    off_edge_streak = 0
    try:
        while True:
            # scripted obstacle check first
            if robot.obstacle_ahead():
                avoid_obstacle(robot, direction)
                find_path(robot, direction)
                off_edge_streak = 0
                continue

            value = robot.brightness()
            off_edge_streak = update_off_edge_streak(value, off_edge_streak)
            state = get_state(value, direction, off_edge_streak)

            action = qt.best_action(state)   # frozen greedy: no exploration
            robot.act(action)
            time.sleep(config.DT)
    except KeyboardInterrupt:
        robot.stop()
        print('Stopped.')


if __name__ == '__main__':
    main()
