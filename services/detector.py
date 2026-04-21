# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from PIL import Image

@dataclass
class Detection:
    label: str
    conf: float
    box: Tuple[int, int, int, int] = (0, 0, 0, 0)

class Detector:
    def __init__(self, weights_path: str):
        from ultralytics import YOLO
        self.model = YOLO(weights_path)
        self.is_classifier = self.model.task == "classify"

    def predict(self, image: Image.Image, conf: float = 0.35) -> List[Detection]:
        img = np.array(image.convert("RGB"))
        results = self.model.predict(source=img, verbose=False)
        if not results:
            return []

        r0 = results[0]

        # ── Classification model ──────────────────────────
        if self.is_classifier:
            probs = r0.probs
            if probs is None:
                return []
            names = r0.names
            top_indices = probs.top5
            top_confs = probs.top5conf.tolist()
            # Always return all top-5; threshold is applied by the API layer
            # so the Flutter UI can always show alternatives even when confidence is low.
            dets = []
            for idx, c in zip(top_indices, top_confs):
                dets.append(Detection(label=str(names[idx]), conf=float(c)))
            return dets

        # ── Object detection model ────────────────────────
        names = r0.names
        dets = []
        if r0.boxes is None:
            return dets
        for b in r0.boxes:
            cls_id = int(b.cls[0])
            label = str(names.get(cls_id, f"class_{cls_id}"))
            c = float(b.conf[0])
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            dets.append(Detection(label=label, conf=c, box=(x1, y1, x2, y2)))
        dets.sort(key=lambda d: d.conf, reverse=True)
        return dets