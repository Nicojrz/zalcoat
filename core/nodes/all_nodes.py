import cv2
import numpy as np
from core.node_base import BaseNode, NodeParam


# ─────────────────────────────────────────────
#  I/O
# ─────────────────────────────────────────────

class InputImageNode(BaseNode):
    node_type = "input_image"
    label = "Input Image"
    category = "I/O"
    color = "#5B6CFF"
    max_inputs = 0

    def __init__(self, node_id: str):
        super().__init__(node_id)
        self._image: np.ndarray | None = None

    def param_descriptors(self):
        return []

    def set_image(self, img: np.ndarray):
        self._image = img
        self._dirty = True

    def process(self, inputs):
        if self._image is None:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        return self._image.copy()


class OutputImageNode(BaseNode):
    node_type = "output_image"
    label = "Output Image"
    category = "I/O"
    color = "#5B6CFF"
    max_outputs = 0

    def param_descriptors(self):
        return []

    def process(self, inputs):
        return inputs[0] if inputs else np.zeros((256, 256, 3), dtype=np.uint8)


# ─────────────────────────────────────────────
#  FILTROS ESPACIALES
# ─────────────────────────────────────────────

class GaussianBlurNode(BaseNode):
    node_type = "gaussian_blur"
    label = "Gaussian Blur"
    category = "Filtros espaciales"
    color = "#E07B3F"

    def param_descriptors(self):
        return [
            NodeParam("kernel_size", "Kernel size", "int", 5, 1, 31, 2),
            NodeParam("sigma", "Sigma", "float", 1.0, 0.1, 10.0, 0.1),
        ]

    def process(self, inputs):
        img = inputs[0]
        k = self.params["kernel_size"]
        k = k if k % 2 == 1 else k + 1
        return cv2.GaussianBlur(img, (k, k), self.params["sigma"])


class MedianBlurNode(BaseNode):
    node_type = "median_blur"
    label = "Median Blur"
    category = "Filtros espaciales"
    color = "#E07B3F"

    def param_descriptors(self):
        return [NodeParam("kernel_size", "Kernel size", "int", 5, 1, 31, 2)]

    def process(self, inputs):
        k = self.params["kernel_size"]
        k = k if k % 2 == 1 else k + 1
        return cv2.medianBlur(inputs[0], k)


class BilateralFilterNode(BaseNode):
    node_type = "bilateral_filter"
    label = "Bilateral Filter"
    category = "Filtros espaciales"
    color = "#E07B3F"

    def param_descriptors(self):
        return [
            NodeParam("d", "Diameter", "int", 9, 1, 25, 1),
            NodeParam("sigma_color", "Sigma color", "float", 75.0, 1.0, 200.0, 1.0),
            NodeParam("sigma_space", "Sigma space", "float", 75.0, 1.0, 200.0, 1.0),
        ]

    def process(self, inputs):
        p = self.params
        return cv2.bilateralFilter(inputs[0], p["d"], p["sigma_color"], p["sigma_space"])


class SharpenNode(BaseNode):
    node_type = "sharpen"
    label = "Sharpen"
    category = "Filtros espaciales"
    color = "#E07B3F"

    def param_descriptors(self):
        return [NodeParam("strength", "Strength", "float", 1.0, 0.0, 5.0, 0.1)]

    def process(self, inputs):
        s = self.params["strength"]
        kernel = np.array([
            [0, -s, 0],
            [-s, 1 + 4 * s, -s],
            [0, -s, 0]
        ])
        return cv2.filter2D(inputs[0], -1, kernel)


class SobelNode(BaseNode):
    node_type = "sobel"
    label = "Sobel Edge"
    category = "Filtros espaciales"
    color = "#E07B3F"

    def param_descriptors(self):
        return [
            NodeParam("ksize", "Kernel size", "int", 3, 1, 7, 2),
            NodeParam("axis", "Axis", "choice", "both", choices=["x", "y", "both"]),
        ]

    def process(self, inputs):
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY) if len(inputs[0].shape) == 3 else inputs[0]
        k = self.params["ksize"]
        axis = self.params["axis"]
        if axis == "x":
            result = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
        elif axis == "y":
            result = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
        else:
            sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
            sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
            result = cv2.magnitude(sx, sy)
        result = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_GRAY2BGR)


class LaplacianNode(BaseNode):
    node_type = "laplacian"
    label = "Laplacian"
    category = "Filtros espaciales"
    color = "#E07B3F"

    def param_descriptors(self):
        return [NodeParam("ksize", "Kernel size", "int", 3, 1, 31, 2)]

    def process(self, inputs):
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY) if len(inputs[0].shape) == 3 else inputs[0]
        result = cv2.Laplacian(gray, cv2.CV_64F, ksize=self.params["ksize"])
        result = cv2.normalize(np.abs(result), None, 0, 255, cv2.NORM_MINMAX)
        return cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_GRAY2BGR)


# ─────────────────────────────────────────────
#  INTENSIDAD
# ─────────────────────────────────────────────

