import logging
import math
import os
import subprocess
import traceback

import olympe
from olympe.messages.ardrone3.Piloting import TakeOff, moveBy, Landing
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged

olympe.log.update_config({"loggers": {"olympe": {"level": "WARNING"}}})
logger = logging.getLogger(__name__)
DRONE_IP = os.environ.get("DRONE_IP", "10.202.0.1")


def degree_to_rad(value):
    """convert angles to radians"""

    return math.pi / 180 * value


class DroneController(object):
    def __init__(self, drone_ip="10.202.0.1", photo_dir="meta/", num=2, interval=2.0):
        self._drone = olympe.Drone(drone_ip)
        self._photo_dir = photo_dir
        self._num = num  # Number of moves
        self._interval = interval  # Flight interval

    def connect(self) -> None:
        self._drone.connect()

    def disconnect(self) -> None:
        self._drone.disconnect()

    def take_off(self) -> None:
        self._drone(
            TakeOff()
            >> FlyingStateChanged(state="hovering")
        ).wait().success()

    def landing(self) -> None:
        self._drone(Landing()).wait().success()

    def take_photes(self, id_floor=0, id_point=0, id_num=0) -> None:
        dirname = os.path.join(self._photo_dir, str(id_floor), str(id_point), str(id_num))
        cmd = f"sphinx-cli camera front_streaming -n --count=1 -o '{dirname}'"
        subprocess.run(cmd, shell=True)

    def rotate_one_circle(self, id_floor=0, id_point=0) -> None:
        """Rotate in place four times and take photos."""

        for i in range(1, 5):
            self._drone(moveBy(0, 0, 0, degree_to_rad(90))).wait()
            self.take_photes(id_floor, id_point, id_num=i)

    def collect_one_floor(self, floor=1) -> None:
        """Move to num*num points in the same plane."""

        for line in range(1, self._num+1):
            for right_aspect in range(1, self._num+1):
                if right_aspect == self._num:
                    self.rotate_one_circle(id_floor=floor, id_point=(line-1)*self._num+right_aspect)
                else:
                    self.rotate_one_circle(id_floor=floor, id_point=(line-1)*self._num+right_aspect)
                    self._drone(moveBy(0, self._interval, 0, 0)).wait()
            if line < self._num:
                self._drone(moveBy(self._interval, -self._interval*(self._num-1), 0, 0)).wait()

    def up_and_down(self) -> None:
        """Total num layers."""

        for id_f in range(1, self._num+1):
            if id_f < self._num:
                self.collect_one_floor(floor=id_f)
                self._drone(
                    moveBy(-self._interval*(self._num-1), -self._interval*(self._num-1), -self._interval, 0)
                ).wait()
            else:
                self.collect_one_floor(floor=id_f)
                self._drone(
                    moveBy(
                        -self._interval*(self._num-1), -self._interval*(self._num-1),
                        self._interval*(self._num-1), 0
                    )
                ).wait()


def send4control() -> None:
    with olympe.Drone(DRONE_IP) as drone:
        try:
            drone = olympe.Drone(DRONE_IP)
            drone.connect()
            assert drone(
                TakeOff()
                >> FlyingStateChanged(state="hovering")
            ).wait().success()
            while True:
                forward, right, height, angle = map(float, input().split())
                # assert drone(
                #     moveBy(forward, right, height, angle)
                #     >> FlyingStateChanged(state="hovering", _timeout=17124)
                # ).wait().success()
                drone(moveBy(forward, right, height, angle)).wait()
            assert drone(Landing()).wait().success()
            drone.disconnect()
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            drone.disconnect()


def force_landing():
    drone = olympe.Drone(DRONE_IP)
    drone.connect()
    assert drone(Landing()).wait().success()
    drone.disconnect()
