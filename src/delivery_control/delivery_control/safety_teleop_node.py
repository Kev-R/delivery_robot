#!/usr/bin/env python3
"""
safety_teleop_node.py
---------------------
THE ONLY NODE THAT PUBLISHES TO /cmd_vel.

It listens to two sources:
  1. Keyboard input (the user's hands)        -> teleop commands
  2. /cmd_vel_nav (Nav2's controller_server)   -> autonomy commands

It publishes one of three things to /cmd_vel:
  - The teleop command, if the user is pressing keys
  - The autonomy command, if autonomy is ENABLED and no keys are pressed
  - Zero (stop), in all other cases (incl. e-stop, autonomy disabled, watchdog)

Keys:
  i, ,        forward / backward
  j, l        rotate left / right (or strafe — see x mode)
  u, o, m, .  diagonal motions (mecanum strafe)
  k           E-STOP (zeros velocity, disables autonomy)
  space       toggle autonomy on/off
  q, z        speed up / slow down
  x           toggle: rotate vs strafe for j/l
  Ctrl-C      quit cleanly

Publishes at 30 Hz regardless of input rate (so motors never see staleness).
"""
import sys
import select
import termios
import tty
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


KEY_BINDINGS_X_MODE = {
    'i': (1, 0, 0, 0),
    ',': (-1, 0, 0, 0),
    'j': (0, 0, 0, 1),    # rotate left
    'l': (0, 0, 0, -1),   # rotate right
    'u': (1, 0, 0, 1),
    'o': (1, 0, 0, -1),
    'm': (-1, 0, 0, -1),
    '.': (-1, 0, 0, 1),
}
KEY_BINDINGS_Y_MODE = {
    'i': (1, 0, 0, 0),
    ',': (-1, 0, 0, 0),
    'j': (0, 1, 0, 0),    # strafe left
    'l': (0, -1, 0, 0),   # strafe right
    'u': (1, 1, 0, 0),
    'o': (1, -1, 0, 0),
    'm': (-1, -1, 0, 0),
    '.': (-1, 1, 0, 0),
}


class SafetyTeleop(Node):

    def __init__(self):
        super().__init__('safety_teleop')

        # Topics
        self.declare_parameter('autonomy_cmd_topic', '/cmd_vel_nav')
        self.declare_parameter('final_cmd_topic', '/cmd_vel')
        self.declare_parameter('linear_speed', 0.20)
        self.declare_parameter('angular_speed', 1.00)
        self.declare_parameter('autonomy_timeout_sec', 0.5)
        self.declare_parameter('start_in_autonomy', False)

        p = lambda n: self.get_parameter(n).value
        self.linear_speed = float(p('linear_speed'))
        self.angular_speed = float(p('angular_speed'))
        self.autonomy_timeout = float(p('autonomy_timeout_sec'))
        self.autonomy_enabled = bool(p('start_in_autonomy'))

        # Pub / Sub
        self.pub_cmd = self.create_publisher(Twist, p('final_cmd_topic'), 1)
        self.sub_auto = self.create_subscription(
            Twist, p('autonomy_cmd_topic'), self._on_autonomy_cmd, 1
        )

        # State
        self.latest_autonomy_cmd = Twist()
        self.last_autonomy_time = self.get_clock().now()
        self.x_mode = True   # j/l = rotate (true) vs strafe (false)
        self.teleop_cmd = Twist()
        self.last_key_time = 0.0
        self.key_timeout = 0.25  # if no key in 250 ms, drop teleop

        # Set TTY raw mode ONCE (not per poll)
        self.old_term_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        # 30 Hz publish loop
        self.timer = self.create_timer(1.0 / 30.0, self._tick)

        self._print_banner()
        self._print_status()

    # -- Subscribers -----------------------------------------------------

    def _on_autonomy_cmd(self, msg: Twist):
        self.latest_autonomy_cmd = msg
        self.last_autonomy_time = self.get_clock().now()

    # -- Main tick -------------------------------------------------------

    def _tick(self):
        # 1. Poll keyboard (non-blocking)
        key = self._poll_key()
        if key is not None:
            self._handle_key(key)

        # 2. Decide what to publish
        cmd = self._compute_output()

        # 3. Publish (always, even if zero)
        self.pub_cmd.publish(cmd)

    def _compute_output(self) -> Twist:
        now = time.time()

        # Teleop has priority over autonomy
        if (now - self.last_key_time) < self.key_timeout:
            return self.teleop_cmd

        # Autonomy if enabled AND fresh
        if self.autonomy_enabled:
            elapsed = (self.get_clock().now() - self.last_autonomy_time).nanoseconds / 1e9
            if elapsed < self.autonomy_timeout:
                return self.latest_autonomy_cmd

        # Otherwise: stop
        return Twist()

    # -- Keyboard --------------------------------------------------------

    def _poll_key(self):
        rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
        if rlist:
            return sys.stdin.read(1)
        return None

    def _handle_key(self, key):
        now = time.time()

        # E-stop
        if key == 'k':
            self.autonomy_enabled = False
            self.teleop_cmd = Twist()
            self.last_key_time = now
            self.get_logger().warn("E-STOP — autonomy disabled, velocity zeroed")
            self._print_status()
            return

        # Toggle autonomy
        if key == ' ':
            self.autonomy_enabled = not self.autonomy_enabled
            self.last_autonomy_time = self.get_clock().now()  # reset watchdog
            self._print_status()
            return

        # Toggle rotate / strafe
        if key == 'x':
            self.x_mode = not self.x_mode
            self._print_status()
            return

        # Speed adjust
        if key == 'q':
            self.linear_speed *= 1.1
            self.angular_speed *= 1.1
            self._print_status()
            return
        if key == 'z':
            self.linear_speed *= 0.9
            self.angular_speed *= 0.9
            self._print_status()
            return

        # Movement
        bindings = KEY_BINDINGS_X_MODE if self.x_mode else KEY_BINDINGS_Y_MODE
        if key in bindings:
            x, y, _, th = bindings[key]
            t = Twist()
            t.linear.x = x * self.linear_speed
            t.linear.y = y * self.linear_speed
            t.angular.z = th * self.angular_speed
            self.teleop_cmd = t
            self.last_key_time = now
            return

        # Ctrl-C
        if key == '\x03':
            raise KeyboardInterrupt

    # -- UI --------------------------------------------------------------

    def _print_banner(self):
        print("\n" + "=" * 60)
        print(" SAFETY TELEOP — DELIVERY ROBOT GATE")
        print("=" * 60)
        print(" i/,       fwd / back")
        print(" j/l       rotate L/R  (or strafe in y-mode)")
        print(" u/o/m/.   diagonals")
        print(" SPACE     toggle autonomy")
        print(" k         E-STOP")
        print(" q/z       speed up/down")
        print(" x         toggle rotate <-> strafe for j/l")
        print(" Ctrl-C    quit")
        print("=" * 60)

    def _print_status(self):
        mode = "ROTATE" if self.x_mode else "STRAFE"
        auto = "ON" if self.autonomy_enabled else "OFF"
        print(
            f"[autonomy={auto}]  speed={self.linear_speed:.2f} m/s  "
            f"turn={self.angular_speed:.2f} rad/s  j/l={mode}",
            flush=True,
        )

    # -- Cleanup ---------------------------------------------------------

    def shutdown(self):
        # Always publish zero before dying
        try:
            self.pub_cmd.publish(Twist())
        except Exception:
            pass
        # Restore TTY
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_term_settings)


def main():
    rclpy.init()
    node = SafetyTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
