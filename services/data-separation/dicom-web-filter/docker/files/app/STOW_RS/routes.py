import io
import json
import logging
import re
from uuid import UUID

import httpx
import pydicom
from app import config, crud
from app.database import get_session
from app.utils import (
    assert_project_not_archived,
    get_default_project_id,
    get_selected_project_id,
    get_project_short_id_by_id,
    get_user_project_ids,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def __stream_data(request: Request, url: str = "/studies"):
    """Stream the data to the DICOMWeb server.

    Args:
        request (Request): Request object
        url (str, optional): URL to send the request to. Defaults to "/studies".

    """

    async def data_streamer():
        async for chunk in request.stream():
            yield chunk

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{config.DICOMWEB_BASE_URL}/{url}",
            content=data_streamer(),
            headers=dict(request.headers),
        ) as response:
            response.raise_for_status()


async def __forward_to_ctp(body: bytes, headers: dict, url: str = "studies"):
    """Forward a buffered STOW-RS request to the CTP DicomSTOWRSImportService.

    Args:
        body (bytes): Buffered request body (multipart/related DICOM)
        headers (dict): Original request headers
        url (str, optional): URL path to send the request to. Defaults to "studies".
    """
    forward_headers = {
        k: v for k, v in headers.items() if k.lower() in ("content-type", "accept")
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            f"{config.CTP_DICOMWEB_URL}/{url}",
            content=body,
            headers=forward_headers,
        )
        response.raise_for_status()


