import json
from typing import Dict, List
import re
import ast
from typing import Union
import base64
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from opensearchpy import OpenSearch

from app.config import settings
from app.datasets.utils import (
    get_metadata,
    execute_opensearch_query,
    get_field_mapping,
    camel_case_to_space
)
from app.middlewares import sanitize_inputs

router = APIRouter(tags=["datasets"])


@router.post("/tag")
async def tag_data(data: list = Body(...)):
    from typing import List

    def tagging(
        series_instance_uid: str,
        tags: List[str],
        tags2add: List[str] = [],
        tags2delete: List[str] = [],
    ):
        print(series_instance_uid)
        print(f"Tags 2 add: {tags2add}")
        print(f"Tags 2 delete: {tags2delete}")

        # Read Tags
        es = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        )
        doc = es.get(index="meta-index", id=series_instance_uid)
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
        es.update(index="meta-index", id=series_instance_uid, body=body)

    try:
        for series in data:
            tagging(
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
async def get_series(data: dict = Body(...)):

    def _get_field_mapping(index="meta-index") -> Dict:
        """
        Returns a mapping of field for a given index form open search.
        This looks like:
        # {
        #   'Specific Character Set': '00080005 SpecificCharacterSet_keyword.keyword',
        #   'Image Type': '00080008 ImageType_keyword.keyword'
        #   ...
        # }
        """
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).indices.get_mapping(index=index)[index]["mappings"]

        if "properties" in res:
            res = res["properties"]
            name_field_map = {
                camel_case_to_space(k): k for k, v in res.items()
            }

            name_field_map = {
                k: v
                for k, v in name_field_map.items()
                if len(re.findall("\d", k)) == 0 and k != "" and v != ""
            }
            return name_field_map
        else:
            return {}

    def curate_criteria(criteria):
        key = criteria["key"]
        if key is None:
            return {}
        curated_criteria = {}
        for value, condition, count in zip(criteria["values"], criteria["conditions"], criteria["counts"]):
            if None in [value, condition, count, key]:
                continue
            else:             
                if not curated_criteria:
                    curated_criteria = {
                        "key": key,
                        "values": [],
                        "conditions": [],
                        "counts": []
                    }
                curated_criteria["key"] = key
                curated_criteria["values"].append(value)
                curated_criteria["conditions"].append(condition)
                curated_criteria["counts"].append(count)
        return curated_criteria

    def get_count(info, value):
        item_count = 0
        if value in info:
            item_count = int(info[value])
        elif isinstance(value, float):
            tolerance = 1e-9
            close_keys = info.index[np.isclose(list(info.index.drop("N/A", errors="ignore")), value, atol=tolerance)]
            if len(close_keys) > 0:
                item_count = int(info[close_keys[0]])
        elif isinstance(value, int):
            if str(value) in info:
                item_count = int(info[str(value)])
        else:
            for format_time in ["%Y-%m-%d %H:%M:%S.%f", "%H:%M:%S.%f"]:
                try:
                    d_value = datetime.strptime(value, format_time)
                    tolerance = timedelta(milliseconds=10)
                    # Finding keys close to the target value within the given tolerance
                    info.index = pd.to_datetime(info.index, format=format_time)
                    close_keys = [key for key in info.index if abs(key - d_value) <= tolerance]
                    if len(close_keys) > 0:
                        item_count = int(info[close_keys[0]])
                except:
                    continue
        return item_count

    def check_info_and_or_criteria(info, criteria):
        for value, condition, count in zip(criteria["values"], criteria["conditions"], criteria["counts"]):
            item_count = get_count(info, value)
            if condition == '=':
                if item_count == int(count):
                    return True
            elif condition == '!=':
                if item_count != int(count):
                    return True
            elif condition == '<' or condition == '&lt;':
                if item_count < int(count):
                    return True
            elif condition == '>' or condition == '&gt;':
                if item_count > int(count):
                    return True
            else:
                return True
        return False  # No criteria met

    def check_and_or_criteria(group, filterSubProps, target="Series Instance UID"):
        def _is_nested_list(element):
            if isinstance(element, list):
                return True
            return False

        if target == "Series Instance UID":
            for criteria in filterSubProps:
                if _is_nested_list(group[criteria["key"]]):
                    value_counts = group.to_frame().transpose().explode(criteria["key"])[criteria["key"]].value_counts()
                else:
                    value_counts = pd.Series(1, index=[group[criteria["key"]]])
                    
                if not check_info_and_or_criteria(value_counts, criteria):
                    return False
            return True
        else:
            for criteria in filterSubProps:
                if group[criteria["key"]].apply(_is_nested_list).any():
                    if target == "Patient ID":
                        value_counts = group.explode(criteria["key"]).drop_duplicates(["Study Instance UID", criteria["key"]])[criteria["key"]].value_counts()
                    else:
                        value_counts = group.explode(criteria["key"])[criteria["key"]].value_counts()
                else:
                    if target == "Patient ID":
                        value_counts = group.drop_duplicates(["Study Instance UID", criteria["key"]])[criteria["key"]].value_counts()
                    elif target == "Study Instance UID":
                        value_counts = group[criteria["key"]].value_counts()
                if not check_info_and_or_criteria(value_counts, criteria):
                    return group[group.index != group.index]
            return group

    structured: bool = data.get("structured", False)
    query: dict = data.get("query", {"query_string": {"query": "*"}})
    filterProperties: dict = data.get("filterProperties", {})

    if structured:
        columns = list(set([
            "Patient ID",
            "Study Instance UID",
            "Series Instance UID",
            "Modality",
            "Series Number",
            "Study Description",
            "Series Description"
            ] + [
                criteria["key"] for inner_list in filterProperties.values() for criteria in inner_list if criteria["key"] is not None
            ]))
        
        name_field_map = _get_field_mapping()
        includes = [name_field_map[c] if c in name_field_map else c for c in columns]

        hits = execute_opensearch_query(
            query=query,
            source={
                "includes": includes
            },
        )
        res_array = [
            [*[ hit["_source"].get(k, "N/A") for k in includes]
            ]
            for hit in hits
        ]

        df = pd.DataFrame(
            res_array,
            columns=columns,
        )

        curated_filter_properties = {}
        for k, filterSubProps in filterProperties.items():
            curated_filter_properties[k] = []
            for criteria in filterSubProps:
                c = curate_criteria(criteria)
                if c:
                    curated_filter_properties[k].append(c)

        # The order matters!!
        if curated_filter_properties.get("patientFilterProperties", []):
            df = df.groupby("Patient ID", sort=False).apply(check_and_or_criteria, curated_filter_properties.get("patientFilterProperties", []), target="Patient ID").reset_index(drop=True)
        if curated_filter_properties.get("studyFilterProperties", []):
            df = df.groupby("Study Instance UID", sort=False).apply(check_and_or_criteria, curated_filter_properties.get("studyFilterProperties", []), target="Study Instance UID").reset_index(drop=True)
        if curated_filter_properties.get("seriesFilterProperties", []):
            mask = df.apply(lambda s: check_and_or_criteria(s, curated_filter_properties.get("seriesFilterProperties", []), target="Series Instance UID"), axis=1)
            df = df[mask].reset_index(drop=True)
            
        if df.empty:
            print("No results found after filtering -> returning empty list")
            return JSONResponse({})

        df['uid_prefix'] = df['Study Instance UID'].apply(lambda x: ".".join(x.split(".")[:-1]))
        df['uid_last_section'] = df['Study Instance UID'].apply(lambda x: int(x.split(".")[-1]))

        return JSONResponse(
            {
                k: f.groupby("Study Instance UID", sort=False)["Series Instance UID"]
                .apply(list)
                .to_dict()
                for k, f in df.sort_values(
                    [
                        "Patient ID",
                        "uid_prefix",
                        "uid_last_section",
                        "Modality",
                        "Series Number",
                        "Study Description",
                        "Series Description",
                    ]
                ).groupby("Patient ID", sort=False)
            }
        )
    elif not structured:
        return JSONResponse([d["_id"] for d in execute_opensearch_query(query)])


