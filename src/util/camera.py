import requests
import os
import cv2
import numpy as np
import threading
from time import sleep, time
from enum import Enum
from .frame import Frame
import json
from datetime import datetime
from .MA import MovingAverage
import platform


class SourceType(Enum):
    VIDEO_FILE     = 1
    ACTUAL_CAMERA  = 2


BASE_PATH = None
if platform.system() == "Windows":
    BASE_PATH = "C:\\tahir\\codes\\Gujral_Sir\\PnG\\pi\\training-data"
else:
    BASE_PATH = "/home/png/pro/png-pi"
    
# BASE_PATH = "."

class Camera:
    def __init__(self, name, source, plc):
        self.iterations = 0
        self.plc = plc
        self.name = name
        self.source = source
        self.cam = None
        self.ratio = 1
        self.latest_frame = None
        self.frame_to_serve = None
        self.running = False
        self.display_running = False
        self.last_save = 0
        self.lock = threading.Lock()
        self.data_read_lock = threading.Lock()
        self.thread = None
        self.saving_thread = None
        self.acquired = False
        self.acquired_callback = None
        self.released_callback = None
        self.completed = False
        self.fourcc = None
        self.writer = None
        self.capture = False
        self.recording = False
        self.next_capture = 0
        self.temperature = 0
        self.directory = None
        self.impression_cycle = {
            "active": False,
            "start": 0,
            "spt": None,
            "running": False,
            "frame": None
        }
        self.sachets = {}
        self.sachets_temperature = {}
        self.path = os.path.join(BASE_PATH, self.name)
        self.temp_ranges = {}
        
        self.calculated_temp = {}

        if not os.path.exists(self.path):
            os.makedirs(self.path)
        
        try:
            int(self.source)
            self.type = SourceType.ACTUAL_CAMERA
        except:
            self.type = SourceType.VIDEO_FILE

        self.frame_format = {
            'color_format': cv2.COLOR_BGR2GRAY,
            'colormap': cv2.COLORMAP_INFERNO
        }
        self.load_frames()
        self.update_sachets()
        print(self.frames)

    def __str__(self):
        width, height = self.get_frame_size()
        is_opened = self.cam.isOpened() if self.cam else False
        frame_rate = self.cam.get(cv2.CAP_PROP_FPS) if self.cam and is_opened else 0
        codec = (
            int(self.cam.get(cv2.CAP_PROP_FOURCC)) if self.cam and is_opened else 0
        )
        codec_str = (
            ''.join([chr((codec >> 8 * i) & 0xFF) for i in range(4)]) if codec else "N/A"
        )
        backend = (
            self.cam.getBackendName() if self.cam and is_opened else "N/A"
        )
        return (
            f"Camera Details:\n"
            f"----------------\n"
            f"Name: {self.name}\n"
            f"Source: {self.source}\n"
            f"Resolution: {width}x{height} pixels\n"
            f"Frame Rate: {frame_rate} FPS\n"
            f"Codec: {codec_str}\n"
            f"Backend: {backend}\n"
            f"Camera Open: {'Yes' if is_opened else 'No'}\n"
            f"Current Frame Format: {self.frame_format if self.frame_format else 'Default'}\n"
        )
    
    def get_specification(self):
        specs = {}
        width, height = self.get_frame_size()
        specs["name"] = self.name
        specs["width"] = width
        specs["height"] = height
        return specs

    def get_frame_size(self):
        if self.cam and self.cam.isOpened():
            return int(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return 0, 0
    
    def on_acquire(self, callback):
        self.acquired_callback = callback

    def on_release(self, callback):
        self.released_callback = callback

    def acquire(self):
        if self.cam is None:
            self.release()
            print('creating camera object')
            self.cam = cv2.VideoCapture(self.source)
            print(self.cam)

        if not self.cam.isOpened():
            if self.acquired:
                self.acquired = False
                if self.released_callback:
                    self.released_callback(self)
            self.completed = self.type == SourceType.VIDEO_FILE
            print(self.completed)
            raise RuntimeError(f"Unable to acquire camera: {self.source}")

        ret, frame = self.cam.read()
        if not ret:
            self.completed = self.type == SourceType.VIDEO_FILE
            self.acquired = False
            raise RuntimeError(f"Failed to capture frame from {self.name}. Camera might not be available.")
        
        if not self.acquired and self.acquired_callback:
            self.acquired = True
            self.acquired_callback(self)
            
        return frame

    def release(self):
        if self.cam:
            self.cam.release()
        if self.recording:
            self.writer.release()
        self.cam = None
        self.acquired = False

    def start(self):
        """Start the camera in a separate thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.thread.start()
            self.saving_thread = threading.Thread(target=self.save_impression, daemon=True)
            self.saving_thread.start() 
            
    def get_frames_with_temperature(self):
        for frame in self.frames:
            try:
                frame['temperature'] = self.sachets_temperature[str(frame['sachet'])]
            except Exception as e:
                print('error in frame temperature', e)
        return self.frames       
    def save_target_frames(self):        
        main_frame = self.get_latest_frame()
        instant = str(round(time() * 1000))
        directory_path = os.path.join(self.path, self.directory)
        print(instant, directory_path)
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
        cv2.imwrite(os.path.join(directory_path, instant + '-frame.png'), main_frame)
        
        params = self.get_frames_with_temperature()
        json_path = os.path.join(directory_path, instant + '-params.json')
        with open(json_path, 'w') as json_file:
            json.dump(params, json_file, indent=4)
    
    def get_frame_file_name(self):
        path = os.path.join(self.path, self.name + '-frames.json')
        # path = path.replace('\\', '/')
        print(path)
        return path
    
    def save_frames(self):
        try:
            with open(self.get_frame_file_name(), "w") as f:
                f.write(json.dumps(self.frames))
        except:
            print('unable to save frames')
            
    def update_sachets(self):
        self.sachets = {}
        self.temp_ranges = {}
        for frame in self.frames:
            self.sachets[frame["sachet"]] = {
                "top": frame["top"],
                "left": frame["left"],
                "right": frame["right"],
                "bottom": frame["bottom"],
                "temperature": 0
            }
            self.temp_ranges[frame["sachet"]] = MovingAverage(20)
            self.sachets["length"] = len(self.frames)
        
    def load_frames(self):
        try:
            with open(self.get_frame_file_name(), "r") as f:
                self.frames = json.load(f)
        except Exception as e:
            self.frames = [] 
            print(e)

    def update_reference_temperature(self):
        tags = None
        if self.plc:
            self.plc.update()
            tags = self.plc.get_tags()
            print(tags)
        else:
            tags = {
                '0': 128,'1': 128,'2': 128,'3': 128,'4': 128,'5': 128,'6': 128,'7': 128,'8': 128,
                '9': 128,'10': 128,'11': 128,'12': 128,'13': 128,'14': 128,'15': 128,'16': 128,'17': 128,"motor": 1
            }
            # response = requests.get('http://raspberrypi.local:5000/get-plc-data/' + self.name)
            # tags = json.loads(response.text)
        self.sachets_temperature = tags
        print(tags["motor"])
        return tags
    
    
    def is_impression_ready(self):
        if round(time() * 1000) - self.impression_cycle["start"] > 700:
            self.impression_cycle["active"] = False
            return True
        return False
    
    def save_impression(self):
        while True:
            if self.capture:
                self.save_target_frames()
                print("saving frame")
            sleep(.7)
            
    
    def reset_impression(self):
        self.impression_cycle["start"] = round(time() * 1000)
        self.impression_cycle["active"] = True
        self.impression_cycle["spt"] = None
        # self.frame_to_serve = self.impression_cycle["frame"]
        
        if hasattr(self, "frame_to_serve") and self.frame_to_serve is not None:
            # Compute the average of the previous frame_to_serve and the new frame
            self.frame_to_serve = cv2.addWeighted(self.frame_to_serve, 0.3, self.impression_cycle["frame"], 0.7, 0)
        else:
            # If frame_to_serve is not initialized, set it to the new frame
            self.frame_to_serve = self.impression_cycle["frame"]
    
    def update_impression(self, latest_frame, sachet_pixel_temperature):
        [sachet_id, pixel, temperature] = min(sachet_pixel_temperature, key=lambda x: abs(x[2] - 125))
        self.ratio = temperature / pixel
        self.latest_frame = (self.latest_frame * self.ratio).astype(np.uint8)
        
        if not self.impression_cycle["spt"]:
            self.impression_cycle["spt"] = sachet_pixel_temperature
        previous_mean_pixel = np.mean([entry[1] for entry in self.impression_cycle["spt"]])
        current_mean_pixel = np.mean([entry[1] for entry in sachet_pixel_temperature])
        
        self.impression_cycle["spt"] = sachet_pixel_temperature
        if previous_mean_pixel > current_mean_pixel or not self.impression_cycle["running"]:
            self.impression_cycle["frame"] = latest_frame
            self.impression_cycle["running"] = True
            for sachet_id, pixel, temperature in sachet_pixel_temperature:
                self.calculated_temp[sachet_id] = pixel * self.ratio
            

    def normalize(self):        
        if self.latest_frame is None:
            print("No frame available.")
            return
        
        threshold = 100
        averages = []
        temp_value = 0
        sachet_temp = 0
        self.ratio = 1
        # Apply threshold while keeping 3 channels intact
        mask = self.latest_frame > threshold  # Mask of bright pixels
        self.latest_frame = np.where(mask, self.latest_frame, 0)  # Set dark pixels to 0
        
        
        sachet_pixel_temperature = []
        print(self.sachets)
        for sachet_id, sachet in self.sachets.items():
            if sachet_id == "length":  
                continue
            top, left, bottom, right = sachet["top"], sachet["left"], sachet["bottom"], sachet["right"]
            sachet_region = self.latest_frame[top:bottom, left:right]
            valid_pixels = sachet_region[sachet_region > 0]  # Exclude dark pixels
            if valid_pixels.size > 0:
                avg_pixel_value = np.mean(valid_pixels)
            else:
                avg_pixel_value = 255  # If no bright pixels, default to 0
            
            sachet_temp = int(self.sachets_temperature[str(sachet_id)])
            with self.data_read_lock:
                avg_pixel_value = self.temp_ranges[sachet_id].update(avg_pixel_value)
            
            sachet_pixel_temperature.append([sachet_id, int(avg_pixel_value), sachet_temp])
            
        self.update_impression(self.latest_frame, sachet_pixel_temperature)
        if self.is_impression_ready():
            try:
                for sachet_id, pixel, temperature in sachet_pixel_temperature:
                    print(f'{sachet_id} -> {int(self.calculated_temp[sachet_id])} {temperature}')
            except Exception as e:
                print('error here', e)
            print(f'ratio: {self.ratio:.2f}')
            print('\n'.join(averages))
            print('\n')
            self.iterations = 0
        if not self.impression_cycle["active"]:
            self.reset_impression()
            
            
        # self.iterations += 1
        # if self.iterations == 20:

            
    def get_sachet_temperature(self):
        with self.data_read_lock:
            response = {}
            for sachet_id, sachet in self.sachets.items():
                if sachet_id == 'length':
                    continue
                response[sachet_id] = self.temp_ranges[sachet_id].get_current()
            return response

    def _capture_frames(self):
        """Internal method to continuously capture frames."""
        try:
            while self.running:
                try:
                    with self.lock:
                        self.latest_frame = self.acquire()
                        if True or platform.system() != "Windows":
                            try:
                                self.normalize()
                            except Exception as e:
                                print('error in normalize', e)
                                pass
                        else:
                            self.frame_to_serve = self.latest_frame
                    if self.display_running:
                        cv2.imshow(self.name, self.get_formatted_frame())
                        pass
                    
                    if self.capture:
                        instant = round(time() * 1000)
                        if platform.system() == "Windows":
                            if instant - self.last_save > 700:
                                self.last_save = instant
                                print('saving')
                                self.save_target_frames()
                        
                        # if not self.recording:
                            
                        #     self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        #     directory = os.path.join(self.path, self.directory, "video")
                        #     if not os.path.exists(directory):
                        #         os.makedirs(directory, exist_ok=True)
                            
                        #     video_file = os.path.join(directory, str(instant) + ".mp4")
                                                        
                        #     frame_width = int(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH))
                        #     frame_height = int(self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        #     self.writer = cv2.VideoWriter(video_file, self.fourcc, 20.0, (frame_width, frame_height))

                        #     print((frame_width, frame_height))
                        #     self.recording = True
                            
                    # else:
                        # if  self.recording:
                        #     try:
                        #         print('releasing video')
                        #         self.writer.release()
                        #     except:
                        #         pass
                        #     self.recording = False
                    if self.recording:
                        self.writer.write(self.latest_frame)

                    key = cv2.waitKey(1) & 0xFF

                    if key == ord('q'):
                        cv2.destroyWindow(self.name)
                        self.stop_display()

                    elif key == ord('s'):
                        cv2.imwrite(self.name + '-ref.jpg', self.get_formatted_frame())
                        print(self.name + '-ref.jpg saved')
                except Exception as e:
                    if self.completed:
                        print("completed", self.name)
                        # break
                    print(f'error in {self.name}: {e}')
                    self.release()
                    sleep(1)
        finally:    
            print("here")

            self.stop_display()
            self.stop()
            self.release()

            try:
                pass
                cv2.destroyWindow(self.name)
            except:
                pass
            if self.released_callback:
                self.released_callback(self)
            

    def stop(self):
        """Stop the camera thread."""
        print(self.name, "stopping")
        self.running = False


    def get_latest_frame(self):
        """Fetch the latest frame."""
        with self.lock:
            return self.frame_to_serve

    def set_frame_format(self, color_format=None, colormap=None):
        """
        Update the frame type for processing.

        Parameters:
            color_format (int): OpenCV color conversion code (e.g., cv2.COLOR_BGR2GRAY).
            colormap (int): OpenCV colormap (e.g., cv2.COLORMAP_INFERNO).
        """
        self.frame_format = {
            'color_format': color_format,
            'colormap': colormap
        }

    def get_formatted_frame(self):
        with self.lock:
            if self.frame_to_serve is None:
                return None

            frame = self.frame_to_serve
            
            if self.frame_format:
                if self.frame_format['color_format'] is not None:
                    frame = cv2.cvtColor(frame, self.frame_format['color_format'])
                if self.frame_format['colormap'] is not None:
                    frame = cv2.applyColorMap(frame, self.frame_format['colormap'])
            return frame
        
    def _get_formatted_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None

            frame = self.latest_frame
            return frame


    def display(self):
        self.display_running = True


    def stop_display(self):
        self.display_running = False
        
    def __del__(self):
        """Destructor to ensure proper cleanup of resources."""
        self.stop_display()
        self.stop()
        self.release()
        print(f'{self.name} released')

if __name__ == '__main__':
    def on_camera_acquired(cam):
        cam.display()
        cam.update_reference_temperature()
        
        
    def on_camera_released(cam):
        cam.stop_display()

    cameras = [Camera('pc_cam', 0)]

    # Start all cameras
    for cam in cameras:
        cam.on_acquire(on_camera_acquired)
        cam.on_release(on_camera_released)
        cam.start()

    try:
        while True:
            sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Stopping cameras...")
    finally:
        for cam in cameras:
            cam.stop_display()
            cam.stop()
            cam.release()
        cv2.destroyAllWindows()
        