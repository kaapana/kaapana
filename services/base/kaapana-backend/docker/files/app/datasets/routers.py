import json

import requests
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from opensearchpy import OpenSearch
from typing import List, Dict

from app.config import settings
from app.experiments.utils import (
    requests_retry_session,
    TIMEOUT,
    raise_kaapana_connection_error,
)

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
        index_tags = doc["_source"].get("dataset_tags_keyword", [])

        final_tags = list(
            set(tags)
            .union(set(index_tags))
            .difference(set(tags2delete))
            .union(set(tags2add))
        )
        print(f"Final tags: {final_tags}")

        # Write Tags back
        body = {"doc": {"dataset_tags_keyword": final_tags}}
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


@router.post("/curation_tool/structured")
async def get_query_elastic_structured(query: dict = Body(...)):
    if not query:
        query = {"query_string": {"query": "*"}}

    try:
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).search(
            body={
                "size": 0,
                "query": query,
                "aggs": {
                    "Patients": {
                        "terms": {
                            "field": "00100020 PatientID_keyword.keyword",
                            "size": 10000,
                        },
                        "aggs": {
                            "Modalities": {
                                "terms": {"field": "00080060 Modality_keyword.keyword"}
                            },
                            "Studies": {
                                "terms": {
                                    "field": "0020000D StudyInstanceUID_keyword.keyword",
                                    "size": 10000,
                                },
                                "aggs": {
                                    "Series": {
                                        "top_hits": {
                                            "size": 100,
                                            "_source": {
                                                "includes": [
                                                    "00100020 PatientID_keyword",
                                                    "00100040 PatientSex_keyword",
                                                    "00101010 PatientAge_integer",
                                                    "00082218 AnatomicRegionSequence_object_object.00080104 CodeMeaning_keyword",
                                                    "0020000D StudyInstanceUID_keyword",
                                                    "0020000E SeriesInstanceUID_keyword",
                                                    "00080018 SOPInstanceUID_keyword",
                                                    "00080060 Modality_keyword",
                                                    "00081030 StudyDescription_keyword",
                                                    "0008103E SeriesDescription_keyword",
                                                    "00100010 PatientName_keyword_alphabetic",
                                                    "00181030 ProtocolName_keyword",
                                                    "00180050 SliceThickness_float",
                                                    "00080021 SeriesDate_date",
                                                    "00080020 StudyDate_date",
                                                    "00200011 SeriesNumber_integer",
                                                    "dataset_tags_keyword",
                                                ]
                                            },
                                            "sort": [
                                                {
                                                    "00080020 StudyDate_date": {
                                                        "order": "desc"
                                                    }
                                                }
                                            ],
                                        }
                                    }
                                },
                            },
                        },
                    }
                },
            }
        )
    except Exception as e:
        print("ERROR in elasticsearch search!")
        raise HTTPException(500, e)

    results = list()

    for patient in res["aggregations"]["Patients"]["buckets"]:
        patient_dict = dict(
            patient_key=patient["key"],
            study_count=patient["doc_count"],
            modalities=[m["key"] for m in patient["Modalities"]["buckets"]],
            studies=[],
        )
        for study in patient["Studies"]["buckets"]:
            study_dict = dict(
                study_key=study["key"], series_count=study["doc_count"], series=[]
            )
            for i, series in enumerate(study["Series"]["hits"]["hits"]):
                study_dict["series"].append(series["_source"])
                if i == 0:
                    # Patient params
                    if "00101010 PatientAge_integer" in series["_source"].keys():
                        patient_dict["00101010 PatientAge_integer"] = series["_source"][
                            "00101010 PatientAge_integer"
                        ]
                    if (
                        "00100010 PatientName_keyword_alphabetic"
                        in series["_source"].keys()
                    ):
                        patient_dict[
                            "00100010 PatientName_keyword_alphabetic"
                        ] = series["_source"]["00100010 PatientName_keyword_alphabetic"]
                    if "00100040 PatientSex_keyword" in series["_source"].keys():
                        patient_dict["00100040 PatientSex_keyword"] = series["_source"][
                            "00100040 PatientSex_keyword"
                        ]
                    # Study params
                    if "00081030 StudyDescription_keyword" in series["_source"].keys():
                        study_dict["00081030 StudyDescription_keyword"] = series[
                            "_source"
                        ]["00081030 StudyDescription_keyword"]
                    if "00080020 StudyDate_date" in series["_source"].keys():
                        study_dict["00080020 StudyDate_date"] = series["_source"][
                            "00080020 StudyDate_date"
                        ]
            patient_dict["studies"].append(study_dict)
        results.append(patient_dict)
    return JSONResponse(results)


