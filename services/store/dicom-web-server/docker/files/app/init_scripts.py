import logging
from .clients import minio_client, opensearch_client

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)


def database_initialzation():
    # Create bucket if not exists
    bucket_name = "dicom"

    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    # Create index if not exists
    index_name = "dicom-metadata"
    index_body = {
        "settings": {
            "index": {
                "number_of_replicas": 0,
                "number_of_shards": 4,
                "mapping.total_fields.limit": 6000,
                "max_docvalue_fields_search": 150,
            }
        },
        "mappings": {
            "dynamic": "true",
            "date_detection": "false",
            "numeric_detection": "false",
            "dynamic_templates": [
                {
                    "check_integer": {
                        "match_pattern": "regex",
                        "match": "^.*_integer.*$",
                        "mapping": {"type": "long"},
                    }
                },
                {
                    "check_float": {
                        "match_pattern": "regex",
                        "match": "^.*_float.*$",
                        "mapping": {"type": "float"},
                    }
                },
                {
                    "check_double": {
                        "match_pattern": "regex",
                        "match": "^.*_double.*$",
                        "mapping": {"type": "double"},
                    }
                },
                {
                    "check_datetime": {
                        "match_pattern": "regex",
                        "match": "^.*_datetime.*$",
                        "mapping": {
                            "type": "date",
                            "format": "yyyy-MM-dd HH:mm:ss.SSSSSS",
                        },
                    }
                },
                {
                    "check_date": {
                        "match_pattern": "regex",
                        "match": "^.*_date.*$",
                        "mapping": {"type": "date", "format": "yyyy-MM-dd"},
                    }
                },
                {
                    "check_time": {
                        "match_pattern": "regex",
                        "match": "^.*_time.*$",
                        "mapping": {"type": "date", "format": "HH:mm:ss.SSSSSS"},
                    }
                },
                {
                    "check_timestamp": {
                        "match_pattern": "regex",
                        "match": "^.*timestamp.*$",
                        "mapping": {
                            "type": "date",
                            "format": "yyyy-MM-dd HH:mm:ss.SSSSSS",
                        },
                    }
                },
                {
                    "check_object": {
                        "match_pattern": "regex",
                        "match": "^.*_object.*$",
                        "mapping": {"type": "object"},
                    }
                },
                {
                    "check_boolean": {
                        "match_pattern": "regex",
                        "match": "^.*_boolean.*$",
                        "mapping": {"type": "boolean"},
                    }
                },
                {
                    "check_array": {
                        "match_pattern": "regex",
                        "match": "^.*_array.*$",
                        "mapping": {"type": "array"},
                    }
                },
            ],
        },
    }

    if not opensearch_client.indices.exists(index=index_name):
        opensearch_client.indices.create(index=index_name, body=index_body)
