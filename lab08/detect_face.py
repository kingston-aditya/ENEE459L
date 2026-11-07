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
    def area_of(left_top, right_bottom):
        hw = np.clip(right_bottom - left_top, 0.0, None)
        return hw[..., 0] * hw[..., 1]

    def iou_of(boxes0, boxes1, eps=1e-5):
        overlap_left_top = np.maximum(boxes0[..., :2], boxes1[..., :2])
        overlap_right_bottom = np.minimum(boxes0[..., 2:], boxes1[..., 2:])
        overlap_area = area_of(overlap_left_top, overlap_right_bottom)
        area0 = area_of(boxes0[..., :2], boxes0[..., 2:])
        area1 = area_of(boxes1[..., :2], boxes1[..., 2:])
        return overlap_area / (area0 + area1 - overlap_area + eps)

    if box_scores.size == 0:
        return box_scores
    scores = box_scores[:, -1]
    boxes = box_scores[:, :-1]
    picked = []
    indexes = np.argsort(scores)[-candidate_size:]
    while len(indexes) > 0:
        current = indexes[-1]
        picked.append(current)
        if 0 < top_k == len(picked) or len(indexes) == 1:
            break
        current_box = boxes[current, :]
        indexes = indexes[:-1]
        rest_boxes = boxes[indexes, :]
        iou = iou_of(rest_boxes, np.expand_dims(current_box, axis=0))
        indexes = indexes[iou <= iou_threshold]
    return box_scores[picked, :]

def detect_faces(image_path, output_path="output_detected.png", conf_threshold=0.7):
    session = ort.InferenceSession(
        MODEL_PATH, sess_options=sess_options, providers=available_providers
    )
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    resized = image.resize((320, 240))
    tensor = np.asarray(resized, dtype=np.float32)
    tensor = (tensor - 127.0) / 128.0
    tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
    scores, boxes = session.run(None, {"input": tensor})
    probs = scores[0, :, 1]
    mask = probs > conf_threshold
    image_out = image.copy()
    if np.any(mask):
        box_probs = np.concatenate(
            [boxes[0, mask, :], probs[mask, None]], axis=1
        )
        box_probs = hard_nms(box_probs, iou_threshold=0.3)
        box_probs[:, 0] *= width
        box_probs[:, 1] *= height
        box_probs[:, 2] *= width
        box_probs[:, 3] *= height
        draw = ImageDraw.Draw(image_out)
        for row in box_probs:
            draw.rectangle(
                [int(row[0]), int(row[1]), int(row[2]), int(row[3])],
                outline=(0, 255, 0),
                width=3,
            )
    image_out.save(output_path)

# Edge detection
def non_maximum_suppression(magnitude, angle):
    ang = np.mod(angle, 180.0)
    m = magnitude
    east = np.zeros_like(m)
    west = np.zeros_like(m)
    north = np.zeros_like(m)
    south = np.zeros_like(m)
    northeast = np.zeros_like(m)
    northwest = np.zeros_like(m)
    southeast = np.zeros_like(m)
    southwest = np.zeros_like(m)
    east[:, :-1] = m[:, 1:]
    west[:, 1:] = m[:, :-1]
    north[1:, :] = m[:-1, :]
    south[:-1, :] = m[1:, :]
    northeast[1:, :-1] = m[:-1, 1:]
    northwest[1:, 1:] = m[:-1, :-1]
    southeast[:-1, :-1] = m[1:, 1:]
    southwest[:-1, 1:] = m[1:, :-1]
    horizontal = (ang < 22.5) | (ang >= 157.5)
    diagonal = (ang >= 22.5) & (ang < 67.5)
    vertical = (ang >= 67.5) & (ang < 112.5)
    antidiagonal = (ang >= 112.5) & (ang < 157.5)
    q = np.zeros_like(m)
    r = np.zeros_like(m)
    q = np.where(horizontal, east, q)
    r = np.where(horizontal, west, r)
    q = np.where(diagonal, southwest, q)
    r = np.where(diagonal, northeast, r)
    q = np.where(vertical, south, q)
    r = np.where(vertical, north, r)
    q = np.where(antidiagonal, northwest, q)
    r = np.where(antidiagonal, southeast, r)
    keep = (m >= q) & (m >= r)
    keep[0, :] = False
    keep[-1, :] = False
    keep[:, 0] = False
    keep[:, -1] = False
    thinned = np.zeros_like(m)
    thinned[keep] = m[keep]
    return thinned

def hysteresis_thresholding(img, low_thresh, high_thresh):
    height, width = img.shape
    out = np.zeros((height, width), dtype=np.uint8)
    out[img >= high_thresh] = 255
    weak_y, weak_x = np.nonzero((img >= low_thresh) & (img < high_thresh))
    for y, x in zip(weak_y.tolist(), weak_x.tolist()):
        if y == 0 or x == 0 or y == height - 1 or x == width - 1:
            continue
        if (
            out[y + 1, x - 1] == 255
            or out[y + 1, x] == 255
            or out[y + 1, x + 1] == 255
            or out[y, x - 1] == 255
            or out[y, x + 1] == 255
            or out[y - 1, x - 1] == 255
            or out[y - 1, x] == 255
            or out[y - 1, x + 1] == 255
        ):
            out[y, x] = 255
    return out

def canny_scipy(image_path, output_path="edges_scipy.png", low=20, high=60):
    gray = np.asarray(Image.open(image_path).convert("L"), dtype=np.float32)
    blurred = gaussian_filter(gray, sigma=1.4)
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
    gx = convolve(blurred, kx)
    gy = convolve(blurred, ky)
    magnitude = np.hypot(gx, gy)
    peak = float(magnitude.max())
    if peak > 0:
        magnitude = magnitude / peak * 255.0
    angle = np.rad2deg(np.arctan2(-gy, gx))
    edges = hysteresis_thresholding(
        non_maximum_suppression(magnitude, angle), low, high
    )
    Image.fromarray(edges).save(output_path)

if __name__ == "__main__":
    detect_faces("face.jpg")
    canny_scipy("face.jpg")