@router.post("/curation_tool/unstructured")
async def get_query_elastic_unstructured(query: dict = Body(...)):
    print(query)
    if not query:
        query = {"query_string": {"query": "*"}}

    try:
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).search(
            body={
                "query": query,
                "size": 10000,
                "_source": {
                    "includes": [
                        "00100020 PatientID_keyword",
                        "00100040 PatientSex_keyword",
                        "00101010 PatientAge_integer",
                        "0020000D StudyInstanceUID_keyword",
                        "0020000E SeriesInstanceUID_keyword",
                        "00080018 SOPInstanceUID_keyword",
                        "00081030 StudyDescription_keyword",
                        "0008103E SeriesDescription_keyword",
                        "00100010 PatientName_keyword_alphabetic",
                        "00080021 SeriesDate_date",
                        "00080020 StudyDate_date",
                        "dataset_tags_keyword",
                    ]
                },
            },
            index="meta-index",
        )

    except Exception as e:
        print("ERROR in elasticsearch search!")
        raise HTTPException(500, e)

    return JSONResponse([d["_source"] for d in res["hits"]["hits"]])


async def get_metadata_pacs(study_instance_UID: str, series_instance_UID: str) -> dict:
    def load_metadata_form_pacs(study_uid, series_uid) -> dict:
        url = (
            f"http://dcm4chee-service.{settings.services_namespace}.svc:8080/dcm4chee-arc/aets/KAAPANA"
            + f"/rs/studies/{study_uid}/series/{series_uid}/metadata"
        )
        with requests.Session() as s:
            http_response = requests_retry_session(retries=5, session=s).get(
                url,
                timeout=TIMEOUT,
            )
            raise_kaapana_connection_error(http_response)

        if http_response.status_code == 200:
            return http_response.json()
        else:
            print("################################")
            print("#")
            print("# Can't request metadata from PACS!")
            print(f"# StudyUID: {study_uid}")
            print(f"# SeriesUID: {series_uid}")
            print(f"# Status code: {http_response.status_code}")
            print(http_response.text)
            print("#")
            print("################################")
            return {}

    try:
        data = load_metadata_form_pacs(study_instance_UID, series_instance_UID)
    except Exception as e:
        print("Exception", e)
        raise HTTPException(500, e)

    from dicom_parser.utils.vr_to_data_element import get_data_element_class
    from pydicom import Dataset

    dataset = Dataset.from_json(data[0])
    parsed_and_filtered_data = [
        get_data_element_class(dataElement)(dataElement)
        for _, dataElement in dataset.items()
        if dataElement.VR != "SQ"
        and dataElement.VR != "OW"
        and dataElement.keyword != ""
    ]

    res = {}
    for d_ in parsed_and_filtered_data:
        value = d_.value
        if d_.VALUE_REPRESENTATION.name == "PN":
            value = "".join([v + " " for v in d_.value.values() if v != ""])
        # res[d_.description] = dict(value=str(value), tag=d_.tag)
        res[d_.description] = str(value)
    return res


import re


def contains_numbers(s):
    return bool(re.search(r"\d", s))


def camel_case_to_space(s):
    removed_tag = " ".join(s.split(" ")[-1::])
    potential_type = removed_tag.split("_")[-1]
    removed_type = removed_tag
    for type in ["keyword", "float", "date", "integer", "datetime", "alphabetic"]:
        if potential_type == type:
            removed_type = " ".join(removed_tag.split("_")[:-1])
            break
    res = " ".join(
        re.sub(
            "([A-Z][a-z]+)",
            r" \1",
            re.sub(
                "([A-Z]+)",
                r" \1",
                removed_type,
            ),
        ).split()
    )
    return res


