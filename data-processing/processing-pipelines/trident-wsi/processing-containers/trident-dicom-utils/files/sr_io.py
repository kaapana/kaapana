"""
Build a DICOM Comprehensive 3D SR document carrying TRIDENT's tissue-mask
polygons as SCOORD3D (slide-coordinate-system) regions - a lightweight,
vector-based, QC/visualization-only representation of the segmentation.

Unlike a rasterized Parametric Map, this scales with polygon complexity, not
slide resolution - no OOM risk regardless of slide size. Nothing downstream
reads this back into the pipeline (see dag_trident_feature_extraction.py's
own comments): the real segmentation data persists via MinIO as plain
GeoJSON, and this SR exists purely so the result can be inspected in SLIM.

SLIM's dicom-microscopy-viewer does NOT treat an arbitrary SR content tree as
an annotation overlay - it specifically looks for Comprehensive 3D SR
instances structured per TID 1500 "Measurement Report", with each ROI as its
own TID 1400 "Planar ROI Measurements and Qualitative Evaluations" group
(confirmed via the Slim/highdicom papers and highdicom's own TID1500
documentation/example). A flat ContainerContentItem of raw ImageRegion3D
items (the first version of this file) built and saved without error, but
Slim reported "Annotations could not be loaded" - it never recognized the
content as a measurement report at all.

Built against highdicom's own TID1500 example
(highdicom.readthedocs.io/en/stable/tid1500.html):
MeasurementReport, ObservationContext, ObserverContext,
DeviceObserverIdentifyingAttributes, TrackingIdentifier,
PlanarROIMeasurementsAndQualitativeEvaluations, ImageRegion3D,
Comprehensive3DSR, highdicom.spatial.ImageToReferenceTransformer.
"""
import logging

import numpy as np
import geopandas as gpd
import pydicom
from pydicom.uid import generate_uid
from pydicom.sr.codedict import codes
from highdicom.sr import (
    Comprehensive3DSR,
    ImageRegion3D,
    ObservationContext,
    ObserverContext,
    DeviceObserverIdentifyingAttributes,
    SubjectContext,
    SubjectContextSpecimen,
    TrackingIdentifier,
    PlanarROIMeasurementsAndQualitativeEvaluations,
    MeasurementReport,
)
from highdicom.sr.coding import CodedConcept
from highdicom.spatial import ImageToReferenceTransformer

MANUFACTURER = "Kaapana"
logger = logging.getLogger("trident-dicom-utils")

# TRIDENT's raw tissue contours are traced at level-0 pixel resolution and can
# carry hundreds of thousands of vertices for a single boundary - far more
# detail than a QC overlay in SLIM needs or can render usefully, and encoding
# that many points into SCOORD3D GraphicData (plus geopandas/GDAL's own
# per-coordinate parsing overhead) is what was OOM-killing this step even
# though it no longer rasterizes anything. Simplify first; 5px at level-0 is
# imperceptible at any zoom level actually used for inspection.
SIMPLIFY_TOLERANCE_PX = 5.0

# SNOMED CT "Microscopy (procedure)" / "Tissue (body structure)" - real,
# standard concepts (not DICOM-context-group shortcuts in pydicom's own
# codedict, so built directly) used to fill TID 1500's required
# procedure_reported / finding_type slots; their exact meaning isn't load-
# bearing for Slim's rendering, which cares about the template structure.
PROCEDURE_REPORTED_CODE = CodedConcept(value="108252007", meaning="Microscopy", scheme_designator="SCT")
TISSUE_FINDING_CODE = CodedConcept(value="85756007", meaning="Tissue", scheme_designator="SCT")

# Explicit VR Little Endian (kept as-is - see below) uses a 2-byte length
# field for VR FL, capping any single element at 65535 bytes. GraphicData
# (0070,0022) holds 3 floats (x,y,z) per vertex * 4 bytes each, so this is
# the hard ceiling on vertices-per-region, with headroom.
_MAX_BYTES_PER_GRAPHIC_DATA = 65535
MAX_VERTICES_PER_REGION = _MAX_BYTES_PER_GRAPHIC_DATA // (3 * 4) - 100


