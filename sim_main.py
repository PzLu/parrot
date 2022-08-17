from utils.simulation import DroneController, send4control, force_landing


def collect_data():
    my_drone = DroneController(drone_ip="10.202.0.1", photo_dir="images/auto", num=4, interval=5.0)
    my_drone.connect()
    my_drone.take_off()
    my_drone.up_and_down()
    my_drone.landing()
    my_drone.disconnect()


def control_test():
    """Input 4 values to control drone
    forward, right, height, angle
    loop :)
    """
    send4control()


def force_end():
    force_landing()


if __name__ == "__main__":
    collect_data()
    # control_test()
    # force_end()
