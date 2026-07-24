import cv2
from ultralytics import YOLO
import numpy as np

class PerceptionLayer:
    def __init__(self, model_weights="yolov8n.pt", conf_threshold=0.5):
        self.model = YOLO(model_weights)
        self.conf_threshold = conf_threshold
        self.class_mapping = {
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck",
            9: "emergency"
        }

    def process_frame(self, frame):
        results = self.model(frame, conf=self.conf_threshold, verbose=False)[0]
        detections = []
        
        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            if cls_id in self.class_mapping:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = box.conf[0].item()
                v_class = self.class_mapping[cls_id]
                detections.append({
                    "class": v_class,
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf
                })
                
        return detections

    def run_stream(self, stream_url):
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open stream: {stream_url}")
            
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                detections = self.process_frame(frame)
                
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    color = (0, 0, 255) if det["class"] == "emergency" else (0, 255, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{det['class']} {det['confidence']:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                cv2.imshow("FlowGrid Perception Stream", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    dummy_stream = "rtsp://dummy_camera_stream_url"
