import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from util import Camera, Streamer
from assets import raw_videos
from time import sleep


def release_video_source(cam):
    print(cam.name, 'released')
    streamer.remove_cam(cam.name)
    cam.start()

def camera_ready(cam):
    print(cam.source)
    print(cam.name, 'acquired')
    cam.display()
    streamer.add_cam(cam)

# cameras = [Camera('raw-video', raw_videos['bottom-sealing'])]
# cameras = [
#     Camera('raw-video',        raw_videos['with-liquid']),
#     Camera('heater-off',       raw_videos['heater-off']),
#     Camera('leakage',          raw_videos['leakage']),
#     Camera('left-most-leak',   raw_videos['left-most-leak']),
#     Camera('spill-open',       raw_videos['spill-open']),
#     Camera('near-spill',       raw_videos['near-spill']),
# ]
cameras = [Camera('thermal-cam', 1)]
# cameras = [Camera(key, raw_videos[key]) for key in raw_videos]

streamer = Streamer()

for cam in cameras:
    cam.start()
    cam.on_acquire(camera_ready)
    cam.on_release(release_video_source)

try:
    streamer.start()
    while True:
        print("main loop")
        sleep(1)
except Exception as e:
    print(e)
    print('closing routines')
    for cam in cameras:
        print("stopping", cam.name)
        cam.stop_display()
        cam.stop()
        cam.release()