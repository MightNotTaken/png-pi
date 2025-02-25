import os
import cv2
import threading
from time import sleep, time
from enum import Enum
from .frame import Frame

class SourceType(Enum):
    VIDEO_FILE     = 1
    ACTUAL_CAMERA  = 2

BASE_PATH = "C:/tahir/codes/Gujral_Sir/PnG/pi/training-data"

class Camera:
    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.cam = None
        self.latest_frame = None
        self.running = False
        self.display_running = False
        self.lock = threading.Lock()
        self.thread = None
        self.acquired = False
        self.acquired_callback = None
        self.released_callback = None
        self.completed = False
        self.fps = 2
        self.capture = False
        self.next_capture = 0
        self.frames: Frame = []
        self.leakage_path       = BASE_PATH + "/leakage/" + self.name
        self.non_leakage_path   = BASE_PATH + "/non-leakage/" + self.name
        os.makedirs(BASE_PATH + "/leakage/" + self.name, exist_ok=True)
        os.makedirs(BASE_PATH + "/non-leakage/" + self.name, exist_ok=True)
        try:
            int(self.source)
            self.type = SourceType.ACTUAL_CAMERA
        except:
            self.type = SourceType.VIDEO_FILE

        self.frame_format = {
            'color_format': cv2.COLOR_BGR2GRAY,
            'colormap': cv2.COLORMAP_INFERNO
        }

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
        self.cam = None
        self.acquired = False

    def start(self):
        """Start the camera in a separate thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.thread.start()

    def save_target_frames(self):
        main_frame = self.get_formatted_frame()
        instant = str(round(time() * 10))
        for frame in self.frames:
            try:
                if frame["capture"]:
                    file_name = os.path.join(self.leakage_path, instant + '-' + str(frame['sachet']) + '.png')
                    roi = main_frame[frame['top']:frame['bottom'], frame['left']:frame['right']]
                    if not frame['leakage']:
                        file_name = os.path.join(self.non_leakage_path, instant + '-' + str(frame['sachet']) + '.png')
                    print('writing image')
                    cv2.imwrite(file_name, roi)            
            except Exception as e:
                print(e)
    def _capture_frames(self):
        """Internal method to continuously capture frames."""
        try:
            while self.running:
                try:
                    self.latest_frame = self.acquire()
                    if self.display_running:
                        cv2.imshow(self.name, self.get_formatted_frame())
                        pass
                    if self.capture:
                        instant = round(time() * 1000)
                        if instant > self.next_capture:
                            self.next_capture = instant + round(1000 / self.fps)
                            self.save_target_frames()
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
                        break
                    print(f'error in {self.name}: {e}')
                    self.release()
                    sleep(.5)
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
            return self.latest_frame

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
        """
        Get the latest frame formatted as per the set frame type.

        Returns:
            Formatted frame or None if no frame is available.
        """
        with self.lock:
            if self.latest_frame is None:
                return None

            frame = self.latest_frame

            if self.frame_format:
                if self.frame_format['color_format'] is not None:
                    frame = cv2.cvtColor(frame, self.frame_format['color_format'])
                if self.frame_format['colormap'] is not None:
                    frame = cv2.applyColorMap(frame, self.frame_format['colormap'])

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
        
    def on_camera_released(cam):
        cam.stop_display()

    cameras = [Camera('pc_cam', 0), Camera('thermal_cam', 1)]

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
