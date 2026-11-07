import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw
import warnings
from scipy.ndimage import convolve, gaussian_filter

MODEL_PATH = "version-RFB-320.onnx"

warnings.filterwarnings("ignore", category=UserWarning)

sess_options = ort.SessionOptions()
sess_options.log_severity_level = 3  

# 3. Use only available providers to prevent the provider fallback warning
desired_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
available_providers = [p for p in desired_providers if p in ort.get_available_providers()]

# face detection
def hard_nms(box_scores, iou_threshold, top_k=-1, candidate_size=200):
    pass

def detect_faces(image_path, output_path="output_detected.png", conf_threshold=0.7):
    pass

# Edge detection
def non_maximum_suppression(magnitude, angle):
    pass

def hysteresis_thresholding(img, low_thresh, high_thresh):
    pass

def canny_scipy(image_path, output_path="edges_scipy.png", low=20, high=60):
    pass

if __name__ == "__main__":
    detect_faces("face.jpg")
    canny_scipy("face.jpg")