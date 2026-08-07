# CLAUDE.md — EV3 Q-Learning Path Follower

Context and working rules for this project. Read this fully before writing or editing code.

---

## 1. Project goal

Train a LEGO Mindstorms EV3 robot to follow a taped path using **reinforcement
learning (tabular Q-learning)**. The robot must *learn* — not be told — when to go
**forward, reverse, turn left, and turn right**, and follow a closed loop in **both
clockwise and anticlockwise** directions. Obstacle avoidance and re-finding the path
after a detour may be scripted.

The track is white tape on black paper forming a closed loop with some stub/dead-end
segments.

---

## 2. HARD CONSTRAINTS — read before anything else

1. **NEVER hardcode the decision policy.** Do not write `if sees_black: turn_left()`
   or any rule that maps a sensed state directly to one of the four behaviours. The
   mapping from **state → action** must be *learned* by Q-learning. Writing that
   mapping by hand fails the assignment outright.

2. **Defining the four action *primitives* is fine and required.** "No hardcoding"
   applies to the *policy* (which action in which state), NOT to what each action
   does mechanically. It is correct and necessary to define, e.g., `FORWARD =
   both motors +speed`. It is forbidden to decide *when* to use it — that is learned.

3. **Reverse must emerge from the reward, not from a script.** Reverse is the
   heaviest-weighted behaviour (20 marks). It must be learned as the recovery action
   in the `LOST` state via reward shaping — do not add an `if stuck: reverse()` rule.

4. **Keep the state space tiny.** More states = slower real-world convergence. Do not
   add states for "smoothness" or extra granularity without a strong reason.

5. **The Q-learning code runs ON the EV3 brick**, in Python via `ev3dev2`. Claude Code
   runs on the laptop and deploys over SSH. `ev3dev2` cannot be imported off-brick.

---

## 3. Hardware

- **Brick:** LEGO EV3 running ev3dev (kernel `ev3dev-2.3.5`, Brickman `0.10.3`,
  Debian **Stretch** base).
- **Sensors:** exactly **one Colour Sensor** and **one IR Sensor**. No second colour
  sensor, no ultrasonic, no touch sensor.
  - Colour sensor → line following (reflected-light mode, 0–100).
  - IR sensor → obstacle detection (proximity mode, 0–100, low = close).
- **Drive:** ASSUMED standard two-motor differential (tank) drive — one Large Motor
  per wheel. **CONFIRM THIS** (see §11).
- **Ports:** TODO — fill in actual motor/sensor ports in `config.py`.

Physical mounting: colour sensor points **down** just above the track, positioned over
one **edge** of the tape. IR sensor points **forward**.

---

## 4. Connection & deployment workflow

Default ev3dev credentials (verify): host `ev3dev.local`, user `robot`, password `maker`.

Claude Code's normal loop for this repo:
1. Edit code locally.
2. Sync to the brick:
   `rsync -avz ./pathfollower/ robot@ev3dev.local:~/pathfollower/`
   (or `scp` individual files).
3. Run on the brick, interactively so output/Ctrl-C work:
   `ssh robot@ev3dev.local 'cd ~/pathfollower && python3 train.py'`

Do **not** try to run the robot code locally — it will fail to import `ev3dev2`.
Pure-logic parts (Q-update, `get_state`, `reward`) should be written so they *can* be
unit-tested locally with mocked sensor values — keep hardware I/O out of those functions.

---

## 5. RL design — the MDP

### State = `(brightness, dir)`
- `brightness` ∈ { `WHITE`, `EDGE`, `BLACK`, `LOST` }
  - Derived from the colour sensor's reflected-light value using calibrated thresholds.
  - `WHITE` = drifted onto tape; `BLACK` = drifted onto background; `EDGE` = on the
    boundary (good); `LOST` = stuck at an extreme for ≥ `k` consecutive steps.
- `dir` ∈ { `CW`, `ACW` }
  - Set by a **button press at the start of each episode/run**, not sensed.

**Why the direction bit exists:** one colour sensor reads only brightness, which cannot
reveal which side the line is on. Clockwise corners are right turns; anticlockwise
corners are left turns — so the correct recovery for `BLACK` is opposite in the two
directions. A brightness-only table cannot store both. The direction bit gives each
direction its own rows so the robot can *learn* the right turn per direction. This is
NOT hardcoding — we only tell it which way it faces; it still learns which turn recovers
the line. 4 brightness × 2 dir = **8 states**.

### Actions (primitives — defining these is allowed)
`FORWARD`, `LEFT`, `RIGHT`, `REVERSE` → 4 actions. Table size = 8 × 4 = **32 values**.

### Reward (shaped, dense — feedback every step)
- `EDGE` → high positive (highest reward).
- `WHITE` / `BLACK` → small positive or zero.
- `LOST` → negative.
- Small extra bonus for `FORWARD` while on the line (rewards progress, discourages
  wiggling in place).
- Effect: from `LOST`, only reversing escapes the negative reward → the robot learns
  `LOST → REVERSE`. Every behaviour gets a home: `EDGE→FORWARD`, off-edge→turns,
  `LOST→REVERSE`.

---

## 6. Hyperparameters (starting points)

