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
_QIDO_PAGE = 5000  # instances requested per QIDO page


def _list_instance_uids(session, series_url: str, headers: dict) -> List[str]:
    """Page QIDO ``/instances`` until exhausted, returning every SOPInstanceUID.

    ``offset`` advances by the count actually returned, so a server-side result
    cap (dcm4chee ``QidoMaxNumberOfResults``, unlimited in Kaapana's own config)
    can truncate a page but never the series. A missing SOPInstanceUID is a loud
    failure, never a silent skip.
    """
    uids: List[str] = []
    seen: set = set()
    offset = 0
    while True:
        qido = session.get(
            f"{series_url}/instances",
            headers=headers,
            params={"limit": _QIDO_PAGE, "offset": offset},
            timeout=_TIMEOUT,
        )
        if qido.status_code == 204:
            break
        qido.raise_for_status()
        page = qido.json()
        if not page:
            break
        added = 0
        for entry in page:
            try:
                sop_uid = entry["00080018"]["Value"][0]  # SOPInstanceUID
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(
                    f"QIDO instance listing for {series_url} has an entry without a "
                    f"SOPInstanceUID; refusing to silently drop an instance"
                ) from exc
            if sop_uid not in seen:
                seen.add(sop_uid)
                uids.append(sop_uid)
                added += 1
        offset += len(page)
        if added == 0:  # server ignored offset / only returned dups — stop, no loop
            break
    return uids


def _retrieve_instance(session, url: str, headers: dict) -> bytes:
    """WADO-RS one instance; only its bytes leave this frame, so the raw
    multipart response is freed before the caller yields."""
    from requests_toolbelt.multipart import decoder

    response = session.get(url, headers=headers, timeout=_TIMEOUT)
    response.raise_for_status()
    return decoder.MultipartDecoder.from_response(response).parts[0].content


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
    ) -> Iterator[Tuple[str, int, Iterator[bytes]]]:
        """Fetch a series one instance at a time (QIDO listing, then WADO-RS per instance).

        Bounds memory to a single instance instead of buffering the whole series
        multipart: ``requests_toolbelt`` has no streaming decoder.
        """
        import requests

        if not coordinate.series_uid:
            raise ValueError("PACS download requires a series_uid")

        base = (coordinate.pacs_id or get_settings().dicom_wadors_endpoint).rstrip("/")
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            headers["x-forwarded-access-token"] = access_token

        series_url = f"{base}/studies/{coordinate.study_uid}/series/{coordinate.series_uid}"

        with requests.Session() as session:
            uids = _list_instance_uids(session, series_url, headers)
            if not uids:
                # The dicom-web-filter answers 204 for a series outside the caller's
                # project, so "no instances" is never a successful download.
                raise RuntimeError(f"QIDO listed no instances for {series_url}")
            for sop_uid in uids:
                content = _retrieve_instance(session, f"{series_url}/instances/{sop_uid}", headers)
                yield f"{sop_uid}.dcm", len(content), iter([content])

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
                (f"--{boundary}\r\nContent-Type: application/dicom\r\nContent-Length: {len(content)}\r\n\r\n").encode()
                + content
                + b"\r\n"
            )
        if not body_parts:
            return []

        body = b"".join(body_parts) + f"--{boundary}--\r\n".encode()
        headers = {
            "Content-Type": (f'multipart/related; type="application/dicom"; boundary={boundary}'),
            "Accept": "application/dicom+json",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            headers["x-forwarded-access-token"] = access_token

        response = requests.post(f"{base}/studies", data=body, headers=headers, timeout=_TIMEOUT)
        response.raise_for_status()

        return [
            PacsCoordinate(
                pacs_id=target.pacs_id or "",
                study_uid=study_uid,
                series_uid=series_uid,
            )
            for (study_uid, series_uid) in series
        ]
