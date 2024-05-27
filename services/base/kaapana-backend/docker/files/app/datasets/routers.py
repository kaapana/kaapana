from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from app.dependencies import get_opensearch

router = APIRouter(tags=["datasets"])


@router.post("/tag")
async def tag_data(data: list = Body(...), opensearchClient=Depends(get_opensearch)):
    try:
        for series in data:
            opensearchClient.tagging(
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
async def get_series(data: dict = Body(...), opensearchClient=Depends(get_opensearch)):
    import pandas as pd

    structured: bool = data.get("structured", False)
    query: dict = data.get("query", {"query_string": {"query": "*"}})

    if structured:
        hits = opensearchClient.aggregate_search_results(
            query=query,
            source={
                "includes": [
                    "00100020 PatientID_keyword",
                    "0020000D StudyInstanceUID_keyword",
                    "0020000E SeriesInstanceUID_keyword",
                ]
            },
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
    elif not structured:
        return JSONResponse(
            [d["_id"] for d in opensearchClient.aggregate_search_results(query)]
        )


@router.get("/series/{series_instance_uid}")
async def get_data(series_instance_uid, opensearchClient=Depends(get_opensearch)):
    metadata = await opensearchClient.get_sanitized_metadata(series_instance_uid)

    modality = metadata["Modality"]

    if modality in ["SEG", "RTSTRUCT"]:
        # TODO: We could actually check if this file already exists.
        #  If not, we could either point to the default dcm4chee thumbnail or trigger the process

        path = f"batch/{series_instance_uid}/generate-segmentation-thumbnail/{series_instance_uid}.png"
        thumbnail_src = f"/thumbnails/{path}"
    else:
        thumbnail_src = (
            f"/dcm4chee-arc/aets/KAAPANA/rs/studies/{metadata['Study Instance UID']}/"
            f"series/{series_instance_uid}/thumbnail?viewport=300,300"
        )
    return JSONResponse(dict(metadata=metadata, thumbnail_src=thumbnail_src))


# This should actually be a get request but since the body is too large for a get request
# we use a post request
@router.post("/dashboard")
async def get_dashboard(
    config: dict = Body(...), opensearchClient=Depends(get_opensearch)
):
    series_instance_uids = config.get("series_instance_uids")
    names = config.get("names", [])

    name_field_map = await opensearchClient.get_field_mapping()
    filtered_name_field_map = {
        name: name_field_map[name] for name in names if name in name_field_map
    }

    res = opensearchClient.search(
        body={
            "size": 0,
            **(
                {"query": {"ids": {"values": series_instance_uids}}}
                if series_instance_uids
                else {}
            ),
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
        }
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


@router.post("/query_values/{field_name}")
async def get_query_values_item(
    field_name: str, query: dict = Body(...), opensearchClient=Depends(get_opensearch)
):
    if not query or query == {}:
        query = {"query_string": {"query": "*"}}

    return JSONResponse(await opensearchClient.get_values_of_field(field_name, query))


@router.get("/field_names")
async def get_field_names(opensearchClient=Depends(get_opensearch)):
    return JSONResponse(list((await opensearchClient.get_field_mapping()).keys()))


@router.get("/fields")
async def get_fields(
    index: str = "meta-index",
    field: str = None,
    opensearchClient=Depends(get_opensearch),
):
    mapping = await opensearchClient.get_field_mapping()
    if field:
        return JSONResponse(mapping[field])
    else:
        return JSONResponse(mapping)
