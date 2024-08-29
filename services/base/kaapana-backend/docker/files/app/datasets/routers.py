from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import JSONResponse

from app.datasets.utils import (
    get_metadata,
    execute_opensearch_query,
    get_field_mapping,
)
from app.dependencies import get_opensearch

router = APIRouter(tags=["datasets"])


@router.post("/tag")
async def tag_data(data: list = Body(...), os_client=Depends(get_opensearch)):
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
        doc = os_client.get(index="meta-index", id=series_instance_uid)
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
        os_client.update(index="meta-index", id=series_instance_uid, body=body)

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
async def get_series(data: dict = Body(...), os_client=Depends(get_opensearch)):
    import pandas as pd

    structured: bool = data.get("structured", False)
    query: dict = data.get("query", {"query_string": {"query": "*"}})

    if structured:
        hits = execute_opensearch_query(
            os_client,
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
            [d["_id"] for d in execute_opensearch_query(os_client, query)]
        )


@router.get("/series/{series_instance_uid}")
async def get_data(series_instance_uid, os_client=Depends(get_opensearch)):
    metadata = await get_metadata(os_client, series_instance_uid)

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
async def get_dashboard(config: dict = Body(...), os_client=Depends(get_opensearch)):
    series_instance_uids = config.get("series_instance_uids")
    names = config.get("names", [])

    name_field_map = await get_field_mapping(os_client)
    filtered_name_field_map = {
        name: name_field_map[name] for name in names if name in name_field_map
    }

    res = os_client.search(
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


async def get_all_values(os_client, item_name, query):
    name_field_map = await get_field_mapping(os_client)

    item_key = name_field_map.get(item_name)
    if not item_key:
        return {}  # todo: maybe better default

    item = os_client.search(
        body={
            "size": 0,
            # {"query":"D","field":"00000000 Tags_keyword.keyword","boolFilter":[]}
            "query": query,  # {"query": {"ids": {"values": series_instance_uids}}}
            "aggs": {item_name: {"terms": {"field": item_key, "size": 10000}}},
        }
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
    field_name: str, query: dict = Body(...), os_client=Depends(get_opensearch)
):
    if not query or query == {}:
        query = {"query_string": {"query": "*"}}

    return JSONResponse(await get_all_values(os_client, field_name, query))


@router.get("/field_names")
async def get_field_names(os_client=Depends(get_opensearch)):
    return JSONResponse(list((await get_field_mapping(os_client)).keys()))


@router.get("/fields")
async def get_fields(
    index: str = "meta-index", field: str = None, os_client=Depends(get_opensearch)
):
    mapping = await get_field_mapping(os_client, index)
    if field:
        return JSONResponse(mapping[field])
    else:
        return JSONResponse(mapping)
