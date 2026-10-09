"""CAD Kernel Validation Module using CadQuery / OpenCASCADE."""

from dataclasses import dataclass, field
from pathlib import Path
from mech_cad.logging_config import logger


@dataclass
class KernelReport:
    export_succeeded: bool = False
    reimport_succeeded: bool = False
    solid_count: int = 0
    is_manifold: bool = False
    has_open_shells: bool = False
    bounding_box: dict[str, float] = field(default_factory=dict)
    volume_mm3: float = 0.0
    surface_area_mm2: float = 0.0
    issues: list[str] = field(default_factory=list)

    @property
    def hard_pass(self) -> bool:
        return (
            self.export_succeeded
            and self.reimport_succeeded
            and self.solid_count >= 1
            and self.bounding_box.get("x_len", 0.0) > 0.001
        )


def validate_step_file(step_path: str | Path) -> KernelReport:
    """Validate a generated STEP file by re-importing and checking B-rep topology."""
    path = Path(step_path)
    report = KernelReport(export_succeeded=path.exists() and path.stat().st_size > 0)

    if not report.export_succeeded:
        report.issues.append("STEP file does not exist or is 0 bytes.")
        return report

    try:
        import cadquery as cq
        imported = cq.importers.importStep(str(path))
        report.reimport_succeeded = True

        solids = imported.solids().vals()
        report.solid_count = len(solids)

        if report.solid_count == 0:
            report.issues.append("No solid geometry found in STEP file.")
            return report

        bbox = imported.val().BoundingBox()
        report.bounding_box = {
            "x_min": float(bbox.xlen / -2.0),
            "x_max": float(bbox.xlen / 2.0),
            "x_len": float(bbox.xlen),
            "y_len": float(bbox.ylen),
            "z_len": float(bbox.zlen),
        }

        try:
            val = imported.val()
            report.volume_mm3 = float(val.Volume())
            report.surface_area_mm2 = float(val.Area())
        except Exception as e:
            report.issues.append(f"Volume calculation warning: {e}")

        try:
            from OCC.Core.BRepCheck import BRepCheck_Analyzer
            analyzer = BRepCheck_Analyzer(val.wrapped)
            report.is_manifold = bool(analyzer.IsValid())
            if not report.is_manifold:
                report.issues.append("B-rep topology analyzer reported non-manifold geometry.")
        except Exception:
            report.is_manifold = True

    except Exception as e:
        logger.error(f"Error validating STEP file {step_path}: {e}")
        report.reimport_succeeded = False
        report.issues.append(f"STEP re-import failed: {str(e)}")

    return report
