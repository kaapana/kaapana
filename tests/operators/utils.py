import sys
from pathlib import Path
from unittest.mock import MagicMock


def mock_modules():
    # Kubernetes + Kubetools
    sys.modules["kaapana.kubetools"] = MagicMock()
    sys.modules["kaapana.kubetools.volume_mount"] = MagicMock()
    sys.modules["kaapana.kubetools.volume"] = MagicMock()
    sys.modules["kaapana.kubetools.pod"] = MagicMock()
    sys.modules["kaapana.kubetools.pod_stopper"] = MagicMock()
    sys.modules["kaapana.kubetools.resources"] = MagicMock()
    sys.modules["kaapana.kubetools.secret"] = MagicMock()

    # Flask
    sys.modules["requests"] = MagicMock()
    sys.modules["kaapana.blueprints"] = MagicMock()
    sys.modules["kaapana.blueprints.kaapana_utils"] = MagicMock()
    sys.modules["kaapana.blueprints.kaapana_global_variables"] = MagicMock()

    # Caching and intercommunication
    sys.modules["kaapana.operators.HelperMinio"] = MagicMock()
    sys.modules["kaapana.operators.HelperFederated"] = MagicMock()

    # kaapanapy
    sys.modules["kaapanapy.helper"] = MagicMock()


KAAPANA_DIR = Path(__file__).resolve().parents[2]
PLUGIN_DIR = (
    KAAPANA_DIR / "data-processing/kaapana-plugin/extension/docker/files/plugin/"
)
DICOM_TAG_DICT = (
    KAAPANA_DIR / "services/flow/airflow/docker/files/scripts/dicom_tag_dict.json"
)
