import base64
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
        self.filename: str = ""

    def param_descriptors(self):
        return []

    def set_image(self, img: np.ndarray):
        self._image = img
        self._dirty = True

    def serialize(self):
        data = super().serialize()
        data["filename"] = self.filename
        if self._image is not None:
            success, buffer = cv2.imencode(".png", self._image)
            if success:
                data["image_data"] = base64.b64encode(buffer.tobytes()).decode("ascii")
        return data

    @classmethod
    def deserialize(cls, node_id: str, data: dict):
        node = cls(node_id)
        params = data.get("params", {})
        node.params.update(params)
        node.filename = data.get("filename", "")
        image_data = data.get("image_data")
        if image_data:
            raw = base64.b64decode(image_data)
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
            if img is None:
                img = np.zeros((256, 256, 3), dtype=np.uint8)
            node.set_image(img)
        return node

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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        return cv2.convertScaleAbs(inputs[0], alpha=self.params["alpha"], beta=self.params["beta"])


class GammaCorrectionNode(BaseNode):
    node_type = "gamma_correction"
    label = "Gamma Correction"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [NodeParam("gamma", "Gamma", "float", 1.0, 0.1, 5.0, 0.05)]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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


class HSVThresholdNode(BaseNode):
    node_type = "hsv_threshold"
    label = "HSV Threshold"
    category = "Segmentación"
    color = "#8B5CF6"

    def param_descriptors(self):
        return [
            NodeParam("lower_hsv", "Lower HSV", "hsv", (0, 100, 100)),
            NodeParam("upper_hsv", "Upper HSV", "hsv", (10, 255, 255)),
            NodeParam("output", "Output", "choice", "color",
                      choices=["color", "mask"]),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)

        img = inputs[0]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        lower = np.array(self.params["lower_hsv"], dtype=np.uint8)
        upper = np.array(self.params["upper_hsv"], dtype=np.uint8)

        if lower[0] <= upper[0]:
            mask = cv2.inRange(hsv, lower, upper)
        else:
            mask_lower = np.array([lower[0], lower[1], lower[2]], dtype=np.uint8)
            mask_upper = np.array([179, upper[1], upper[2]], dtype=np.uint8)
            mask1 = cv2.inRange(hsv, mask_lower, mask_upper)
            wrap_lower = np.array([0, lower[1], lower[2]], dtype=np.uint8)
            wrap_upper = np.array([upper[0], upper[1], upper[2]], dtype=np.uint8)
            mask2 = cv2.inRange(hsv, wrap_lower, wrap_upper)
            mask = cv2.bitwise_or(mask1, mask2)

        if self.params.get("output", "color") == "mask":
            return cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        return cv2.bitwise_and(img, img, mask=mask)


class HistogramEqualizationNode(BaseNode):
    node_type = "histogram_eq"
    label = "Histogram Equalization"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [NodeParam("method", "Method", "choice", "standard", choices=["standard", "clahe"])]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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