def type_suffix(v):
    if "type" in v:
        type_ = v["type"]
        return "" if type_ != "text" and type_ != "keyword" else ".keyword"
    else:
        return ""


def remove_type_suffix(v: str):
    print(v)
    potential_type = v.split("_")[-1]
    for type in ["keyword", "text", "float"]:
        if type == potential_type:
            return v.replace(f"_{type}", "")


async def get_metadata_opensearch(series_instance_uid: str) -> dict:
    try:
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).search(body={"query": {"ids": {"values": [series_instance_uid]}}})
    except Exception as e:
        print("ERROR in elasticsearch search!")
        raise HTTPException(500, e)
    data = res["hits"]["hits"][0]["_source"]

    # filter for dicoms tags
    return {
        # camel_case_to_space(key): dict(value=value, tag=["0000", "0000"])
        camel_case_to_space(key): value
        for key, value in data.items()
        if key != ""
    }


async def get_metadata(
    study_instance_uid: str, series_instance_uid: str
) -> Dict[str, str]:
    # pacs_metadata: dict = await get_metadata_pacs(
    #     study_instance_uid, series_instance_uid
    # )
    opensearch_metadata: dict = await get_metadata_opensearch(series_instance_uid)

    # return {**pacs_metadata, **opensearch_metadata}
    return opensearch_metadata


@router.get("/curation_tool/{study_instance_uid}/{series_instance_uid}")
async def get_data(study_instance_uid, series_instance_uid):
    metadata = await get_metadata(study_instance_uid, series_instance_uid)

    modality = metadata["Modality"]

    if modality == "SEG" or modality == "RTSTRUCT":
        # TODO: We could actually check if this file already exists.
        #  If not, we could either point to the default dcm4chee thumbnail or trigger the process
        thumbnail_src = (
            f"minio/service-segmentation-thumbnail/batch/{series_instance_uid}"
            f"/generate-segmentation-thumbnail/{series_instance_uid}.png"
        )
    else:
        thumbnail_src = (
            f"/dcm4chee-arc/aets/KAAPANA/rs/studies/{study_instance_uid}/"
            f"series/{series_instance_uid}/thumbnail?viewport=300,300"
        )

    return JSONResponse(dict(metadata=metadata, thumbnail_src=thumbnail_src))


@router.post("/curation_tool/query_values")
async def get_query_values(query: dict = Body(...)):
    import re

    if not query:
        query = {"query_string": {"query": "*"}}

    try:
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).indices.get_mapping("meta-index")["meta-index"]["mappings"]["properties"]

        name_field_map = {
            camel_case_to_space(k): k + type_suffix(v) for k, v in res.items()
        }
        name_field_map = {
            k: v
            for k, v in name_field_map.items()
            if len(re.findall("\d", k)) == 0 and k != "" and v != ""
        }
        # TODO: This is from a performance perspective not ideal, sine we will have an request per item
        # The problem is, that if we have 'too' diverse data, we reach the bucket limit and the query fails.
        res = {}
        for name, field in name_field_map.items():
            temp_res = OpenSearch(
                hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
            ).search(
                body={
                    "size": 0,
                    "query": query,
                    "aggs": {name: {"terms": {"field": field, "size": 10000}}},
                }
            )

            res = {**res, **(temp_res["aggregations"])}

    except Exception as e:
        print("ERROR in elasticsearch search!")
        raise HTTPException(500, e)

    result = {
        k: {
            "items": (
                [
                    dict(
                        text=f"{(i['key_as_string'] if 'key_as_string' in i else i['key'])}  ({i['doc_count']})",
                        value=(
                            i["key_as_string"] if "key_as_string" in i else i["key"]
                        ),
                        count=i["doc_count"],
                    )
                    for i in item["buckets"]
                ]
            ),
            "key": name_field_map[k],
        }
        for k, item in res.items()
        if len(item["buckets"]) > 0
    }

    return JSONResponse(result)