@router.get("/series/{series_instance_uid}")
async def get_data(series_instance_uid):
    # sanitize path params
    series_instance_uid = sanitize_inputs(series_instance_uid)

    metadata = await get_metadata(series_instance_uid)

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


async def get_field_values(query, field, size=10000):
    res = OpenSearch(
        hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
    ).search(
        body={
            "size": 0,
            "query": query,
            "aggs": {
                field: {
                    "composite": {
                        "sources": [{field: {"terms": {"field": field, "size": size}}}]
                    }
                }
            },
        }
    )

    data = res["hits"]["aggregations"][field]
    if len(data["buckets"]) < size:
        return []


# This should actually be a get request but since the body is too large for a get request
# we use a post request
@router.post("/dashboard")
async def get_dashboard(config: dict = Body(...)):
    series_instance_uids = config.get("series_instance_uids")
    names = config.get("names", [])

    name_field_map = await get_field_mapping()
    filtered_name_field_map = {
        name: name_field_map[name] for name in names if name in name_field_map
    }

    res = OpenSearch(
        hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
    ).search(
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
                    name: {
                        "terms": {
                            "field": field,
                            "size": 10000,
                            "order": {"_key": "asc"},
                        }
                    }
                    for name, field in filtered_name_field_map.items()
                },
            },
        }
    )[
        "aggregations"
    ]

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


async def get_all_values(item_name, query):
    name_field_map = await get_field_mapping()

    item_key = name_field_map.get(item_name)
    if not item_key:
        return {}  # todo: maybe better default

    item = OpenSearch(
        hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
    ).search(
        body={
            "size": 0,
            # {"query":"D","field":"00000000 Tags_keyword.keyword","boolFilter":[]}
            "query": query,  # {"query": {"ids": {"values": series_instance_uids}}}
            "aggs": {item_name: {"terms": {"field": item_key, "size": 10000}}},
        }
    )[
        "aggregations"
    ][
        item_name
    ]

    if "buckets" in item and len(item["buckets"]) > 0:
        filtered_buckets = [
            bucket for bucket in item["buckets"]
            if not isinstance(bucket["key"], str) or (not bucket["key"].startswith("[") and not bucket["key"].endswith("]"))
        ]
        return {
            "items": (
                [
                    dict(
                        text=f"{bucket.get('key_as_string', bucket['key'])}",
                        value=bucket.get("key_as_string", bucket["key"]),
                        count=bucket["doc_count"],
                    )
                    for bucket in filtered_buckets
                ]
            ),
            "key": item_key,
        }
    else:
        return {}


@router.post("/query_values/{field_name}")
async def get_query_values_item(field_name: str, query: dict = Body(...)):
    # sanitize field_name path params
    field_name = sanitize_inputs(field_name)
    if not query or query == {}:
        query = {"query_string": {"query": "*"}}

    return JSONResponse(await get_all_values(field_name, query))


@router.get("/field_names")
async def get_field_names():
    return JSONResponse(list((await get_field_mapping()).keys()))


@router.get("/fields")
async def get_fields(index: str = "meta-index", field: str = None):
    mapping = await get_field_mapping(index)
    if field:
        return JSONResponse(mapping[field])
    else:
        return JSONResponse(mapping)
