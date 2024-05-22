import re
from typing import Dict, List

from kaapanapy.settings import OpensearchSettings
from opensearchpy import OpenSearch


class KaapanaOpensearchHelper(OpenSearch):
    """
    A helper class for retrieving data from an opensearch backend.
    """

    def __init__(self, x_auth_token, index="meta-index"):
        self.settings = OpensearchSettings()
        auth_headers = {"Authorization": f"Bearer {x_auth_token}"}
        self.index = index
        super().__init__(
            hosts=[
                {
                    "host": self.settings.opensearch_host,
                    "port": self.settings.opensearch_port,
                }
            ],
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=10,
            headers=auth_headers,
        )

    def execute_opensearch_query(
        self,
        query: Dict = dict(),
        source=dict(),
        sort=[{"0020000E SeriesInstanceUID_keyword.keyword": "desc"}],
        scroll=False,
        search_after=None,
        size=10000,
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
        :param sort: TODO
        :param scroll: use scrolling or pagination -> scrolling currently not impelmented
        :return: aggregated search results
        """

        res = self.search(
            body={
                "query": query,
                "size": size,
                "_source": source,
                "sort": sort,
                **({"search_after": search_after} if search_after else {}),
            },
            index=self.index,
        )
        if len(res["hits"]["hits"]) > 0:
            return [
                *res["hits"]["hits"],
                *self.execute_opensearch_query(
                    query=query,
                    source=source,
                    sort=sort,
                    scroll=scroll,
                    search_after=res["hits"]["hits"][-1]["sort"],
                    size=size,
                ),
            ]
        else:
            return res["hits"]["hits"]

    async def get_metadata_for_series(self, series_instance_uid: str) -> dict:
        """
        Return dictionary of all meta data associated to a series.

        Format the keys to be space separated uppercase expressions.
        """
        data = self.get(index=self.index, id=series_instance_uid)["_source"]
        return {
            sanitize_field_name(key): value for key, value in data.items() if key != ""
        }

    async def get_field_mapping(self) -> Dict:
        """
        Returns a mapping of field for a given index from open search.
        This looks like:
        # {
        #   'Specific Character Set': '00080005 SpecificCharacterSet_keyword.keyword',
        #   'Image Type': '00080008 ImageType_keyword.keyword'
        #   ...
        # }
        """

        res = self.indices.get_mapping(index=self.index)[self.index]["mappings"][
            "properties"
        ]
        name_field_map = {
            sanitize_field_name(k): k + type_suffix(v) for k, v in res.items()
        }
        name_field_map = {
            k: v
            for k, v in name_field_map.items()
            if len(re.findall("\d", k)) == 0 and k != "" and v != ""
        }
        return name_field_map

    async def get_values_of_field(self, field: str, query: dict):
        """
        Return the key name of the field in opensearch together with a list of all values for this field.

        :param: field: Name of the field, e.g. Tags, Modality

        Example return:
        { "items": list_of_all_values, "key": field_key }
        """
        name_field_map = await self.get_field_mapping()

        item_key = name_field_map.get(field)
        if not item_key:
            return {}  # todo: maybe better default

        item = self.search(
            body={
                "size": 0,
                "query": query,
                "aggs": {field: {"terms": {"field": item_key, "size": 10000}}},
            }
        )["aggregations"][field]

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

    def tagging(
        self,
        series_instance_uid: str,
        tags: List[str],
        tags2add: List[str] = [],
        tags2delete: List[str] = [],
    ):
        """
        Update the 00000000 Tags_keyword field of the series with series_instance_uid.

        :param: series_instance_uid: The series instance uid of the series of which the tags will be updated.
        :param: tags: List of tags that will be added to the series.
        :param: tags2add: A second list of tags that will be added to the series.
        :param: tags2delete: A list of dags that will be removed from the series.
        """
        print(series_instance_uid)
        print(f"Tags 2 add: {tags2add}")
        print(f"Tags 2 delete: {tags2delete}")

        # Read Tags
        doc = self.get(index=self.index, id=series_instance_uid)
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
        self.update(index=self.index, id=series_instance_uid, body=body)


def sanitize_field_name(field_name: str) -> str:
    """
    Return a sanitized field name.
    Remove the dicom tag and the dicom type from the field and change camel case to uppercase space separated expression.
    E.g. '"00180015 BodyPartExamined_keyword.keyword"' -> 'Body Part Examined'.
    """
    removed_tag = field_name.split(" ")[-1]
    removed_type = removed_tag.split("_")[0]
    spaceCase = " ".join(
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
    return spaceCase


def type_suffix(v):
    if "type" in v:
        type_ = v["type"]
        return "" if type_ != "text" and type_ != "keyword" else ".keyword"
    else:
        return ""
