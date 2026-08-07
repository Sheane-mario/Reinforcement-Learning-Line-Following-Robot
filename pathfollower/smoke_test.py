# smoke_test.py -- hardware bring-up check. RUNS ON THE BRICK.
#
# Read-only sensor/port detection runs automatically. Motor pulses are gated
# behind the brick's ENTER button so the robot cannot drive off unexpectedly.
# Python 3.5: no f-strings.
#
# Purpose: confirm the CLAUDE.md section 12 open items --
#   - which ports the motors and sensors are actually on,
#   - colour sensor reads black vs white sensibly,
#   - IR sensor reports proximity,
#   - each motor's port + spin direction under FORWARD.

import time


def scan_devices():
    """List connected motors and sensors with their ports (addresses)."""
    print('=== Connected devices ===')

    from ev3dev2.motor import list_motors
    motors = list(list_motors())
    if not motors:
        print('MOTORS: none found!')
    for m in motors:
        print('MOTOR  port=%-6s driver=%s' % (m.address, m.driver_name))

    # Sensors: read straight from the ev3dev sysfs class via ev3dev2.
    from ev3dev2.sensor import list_sensors
    sensors = list(list_sensors())
    if not sensors:
        print('SENSORS: none found!')
    for s in sensors:
        print('SENSOR port=%-6s driver=%s' % (s.address, s.driver_name))
    print('')
    return motors, sensors


def test_colour():
    print('=== Colour sensor (reflected light 0-100) ===')
    from ev3dev2.sensor.lego import ColorSensor
    cs = ColorSensor()
    cs.mode = 'COL-REFLECT'
    for _ in range(5):
        print('  reflected = %d' % cs.reflected_light_intensity)
        time.sleep(0.3)
    print('  (move it over black vs white -- values should differ a lot)\n')


def test_ir():
    print('=== IR sensor (proximity 0-100, low = close) ===')
    from ev3dev2.sensor.lego import InfraredSensor
    ir = InfraredSensor()
    ir.mode = 'IR-PROX'
    for _ in range(5):
        print('  proximity = %d' % ir.proximity)
        time.sleep(0.3)
    print('  (wave your hand in front -- value should drop when close)\n')


def test_motors():
    print('=== Motor pulse test (GATED by ENTER button) ===')
    from ev3dev2.motor import Motor, OUTPUT_A, OUTPUT_C, SpeedPercent
    from ev3dev2.button import Button
    from ev3dev2.sound import Sound

    btn = Button()
    snd = Sound()

    def wait_enter(msg):
        print(msg)
        snd.beep()
        while not btn.enter:
            time.sleep(0.02)
        while btn.any():
            time.sleep(0.02)

    from ev3dev2.motor import Motor
    # Pulse each motor separately so we learn which physical wheel is which port.
    # outA is a MEDIUM motor, outC a LARGE motor -- use the generic Motor class
    # so either type works.
    for port, name in [(OUTPUT_A, 'OUTPUT_A (medium)'),
                       (OUTPUT_C, 'OUTPUT_C (large)')]:
        wait_enter('Lift wheels off surface. Press ENTER to pulse %s forward.'
                   % name)
        try:
            mot = Motor(port)
            mot.on(SpeedPercent(20))
            time.sleep(0.6)
            mot.off()
            print('  pulsed %s -- note which wheel turned and which way.' % name)
        except Exception as e:
            print('  %s ERROR: %s (is a motor plugged into that port?)'
                  % (name, e))
        time.sleep(0.4)

    # Both together as tank FORWARD -- two independent Motor objects because the
    # medium (outA) + large (outC) pair can't share one MoveTank motor_class.
    wait_enter('Press ENTER to pulse BOTH forward (tank FORWARD).')
    left = Motor(OUTPUT_A)
    right = Motor(OUTPUT_C)
    left.on(SpeedPercent(20))
    right.on(SpeedPercent(20))
    time.sleep(0.8)
    left.off()
    right.off()
    print('  Both should drive the robot FORWARD (straight). If it spins or\n'
          '  reverses, ports B/C are swapped or a motor is mounted mirrored.\n')


def main():
    print('EV3 hardware smoke test\n')
    scan_devices()
    test_colour()
    test_ir()
    test_motors()
    print('Smoke test done.')


if __name__ == '__main__':
    main()
