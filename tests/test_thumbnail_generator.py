import sys
from pathlib import Path
from unittest.mock import MagicMock

import pydicom
import pytest
from pydicom.uid import ExplicitVRLittleEndian

np = pytest.importorskip("numpy")
pytest.importorskip("PIL")

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "data-processing/kaapana-plugin/processing-containers"
        / "thumbnail-generator/files"
    ),
)
# Container-only dependencies that the palette path does not use.
sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("kaapanapy", MagicMock())
sys.modules.setdefault("kaapanapy.logger", MagicMock())

from generic import _convert_palette


def test_palette_color_decodes_16_bit_ow_lut():
    ds = pydicom.Dataset()
    ds.file_meta = pydicom.dataset.FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.is_little_endian, ds.is_implicit_VR = True, False
    ds.PhotometricInterpretation = "PALETTE COLOR"
    ds.Rows, ds.Columns, ds.SamplesPerPixel = 1, 2, 1
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 8, 8, 7, 0
    ds.PixelData = bytes([0, 1])
    for color, lut in (("Red", [0, 65535]), ("Green", [0, 0]), ("Blue", [65535, 0])):
        setattr(ds, f"{color}PaletteColorLookupTableDescriptor", [2, 0, 16])
        lut_bytes = np.array(lut, "<u2").tobytes()
        setattr(ds, f"{color}PaletteColorLookupTableData", lut_bytes)

    img = _convert_palette(ds)

    assert [img.getpixel((0, 0)), img.getpixel((1, 0))] == [(0, 0, 255), (255, 0, 0)]
