from minio import Minio
from opensearchpy import OpenSearch

access_key = "kaapanaminio"
secret_key = "Kaapana2020"
minio_host = "minio-service.services.svc"
minio_port = "9000"

# MinIO Client
minio_client = Minio(
    endpoint=f"{minio_host}:{minio_port}",
    access_key=access_key,
    secret_key=secret_key,
    secure=False,
)

host = "opensearch-service.services.svc"
port = "9200"

# OpenSearch Client
opensearch_client = OpenSearch(
    hosts=[{"host": host, "port": port}],
    http_compress=True,
    http_auth=None,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=2,
)


