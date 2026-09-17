import sys
from unittest.mock import MagicMock

from .utils import KAAPANA_DIR

# The delete-from-meta processing container is a plain script, so import it from its
# files/ directory. Only the kaapanapy modules it needs are mocked, so the real
# `requests` stays in place for the tests collected after this one.
CONTAINER_DIR = (
    KAAPANA_DIR / "data-processing/kaapana-plugin/processing-containers/delete-from-meta/files"
)
sys.path.insert(0, str(CONTAINER_DIR))
for module in ("kaapanapy", "kaapanapy.helper", "kaapanapy.logger", "kaapanapy.settings"):
    sys.modules.setdefault(module, MagicMock())
from start import DeleteFromMetaOperator  # noqa: E402


def test_delete_all_documents_waits_longer_than_client_default():
    """Emptying a project index must not be cut off by the client's 10 s default."""
    op = DeleteFromMetaOperator(delete_all_documents=True)
    op.os_index, op.os_client = "project_test", MagicMock()

    op.start()

    kwargs = op.os_client.delete_by_query.call_args.kwargs
    assert kwargs["index"] == "project_test"
    assert kwargs.get("request_timeout", 0) > 10
