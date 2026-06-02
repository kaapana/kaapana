from __future__ import annotations

import logging
from io import BytesIO
from typing import Iterator, Optional, Tuple

from app.config import get_settings
from app.models import PacsCoordinate

from .base import StorageBackend

logger = logging.getLogger(__name__)

_TIMEOUT = 300


class PacsBackend(StorageBackend):
    """Fetch a DICOM series from a DICOMweb endpoint via WADO-RS.

    Ported (intentionally, to keep storage-api standalone) from the DICOMweb
    download logic in ``kaapanapy.helper.HelperDcmWeb``. The caller's access
    token is forwarded as a bearer so the dicom-web-filter enforces project
    scoping. Heavy deps are imported lazily so the registry imports without
    pydicom/requests installed.
    """

    store_type = "pacs"

    def fetch(
        self, coordinate: PacsCoordinate, access_token: Optional[str]
    ) -> Iterator[Tuple[str, bytes]]:
        import pydicom
        import requests
        from requests_toolbelt.multipart import decoder

        if not coordinate.series_uid:
            raise ValueError("PACS download requires a series_uid")

        base = (coordinate.pacs_id or get_settings().dicom_wadors_endpoint).rstrip("/")
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            headers["x-forwarded-access-token"] = access_token

        url = f"{base}/studies/{coordinate.study_uid}/series/{coordinate.series_uid}"
        response = requests.get(url, headers=headers, timeout=_TIMEOUT)
        response.raise_for_status()

        multipart = decoder.MultipartDecoder.from_response(response)
        for index, part in enumerate(multipart.parts):
            content = part.content
            try:
                ds = pydicom.dcmread(BytesIO(content), stop_before_pixels=True)
                name = f"{ds.SOPInstanceUID}.dcm"
            except Exception:  # noqa: BLE001 - fall back to a positional name
                name = f"instance-{index}.dcm"
            yield name, content
