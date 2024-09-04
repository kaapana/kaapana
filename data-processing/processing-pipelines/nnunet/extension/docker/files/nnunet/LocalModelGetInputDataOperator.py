from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapanapy.helper.HelperOpensearch import HelperOpensearch


class LocalModelGetInputDataOperator(LocalGetInputDataOperator):
    def start(self, ds, **kwargs):
        conf = kwargs["dag_run"].conf
        print("conf", conf)

        query = {
            "bool": {
                "must": [{"match_all": {}}, {"match_all": {}}],
                "filter": [],
                "should": [],
                "must_not": [],
            }
        }

        if "tasks" in conf["workflow_form"]:
            bool_should = []
            for protocol in conf["workflow_form"]["tasks"]:
                bool_should.append(
                    {
                        "match_phrase": {
                            "00181030 ProtocolName_keyword.keyword": {"query": protocol}
                        }
                    }
                )
            query["bool"]["must"].append(
                {"bool": {"should": bool_should, "minimum_should_match": 1}}
            )

        query["bool"]["must"].append(
            {"match_phrase": {"00080060 Modality_keyword.keyword": {"query": "OT"}}}
        )

        self.data_form = {
            "identifiers": HelperOpensearch.get_query_dataset(
                query=query, only_uids=True
            )
        }
        self.check_modality = False  # might be replaced later by an actual check...

        super().start(ds, **kwargs)

    def __init__(self, dag, name="patched-input-operator", **kwargs):
        super().__init__(dag=dag, name=name, **kwargs)
