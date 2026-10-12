from __future__ import annotations

from typing import Any, Tuple, Union

import numpy as np
from PIL import Image
from wsidicom import WsiDicom

from trident.wsi_objects.WSI import WSI, ReadMode


class DicomWSI(WSI):
    """
    TRIDENT WSI reader backend for a local directory of DICOM WSI (VL Whole Slide
    Microscopy Image) instances, via `wsidicom` (https://github.com/imi-bigpicture/wsidicom).

    Not part of upstream TRIDENT - added by the Kaapana `trident` processing-container
    build (see dicom_wsi_patch/apply_patch.py) because TRIDENT itself has no DICOM reader.

    `slide_path` must be a local directory containing exactly one WSI instance set
    (i.e. the Kaapana batch-element directory a GetInputOperator already downloaded
    the series' .dcm files into) - not a single file path like the other backends.

    NOTE: implemented against the documented wsidicom public API (WsiDicom.open /
    .levels / .read_region / .read_thumbnail / .close). Verify attribute names against
    the exact wsidicom version pinned in requirements.txt the first time this is run
    against a real DICOM WSI series (see the integration plan's "primary technical risk").
    """

    def __init__(self, slide_path: str, **kwargs: Any) -> None:
        super().__init__(slide_path, **kwargs)

    def _lazy_initialize(self) -> None:
        super()._lazy_initialize()

        if not self._initialized:
            self.img = WsiDicom.open(self.slide_path)

            base_level = self.img.levels.base_level
            self.width, self.height = base_level.size.width, base_level.size.height
            self.dimensions = (self.width, self.height)

            levels_sorted = sorted(self.img.levels, key=lambda lvl: lvl.size.width, reverse=True)
            self.level_count = len(levels_sorted)
            self.level_dimensions = [(lvl.size.width, lvl.size.height) for lvl in levels_sorted]
            self.level_downsamples = [
                self.width / dim[0] for dim in self.level_dimensions
            ]
            self.properties = {}

            if self.mpp is None:
                self.mpp = self._fetch_mpp(self.custom_mpp_keys)
            self.mag = self._fetch_magnification(self.custom_mpp_keys)
            self._initialized = True

    def _fetch_mpp(self, custom_mpp_keys=None) -> float:
        """
        Pixel spacing of the base (highest-resolution) level, in mm/pixel per the
        DICOM Pixel Spacing attribute as surfaced by wsidicom, converted to microns/pixel.
        """
        base_level = self.img.levels.base_level
        pixel_spacing_mm = base_level.pixel_spacing.width
        return round(pixel_spacing_mm * 1000, 4)

    def read_region(
        self,
        location: Tuple[int, int],
        level: int,
        size: Tuple[int, int],
        read_as: ReadMode = "pil",
    ) -> Union[Image.Image, np.ndarray]:
        """
        `location` arrives in level-0 (base resolution) pixel coordinates, matching
        the openslide/TRIDENT convention used throughout the rest of the codebase.

        wsidicom's own `read_region` does NOT share that convention: its internal
        scale_factor = 2**(level_to - wsi_level.level) multiplies `location`/`size`
        as given, which only makes sense if they're already expressed in the
        TARGET level's own pixel grid - not level-0's. Passing level-0 coordinates
        straight through (as originally written here) made every read at any
        non-zero level silently request out-of-bounds regions outside that level's
        much smaller extent, caught by the `except` below and returned as a black
        tile - except for the tiny corner where level-0 coordinates happened to
        also be valid coordinates within the target level's own small extent.
        Converting location by the level's downsample factor fixes this.
        """
        downsample = self.level_downsamples[level]
        level_location = (round(location[0] / downsample), round(location[1] / downsample))
        try:
            region = self.img.read_region(level_location, level, size).convert("RGB")
        except Exception:
            region = Image.new("RGB", size, (0, 0, 0))

        if read_as == "pil":
            return region
        elif read_as == "numpy":
            return np.array(region)
        else:
            raise ValueError(f"Invalid `read_as` value: {read_as}. Must be 'pil', 'numpy'.")

    def get_dimensions(self) -> Tuple[int, int]:
        return self.dimensions

    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        return self.img.read_thumbnail(size).convert("RGB")

    def close(self) -> None:
        if getattr(self, "img", None) is not None:
            self.img.close()
