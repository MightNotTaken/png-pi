from flask import Flask, Response, jsonify, request
from .camera import Camera
import cv2
import time
from flask_cors import CORS

class Streamer:
    def __init__(self):
        self.cams = {}

    def add_cam(self, cam: Camera):
        if not cam:
            raise RuntimeError('Please provide a valid Camera')
            return
        self.cams[cam.name] = cam
    
    def remove_cam(self, name):
        if name in self.cams:
            del self.cams[name]

    def get_camera(self, name: str) -> Camera:
        """Fetch a camera by name."""
        return self.cams.get(name, None)

    def generate_frames(self, name: str):
        """Generator function to stream frames from the specified camera."""
        cam = self.get_camera(name)
        if not cam:
            raise RuntimeError(f"Camera with name '{name}' not found.")
        while True:
            frame = cam.get_formatted_frame()
            if frame is not None:
                # Encode the frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    # Convert frame to byte data for streaming
                    frame_data = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n\r\n')
            else:
                # If no frame is available, sleep briefly to avoid CPU overload
                time.sleep(0.05)

    def start(self):
        """Create and return the Flask app."""
        app = Flask(__name__)
        CORS(app)
        
        @app.route('/start-capture', methods=['POST'])
        def start_capture():
            try:
                data = request.get_json()
                frames = data['frames']
                cam = data['cam']
                ref_cam = self.cams[cam['name']]
                ref_cam.frames = frames
                ref_cam.fps = cam['fps']
                ref_cam.capture = True
                return jsonify(frames), 200
            except Exception as e:
                print(e)
                return e.__str__(), 400
        
        @app.route('/stop-capture/<string:camera_name>')
        def stop_capture(camera_name):
            print(camera_name)
            self.cams[camera_name].capture = False
            return jsonify([camera_name]), 200

        @app.route('/available-cams')
        def get_available_cams():
            try:
                cams = []
                for cam in self.cams:  # Assuming `self.cams` is replaced with `cams` or similar
                    print(self.cams[cam].get_specification())
                    cams.append(self.cams[cam].get_specification())  # Replace `cams` as per your actual logic
                return jsonify(cams), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
        @app.route('/video_feed/<string:name>')
        def video_feed(name):
            """Route to handle video feed request for a specific camera."""
            try:
                if self.cams[name]:
                    return Response(self.generate_frames(name),
                                    mimetype='multipart/x-mixed-replace; boundary=frame')
                else:
                    return Response('Camera not found', mimetype='text/plain')
            except Exception as e:
                return jsonify({'name': name, 'status': 'not found'}), 400
        app.run(host='0.0.0.0', port=5000, threaded=True)
        return app