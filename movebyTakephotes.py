from olympe.messages.camera import (
    set_camera_mode,
    set_photo_mode,
    take_photo,
    photo_progress,
)
from olympe.media import download_media, indexing_state
from olympe.messages.ardrone3.Piloting import TakeOff, moveBy, Landing
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
import olympe
from logging import getLogger
import traceback
import os
import re
import tempfile
import xml.etree.ElementTree as ET

olympe.log.update_config({
    "handlers": {
        "olympe_log_file": {
            "class": "logging.FileHandler",
            "formatter": "default_formatter",
            "filename": "olympe.log"
        }
    },
    "loggers": {
        "olympe": {
            "handlers": ["olympe_log_file"]
        },
        "photo_example": {
            "level": "INFO",
            "handlers": ["console"],
        }
    }
})

logger = getLogger("photo_example")


# Drone IP
DRONE_IP = os.environ.get("DRONE_IP", "192.168.42.1")
DRONE_MEDIA_PORT = os.environ.get("DRONE_MEDIA_PORT", "80")

XMP_TAGS_OF_INTEREST = (
    "CameraRollDegree",
    "CameraPitchDegree",
    "CameraYawDegree",
    "CaptureTsUs",
    # NOTE: GPS metadata is only present if the drone has a GPS fix
    # (i.e. they won't be present indoor)
    "GPSLatitude",
    "GPSLongitude",
    "GPSAltitude",
)

def take_photo_burst(drone, save_path):
    # take a photo burst and get the associated media_id
    photo_saved = drone(photo_progress(result="photo_saved", _policy="wait"))
    drone(take_photo(cam_id=0)).wait()
    if not photo_saved.wait(_timeout=30).success():
        assert False, "take_photo timedout"
    photo_progress_info = photo_saved.received_events().last().args
    media_id = photo_progress_info["media_id"]
    photo_count = photo_progress_info["photo_count"]
    # download the photos associated with this media id
    drone.media.download_dir = tempfile.mkdtemp(prefix="olympe_photo_example")
    logger.info(
        "Download photo burst resources for media_id: {} in {}".format(
            media_id,
            drone.media.download_dir,
        )
    )
    media_download = drone(download_media(media_id, download_dir=save_path, integrity_check=True))
    # Iterate over the downloaded media on the fly
    resources = media_download.as_completed(expected_count=1, timeout=60)
    resource_count = 0
    img_id = None  
    for resource in resources:
        logger.info("Resource: {}".format(resource.resource_id))
        img_id = resource.resource_id
        if not resource.success():
            logger.error("Failed to download {}".format(resource.resource_id))
            continue
        resource_count += 1
        # parse the xmp metadata
        with open(resource.download_path, "rb") as image_file:
            image_data = image_file.read()
            image_xmp_start = image_data.find(b"<x:xmpmeta")
            image_xmp_end = image_data.find(b"</x:xmpmeta")
            if image_xmp_start < 0 or image_xmp_end < 0:
                logger.error("Failed to find XMP photo metadata {}".format(resource.resource_id))
                continue
            image_xmp = ET.fromstring(image_data[image_xmp_start: image_xmp_end + 12])
            for image_meta in image_xmp[0][0]:
                xmp_tag = re.sub(r"{[^}]*}", "", image_meta.tag)
                xmp_value = image_meta.text
                # only print the XMP tags we are interested in
                if xmp_tag in XMP_TAGS_OF_INTEREST:
                    logger.info("{} {} {}".format(resource.resource_id, xmp_tag, xmp_value))
    logger.info("{} media resource downloaded".format(resource_count))
    # assert resource_count == 14, "resource count == {} != 14".format(resource_count)
    assert media_download.wait(1.).success(), "Photo burst media download"
    return os.path.join(save_path, img_id)

def setup_photo_burst_mode(drone):

    drone(set_camera_mode(cam_id=0, value="photo")).wait()
    # For the file_format: jpeg is the only available option
    # dng is not supported in burst mode
    assert drone(
        set_photo_mode(
            cam_id=0,
            mode="single",
            format="rectilinear",
            file_format="jpeg",
            burst="burst_4_over_1s",
            bracketing="preset_1ev",
            capture_interval=0.0,
        )
    ).wait().success()

if __name__ == "__main__":
    with olympe.Drone(DRONE_IP, media_port=DRONE_MEDIA_PORT) as drone:
        try:
            drone = olympe.Drone(DRONE_IP)
            drone.connect()
            assert drone(TakeOff()).wait().success()
            assert drone.media(
                indexing_state(state="indexed")
            ).wait(_timeout=60).success()
            setup_photo_burst_mode(drone)

            while True:
                instruction = input().strip()
                if instruction == "0":
                    break
                if instruction == "1": # forward 1
                    drone(moveBy(0.5, 0, 0, 0)).wait()
                    img_path = take_photo_burst(drone, "pic")
                if instruction == "2": # backward 1
                    drone(moveBy(-1, 0, 0, 0)).wait()
                    img_path = take_photo_burst(drone, "pic")
                    img_path = take_photo_burst(drone, "pic")

            assert drone(Landing()).wait().success()
            drone.disconnect()
        except:
            print(traceback.format_exc())
            # assert drone(Landing()).wait().success()
            drone.disconnect()


