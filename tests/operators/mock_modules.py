import sys
from unittest.mock import MagicMock


def mock_modules():
    # Kubernetes + Kubetools
    sys.modules["kaapana.kubetools"] = MagicMock()
    sys.modules["kaapana.kubetools.volume_mount"] = MagicMock()
    sys.modules["kaapana.kubetools.volume"] = MagicMock()
    sys.modules["kaapana.kubetools.pod"] = MagicMock()
    sys.modules["kaapana.kubetools.pod_stopper"] = MagicMock()
    sys.modules["kaapana.kubetools.resources"] = MagicMock()

    # Flask
    sys.modules["requests"] = MagicMock()
    sys.modules["kaapana.blueprints"] = MagicMock()
    sys.modules["kaapana.blueprints.kaapana_utils"] = MagicMock()
    sys.modules["kaapana.blueprints.kaapana_global_variables"] = MagicMock()

    # Caching and intercommunication
    sys.modules["kaapana.operators.HelperMinio"] = MagicMock()
    sys.modules["kaapana.operators.HelperFederated"] = MagicMock()
