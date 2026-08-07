# train.py -- the training loop. RUNS ON THE BRICK.
#
# Episodes of epsilon-greedy Q-learning. Direction bit chosen by button at the
# start of each episode. Q-table saved after every episode so progress survives
# crashes / battery death and can be resumed. Python 3.5: no f-strings.

import sys
import time

import config
from robot import Robot
from qlearning import QTable, epsilon_for_episode
from mdp import get_state, update_off_edge_streak, reward

# Defaults; override from the command line: python3 train.py [episodes] [steps]
STEPS_PER_EPISODE = 120
NUM_EPISODES = 40


def run_episode(robot, qt, epsilon, direction, steps):
    off_edge_streak = 0

    value = robot.brightness()
    state = get_state(value, direction, off_edge_streak)

    total_reward = 0.0
    for _ in range(steps):
        # 1. choose an action (epsilon-greedy) -- policy is learned, not coded
        action = qt.choose_action(state, epsilon)

        # 2. execute it for one burst
        robot.act(action)
        time.sleep(config.DT)

        # 3. observe the resulting state
        value = robot.brightness()
        off_edge_streak = update_off_edge_streak(value, off_edge_streak)
        next_state = get_state(value, direction, off_edge_streak)

        # 4. reward + Q-update
        r = reward(next_state, action)
        qt.learn(state, action, r, next_state)
        total_reward += r

        state = next_state

    robot.stop()
    return total_reward


def main():
    # python3 train.py [episodes] [steps_per_episode]
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else NUM_EPISODES
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else STEPS_PER_EPISODE

    robot = Robot(speed=config.TRAIN_SPEED)
    qt = QTable()
    try:
        qt.load()
        print('Resumed Q-table from %s' % config.QTABLE_PATH)
    except (IOError, OSError, ValueError):
        print('Starting with a fresh Q-table')

    print('Training for %d episodes x %d steps (speed=%d%%).'
          % (episodes, steps, config.TRAIN_SPEED))
    try:
        for episode in range(episodes):
            print('--- Episode %d: pick direction (LEFT=CW, RIGHT=ACW) ---'
                  % (episode + 1))
            direction = robot.read_direction()
            epsilon = epsilon_for_episode(episode)
            print('  direction=%s  epsilon=%.3f' % (direction, epsilon))

            total = run_episode(robot, qt, epsilon, direction, steps)
            qt.save()   # persist after every episode
            print('  episode reward=%.1f  (saved %s)'
                  % (total, config.QTABLE_PATH))

            if episode < episodes - 1:
                print('  Reset the robot on the line, then press ENTER for next.')
                robot.wait_enter()
    except KeyboardInterrupt:
        print('\nInterrupted -- stopping motors and saving.')
    finally:
        robot.stop()          # always halt the motors on exit
        qt.save()

    print('Training run done. Q-table so far:')
    print(qt.pretty())
    robot.snd.beep()


if __name__ == '__main__':
    main()
