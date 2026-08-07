# pathfollower

Tabular Q-learning path follower for a LEGO EV3 robot. See `../CLAUDE.md` for
the full design rationale and hard constraints.

## Files

| File | Runs on | Purpose |
|---|---|---|
| `config.py` | both | ports, calibration thresholds, hyperparameters — **edit these** |
| `mdp.py` | both | `get_state()`, `reward()` — pure logic, no hardware |
| `qlearning.py` | both | Q-table, epsilon-greedy, update rule, JSON save/load |
| `robot.py` | **brick** | sensors, motors, action primitives, calibration (imports `ev3dev2`) |
| `train.py` | **brick** | training loop: episodes, direction button, resets, logging |
| `run.py` | **brick** | frozen greedy policy + scripted obstacle avoidance + path finding |
| `test_logic.py` | laptop | off-brick unit tests for `mdp` + `qlearning` |
| `qtable.json` | generated | the learned table (saved after every episode) |

`mdp.py` and `qlearning.py` have **no hardware imports** so they can be tested
on the laptop: `python3 test_logic.py`.

## The MDP (8 states x 4 actions)

- State = `(brightness, dir)`; brightness ∈ {WHITE, EDGE, BLACK, LOST},
  dir ∈ {CW, ACW} (set by button at episode start).
- Actions = FORWARD, LEFT, RIGHT, REVERSE.
- Reward is shaped so each behaviour has a home: EDGE→FORWARD, off-edge→turns,
  LOST→REVERSE. **The policy is never hardcoded** — only the reward is shaped.

## Deploy & run (from the laptop)

Connection is set up (Phase 0 done): passphraseless deploy key `~/.ssh/ev3` +
an `ev3` SSH alias (see `~/.ssh/config`). `rsync` isn't installed on the laptop,
so we deploy with `scp`.

```sh
# 1. sync to the brick (scp -- rsync not available here)
ssh ev3 'mkdir -p ~/pathfollower'
scp ./pathfollower/*.py ev3:~/pathfollower/

# 2. (first time / new lighting) calibrate colour thresholds
ssh ev3 'cd ~/pathfollower && python3 -c "from robot import Robot; Robot().calibrate()"'
#    -> paste BLACK_MAX / WHITE_MIN into config.py, re-scp

# 3. train  (LEFT button = CW, RIGHT button = ACW; ENTER advances episodes)
ssh ev3 'cd ~/pathfollower && python3 train.py'

# 4. demo the frozen policy
ssh ev3 'cd ~/pathfollower && python3 run.py'
```

## Before a real run — confirm (CLAUDE.md §12)

- [x] Drive — 2 motors, **mismatched**: `outC` large=**left**, `outA` medium=**right**
      (outB empty). Both +speed = straight forward. Driven as two independent
      `Motor` objects (MoveTank can't mix types).
- [x] Colour sensor = **`in2`**; IR sensor = **`in4`**.
- [x] Calibrated colour: tape≈54, background≈16, midpoint≈35 →
      `BLACK_MAX=25`, `WHITE_MIN=45` (EDGE band 26–44, widened for a sharp edge).
- [~] IR obstacle threshold = 30 (untuned starting value; confirm in obstacle phase).
- [x] SSH host/user — `ev3dev.local` / `robot`, key `~/.ssh/ev3`, alias `ev3`.
- [x] Python version on the brick — **3.5.3** (no f-strings; `ev3dev2` imports OK).
- [x] Kernel — `4.14.117-ev3dev-2.3.5-ev3` (above the 2.2.0 minimum).