def _extract_boundary(content_type: str) -> bytes | None:
    """Extract the multipart boundary bytes from a Content-Type header value."""
    match = re.search(r"boundary=([^\s;]+)", content_type or "", re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip('"').encode()


def _split_mime_part(stripped: bytes) -> tuple[bytes, bytes] | None:
    """Split a stripped multipart segment into (mime_headers, dicom_bytes).

    Returns None if no header separator is found or the DICOM payload is empty.
    """
    if b"\r\n\r\n" in stripped:
        mime_headers, dicom_bytes = stripped.split(b"\r\n\r\n", 1)
    elif b"\n\n" in stripped:
        mime_headers, dicom_bytes = stripped.split(b"\n\n", 1)
    else:
        return None
    dicom_bytes = dicom_bytes.rstrip(b"\r\n")
    if not dicom_bytes:
        return None
    return mime_headers, dicom_bytes


def extract_uids_from_multipart(body: bytes, content_type: str) -> dict[str, str]:
    """Parse a multipart/related DICOM body and return {series_uid: study_uid} for each part.

    Args:
        body (bytes): Raw multipart request body
        content_type (str): Content-Type header (must contain boundary parameter)

    Returns:
        dict[str, str]: Mapping of SeriesInstanceUID → StudyInstanceUID
    """
    boundary = _extract_boundary(content_type)
    if not boundary:
        logger.warning(
            "Could not parse multipart boundary from Content-Type: %s", content_type
        )
        return {}

    result: dict[str, str] = {}
    for part in body.split(b"--" + boundary):
        parsed = _split_mime_part(part.strip(b"\r\n"))
        if parsed is None:
            continue
        _, dicom_bytes = parsed
        try:
            ds = pydicom.dcmread(io.BytesIO(dicom_bytes), stop_before_pixels=True)
            result[str(ds.SeriesInstanceUID)] = str(ds.StudyInstanceUID)
        except Exception as e:
            logger.warning("Failed to parse DICOM part: %s", e)

    return result


def _dataset_name_from_referer(request: Request) -> str:
    """Derive a kp-prefixed dataset name from the browser Referer header.

    LocalDcm2JsonOperator strips the 'kp-' prefix, so 'kp-Annotations (SLIM)'
    becomes the dataset label 'Annotations (SLIM)' in the Kaapana UI.
    """
    referer = request.headers.get("referer", "")
    if "/slim" in referer:
        return "kp-Annotations (SLIM)"
    if "/ohif" in referer:
        return "kp-Annotations (OHIF)"
    return "dicom-web"


def enrich_dicom_parts_with_project(
    body: bytes,
    content_type: str,
    project_short_id: str,
    dataset_name: str = "dicom-web",
) -> bytes:
    """Re-encode each DICOM part in the multipart body with project and dataset tags set.

    This ensures that the downstream ingestion DAG (service-process-incoming-dcm)
    can correctly assign the new series to the right project via
    LocalAssignDataToProjectOperator, which reads tag (0012,0020), and to the
    right dataset via LocalAddToDatasetOperator, which reads tag (0012,0010).

    Args:
        body (bytes): Raw multipart/related request body
        content_type (str): Content-Type header (must contain boundary parameter)
        project_short_id (str): Kaapana project short_id to write into tag (0012,0020)
        dataset_name (str): Dataset name to write into tag (0012,0010). Defaults to "dicom-web".

    Returns:
        bytes: Multipart body with ClinicalTrialProtocolID and ClinicalTrialSponsorName
               injected into every part. Returns the original body unchanged if the
               boundary cannot be parsed or if an individual part fails to re-encode.
    """
    boundary = _extract_boundary(content_type)
    if not boundary:
        return body

    delimiter = b"--" + boundary
    parts = body.split(delimiter)
    new_parts = []

    for part in parts:
        parsed = _split_mime_part(part.strip(b"\r\n"))
        if parsed is None:
            new_parts.append(part)
            continue
        mime_headers, dicom_bytes = parsed
        try:
            ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
            ds.ClinicalTrialProtocolID = (
                project_short_id  # (0012,0020) → project assignment
            )
            ds.ClinicalTrialSponsorName = dataset_name  # (0012,0010) → dataset name
            buf = io.BytesIO()
            ds.save_as(buf)
            new_parts.append(
                b"\r\n" + mime_headers + b"\r\n\r\n" + buf.getvalue() + b"\r\n"
            )
        except Exception as e:
            logger.warning("Failed to enrich DICOM part with project context: %s", e)
            new_parts.append(part)

    return delimiter.join(new_parts)


async def __map_dicom_series_to_project(
    session: AsyncSession,
    request: Request,
    project_id: UUID,
):
    """Map the dicom series to the project. This is done by adding the dicom series to the database and mapping it to the project.

    Args:
        session (AsyncSession): Database session
        request (Request): Request object

    """
    logger.info(
        project_id
    )  # Extract the 'clinical_trial_protocol_info' query parameter
    # This parameter was set in the dcmweb helper
    clinical_trial_protocol_info = json.loads(
        request.query_params.get("clinical_trial_protocol_info")
    )

    for series_instance_uid in clinical_trial_protocol_info:
        # Add the dicom data to the database
        try:
            await crud.add_dicom_data(
                session,
                series_instance_uid=series_instance_uid,
                study_instance_uid=clinical_trial_protocol_info[series_instance_uid][
                    "study_instance_uid"
                ],
                description="Dicom data",
            )
        except IntegrityError as e:
            await session.rollback()
            logger.warning(f"{series_instance_uid=} already exists in the database")

        # Map the dicom data to the project
        try:
            await crud.add_data_project_mapping(
                session,
                series_instance_uid=series_instance_uid,
                project_id=project_id,
            )
        except IntegrityError as e:
            await session.rollback()
            logger.warning(
                f"{series_instance_uid=} already exists in the project mapping"
            )


async def __map_viewer_series_to_project(
    session: AsyncSession,
    series_info: dict[str, str],
    project_id: UUID,
) -> None:
    """Map viewer-created DICOM series to the project selected in the Kaapana UI.

    Args:
        session (AsyncSession): Database session
        series_info (dict[str, str]): Mapping of SeriesInstanceUID → StudyInstanceUID
        project_id (UUID): Target project UUID (from the Project cookie)
    """
    for series_uid, study_uid in series_info.items():
        try:
            await crud.add_dicom_data(
                session,
                series_instance_uid=series_uid,
                study_instance_uid=study_uid,
                description="Dicom data",
            )
        except IntegrityError:
            await session.rollback()
            logger.warning(f"{series_uid=} already exists in the database")

        try:
            await crud.add_data_project_mapping(
                session,
                series_instance_uid=series_uid,
                project_id=project_id,
            )
        except IntegrityError:
            await session.rollback()
            logger.warning(f"{series_uid=} already mapped to project {project_id}")


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(
    request: Request,
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Depends(get_default_project_id),
):
    """Store DICOM instances in the DICOMWeb server.

    Path A – clinical_trial_protocol_info present (Kaapana upload helper):
        Series are mapped to the project via the query param, then the data is
        streamed directly to dcm4chee.

    Path B – clinical_trial_protocol_info absent (OHIF / SLIM viewer):
        The request body is buffered, UIDs are parsed from the DICOM payload,
        the new series is mapped to the same project(s) as the parent study,
        and the data is forwarded to CTP's DicomSTOWRSImportService so that
        the service-process-incoming-dcm ingestion DAG is triggered.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """
    await assert_project_not_archived(project_id)

    if "clinical_trial_protocol_info" in request.query_params:
        await __map_dicom_series_to_project(session, request, project_id)
        await __stream_data(request, url="studies")
    else:
        viewer_project_id = get_selected_project_id(request)
        if viewer_project_id is None:
            raise HTTPException(
                status_code=400,
                detail="No project selected. Please select a project in the Kaapana UI before saving annotations.",
            )
        if viewer_project_id not in get_user_project_ids(request):
            raise HTTPException(
                status_code=403,
                detail="User does not have access to the selected project.",
            )
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        series_info = extract_uids_from_multipart(body, content_type)
        await __map_viewer_series_to_project(session, series_info, viewer_project_id)
        project_short_id = await get_project_short_id_by_id(viewer_project_id)
        if project_short_id is None:
            raise HTTPException(
                status_code=500,
                detail="Could not resolve project short_id for DICOM tagging.",
            )
        enriched = enrich_dicom_parts_with_project(
            body,
            content_type,
            project_short_id=project_short_id,
            dataset_name=_dataset_name_from_referer(request),
        )
        await __forward_to_ctp(enriched, dict(request.headers), url="studies")

    return Response(status_code=200)


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(
    study: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Depends(get_default_project_id),
):
    """Store DICOM instances into a specific study (see store_instances for path details).

    Args:
        study (str): StudyInstanceUID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        Response: Response object
    """
    await assert_project_not_archived(project_id)

    if "clinical_trial_protocol_info" in request.query_params:
        await __map_dicom_series_to_project(session, request, project_id)
        await __stream_data(request, url=f"studies/{study}")
    else:
        viewer_project_id = get_selected_project_id(request)
        if viewer_project_id is None:
            raise HTTPException(
                status_code=400,
                detail="No project selected. Please select a project in the Kaapana UI before saving annotations.",
            )
        if viewer_project_id not in get_user_project_ids(request):
            raise HTTPException(
                status_code=403,
                detail="User does not have access to the selected project.",
            )
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        series_info = extract_uids_from_multipart(body, content_type)
        await __map_viewer_series_to_project(session, series_info, viewer_project_id)
        project_short_id = await get_project_short_id_by_id(viewer_project_id)
        if project_short_id is None:
            raise HTTPException(
                status_code=500,
                detail="Could not resolve project short_id for DICOM tagging.",
            )
        enriched = enrich_dicom_parts_with_project(
            body,
            content_type,
            project_short_id=project_short_id,
            dataset_name=_dataset_name_from_referer(request),
        )
        await __forward_to_ctp(enriched, dict(request.headers), url=f"studies/{study}")

    return Response(status_code=200)
