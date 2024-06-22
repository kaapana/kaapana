from fastapi import APIRouter
from ..clients import minio_client, opensearch_client
from pydicom import dcmread
from fastapi import File, UploadFile, HTTPException
from typing import List, Dict
import io

router = APIRouter()


async def store_dicom_file(study_id, series_id, instance_id, file_content):
    bucket_name = f"study-{study_id}"
    object_name = f"series-{series_id}/instance-{instance_id}.dcm"
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    minio_client.put_object(
        bucket_name, object_name, io.BytesIO(file_content), len(file_content)
    )


async def index_dicom_metadata(metadata: Dict):
    opensearch_client.index(index="dicom-metadata", body=metadata)


def extract_dicom_metadata(dataset) -> Dict:
    metadata = {}
    for elem in dataset:
        if elem.VR == "SQ":  # Skip sequences
            continue
        if elem.tag.is_private:  # Skip private tags
            continue
        tag_name = elem.name.replace(" ", "")
        metadata[tag_name] = str(elem.value)
    return metadata


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(files: List[UploadFile] = File(...)):
    for file in files:
        content = await file.read()
        dataset = dcmread(io.BytesIO(content))

        study_id = dataset.StudyInstanceUID
        series_id = dataset.SeriesInstanceUID
        instance_id = dataset.SOPInstanceUID

        await store_dicom_file(study_id, series_id, instance_id, content)

        metadata = extract_dicom_metadata(dataset)
        metadata.update(
            {
                "type": "instance",
                "studyID": study_id,
                "seriesID": series_id,
                "instanceID": instance_id,
            }
        )

        await index_dicom_metadata(metadata)

    return {"status": "success"}


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(study: str, files: List[UploadFile] = File(...)):
    for file in files:
        content = await file.read()
        dataset = dcmread(io.BytesIO(content))

        study_id = dataset.StudyInstanceUID
        if study_id != study:
            raise HTTPException(status_code=400, detail="StudyInstanceUID mismatch.")

        series_id = dataset.SeriesInstanceUID
        instance_id = dataset.SOPInstanceUID

        await store_dicom_file(study_id, series_id, instance_id, content)

        metadata = extract_dicom_metadata(dataset)
        metadata.update(
            {
                "type": "instance",
                "studyID": study_id,
                "seriesID": series_id,
                "instanceID": instance_id,
            }
        )

        await index_dicom_metadata(metadata)

    return {"status": "success"}