import base64

from app.datasets import utils
from app.dependencies import get_minio, get_opensearch, get_project_index
from app.middlewares import sanitize_inputs
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from minio.error import S3Error
from starlette.responses import StreamingResponse
import json

router = APIRouter(tags=["datasets"])


@router.post("/tag")
async def tag_data(
    data: list = Body(...),
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    from typing import List

    def tagging(
        os_client,
        series_instance_uid: str,
        tags: List[str],
        tags2add: List[str] = [],
        tags2delete: List[str] = [],
    ):
        print(series_instance_uid)
        print(f"Tags 2 add: {tags2add}")
        print(f"Tags 2 delete: {tags2delete}")

        # Read Tags
        doc = os_client.get(index=project_index, id=series_instance_uid)
        print(doc)
        index_tags = doc["_source"].get("00000000 Tags_keyword", [])

        final_tags = list(
            set(tags)
            .union(set(index_tags))
            .difference(set(tags2delete))
            .union(set(tags2add))
        )
        print(f"Final tags: {final_tags}")

        # Write Tags back
        body = {"doc": {"00000000 Tags_keyword": final_tags}}
        os_client.update(index=project_index, id=series_instance_uid, body=body)

    try:
        for series in data:
            tagging(
                os_client,
                series["series_instance_uid"],
                series["tags"],
                series["tags2add"],
                series["tags2delete"],
            )
        return JSONResponse({})

    except Exception as e:
        print("ERROR!")
        raise HTTPException(500, e)


# This should actually be a get request but since the body is too large for a get request
# we use a post request
@router.post("/series")
async def get_series(
    data: dict = Body(...),
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    import pandas as pd

    structured: bool = data.get("structured", False)
    query: dict = data.get("query", {"query_string": {"query": "*"}})
    page_index: int = data.get("pageIndex", 1)
    page_length: int = data.get("pageLength", 1000)
    aggregated_series_num: int = data.get("aggregatedSeriesNum", 1)
    sort_param: str = data.get("sort", "00000000 TimestampArrived_datetime")
    sort_direction: str = data.get("sortDirection", "desc").lower()
    use_execute_sliced_search: bool = data.get("executeSlicedSearch", False)

    if sort_direction not in ["asc", "desc"]:
        sort_direction = "desc"
    sort = [{sort_param: sort_direction}]

    # important! only add source if needed, otherwise the hole datastructure is returned
    source = False
    if structured:
        source = {
            "includes": [
                "00100020 PatientID_keyword",
                "0020000D StudyInstanceUID_keyword",
                "0020000E SeriesInstanceUID_keyword",
            ]
        }

    hits = utils.execute_initial_search(
        os_client,
        project_index,
        query,
        source,
        sort,
        page_index,
        page_length,
        aggregated_series_num,
        use_execute_sliced_search,
    )
    if structured:
        if aggregated_series_num > page_length:
            # The results have to be reorderd according to the patients,
            # otherwise patients are not completed (because they can be on another page)
            hits = utils.requery_and_fill_missing_series_for_patients(
                os_client, project_index, query, source, sort, page_length, hits
            )

        res_array = [
            [
                hit["_source"].get("00100020 PatientID_keyword") or "N/A",
                hit["_source"]["0020000D StudyInstanceUID_keyword"],
                hit["_source"]["0020000E SeriesInstanceUID_keyword"],
            ]
            for hit in hits
        ]

        df = pd.DataFrame(
            res_array,
            columns=["Patient ID", "Study Instance UID", "Series Instance UID"],
        )
        return JSONResponse(
            {
                k: f.groupby("Study Instance UID")["Series Instance UID"]
                .apply(list)
                .to_dict()
                for k, f in df.groupby("Patient ID")
            }
        )
    else:
        return JSONResponse([d["_id"] for d in hits])


# This should actually be a get request but since the body is too large for a get request
# we use a post request
# sepcific function, to get a often needed aggregation request
@router.post("/aggregatedSeriesNum")
async def get_aggregatedSeriesNum(
    data: dict = Body(...),
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    query: dict = data.get("query", {"query_string": {"query": "*"}})
    res = os_client.search(
        index=project_index,
        body={
            "size": 0,
            "query": query,
            "aggs": {
                "Series": {
                    "cardinality": {
                        "field": "0020000E SeriesInstanceUID_keyword.keyword",
                    }
                },
            },
            "_source": False,
        },
    )["aggregations"]["Series"]["value"]

    return JSONResponse(res)


@router.get("/series/{series_instance_uid}/thumbnail")
def get_thumbnail_png(
    request: Request,
    series_instance_uid: str,
    minioClient=Depends(get_minio),
) -> StreamingResponse:
    """Get the PNG file from the thumbnails bucket.

    Args:
        series_instance_uid (str): Series instance UID.
        minioClient (Minio): Minio client.

    Raises:
        HTTPException: If object is not found in the bucket.

    Returns:
        StreamingResponse: Streaming response of the PNG file.
    """
    project = json.loads(request.headers.get("project"))

    bucket = project["s3_bucket"]
    object_name = f"thumbnails/{series_instance_uid}.png"

    try:
        png_file = minioClient.get_object(bucket, object_name)
    except S3Error:
        raise HTTPException(status_code=404, detail="Object not found in the bucket.")

    return StreamingResponse(png_file, media_type="image/png")


@router.get("/series/{series_instance_uid}")
async def get_data(
    series_instance_uid,
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    metadata = await utils.get_metadata(os_client, project_index, series_instance_uid)
    # sanitize path params
    series_instance_uid = sanitize_inputs(series_instance_uid)
    modality = metadata["Modality"]
    # dcmweb_endpoint = metadata.get("Source Presentation Address")
    # if dcmweb_endpoint:
    #     thumbnail_src = f"/thumbnails/batch/{series_instance_uid}/external_thumbnail_operator/{series_instance_uid}.png"

    if modality in ["SEG", "RTSTRUCT"]:
        # TODO: We could actually check if this file already exists.
        #  If not, we could either point to the default dcm4chee thumbnail or trigger the process

        thumbnail_src = (
            f"/kaapana-backend/dataset/series/{series_instance_uid}/thumbnail"
        )
    else:
        thumbnail_src = (
            f"/dicom-web-filter/studies/{metadata['Study Instance UID']}/"
            f"series/{series_instance_uid}/thumbnail?viewport=300,300"
        )

    return JSONResponse(dict(metadata=metadata, thumbnail_src=thumbnail_src))


# This should actually be a get request but since the body is too large for a get request
# we use a post request
@router.post("/dashboard")
async def get_dashboard(
    config: dict = Body(...),
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    series_instance_uids = config.get("series_instance_uids")
    names = config.get("names", [])

    name_field_map = utils.get_field_mapping(os_client, project_index)
    filtered_name_field_map = {
        name: name_field_map[name] for name in names if name in name_field_map
    }

    search_query = config.get("query", {})

    if series_instance_uids:
        query = {"query": {"ids": {"values": series_instance_uids}}}
    elif search_query:
        query = {"query": search_query}
    else:
        query = {}

    res = os_client.search(
        index=project_index,
        body={
            "size": 0,
            **(query),
            "aggs": {
                "Series": {
                    "cardinality": {
                        "field": "0020000E SeriesInstanceUID_keyword.keyword",
                    }
                },
                "Studies": {
                    "cardinality": {
                        "field": "0020000D StudyInstanceUID_keyword.keyword",
                    }
                },
                "Patients": {
                    "cardinality": {
                        "field": "00100020 PatientID_keyword.keyword",
                    }
                },
                **{
                    name: {"terms": {"field": field, "size": 10000}}
                    for name, field in filtered_name_field_map.items()
                },
            },
        },
    )["aggregations"]

    histograms = {
        k: {
            "items": (
                {
                    (i["key_as_string"] if "key_as_string" in i else i["key"]): i[
                        "doc_count"
                    ]
                    # dict(
                    # text=f"{(i['key_as_string'] if 'key_as_string' in i else i['key'])}  ({i['doc_count']})",
                    # value=(
                    #     i["key_as_string"]
                    #     if "key_as_string" in i
                    #     else i["key"]
                    # ),
                    # count=i["doc_count"],
                    # )
                    for i in item["buckets"]
                }
            ),
            "key": name_field_map[k],
        }
        for k, item in res.items()
        if "buckets" in item and len(item["buckets"]) > 0
    }
    metrics = dict(
        Series=res["Series"]["value"],
        Studies=res["Studies"]["value"],
        Patients=res["Patients"]["value"],
    )
    return JSONResponse(dict(histograms=histograms, metrics=metrics))


async def get_all_values(os_client, index, item_name, query):
    name_field_map = utils.get_field_mapping(os_client, index)

    item_key = name_field_map.get(item_name)
    if not item_key:
        return {}  # todo: maybe better default

    item = os_client.search(
        index=index,
        body={
            "size": 0,
            # {"query":"D","field":"00000000 Tags_keyword.keyword","boolFilter":[]}
            "query": query,  # {"query": {"ids": {"values": series_instance_uids}}}
            "aggs": {item_name: {"terms": {"field": item_key, "size": 10000}}},
        },
    )["aggregations"][item_name]

    if "buckets" in item and len(item["buckets"]) > 0:
        return {
            "items": (
                [
                    dict(
                        text=f"{bucket.get('key_as_string', bucket['key'])}  ({bucket['doc_count']})",
                        value=bucket.get("key_as_string", bucket["key"]),
                        count=bucket["doc_count"],
                    )
                    for bucket in item["buckets"]
                ]
            ),
            "key": item_key,
        }
    else:
        return {}


@router.post("/query_values/{field_name}")
async def get_query_values_item(
    field_name: str,
    query: dict = Body(...),
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    # sanitize field_name path params
    field_name = sanitize_inputs(field_name)
    if not query or query == {}:
        query = {"query_string": {"query": "*"}}

    return JSONResponse(
        await get_all_values(os_client, project_index, field_name, query)
    )


@router.get("/field_names")
async def get_field_names(
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    return JSONResponse(
        list((utils.get_field_mapping(os_client, project_index)).keys())
    )


@router.get("/fields")
async def get_fields(
    field: str = None,
    os_client=Depends(get_opensearch),
    project_index=Depends(get_project_index),
):
    mapping = utils.get_field_mapping(os_client, project_index)
    if field:
        return JSONResponse(mapping[field])
    else:
        return JSONResponse(mapping)
