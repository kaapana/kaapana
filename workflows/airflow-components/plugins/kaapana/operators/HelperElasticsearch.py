from elasticsearch import Elasticsearch

class HelperElasticsearch():
    study_uid_tag = "0020000D StudyInstanceUID_keyword"
    series_uid_tag = "0020000E SeriesInstanceUID_keyword"
    SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
    modality_tag = "00080060 Modality_keyword"
    protocol_name_tag = "00181030 ProtocolName_keyword"

    _elastichost = "elastic-meta-service.meta.svc:9200"
    es = Elasticsearch(hosts=_elastichost)

    @staticmethod
    def get_query_cohort(elastic_query, elastic_index="meta-index"):
        print("Getting cohort for elastic-query: {}".format(elastic_query))
        print("elastic-index: {}".format(elastic_index))

        queryDict = {}
        queryDict["query"] = elastic_query
        queryDict["_source"] = {"includes": [HelperElasticsearch.study_uid_tag, HelperElasticsearch.series_uid_tag,
                                             HelperElasticsearch.SOPInstanceUID_tag, HelperElasticsearch.modality_tag,
                                             HelperElasticsearch.protocol_name_tag]}

        try:
            res = HelperElasticsearch.es.search(index=[elastic_index], body=queryDict, size=10000, from_=0)
        except Exception as e:
            print("ERROR in elasticsearch search!")
            print(e)
            return None

        hits = res['hits']['hits']

        return hits

    @staticmethod
    def get_series_metadata(series_uid, elastic_index="meta-index"):
        queryDict = {}
        queryDict["query"] = {'bool': {
            'must':
            [
                {'match_all': {}},
                {'match_phrase': {
                    '0020000E SeriesInstanceUID_keyword.keyword': {'query': series_uid}}},
            ], 'filter': [], 'should': [], 'must_not': []}}

        queryDict["_source"] = {}

        try:
            res = HelperElasticsearch.es.search(index=[elastic_index], body=queryDict, size=10000, from_=0)
        except Exception as e:
            print("ERROR in elasticsearch search!")
            print(e)
            return None

        hits = res['hits']['hits']

        if len(hits) != 1:
            print("Elasticsearch got multiple results for series_uid: {}".format(series_uid))
            print("This is unexpected and treated as error -> abort!")
            return None

        hit = hits[0]["_source"]
        return hit