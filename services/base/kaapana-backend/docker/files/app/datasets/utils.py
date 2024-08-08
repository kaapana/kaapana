import logging
import re
from typing import Dict, List

import requests
from fastapi import HTTPException
from app.config import settings
from app.workflows.utils import (
    requests_retry_session,
    TIMEOUT,
    raise_kaapana_connection_error,
)
from app.logger import get_logger
from kaapanapy.settings import OpensearchSettings

logger = get_logger(__name__, logging.DEBUG)


#  from kaapana.operators.HelperOpensearch import HelperOpensearch


def execute_opensearch_query(
    os_client,
    query: Dict = dict(),
    source=dict(),
    index=None,
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
    index = index or OpensearchSettings().default_index

    def _execute_opensearch_query(os_client, search_after=None, size=10000) -> List:
        res = os_client.search(
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
                *_execute_opensearch_query(
                    os_client, res["hits"]["hits"][-1]["sort"], size
                ),
            ]
        else:
            return res["hits"]["hits"]

    return _execute_opensearch_query(os_client=os_client)


def camel_case_to_space(s):
    removed_tag = s.split(" ")[-1]
    removed_type = removed_tag.split("_")[0]

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


async def get_metadata(os_client, series_instance_uid: str) -> Dict[str, str]:
    data = os_client.get(
        index=OpensearchSettings().default_index, id=series_instance_uid
    )["_source"]

    # filter for dicoms tags
    return {
        # camel_case_to_space(key): dict(value=value, tag=["0000", "0000"])
        camel_case_to_space(key): value
        for key, value in data.items()
        if key != ""
    }


async def get_field_mapping(os_client, index=None) -> Dict:
    """
    Returns a mapping of field for a given index form open search.
    This looks like:
    # {
    #   'Specific Character Set': '00080005 SpecificCharacterSet_keyword.keyword',
    #   'Image Type': '00080008 ImageType_keyword.keyword'
    #   ...
    # }
    """
    index = index or OpensearchSettings().default_index
    import re

    res = os_client.indices.get_mapping(index=index)[index]["mappings"]["properties"]

    name_field_map = {
        camel_case_to_space(k): k + type_suffix(v) for k, v in res.items()
    }

    name_field_map = {
        k: v
        for k, v in name_field_map.items()
        if len(re.findall("\d", k)) == 0 and k != "" and v != ""
    }
    return name_field_map
