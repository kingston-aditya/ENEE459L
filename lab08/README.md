# Lab 08 — Face detection

This laboratory exercise focuses on building an end-to-end edge AI vision pipeline on resource-constrained embedded hardware, specifically the NVIDIA Jetson Nano. Rather than relying on high-level, black-box vision libraries, this lab emphasizes understanding and implementing both low-level algorithmic image processing (such as custom Canny edge detection from scratch) and deep-learning-based computer vision (using lightweight ONNX neural network inference for real-time face detection).

## What is this lab is built around

This lab is built around two primary technical foundations:

- Hardware-Constrained Edge Computing: Operating within the computational and memory limits of the NVIDIA Jetson Nano (2GB/4GB shared RAM, Maxwell GPU architecture) without causing out-of-memory (OOM) crashes or excessive pipeline latency.

- Dual-Paradigm Computer Vision:
    1. Classical Pixel-Level Image Processing: Implementing the foundational mathematics of gradient computation, spatial filtering, non-maximum suppression, and hysteresis thresholding using pure NumPy/SciPy rather than built-in OpenCV functions.

    2. Modern Embedded Neural Network Inference: Running optimized lightweight deep neural networks (ONNX Runtime, RFB-320) paired with custom post-processing algorithms (vectorized Non-Maximum Suppression and IoU calculations) to locate faces in arbitrary scenes.


## What You Will Build

Throughout this lab, you will build:

- `A Custom Non-Maximum Suppression (NMS) Engine`: A pure NumPy post-processing module that calculates Intersection over Union (IoU) across hundreds of candidate bounding boxes to discard redundant detections and retain only the highest-scoring bounding boxes.

- `An ONNX Deep Learning Face Detection Pipeline`: A complete detection routine using Pillow and ONNX Runtime that ingests raw images, handles spatial resizing, tensor normalization ($[-1.0, 1.0]$), dimension permutation, neural network forward passes, coordinate de-normalization, and visual annotation.

- `A Pure Mathematical Canny Edge Detector`: A multi-stage edge detection pipeline built without OpenCV, comprising:
    1. Gaussian smoothing and dual-axis Sobel kernel convolutions for spatial gradients.
    2. Directional Non-Maximum Suppression to thin raw, blurred gradient boundaries down to crisp 1-pixel-wide lines.
    3. Dual-threshold hysteresis edge tracking to suppress ambient noise while preserving true structural contours.


## How to Write code

The instructions for writing the code are provided in slides in `Module 1` on ELMS. The slide numbers for each of the function are mentioned below -

1. **hard_nms**: pages 1-2
2. **detect_faces**: page 2
3. **non_maximum_suppression**: page 3
4. **hysteresis_thresholding**: pages 3-4.
5. **canny_scipy**: page 4-5

## How to clone lab07 code

```
git remote add upstream https://github.com/YOUR_USERNAME/YOUR_REPO.git
git pull upstream main
git push origin main
```

## How to Run

```bash
cd lab08/

# Generate the report on the board
python detect_face.py
```

## How to Debug your code

There is only one way to debug code - 
1. One way is to use breakpoints. For that, we use `pdb` the package and `pdb.set_trace()` to add a breakpoint at any line of code. 

## How to save your work

For saving your work, you create a new branch named `solution8` by running the following command.
```bash
git switch -c solution8
```

After this, push your changes with following set of commands - 
```bash
git add .
git commit -m "Adding things"
git push -u origin solution8
```

## Before you hand in
Run your code and verify that its output matches the provided sample files. Once you have confirmed that everything is working correctly, push your changes to a new branch. Before submitting the link to your branch on Canvas, please verify that the branch contains the code you wrote and that all of your changes have been successfully pushed.
