"""
ALPR (Automatic License Plate Recognition) detector using YOLO + OCR.
"""

import logging
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from collections import deque
import numpy as np
import cv2

from .base import (
    Detector, 
    Event, 
    DetectionContext, 
    DetectorRegistry,
    TemporalConfirmationHelper,
    filter_detections,
)
from .yolo_common import load_yolo_model, run_yolo


logger = logging.getLogger(__name__)


def _bbox_to_grid(bbox: List[float], grid_size: int = 20) -> str:
    """Convert bbox to grid cell identifier for deduplication."""
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    grid_x = int(center_x // grid_size)
    grid_y = int(center_y // grid_size)
    return f"{grid_x}_{grid_y}"


def _detection_hash(text: str, bbox: List[float], grid_size: int = 20) -> str:
    """Generate hash for detection deduplication based on plate text and location."""
    grid_id = _bbox_to_grid(bbox, grid_size)
    hash_input = f"{text}:{grid_id}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]


def _crop_and_pad_plate(
    frame: np.ndarray,
    bbox: List[float],
    expand_ratio: float = 0.1
) -> np.ndarray:
    """Crop plate region from frame with padding/expansion."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    width = x2 - x1
    height = y2 - y1
    expand_w = int(width * expand_ratio)
    expand_h = int(height * expand_ratio)
    h, w = frame.shape[:2]
    x1 = max(0, x1 - expand_w)
    y1 = max(0, y1 - expand_h)
    x2 = min(w, x2 + expand_w)
    y2 = min(h, y2 + expand_h)
    crop = frame[y1:y2, x1:x2]
    return crop


@DetectorRegistry.register("alpr")
class ALPRDetector(Detector):
    """ALPR detector using YOLO for plate detection + OCR for text recognition."""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.plate_classes = ["plate", "license_plate"]
        self.conf_threshold = 0.6
        self.iou_threshold = 0.5
        self.crop_expand = 0.1
        self.ocr_engine = "paddleocr"
        self.ocr_lang = "th"
        self.ocr_conf_threshold = 0.6
        self.ocr_reader = None
        self.temporal_helper = None
        self.dedup_window = 60
        self.dedup_grid_size = 20
        self._recent_detections: deque = deque(maxlen=60)
        self._frame_count = 0
    
    def _init_paddleocr(self, lang: str):
        """Initialize PaddleOCR engine."""
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            logger.error("PaddleOCR not installed: pip install paddleocr")
            raise ImportError("PaddleOCR package required") from e
        logger.info(f"Initializing PaddleOCR (lang={lang})...")
        self.ocr_reader = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        logger.info("PaddleOCR initialized successfully")
    
    def _init_tesseract(self, lang: str):
        """Initialize Tesseract OCR engine."""
        try:
            import pytesseract
        except ImportError as e:
            logger.error("pytesseract not installed: pip install pytesseract")
            raise ImportError("pytesseract package required") from e
        self.ocr_reader = {"lang": lang}
        logger.info(f"Tesseract OCR configured (lang={lang})")
    
    def _ocr_paddleocr(self, crop: np.ndarray) -> Tuple[str, float]:
        """Run PaddleOCR on cropped plate image."""
        try:
            result = self.ocr_reader.ocr(crop, cls=True)
            if not result or not result[0]:
                return "", 0.0
            texts, confs = [], []
            for line in result[0]:
                if len(line) >= 2:
                    texts.append(line[1][0])
                    confs.append(line[1][1])
            if not texts:
                return "", 0.0
            combined_text = "".join(texts).strip()
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            return combined_text, avg_conf
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            return "", 0.0
    
    def _ocr_tesseract(self, crop: np.ndarray) -> Tuple[str, float]:
        """Run Tesseract OCR on cropped plate image."""
        try:
            import pytesseract
            from PIL import Image
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(crop_rgb)
            lang = self.ocr_reader["lang"]
            data = pytesseract.image_to_data(pil_img, lang=lang, output_type=pytesseract.Output.DICT)
            texts, confs = [], []
            for i, conf in enumerate(data["conf"]):
                if conf > 0:
                    text = data["text"][i].strip()
                    if text:
                        texts.append(text)
                        confs.append(conf / 100.0)
            if not texts:
                return "", 0.0
            combined_text = "".join(texts)
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            return combined_text, avg_conf
        except Exception as e:
            logger.error(f"Tesseract OCR error: {e}")
            return "", 0.0
    
    def _run_ocr(self, crop: np.ndarray) -> Tuple[str, float]:
        """Run OCR on cropped plate image."""
        if self.ocr_engine == "paddleocr":
            return self._ocr_paddleocr(crop)
        else:
            return self._ocr_tesseract(crop)
    
    def configure(self, cfg: Dict[str, Any]) -> None:
        """Configure the ALPR detector."""
        model_path = cfg.get("model_path")
        if not model_path:
            raise ValueError("alpr detector requires 'model_path' in config")
        self.plate_classes = cfg.get("plate_classes", ["plate", "license_plate"])
        self.conf_threshold = cfg.get("conf_threshold", 0.6)
        self.iou_threshold = cfg.get("iou_threshold", 0.5)
        self.crop_expand = cfg.get("crop_expand", 0.1)
        self.ocr_engine = cfg.get("ocr_engine", "paddleocr")
        self.ocr_lang = cfg.get("ocr_lang", "th")
        self.ocr_conf_threshold = cfg.get("ocr_conf_threshold", 0.6)
        device = cfg.get("device")
        logger.info(f"Loading ALPR detector model: {model_path}")
        self.model = load_yolo_model(model_path, device=device)
        if self.ocr_engine == "paddleocr":
            self._init_paddleocr(self.ocr_lang)
        else:
            self._init_tesseract(self.ocr_lang)
        temporal_window = cfg.get("temporal_window", 5)
        temporal_iou = cfg.get("temporal_iou", 0.3)
        temporal_min_conf = cfg.get("temporal_min_conf", 3)
        self.temporal_helper = TemporalConfirmationHelper(
            window_frames=temporal_window, iou_threshold=temporal_iou, min_confirmations=temporal_min_conf
        )
        self.dedup_window = cfg.get("dedup_window", 60)
        self.dedup_grid_size = cfg.get("dedup_grid_size", 20)
        self._recent_detections = deque(maxlen=self.dedup_window)
        self._configured = True
        logger.info(
            f"ALPR detector configured: classes={self.plate_classes}, conf={self.conf_threshold}, "
            f"ocr={self.ocr_engine}({self.ocr_lang}), temporal=({temporal_window},{temporal_min_conf}), dedup={self.dedup_window}"
        )
    
    def process(self, frame: np.ndarray, ts_ms: int, ctx: DetectionContext) -> List[Event]:
        """Process frame and detect license plates with OCR."""
        if not self.is_configured():
            logger.error("ALPR detector not configured")
            return []
        self._frame_count += 1
        detections = run_yolo(self.model, frame, classes=None, conf=self.conf_threshold, iou=self.iou_threshold)
        if not detections:
            return []
        detections = [(label, conf, bbox) for label, conf, bbox in detections if label in self.plate_classes]
        if not detections:
            return []
        detections = filter_detections(detections, roi_polygons=ctx.roi_polygons, min_area=ctx.min_box_area)
        if not detections:
            return []
        events = []
        for label, conf, bbox in detections:
            is_confirmed = self.temporal_helper.add_and_check(label=label, bbox=bbox, conf=conf, ts_ms=ts_ms)
            if not is_confirmed:
                continue
            try:
                crop = _crop_and_pad_plate(frame, bbox, self.crop_expand)
            except Exception as e:
                logger.error(f"Failed to crop plate: {e}")
                continue
            text, ocr_conf = self._run_ocr(crop)
            if ocr_conf < self.ocr_conf_threshold:
                logger.debug(f"Low OCR confidence: {text} ({ocr_conf:.2f} < {self.ocr_conf_threshold})")
                continue
            text = text.strip()
            if not text:
                logger.debug("Empty OCR result, skipping")
                continue
            det_hash = _detection_hash(text, bbox, self.dedup_grid_size)
            is_duplicate = False
            for frame_num, recent_hash in self._recent_detections:
                if recent_hash == det_hash:
                    if (self._frame_count - frame_num) < self.dedup_window:
                        is_duplicate = True
                        break
            if is_duplicate:
                logger.debug(f"Duplicate plate detection filtered: {text} @ {bbox}")
                continue
            self._recent_detections.append((self._frame_count, det_hash))
            event = Event(
                camera_id=ctx.camera_id,
                type="alpr",
                label=label,
                conf=conf,
                bbox=bbox,
                ts_ms=ts_ms,
                extras={
                    "text": text,
                    "ocr_conf": ocr_conf,
                    "ocr_engine": self.ocr_engine,
                    "frame_count": self._frame_count,
                    "det_hash": det_hash,
                },
            )
            events.append(event)
            logger.info(f"🚗 Plate detected: {text} ({conf:.2f}, OCR: {ocr_conf:.2f}) @ {bbox} [frame={self._frame_count}]")
        return events