def _build_subject_context(level0_dataset):
    """
    Slim's own SR-annotation loader (SlideViewer.tsx's addRetrievedSrRois,
    via describesSpecimenSubject in viewerUtils.ts) silently ignores any SR
    that doesn't describe a "Specimen" subject context (TID 1006/1009) - no
    error is raised, it's just dropped, which is exactly what happened the
    previous attempt: retrieval succeeded, content structurally matched
    TID1500/1410, but nothing rendered. A real WSI DICOM instance's Specimen
    Module (ContainerIdentifier, SpecimenDescriptionSequence) carries this
    information; fall back to a fresh UID if it's ever missing.
    """
    try:
        specimen_description = level0_dataset.SpecimenDescriptionSequence[0]
        specimen_uid = str(specimen_description.SpecimenUID)
        specimen_identifier = str(getattr(specimen_description, "SpecimenIdentifier", "")) or None
    except (AttributeError, IndexError):
        specimen_uid = generate_uid()
        specimen_identifier = None
    container_identifier = str(getattr(level0_dataset, "ContainerIdentifier", "")) or None
    return SubjectContext(
        subject_class=codes.DCM.Specimen,
        subject_class_specific_context=SubjectContextSpecimen(
            uid=specimen_uid,
            identifier=specimen_identifier,
            container_identifier=container_identifier,
        ),
    )


def _iter_polygons(geom):
    """
    Yields plain Polygons out of geom, which may itself be a Polygon, a
    MultiPolygon (TRIDENT's mask_to_gdf commonly produces one feature per
    mask whose geometry is a single MultiPolygon covering every disjoint
    tissue blob), or a GeometryCollection.
    """
    geom_type = geom.geom_type
    if geom_type == "Polygon":
        yield geom
    elif geom_type in ("MultiPolygon", "GeometryCollection"):
        for sub in geom.geoms:
            yield from _iter_polygons(sub)
    else:
        logger.warning("Skipping unsupported geometry type %r", geom_type)