class IntensityEqualizationNode(BaseNode):
    node_type = "intensity_equalization"
    label = "Intensity Equalization"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [
            NodeParam("method", "Method", "choice", "uniform",
                      choices=["uniform", "exponential", "rayleigh", "hypercubic", "logarithmic", "power"]),
            NodeParam("scale", "Scale", "float", 1.0, 0.1, 5.0, 0.1),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        img = inputs[0]
        method = self.params["method"]
        scale = max(0.1, float(self.params.get("scale", 1.0)))

        if method == "uniform":
            return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

        src = img.astype(np.float32) / 255.0
        if method == "exponential":
            result = 1.0 - np.exp(-scale * src)
        elif method == "rayleigh":
            sigma = max(scale, 0.1)
            result = 1.0 - np.exp(-(src ** 2) / (2.0 * sigma * sigma + 1e-9))
        elif method == "hypercubic":
            result = np.power(src, 1.0 / (scale + 1.0))
        elif method == "logarithmic":
            result = np.log1p(scale * src) / np.log1p(scale)
        elif method == "power":
            result = np.power(src, scale)
        else:
            result = src

        result = np.clip(result * 255.0, 0, 255).astype(np.uint8)
        return result


class MultiThresholdNode(BaseNode):
    node_type = "multi_threshold"
    label = "Multi Threshold"
    category = "Intensidad"
    color = "#F5C542"

    def param_descriptors(self):
        return [
            NodeParam("num_thresholds", "Number of thresholds", "choice", "3", 
                      choices=["2", "3", "4", "5"]),
            NodeParam("th1", "Threshold 1", "int", 85, 0, 255, 1),
            NodeParam("th2", "Threshold 2", "int", 170, 0, 255, 1),
            NodeParam("th3", "Threshold 3", "int", 200, 0, 255, 1),
            NodeParam("th4", "Threshold 4", "int", 225, 0, 255, 1),
            NodeParam("th5", "Threshold 5", "int", 240, 0, 255, 1),
            NodeParam("val0", "Value 0 (below th1)", "int", 0, 0, 255, 1),
            NodeParam("val1", "Value 1", "int", 85, 0, 255, 1),
            NodeParam("val2", "Value 2", "int", 170, 0, 255, 1),
            NodeParam("val3", "Value 3", "int", 200, 0, 255, 1),
            NodeParam("val4", "Value 4", "int", 225, 0, 255, 1),
            NodeParam("val5", "Value 5 (above last threshold)", "int", 255, 0, 255, 1),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY) if len(inputs[0].shape) == 3 else inputs[0]
        
        # Get number of thresholds
        num_thresholds = int(self.params["num_thresholds"])
        
        # Get threshold values and sort them
        threshold_vals = []
        for i in range(1, num_thresholds + 1):
            threshold_vals.append(self.params[f"th{i}"])
        threshold_vals.sort()
        
        # Get output values
        output_vals = []
        for i in range(num_thresholds + 1):
            output_vals.append(self.params[f"val{i}"])
        
        # Create segmented image
        segmented = np.zeros_like(gray, dtype=np.uint8)
        segmented[:] = output_vals[0]  # Initialize with first value
        
        # Apply thresholds
        for i, thresh in enumerate(threshold_vals):
            segmented[gray > thresh] = output_vals[i + 1]
        
        return cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)


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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
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
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        img = inputs[0]
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), self.params["angle"], 1.0)
        return cv2.warpAffine(img, M, (w, h))


class InverseImageNode(BaseNode):
    node_type = "inverse_image"
    label = "Inverse Image"
    category = "Utilidades"
    color = "#9B9B9B"

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        return cv2.bitwise_not(inputs[0])


# ─────────────────────────────────────────────
#  OPERACIONES LÓGICAS
# ─────────────────────────────────────────────