class BrightnessContrastNode(BaseNode):
    node_type = "brightness_contrast"
    label = "Brightness / Contrast"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [
            NodeParam("alpha", "Contrast", "float", 1.0, 0.0, 3.0, 0.05),
            NodeParam("beta", "Brightness", "int", 0, -100, 100, 1),
        ]

    def process(self, inputs):
        return cv2.convertScaleAbs(inputs[0], alpha=self.params["alpha"], beta=self.params["beta"])


class GammaCorrectionNode(BaseNode):
    node_type = "gamma_correction"
    label = "Gamma Correction"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [NodeParam("gamma", "Gamma", "float", 1.0, 0.1, 5.0, 0.05)]

    def process(self, inputs):
        gamma = self.params["gamma"]
        lut = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)], dtype=np.uint8)
        return cv2.LUT(inputs[0], lut)


class ThresholdNode(BaseNode):
    node_type = "threshold"
    label = "Threshold"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [
            NodeParam("thresh", "Threshold", "int", 127, 0, 255, 1),
            NodeParam("method", "Method", "choice", "binary",
                      choices=["binary", "binary_inv", "otsu", "adaptive_mean", "adaptive_gaussian"]),
        ]

    def process(self, inputs):
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY) if len(inputs[0].shape) == 3 else inputs[0]
        method = self.params["method"]
        t = self.params["thresh"]

        if method == "otsu":
            _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == "binary_inv":
            _, result = cv2.threshold(gray, t, 255, cv2.THRESH_BINARY_INV)
        elif method == "adaptive_mean":
            result = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
        elif method == "adaptive_gaussian":
            result = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        else:
            _, result = cv2.threshold(gray, t, 255, cv2.THRESH_BINARY)

        return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


class HistogramEqualizationNode(BaseNode):
    node_type = "histogram_eq"
    label = "Histogram Equalization"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [NodeParam("method", "Method", "choice", "standard", choices=["standard", "clahe"])]

    def process(self, inputs):
        img = inputs[0]
        if self.params["method"] == "clahe":
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            if len(img.shape) == 3:
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            return clahe.apply(img)
        else:
            if len(img.shape) == 3:
                yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
                yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
                return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
            return cv2.equalizeHist(img)


# ─────────────────────────────────────────────
#  MORFOLOGÍA
# ─────────────────────────────────────────────

class MorphologyNode(BaseNode):
    node_type = "morphology"
    label = "Morphology"
    category = "Morfología"
    color = "#5DBE8A"

    def param_descriptors(self):
        return [
            NodeParam("operation", "Operation", "choice", "erode",
                      choices=["erode", "dilate", "opening", "closing", "gradient", "tophat", "blackhat"]),
            NodeParam("kernel_size", "Kernel size", "int", 5, 1, 31, 2),
            NodeParam("iterations", "Iterations", "int", 1, 1, 10, 1),
        ]

    def process(self, inputs):
        k = self.params["kernel_size"]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        ops = {
            "erode": cv2.MORPH_ERODE,
            "dilate": cv2.MORPH_DILATE,
            "opening": cv2.MORPH_OPEN,
            "closing": cv2.MORPH_CLOSE,
            "gradient": cv2.MORPH_GRADIENT,
            "tophat": cv2.MORPH_TOPHAT,
            "blackhat": cv2.MORPH_BLACKHAT,
        }
        return cv2.morphologyEx(inputs[0], ops[self.params["operation"]], kernel,
                                iterations=self.params["iterations"])


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────

class GrayscaleNode(BaseNode):
    node_type = "grayscale"
    label = "Grayscale"
    category = "Utilidades"
    color = "#9B9B9B"

    def param_descriptors(self):
        return []

    def process(self, inputs):
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


class FlipNode(BaseNode):
    node_type = "flip"
    label = "Flip"
    category = "Utilidades"
    color = "#9B9B9B"

    def param_descriptors(self):
        return [NodeParam("axis", "Axis", "choice", "horizontal",
                          choices=["horizontal", "vertical", "both"])]

    def process(self, inputs):
        axis_map = {"horizontal": 1, "vertical": 0, "both": -1}
        return cv2.flip(inputs[0], axis_map[self.params["axis"]])


class RotateNode(BaseNode):
    node_type = "rotate"
    label = "Rotate"
    category = "Utilidades"
    color = "#9B9B9B"

    def param_descriptors(self):
        return [NodeParam("angle", "Angle (°)", "float", 0.0, -180.0, 180.0, 1.0)]

    def process(self, inputs):
        img = inputs[0]
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), self.params["angle"], 1.0)
        return cv2.warpAffine(img, M, (w, h))


# ─────────────────────────────────────────────
#  REGISTRO GLOBAL
# ─────────────────────────────────────────────

NODE_REGISTRY: dict[str, type[BaseNode]] = {
    cls.node_type: cls
    for cls in [
        InputImageNode, OutputImageNode,
        GaussianBlurNode, MedianBlurNode, BilateralFilterNode,
        SharpenNode, SobelNode, LaplacianNode,
        BrightnessContrastNode, GammaCorrectionNode,
        ThresholdNode, HistogramEqualizationNode,
        MorphologyNode,
        GrayscaleNode, FlipNode, RotateNode,
    ]
}