def build_tissue_region_sr(
    gdf: gpd.GeoDataFrame,
    level0_dataset: pydicom.Dataset,
    series_number: int = 301,
    instance_number: int = 1,
) -> pydicom.Dataset:
    """
    :param gdf: TRIDENT's tissue-mask GeoDataFrame, polygon coordinates in
        level-0 pixel space (confirmed by reading TRIDENT's own source:
        WSI.segment_tissue always passes contour_scale=1/mpp_reduction_factor
        into mask_to_gdf, which makes the saved GeoJSON coordinates land in
        plain level-0 pixel space regardless of the magnification segmentation
        ran at internally).
    :param level0_dataset: full dataset (incl. SharedFunctionalGroupsSequence,
        TotalPixelMatrixOriginSequence, ImageOrientationSlide, FrameOfReferenceUID)
        of the WSI's level-0 (highest-resolution) pyramid instance.
    """
    shared = level0_dataset.SharedFunctionalGroupsSequence[0]
    pixel_spacing = shared.PixelMeasuresSequence[0].PixelSpacing
    origin = level0_dataset.TotalPixelMatrixOriginSequence[0]
    image_position = [
        float(origin.XOffsetInSlideCoordinateSystem),
        float(origin.YOffsetInSlideCoordinateSystem),
        0.0,
    ]
    image_orientation = [float(v) for v in level0_dataset.ImageOrientationSlide]
    frame_of_reference_uid = str(level0_dataset.FrameOfReferenceUID)

    transformer = ImageToReferenceTransformer(
        image_position=image_position,
        image_orientation=image_orientation,
        pixel_spacing=[float(pixel_spacing[0]), float(pixel_spacing[1])],
    )

    raw_vertex_count = sum(len(g.exterior.coords) for geom in gdf.geometry for g in _iter_polygons(geom))
    logger.info("Tissue mask: %d raw exterior vertices before simplification", raw_vertex_count)

    # One TID 1400 Planar ROI group per disjoint tissue polygon - a group can
    # only reference a single region, so a MultiPolygon mask (TRIDENT's usual
    # output: one feature covering every disjoint tissue blob) becomes several
    # groups, not one group with several regions.
    groups = []
    total_vertex_count = 0
    for geom in gdf.geometry:
        for poly in _iter_polygons(geom):
            simplified = poly.simplify(SIMPLIFY_TOLERANCE_PX, preserve_topology=True)
            if simplified.is_empty:
                continue
            # Exterior ring only - SCOORD3D POLYGON graphic type doesn't carry a
            # separate "holes" concept; sufficient for a QC/visualization overlay.
            coords = np.array(simplified.exterior.coords, dtype=float)

            # A single very large/complex tissue blob can still exceed the
            # per-element byte budget even after the baseline simplification
            # above (this is exactly what happened on the first real slide
            # tested: one polygon, 6732 vertices, 80784 bytes > 65535). Keep
            # re-simplifying with a growing tolerance until it fits, instead
            # of just picking one fixed tolerance and hoping - this guarantees
            # no future slide can blow the limit regardless of how complex its
            # tissue boundary is.
            tolerance = SIMPLIFY_TOLERANCE_PX
            while len(coords) > MAX_VERTICES_PER_REGION:
                tolerance *= 2
                simplified = poly.simplify(tolerance, preserve_topology=True)
                if simplified.is_empty:
                    break
                coords = np.array(simplified.exterior.coords, dtype=float)
            if simplified.is_empty:
                continue
            if tolerance != SIMPLIFY_TOLERANCE_PX:
                logger.info(
                    "Region needed extra simplification to fit the size budget: "
                    "tolerance %.1fpx -> %.1fpx, %d vertices",
                    SIMPLIFY_TOLERANCE_PX, tolerance, len(coords),
                )

            if not np.array_equal(coords[0], coords[-1]):
                coords = np.vstack([coords, coords[0]])
            total_vertex_count += len(coords)
            ref_coords = transformer(coords)
            region = ImageRegion3D(
                graphic_type="POLYGON",
                graphic_data=ref_coords,
                frame_of_reference_uid=frame_of_reference_uid,
            )
            groups.append(
                PlanarROIMeasurementsAndQualitativeEvaluations(
                    tracking_identifier=TrackingIdentifier(
                        uid=generate_uid(),
                        identifier=f"TridentTissueRegion{len(groups) + 1}",
                    ),
                    referenced_region=region,
                    finding_type=TISSUE_FINDING_CODE,
                )
            )
    logger.info(
        "Tissue mask: %d TID1400 groups, %d total vertices after simplification (tolerance=%.1fpx)",
        len(groups), total_vertex_count, SIMPLIFY_TOLERANCE_PX,
    )
    if not groups:
        raise ValueError("No non-empty tissue polygons left after simplification - cannot build an SR")

    observation_context = ObservationContext(
        observer_device_context=ObserverContext(
            observer_type=codes.DCM.Device,
            observer_identifying_attributes=DeviceObserverIdentifyingAttributes(
                uid=generate_uid(),
                manufacturer_name=MANUFACTURER,
                model_name="TRIDENT tissue segmentation",
            ),
        ),
        subject_context=_build_subject_context(level0_dataset),
    )

    measurement_report = MeasurementReport(
        observation_context=observation_context,
        procedure_reported=PROCEDURE_REPORTED_CODE,
        imaging_measurements=groups,
        title=codes.DCM.ImagingMeasurementReport,
    )

    sr = Comprehensive3DSR(
        evidence=[level0_dataset],
        content=measurement_report,
        series_instance_uid=generate_uid(),
        series_number=series_number,
        sop_instance_uid=generate_uid(),
        instance_number=instance_number,
        manufacturer=MANUFACTURER,
        # Matches a known-good reference SR exported by Slim itself for this
        # same test slide (CMU-1): CompletionFlag=PARTIAL, PreliminaryFlag=
        # PRELIMINARY. Also just semantically honest - this is machine-generated,
        # unreviewed output, not a completed/final human report.
        is_complete=False,
        is_final=False,
    )

    # Deliberately NOT switching to Implicit VR Little Endian here (an earlier
    # version of this function did, to dodge Explicit VR's 64KB/VR-FL ceiling on
    # GraphicData) - that produced a file that built and saved fine locally, but
    # Slim then failed with "Annotations could not be loaded", traced to Slim's
    # own SlideViewer.tsx: that message fires when the DICOMweb retrieveInstance
    # HTTP call itself fails, not when SR content parsing fails - i.e. a
    # transfer-syntax/encoding problem on retrieval, not a structural one. A
    # known-good SR exported by Slim for this same slide is Explicit VR Little
    # Endian, so staying on highdicom's default (Explicit VR Little Endian) and
    # instead guaranteeing every single region fits the 64KB budget via the
    # adaptive simplification above is the fix that doesn't risk retrieval.
    return sr
