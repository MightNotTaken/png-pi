import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from util import Camera, Streamer, PLCData
from time import sleep

plc_ip = "192.168.11.1"
plc_tags = [
    {"heater": "13", "key": "13", "tag_name": "FROM_MACHINE_4C_PLC[43]"},
    {"heater": "12", "key": "12", "tag_name": "FROM_MACHINE_4C_PLC[42]"},
    {"heater": "11", "key": "11", "tag_name": "FROM_MACHINE_4C_PLC[41]"},
    {"heater": "10", "key": "10", "tag_name": "FROM_MACHINE_4C_PLC[39]"},
    {"heater": "9",  "key": "9", "tag_name": "FROM_MACHINE_4C_PLC[38]"},
    {"heater": "8",  "key": "8", "tag_name": "FROM_MACHINE_4C_PLC[37]"},
    {"heater": "7",  "key": "7", "tag_name": "FROM_MACHINE_4C_PLC[36]"},
    {"heater": "", "key": "26", "tag_name": "FROM_MACHINE_4C_PLC[56]"},
    {"heater": "", "key": "25", "tag_name": "FROM_MACHINE_4C_PLC[55]"},
    {"heater": "", "key": "24", "tag_name": "FROM_MACHINE_4C_PLC[54]"},
    {"heater": "", "key": "23", "tag_name": "FROM_MACHINE_4C_PLC[53]"},
    {"heater": "", "key": "22", "tag_name": "FROM_MACHINE_4C_PLC[52]"},
    {"heater": "", "key": "21", "tag_name": "FROM_MACHINE_4C_PLC[51]"},
    {"heater": "", "key": "20", "tag_name": "FROM_MACHINE_4C_PLC[50]"},
]

def release_video_source(cam):
    print(cam.name, 'released')
    streamer.remove_cam(cam.name)
    cam.start()

def camera_ready(cam):
    print(cam.source)
    print(cam.name, 'acquired')
    # cam.display()
    streamer.add_cam(cam)
    
plc = PLCData(plc_ip, plc_tags)
cameras = [Camera('thermal-cam', 0, plc)]
# cameras = [
#     Camera('raw-video',        'https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4'),
#     Camera('heater-off',       raw_videos['heater-off']),
#     Camera('leakage',          raw_videos['leakage']),
#     Camera('left-most-leak',   raw_videos['left-most-leak']),
#     Camera('spill-open',       raw_videos['spill-open']),
#     Camera('near-spill',       raw_videos['near-spill']),
# ]
# cameras = [Camera('thermal-cam', 'http://192.168.93.89:5000/video_feed/thermal-cam/no-format')]
# cameras = [Camera(key, raw_videos[key]) for key in raw_videos]

streamer = Streamer()
for cam in cameras:
    cam.start()
    cam.on_acquire(camera_ready)
    cam.on_release(release_video_source)

try:
    streamer.start()
    while True:
        sleep(1)
except Exception as e:
    print(e)
    print('closing routines')
    for cam in cameras:
        print("stopping", cam.name)
        cam.stop_display()
        cam.stop()
        cam.release()