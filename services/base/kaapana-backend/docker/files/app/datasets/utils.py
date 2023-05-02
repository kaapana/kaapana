import logging
import re
from typing import Dict, List

import requests
from fastapi import HTTPException
from opensearchpy import OpenSearch

from app.config import settings
from app.workflows.utils import (
    requests_retry_session,
    TIMEOUT,
    raise_kaapana_connection_error,
)
from app.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


#  from kaapana.operators.HelperOpensearch import HelperOpensearch


def execute_opensearch_query(
    query: Dict = dict(),
    source=dict(),
    index="meta-index",
    sort=[{"0020000E SeriesInstanceUID_keyword.keyword": "desc"}],
    scroll=False,
) -> List:
    """
    Since Opensearch has a strict size limit of 10000 but sometimes scrolling or
    pagination is not desirable, this helper function aggregates paginated results
    into a single one.

    Caution: Removing or adding entries between requests will lead to inconsistencies.
    Opensearch offers the 'scroll' functionality which prevents this, but creating
    the required sessions takes too much time for most requests.
    Therefore, it is not implemented yet

    :param query: query to execute
    :param source: opensearch _source parameter
    :param index: index on which to execute the query
    :param sort: TODO
    :param scroll: use scrolling or pagination -> scrolling currently not impelmented
    :return: aggregated search results
    """

    def _execute_opensearch_query(search_after=None, size=10000) -> List:
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).search(
            body={
                "query": query,
                "size": size,
                "_source": source,
                "sort": sort,
                **({"search_after": search_after} if search_after else {}),
            },
            index=index,
        )
        if len(res["hits"]["hits"]) > 0:
            return [
                *res["hits"]["hits"],
                *_execute_opensearch_query(res["hits"]["hits"][-1]["sort"], size),
            ]
        else:
            return res["hits"]["hits"]

    return _execute_opensearch_query()


def contains_numbers(s):
    return bool(re.search(r"\d", s))


def camel_case_to_space(s):
    removed_tag = " ".join(s.split(" ")[-1::])
    potential_type = removed_tag.split("_")[-1]
    removed_type = removed_tag
    for type in [
        "keyword",
        "keyword.keyword",
        "float",
        "date",
        "integer",
        "datetime",
        "alphabetic",
    ]:
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
    data = OpenSearch(
        hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
    ).get(index="meta-index", id=series_instance_uid)["_source"]

    # filter for dicoms tags
    return {
        # camel_case_to_space(key): dict(value=value, tag=["0000", "0000"])
        camel_case_to_space(key): value
        for key, value in data.items()
        if key != ""
    }


async def get_metadata(series_instance_uid: str) -> Dict[str, str]:
    # TODO: retrieve study_instance_uid using meta-index
    # pacs_metadata: dict = await get_metadata_pacs(
    #     study_instance_uid, series_instance_uid
    # )
    opensearch_metadata: dict = await get_metadata_opensearch(series_instance_uid)

    # return {**pacs_metadata, **opensearch_metadata}
    return opensearch_metadata


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


async def get_field_mapping(index="meta-index") -> Dict:
    """
    Returns a mapping of field for a given index form open search.
    This looks like:
    # {
    #   'Specific Character Set': '00080005 SpecificCharacterSet_keyword.keyword',
    #   'Image Type': '00080008 ImageType_keyword.keyword'
    #   ...
    # }
    """
    import re

    res = OpenSearch(
        hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
    ).indices.get_mapping(index=index)[index]["mappings"]["properties"]

    name_field_map = {
        camel_case_to_space(k): k + type_suffix(v) for k, v in res.items()
    }

    name_field_map = {
        k: v
        for k, v in name_field_map.items()
        if len(re.findall("\d", k)) == 0 and k != "" and v != ""
    }
    return name_field_map