def _normalize_images(img1: np.ndarray, img2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Normaliza dos imágenes para que tengan el mismo tamaño."""
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    
    if h1 == h2 and w1 == w2:
        return img1, img2
    
    # Usa el tamaño más grande
    max_h = max(h1, h2)
    max_w = max(w1, w2)
    
    # Redimensiona ambas imágenes al tamaño más grande
    img1_resized = cv2.resize(img1, (max_w, max_h), interpolation=cv2.INTER_LINEAR)
    img2_resized = cv2.resize(img2, (max_w, max_h), interpolation=cv2.INTER_LINEAR)
    
    return img1_resized, img2_resized


class LogicalAndNode(BaseNode):
    node_type = "logical_and"
    label = "Logical AND"
    category = "Operaciones lógicas"
    color = "#FF6B6B"
    max_inputs = 2

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if len(inputs) < 2:
            return inputs[0] if inputs else np.zeros((256, 256, 3), dtype=np.uint8)
        img1, img2 = _normalize_images(inputs[0], inputs[1])
        return cv2.bitwise_and(img1, img2)


class LogicalOrNode(BaseNode):
    node_type = "logical_or"
    label = "Logical OR"
    category = "Operaciones lógicas"
    color = "#FF6B6B"
    max_inputs = 2

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if len(inputs) < 2:
            return inputs[0] if inputs else np.zeros((256, 256, 3), dtype=np.uint8)
        img1, img2 = _normalize_images(inputs[0], inputs[1])
        return cv2.bitwise_or(img1, img2)


class LogicalXorNode(BaseNode):
    node_type = "logical_xor"
    label = "Logical XOR"
    category = "Operaciones lógicas"
    color = "#FF6B6B"
    max_inputs = 2

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if len(inputs) < 2:
            return inputs[0] if inputs else np.zeros((256, 256, 3), dtype=np.uint8)
        img1, img2 = _normalize_images(inputs[0], inputs[1])
        return cv2.bitwise_xor(img1, img2)


class LogicalNotNode(BaseNode):
    node_type = "logical_not"
    label = "Logical NOT"
    category = "Operaciones lógicas"
    color = "#FF6B6B"
    max_inputs = 1

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        return cv2.bitwise_not(inputs[0])


# ─────────────────────────────────────────────
#  OPERACIONES ARITMÉTICAS
# ─────────────────────────────────────────────

class AdditionNode(BaseNode):
    node_type = "addition"
    label = "Addition"
    category = "Operaciones aritméticas"
    color = "#FFD93D"
    max_inputs = 2

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if len(inputs) < 2:
            return inputs[0] if inputs else np.zeros((256, 256, 3), dtype=np.uint8)
        img1, img2 = _normalize_images(inputs[0], inputs[1])
        return cv2.add(img1, img2)


class SubtractionNode(BaseNode):
    node_type = "subtraction"
    label = "Subtraction"
    category = "Operaciones aritméticas"
    color = "#FFD93D"
    max_inputs = 2

    def param_descriptors(self):
        return []

    def process(self, inputs):
        if len(inputs) < 2:
            return inputs[0] if inputs else np.zeros((256, 256, 3), dtype=np.uint8)
        img1, img2 = _normalize_images(inputs[0], inputs[1])
        return cv2.subtract(img1, img2)


class ScalarMultiplyNode(BaseNode):
    node_type = "scalar_multiply"
    label = "Scalar Multiply"
    category = "Operaciones aritméticas"
    color = "#FFD93D"
    max_inputs = 1

    def param_descriptors(self):
        return [NodeParam("scalar", "Scalar", "float", 1.0, 0.0, 5.0, 0.1)]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        return cv2.multiply(inputs[0], self.params["scalar"])


# ─────────────────────────────────────────────
#  RUIDO
# ─────────────────────────────────────────────

class SaltPepperNoiseNode(BaseNode):
    node_type = "salt_pepper_noise"
    label = "Salt & Pepper Noise"
    category = "Ruido"
    color = "#8B5CF6"

    def param_descriptors(self):
        return [
            NodeParam("amount", "Amount", "float", 0.05, 0.0, 0.5, 0.01),
            NodeParam("salt_vs_pepper", "Salt/Pepper ratio", "float", 0.5, 0.0, 1.0, 0.1),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        img = inputs[0].copy()
        amount = self.params["amount"]
        salt_ratio = self.params["salt_vs_pepper"]
        
        # Salt noise
        salt_mask = np.random.random(img.shape[:2]) < (amount * salt_ratio)
        img[salt_mask] = 255
        
        # Pepper noise
        pepper_mask = np.random.random(img.shape[:2]) < (amount * (1 - salt_ratio))
        img[pepper_mask] = 0
        
        return img


class GaussianNoiseNode(BaseNode):
    node_type = "gaussian_noise"
    label = "Gaussian Noise"
    category = "Ruido"
    color = "#8B5CF6"

    def param_descriptors(self):
        return [
            NodeParam("mean", "Mean", "float", 0.0, -50.0, 50.0, 1.0),
            NodeParam("std", "Std Dev", "float", 25.0, 0.0, 100.0, 1.0),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        img = inputs[0].astype(np.float32)
        noise = np.random.normal(self.params["mean"], self.params["std"], img.shape)
        noisy = img + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)


# ─────────────────────────────────────────────
#  ETIQUETADO
# ─────────────────────────────────────────────

class ConnectedComponentsNode(BaseNode):
    node_type = "connected_components"
    label = "Connected Components"
    category = "Etiquetado"
    color = "#06B6D4"

    def param_descriptors(self):
        return [
            NodeParam("connectivity", "Connectivity", "choice", "8", choices=["4", "8"]),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY) if len(inputs[0].shape) == 3 else inputs[0]
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        connectivity = 8 if self.params["connectivity"] == "8" else 4
        num_labels, labels = cv2.connectedComponents(binary, connectivity=connectivity)
        
        # Normalize labels to 0-255 range for visualization
        if num_labels > 1:
            labels = (labels / (num_labels - 1) * 255).astype(np.uint8)
        else:
            labels = np.zeros_like(labels, dtype=np.uint8)
        
        return cv2.cvtColor(labels, cv2.COLOR_GRAY2BGR)


# ─────────────────────────────────────────────
#  PSEUDOCOLOR
# ─────────────────────────────────────────────

class PseudocolorNode(BaseNode):
    node_type = "pseudocolor"
    label = "Pseudocolor"
    category = "Utilidades"
    color = "#9B9B9B"

    def param_descriptors(self):
        return [
            NodeParam("colormap", "Colormap", "choice", "jet",
                      choices=["autumn", "bone", "jet", "winter", "rainbow", "ocean", "summer", "spring",
                               "cool", "hsv", "pink", "hot", "parula", "magma", "inferno", "plasma", "viridis",
                               "cividis", "twilight", "twilight_shifted", "turbo", "deepgreen"]),
        ]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        gray = cv2.cvtColor(inputs[0], cv2.COLOR_BGR2GRAY) if len(inputs[0].shape) == 3 else inputs[0]
        
        colormap_map = {
            "autumn": cv2.COLORMAP_AUTUMN,
            "bone": cv2.COLORMAP_BONE,
            "jet": cv2.COLORMAP_JET,
            "winter": cv2.COLORMAP_WINTER,
            "rainbow": cv2.COLORMAP_RAINBOW,
            "ocean": cv2.COLORMAP_OCEAN,
            "summer": cv2.COLORMAP_SUMMER,
            "spring": cv2.COLORMAP_SPRING,
            "cool": cv2.COLORMAP_COOL,
            "hsv": cv2.COLORMAP_HSV,
            "pink": cv2.COLORMAP_PINK,
            "hot": cv2.COLORMAP_HOT,
            "parula": cv2.COLORMAP_PARULA,
            "magma": cv2.COLORMAP_MAGMA,
            "inferno": cv2.COLORMAP_INFERNO,
            "plasma": cv2.COLORMAP_PLASMA,
            "viridis": cv2.COLORMAP_VIRIDIS,
            "cividis": cv2.COLORMAP_CIVIDIS,
            "twilight": cv2.COLORMAP_TWILIGHT,
            "twilight_shifted": cv2.COLORMAP_TWILIGHT_SHIFTED,
            "turbo": cv2.COLORMAP_TURBO,
            "deepgreen": cv2.COLORMAP_DEEPGREEN,
        }
        
        return cv2.applyColorMap(gray, colormap_map[self.params["colormap"]])


# ─────────────────────────────────────────────
#  FILTROS MORFOLÓGICOS
# ─────────────────────────────────────────────

class MaxFilterNode(BaseNode):
    node_type = "max_filter"
    label = "Maximum Filter"
    category = "Morfología"
    color = "#5DBE8A"

    def param_descriptors(self):
        return [NodeParam("kernel_size", "Kernel size", "int", 3, 1, 31, 2)]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        k = self.params["kernel_size"]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        return cv2.dilate(inputs[0], kernel)


class MinFilterNode(BaseNode):
    node_type = "min_filter"
    label = "Minimum Filter"
    category = "Morfología"
    color = "#5DBE8A"

    def param_descriptors(self):
        return [NodeParam("kernel_size", "Kernel size", "int", 3, 1, 31, 2)]

    def process(self, inputs):
        if not inputs:
            return np.zeros((256, 256, 3), dtype=np.uint8)
        k = self.params["kernel_size"]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        return cv2.erode(inputs[0], kernel)


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
        ThresholdNode, HSVThresholdNode, HistogramEqualizationNode,
        MorphologyNode,
        GrayscaleNode, FlipNode, RotateNode,
        LogicalAndNode, LogicalOrNode, LogicalXorNode, LogicalNotNode,
        AdditionNode, SubtractionNode, ScalarMultiplyNode,
        SaltPepperNoiseNode, GaussianNoiseNode,
        ConnectedComponentsNode,
        PseudocolorNode,
        MaxFilterNode, MinFilterNode,
        IntensityEqualizationNode, MultiThresholdNode,
        InverseImageNode,
    ]
}
