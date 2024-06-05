import re
from typing import Dict, List
from kaapanapy.settings import OpensearchSettings, ProjectSettings
from kaapanapy.logger import get_logger
from kaapanapy.Clients.KaapanaAuthorization import get_project_user_access_token
from opensearchpy import OpenSearch

logger = get_logger(__file__)


class DicomKeywords:
    """
    Collection of dicom tags.
    """

    study_uid_tag = "0020000D StudyInstanceUID_keyword"
    series_uid_tag = "0020000E SeriesInstanceUID_keyword"
    SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
    modality_tag = "00080060 Modality_keyword"
    protocol_name = "00181030 ProtocolName_keyword"
    curated_modality_tag = "00000000 CuratedModality_keyword"
    custom_tag = "00000000 Tags_keyword"


class DicomUid(dict):
    """
    Custom response object.
    """

    def __init__(self, study_uid, series_uid, modality, curated_modality):
        super().__init__(
            {
                "study-uid": study_uid,
                "series-uid": series_uid,
                "modality": modality,
                "curated_modality": curated_modality,
            }
        )


class KaapanaOpensearchHelper(OpenSearch):
    """
    A helper class for retrieving data from an opensearch backend.
    """

    def __init__(self, x_auth_token=None, index="meta-index"):
        if not x_auth_token:
            try:
                x_auth_token = get_project_user_access_token()
            except Exception as e:
                logger.error("No access token provided and env variables missing!")
                raise e
        self.settings = OpensearchSettings()
        auth_headers = {"Authorization": f"Bearer {x_auth_token}"}
        if not index:
            try:
                project_settings = ProjectSettings()
                index = project_settings.project_name
            except Exception as e:
                logger.WARNING("Could not fetch index name from environment variables.")
                index = "meta-index"
                logger.WARNING(f"Set {index=}")
        self.target_index = index
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

    def aggregate_search_results(
        self,
        query: Dict = dict(),
        source=dict(),
        sort=[{"0020000E SeriesInstanceUID_keyword.keyword": "desc"}],
        search_after=None,
        size=10000,
    ) -> List:
        """
        Since Opensearch has a strict size limit of 10000 but sometimes scrolling or
        pagination is not desirable, this function aggregates paginated results.

        :param query: query to execute
        :param source: opensearch _source parameter; specify which fields to include from the document in the search response.
        :param sort: The sort parameter in the body of the request to opensearch.
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
            index=self.target_index,
        )
        if len(res["hits"]["hits"]) > 0:
            return [
                *res["hits"]["hits"],
                *self.aggregate_search_results(
                    query=query,
                    source=source,
                    sort=sort,
                    search_after=res["hits"]["hits"][-1]["sort"],
                    size=size,
                ),
            ]
        else:
            return res["hits"]["hits"]

    async def get_sanitized_metadata(self, series_instance_uid: str) -> dict:
        """
        Return dictionary of all meta data associated to a series.

        Format the keys to be space separated uppercase expressions.
        """
        data = self.get(index=self.target_index, id=series_instance_uid)["_source"]
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

        res = self.indices.get_mapping(index=self.target_index)[self.target_index][
            "mappings"
        ]["properties"]
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
        :param: tags: List of tags that will be added to the series, if not in tags2delete.
        :param: tags2add: A second list of tags that will be added to the series.
        :param: tags2delete: A list of tags that will be removed from the series.
        """
        logger.debug(series_instance_uid)
        logger.debug(f"Tags 2 add: {tags2add}")
        logger.debug(f"Tags 2 delete: {tags2delete}")

        # Read Tags
        doc = self.get(index=self.target_index, id=series_instance_uid)
        logger.debug(doc)
        index_tags = doc["_source"].get("00000000 Tags_keyword", [])

        final_tags = combine_tags(
            tags=tags,
            tags2add=tags2add,
            tags2delete=tags2delete,
            original_tags=index_tags,
        )
        logger.debug(f"Final tags: {final_tags}")

        # Write Tags back
        body = {"doc": {"00000000 Tags_keyword": final_tags}}
        self.update(index=self.target_index, id=series_instance_uid, body=body)

    def delete_by_query(self, query):
        """
        Delete the queried items from Opensearch index.
        """
        try:
            res = super().delete_by_query(index=self.target_index, body=query)
            logger.info(f"{res=}")
        except Exception as e:
            logger.error(f"Deleting from Opensearch failed for {query=}: {str(e)}")
            raise e

    def get_series_metadata(self, series_instance_uid):
        """
        Get metadata of a series.
        """
        res = self.get(index=self.target_index, id=series_instance_uid)
        return res["_source"]

    def get_dcm_uid_objects(
        self,
        series_instance_uids: list,
        include_custom_tag: str = None,
        exclude_custom_tag: str = None,
    ) -> List[DicomUid]:
        """
        From HelperOpensearch

        :param: series_instance_uids
        :param: include_customn_tag
        :param_exclude_custom_tag
        """
        # defauly query for fetching via identifiers
        query = {"bool": {"must": [{"ids": {"values": series_instance_uids}}]}}
        # must have custom tag
        if include_custom_tag:
            query["bool"]["must"].append(
                {"term": {"00000000 Tags_keyword.keyword": include_custom_tag}}
            )
        # must_not have custom tag
        if exclude_custom_tag:
            if "must_not" in query["bool"]:
                query["bool"]["must_not"].append(
                    {"term": {"00000000 Tags_keyword.keyword": exclude_custom_tag}}
                )
            else:
                query["bool"]["must_not"] = [
                    {"term": {"00000000 Tags_keyword.keyword": exclude_custom_tag}}
                ]

        res = self.aggregate_search_results(
            query=query,
            source={
                "includes": [
                    DicomKeywords.study_uid_tag,
                    DicomKeywords.series_uid_tag,
                    DicomKeywords.SOPInstanceUID_tag,
                    DicomKeywords.modality_tag,
                    DicomKeywords.curated_modality_tag,
                ]
            },
        )

        return [
            DicomUid(
                study_uid=hit["_source"][DicomKeywords.study_uid_tag],
                series_uid=hit["_source"][DicomKeywords.series_uid_tag],
                modality=hit["_source"][DicomKeywords.modality_tag],
                curated_modality=hit["_source"][DicomKeywords.curated_modality_tag],
            )
            for hit in res
        ]

    def get_query_dataset(
        self,
        query: dict,
        only_uids: bool = False,
        include_custom_tag: str = None,
    ):
        """
        Return the aggregated opensearch result of query exclusively including fields specified in DicomKeywords and include_custom_tag.

        :param: query: The query for opensearch.
        :param: only_uids: If True return a list of uids.
        :param: include_custom_tag: Include this field in the response.
        """
        logger.info("Getting dataset for query: {}".format(query))
        logger.info("index: {}".format(self.target_index))
        includes = [
            DicomKeywords.study_uid_tag,
            DicomKeywords.series_uid_tag,
            DicomKeywords.SOPInstanceUID_tag,
            DicomKeywords.modality_tag,
            DicomKeywords.protocol_name,
            DicomKeywords.curated_modality_tag,
        ]
        if include_custom_tag:
            includes.append(include_custom_tag)
        try:
            hits = self.aggregate_search_results(
                query=query, source={"includes": includes}
            )
        except Exception as e:
            logger.error(f"ERROR in search: {str(e)}")
            return None

        if only_uids:
            return [hit["_id"] for hit in hits]
        else:
            return hits


def sanitize_field_name(field_name: str) -> str:
    """
    Return a sanitized field name.
    Remove the dicom tag and the dicom type from the field and change camel case to uppercase space separated expression.
    E.g. '"00180015 BodyPartExamined_keyword.keyword"' -> 'Body Part Examined'.
    """
    removed_tag = field_name.split(" ")[-1]
    removed_type = removed_tag.split("_")[0]
    sanitized_field_name = " ".join(
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
    return sanitized_field_name


def type_suffix(v):
    if "type" in v:
        type_ = v["type"]
        return "" if type_ != "text" and type_ != "keyword" else ".keyword"
    else:
        return ""


def combine_tags(tags, tags2add, tags2delete, original_tags) -> list:
    """
    Create a list of strings, that
    * includes all strings in tags and original_tags that are not in tags2delete
    * includes all strings in tags2add

    :param: tags: List of tags that will be added to the series, if not in tags2delete.
    :param: tags2add: A second list of tags that will be added to the series.
    :param: tags2delete: A list of tags that will be removed from the series.
    :param: original_tags:
    """
    return list(
        set(tags)
        .union(set(original_tags))
        .difference(set(tags2delete))
        .union(set(tags2add))
    )
