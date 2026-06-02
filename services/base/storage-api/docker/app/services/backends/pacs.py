from __future__ import annotations

import logging
import uuid
from io import BytesIO
from typing import Iterable, Iterator, List, Optional, Tuple

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

    def store(
        self,
        target,
        files: Iterable[Tuple[str, bytes]],
        access_token: Optional[str],
    ) -> List[PacsCoordinate]:
        """STOW-RS the DICOM instances and return one coordinate per series.

        Builds a ``multipart/related; type="application/dicom"`` body (the
        STOW-RS contract) and POSTs to ``{base}/studies``. The Study/Series UIDs
        are read from the instances so the returned coordinates resolve on a
        later WADO-RS fetch.
        """
        import pydicom
        import requests

        base = (target.pacs_id or get_settings().dicom_stowrs_endpoint).rstrip("/")

        boundary = uuid.uuid4().hex
        body_parts: List[bytes] = []

        series: "dict[Tuple[str, str], None]" = {}
        for filename, content in files:
            ds = pydicom.dcmread(BytesIO(content), stop_before_pixels=True)
            series.setdefault((str(ds.StudyInstanceUID), str(ds.SeriesInstanceUID)))
            body_parts.append(
                (
                    f"--{boundary}\r\n"
                    f"Content-Type: application/dicom\r\n"
                    f"Content-Length: {len(content)}\r\n\r\n"
                ).encode()
                + content
                + b"\r\n"
            )
        if not body_parts:
            return []

        body = b"".join(body_parts) + f"--{boundary}--\r\n".encode()
        headers = {
            "Content-Type": (
                f'multipart/related; type="application/dicom"; boundary={boundary}'
            ),
            "Accept": "application/dicom+json",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            headers["x-forwarded-access-token"] = access_token

        response = requests.post(
            f"{base}/studies", data=body, headers=headers, timeout=_TIMEOUT
        )
        response.raise_for_status()

        return [
            PacsCoordinate(
                pacs_id=target.pacs_id or "",
                study_uid=study_uid,
                series_uid=series_uid,
            )
            for (study_uid, series_uid) in series
        ]