| Param | Value | Note |
|---|---|---|
| `alpha` (learning rate) | 0.3 | moderate; sensors are noisy |
| `gamma` (discount) | 0.9 | slight lookahead helps smoothness |
| `epsilon` start | 0.9 | mostly explore early |
| `epsilon` end | 0.05 | mostly exploit once learned |
| `epsilon` decay | ×0.995 / episode | tune |
| `dt` (action burst) | 0.08–0.12 s | how long each action runs before re-deciding |
| `k` (LOST threshold) | 8–10 steps | steps at an extreme before `LOST` |
| train speed | ~20–30% | slow = better discrete-time approximation |
| demo speed | ~40–50% | speed up once policy is frozen |

Persist the Q-table to `qtable.json` **after every episode** so progress survives
crashes/battery death and can be resumed.

---

## 7. Non-RL components (scripted — explicitly allowed)

- **Obstacle avoidance (IR):** poll `ir.proximity`; on a *confirmed* close reading
  (require 2–3 consecutive reads to reject noise), pause the policy → scripted maneuver
  (stop → turn ~90° → drive forward to clear → turn back).
- **Find the path:** after the maneuver, drive/sweep until the colour sensor reads the
  edge again, then hand control back to the Q-policy.

These are plain conditional logic — no learning.

---

## 8. ev3dev2 API quick reference

```python
from ev3dev2.motor import MoveTank, OUTPUT_B, OUTPUT_C, SpeedPercent
from ev3dev2.sensor.lego import ColorSensor, InfraredSensor
from ev3dev2.button import Button
from ev3dev2.sound import Sound
import time

tank = MoveTank(OUTPUT_B, OUTPUT_C)      # confirm ports
cs = ColorSensor()
cs.mode = 'COL-REFLECT'                   # reflected light intensity
brightness = cs.reflected_light_intensity # 0-100

ir = InfraredSensor()
ir.mode = 'IR-PROX'
dist = ir.proximity                       # 0-100, low = close

btn = Button()                            # btn.enter, btn.left, etc. -> bool
snd = Sound()

# Control-loop pattern: set motors (non-blocking), wait dt, then re-decide.
tank.on(SpeedPercent(left_pct), SpeedPercent(right_pct))
time.sleep(dt)
```

Action → motor primitives (tank drive; tune the turn differential):
- `FORWARD`: `on(+s, +s)`
- `REVERSE`: `on(-s, -s)`
- `LEFT`:  `on(-t, +t)`  (pivot/curve left)
- `RIGHT`: `on(+t, -t)`  (pivot/curve right)

---

## 9. Environment gotchas

- **Python 3.5 on ev3dev-stretch** → **no f-strings**. Use `.format()` or `%`.
- **Brick is slow (~300 MHz ARM, 64 MB RAM)** → do NOT use numpy/pandas. Plain `dict`
  + `list` for the Q-table; `json` for saving.
- **Q-table JSON keys:** tuple state keys aren't JSON-native. Encode as a string, e.g.
  `"EDGE|CW"`, when saving; decode on load.
- **IR sensor is coarse/noisy** → threshold + require consecutive confirming reads.
- **Colour readings drift** with ambient light and sensor height → recalibrate at the
  start of a session if lighting changed; store thresholds in `config.py`.
- **Battery level affects motor speed** → keep charged; low battery changes behaviour
  and hurts the smoothness marks.
- **Real-world RL needs manual resets** → keep episodes short; use a button press to
  advance to the next episode after you replace the robot on the line.

---

## 10. Project structure

```
pathfollower/
  config.py       # ports, calibration thresholds, hyperparameters (edit these)
  robot.py        # hardware wrapper: sensors, motors, action primitives, calibration
  mdp.py          # get_state(), reward() — pure logic, unit-testable off-brick
  qlearning.py    # Q-table, choose_action(eps), learn(s,a,r,s2), save/load JSON
  train.py        # training loop: episodes, direction-bit button, resets, logging
  run.py          # frozen greedy policy + IR obstacle avoidance + path-finding
  qtable.json     # generated: the learned table
```

Keep `mdp.py` and `qlearning.py` free of hardware imports so their logic can be tested
locally with mocked inputs.

---

## 11. Marking priorities (optimize for these)

- Learning reverse — **20**
- Following path clockwise + anticlockwise — **20**
- Learning forward — 10
- Learning left turn — 10
- Learning right turn — 10
- Smoothness of turns — 10
- Obstacle avoidance — 10
- Smoothness of line following — 5
- Finding the path — 5

For the "learning X" items, print the trained Q-table in the report/demo as evidence:
e.g. in `(EDGE, CW)` FORWARD has the highest Q-value; in `(LOST, *)` REVERSE wins.

---

## 12. Open items to confirm (fill in before building)

- [ ] Drive configuration — is it two-motor tank drive? Which ports (e.g. B, C)?
- [ ] Colour sensor port; IR sensor port.
- [ ] Calibrated colour values: black ≈ ?, white ≈ ?, EDGE band = ?
- [ ] IR obstacle threshold (from calibration).
- [ ] Confirmed SSH host/user/password.
- [ ] Python version on the brick (`python3 --version`) — confirm 3.5 vs newer.