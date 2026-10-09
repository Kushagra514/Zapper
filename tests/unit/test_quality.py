"""Unit tests for OpenCV Drawing Quality Assessor."""

from PIL import Image
from mech_cad.drawing.quality import assess_quality


def test_quality_assessment_clean_image():
    # Create synthetic sharp high-contrast image
    img = Image.new("RGB", (200, 200), color="white")
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (0, 0, 0))

    report = assess_quality(img)
    assert report.blur_score > 0
    assert report.contrast_range > 100.0
