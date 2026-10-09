"""Drawing Quality Assessment Module using OpenCV."""

from dataclasses import dataclass, field
import cv2
import numpy as np
from PIL import Image


@dataclass
class QualityReport:
    blur_score: float  # Laplacian variance (higher = sharper, <100 = blurry)
    is_blurry: bool
    contrast_range: float  # Difference between 95th and 5th percentile intensity
    is_low_contrast: bool
    estimated_skew_angle: float  # Skew in degrees
    warnings: list[str] = field(default_factory=list)


def assess_quality(pil_image: Image.Image, blur_threshold: float = 100.0) -> QualityReport:
    """Analyze image quality (blur, contrast, skew).
    
    Args:
        pil_image: PIL Image object
        blur_threshold: Threshold for Laplacian variance below which image is considered blurry
        
    Returns:
        QualityReport with quality metrics and warnings
    """
    warnings = []
    # Convert PIL Image to OpenCV BGR format
    open_cv_image = np.array(pil_image)
    if open_cv_image.ndim == 3:
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    else:
        gray = open_cv_image

    # 1. Blur Detection using Laplacian Variance
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = blur_score < blur_threshold
    if is_blurry:
        warnings.append(f"Image appears blurry (Laplacian variance {blur_score:.1f} < {blur_threshold})")

    # 2. Contrast Check
    p5, p95 = np.percentile(gray, (5, 95))
    contrast_range = float(p95 - p5)
    is_low_contrast = contrast_range < 50.0
    if is_low_contrast:
        warnings.append(f"Image has low contrast (intensity range {contrast_range:.1f})")

    # 3. Skew Angle Estimation using Minimum Area Rectangle on Edges
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    coords = np.column_stack(np.where(edges > 0))
    skew_angle = 0.0
    if len(coords) > 10:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        skew_angle = float(angle)
        if abs(skew_angle) > 2.0:
            warnings.append(f"Detected image skew of {skew_angle:.1f} degrees")

    return QualityReport(
        blur_score=blur_score,
        is_blurry=is_blurry,
        contrast_range=contrast_range,
        is_low_contrast=is_low_contrast,
        estimated_skew_angle=skew_angle,
        warnings=warnings,
    )
