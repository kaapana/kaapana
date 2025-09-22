import sys
from pathlib import Path
from unittest.mock import MagicMock


def mock_modules():
    # Flask
    sys.modules["requests"] = MagicMock()
    sys.modules["kaapana.blueprints"] = MagicMock()
    sys.modules["kaapana.blueprints.kaapana_utils"] = MagicMock()
    sys.modules["kaapana.blueprints.kaapana_global_variables"] = MagicMock()

    # Caching and intercommunication
    sys.modules["kaapana.operators.HelperMinio"] = MagicMock()
    sys.modules["kaapana.operators.HelperFederated"] = MagicMock()

    # kaapanapy
    sys.modules["kaapanapy"] = MagicMock()
    sys.modules["kaapanapy.settings"] = MagicMock()
    sys.modules["kaapanapy.helper"] = MagicMock()
    sys.modules["kaapanapy.services"] = MagicMock()
    sys.modules["kaapanapy.services.NotificationService"] = MagicMock()

    # task_api
    sys.modules["task_api"] = MagicMock()
    sys.modules["task_api.processing_container"] = MagicMock()
    sys.modules["task_api.processing_container.task_models"] = MagicMock()
    sys.modules["task_api.processing_container.pc_models"] = MagicMock()
    sys.modules["task_api.runners"] = MagicMock()
    sys.modules["task_api.runners.KubernetesRunner"] = MagicMock()
    sys.modules["task_api.runners.KubernetesRunner.KubernetesRunner"] = MagicMock()
    # Mock kubernetes and its submodules
    sys.modules["kubernetes"] = MagicMock()
    sys.modules["kubernetes.client"] = MagicMock()
    sys.modules["kubernetes.config"] = MagicMock()

    from kaapanapy.settings import KaapanaSettings

    KaapanaSettings().timezone = "Europe/Berlin"


KAAPANA_DIR = Path(__file__).resolve().parents[2]
PLUGIN_DIR = (
    KAAPANA_DIR / "data-processing/kaapana-plugin/extension/docker/files/plugin/"
)
DICOM_TAG_DICT = (
    KAAPANA_DIR / "services/flow/airflow/docker/files/scripts/dicom_tag_dict.json"
)
