import sys
import os
import platform
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from util import Camera, Streamer, PLCData, HorizontalCamera
from time import sleep

plc_ip = "192.168.11.1"
plc_tags = [
    {"src": "heater", "key": "13", "tag_name": "FROM_MACHINE_4C_PLC[43]"},
    {"src": "heater", "key": "12", "tag_name": "FROM_MACHINE_4C_PLC[42]"},
    {"src": "heater", "key": "11", "tag_name": "FROM_MACHINE_4C_PLC[41]"},
    {"src": "heater", "key": "10", "tag_name": "FROM_MACHINE_4C_PLC[39]"},
    {"src": "heater",  "key": "9", "tag_name": "FROM_MACHINE_4C_PLC[38]"},
    {"src": "heater",  "key": "8", "tag_name": "FROM_MACHINE_4C_PLC[37]"},
    {"src": "heater",  "key": "7", "tag_name": "FROM_MACHINE_4C_PLC[36]"},
    {"src": "heater", "key": "26", "tag_name": "FROM_MACHINE_4C_PLC[56]"},
    {"src": "heater", "key": "25", "tag_name": "FROM_MACHINE_4C_PLC[55]"},
    {"src": "heater", "key": "24", "tag_name": "FROM_MACHINE_4C_PLC[54]"},
    {"src": "heater", "key": "23", "tag_name": "FROM_MACHINE_4C_PLC[53]"},
    {"src": "heater", "key": "22", "tag_name": "FROM_MACHINE_4C_PLC[52]"},
    {"src": "heater", "key": "21", "tag_name": "FROM_MACHINE_4C_PLC[51]"},
    {"src": "heater", "key": "20", "tag_name": "FROM_MACHINE_4C_PLC[50]"},
    {"src": "heater", "key": "14", "tag_name": "FROM_MACHINE_4C_PLC[57]"},
    {"src": "heater", "key": "15", "tag_name": "FROM_MACHINE_4C_PLC[57]"},
    {"src": "heater", "key": "16", "tag_name": "FROM_MACHINE_4C_PLC[57]"},
    {"src": "main-motor", "key": "motor", "tag_name": "FROM_MACHINE_4C_PLC[40].5"},
]

def release_video_source(cam):
    print(cam.name, 'released')
    streamer.remove_cam(cam.name)
    cam.start()

def camera_ready(cam):
    print(cam.source)
    print(cam.name, 'acquired')
    if platform.system() == "Windows":
        cam.display()
    cam.update_reference_temperature()
    streamer.add_cam(cam)
    
plc = PLCData(plc_ip, plc_tags)
# cameras = [Camera('thermal-cam', 0, plc)]
# cameras = [
#     Camera('raw-video',        'https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4'),
#     Camera('heater-off',       raw_videos['heater-off']),
#     Camera('leakage',          raw_videos['leakage']),
#     Camera('left-most-leak',   raw_videos['left-most-leak']),
#     Camera('spill-open',       raw_videos['spill-open']),
#     Camera('near-spill',       raw_videos['near-spill']),
# ]
if platform.system() == "Windows":
    cameras = [Camera('thermal-cam', 'C:\\Users\\Tahir\\OneDrive\\Desktop\\camera\\high-temperature.mp4', None)]
    # cameras = [Camera('thermal-cam-horizontal', 'http://192.168.140.89:5000/video_feed/thermal-cam/no-format', None)]
else:  # For Raspberry Pi (Linux)
    # cameras = [Camera('thermal-cam', 0, plc)]
    cameras = [HorizontalCamera('thermal-cam-horizontal', 0, plc)]
# cameras = [Camera(key, raw_videos[key]) for key in raw_videos]

streamer = Streamer()
for cam in cameras:
    cam.start()
    cam.on_acquire(camera_ready)
    cam.on_release(release_video_source)

def monitor_cameras():
    while True:
        try:
            for cam in cameras:
                cam.update_reference_temperature()
            sleep(2)
        except Exception as e:
            print(f"Camera monitoring error: {e}")
try:
    monitor_thread = threading.Thread(target=monitor_cameras, daemon=True)
    monitor_thread.start()
    
    streamer.start()
        
except Exception as e:
    print(e)
    print('closing routines')
    for cam in cameras:
        print("stopping", cam.name)
        cam.stop_display()
        cam.stop()
        cam.release()