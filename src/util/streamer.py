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

    def generate_frames(self, name: str, format = 'no-format'):
        """Generator function to stream frames from the specified camera."""
        cam = self.get_camera(name)
        if not cam:
            raise RuntimeError(f"Camera with name '{name}' not found.")
        while True:
            frame = None
            if format == 'no-format':
                frame = cam.get_latest_frame()
            else:
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
        
        @app.route('/get-temperature-data/<string:camera_name>')
        def get_temperature(camera_name):
            try:
                cam = self.cams[camera_name]
                if cam.temp_ranges:
                    return jsonify(cam.get_sachet_temperature())
            except Exception as e:
                print(e)       
            return jsonify([])
        
        @app.route('/get-plc-data/<string:camera_name>')
        def get_plc_data(camera_name):
            try:
                cam = self.cams[camera_name]
                
                if cam.plc:
                    cam.plc.update()
                    return cam.plc.get_tags(), 200
            except Exception as e:
                print(e)       
            return jsonify([])
        
        
        
        @app.route('/start-capture', methods=['POST'])
        def start_capture():
            try:
                data = request.get_json()
                frames = data['frames']
                cam = data['cam']
                ref_cam = self.cams[cam['name']]
                ref_cam.frames = frames
                ref_cam.save_frames()
                ref_cam.update_sachets()
                ref_cam.fps = cam['fps']
                ref_cam.capture = True
                ref_cam.directory = data['folder']
                ref_cam.temperature = data['temperature']
                print('parameters changed')
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
    
        @app.route('/video_feed/<string:name>/<string:format>')
        def video_feed(name, format):
            """Route to handle video feed request for a specific camera."""
            try:
                if self.cams[name]:
                    return Response(self.generate_frames(name, format),
                                    mimetype='multipart/x-mixed-replace; boundary=frame')
                else:
                    return Response('Camera not found', mimetype='text/plain')
            except Exception as e:
                return jsonify({'name': name, 'status': 'not found'}), 400
        app.run(host='0.0.0.0', port=5000, threaded=True)
        return app