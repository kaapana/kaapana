import sys
from unittest.mock import MagicMock


def mock_modules():
    sys.modules["kaapanapy"] = MagicMock()
    sys.modules["kaapanapy.helper"] = MagicMock()
    sys.modules["kaapanapy.helper.get_minio_client"] = MagicMock()
    sys.modules["kaapanapy.helper.minio_credentials"] = MagicMock()
    sys.modules["kaapanapy.logger"] = MagicMock()
    sys.modules["kaapanapy.settings"] = MagicMock()


mock_modules()


from app.projects.schemas import is_valid_dicom_ae_title
from app.projects.minio import is_valid_minio_bucket_name
from app.projects.opensearch import is_valid_opensearch_index_name
from app.projects.kubehelm import is_valid_kubernetes_namespace


def test_is_valid_dicom_ae_title() -> bool:
    # Test the function

    success = True
    test_ae_titles = [
        ("MYAE", True),  # Valid
        ("MY_AE_TITLE", True),  # Valid (within 16 characters, valid chars)
        ("LONG_AE_TITLE_12345", False),  # Invalid (more than 16 characters)
        ("INVALID\\TITLE", False),  # Invalid (contains backslash)
        ("   ", False),  # Invalid (entirely spaces)
        ("VALID TITLE", True),  # Valid (has spaces and uppercase)
        ("VALIDTITLE!@#", True),  # Valid (special characters allowed)
        ("LOWERcase", False),  # Invalid (contains lowercase letters)
    ]

    for title_tuple in test_ae_titles:
        valid_response = is_valid_dicom_ae_title(title_tuple[0])
        assert (
            title_tuple[1] == valid_response
        ), f"{title_tuple[0]} assertion failed, response {valid_response}"
        success = title_tuple[1] == valid_response

    assert success


def test_is_valid_minio_bucket_name() -> bool:
    # Test the function

    success = True
    test_bucket_names = [
        ("valid-bucket-name", True),
        ("InvalidBucket", False),
        ("bucket-with-dots.", False),
        ("123", True),
        ("192.168.1.1", False),
        ("a" * 64, False),
        ("project-s3alias", False),
    ]

    for name_tuple in test_bucket_names:
        valid_response = is_valid_minio_bucket_name(name_tuple[0])
        assert name_tuple[1] == valid_response
        success = name_tuple[1] == valid_response

    assert success


def test_is_valid_opensearch_index_name() -> bool:
    success = True
    # Test the function
    test_index_names = [
        ("valid-index", True),  # Valid
        ("invalid_index", True),  # Valid (underscore is allowed per updated pattern)
        ("InvalidUpperCase", False),  # Invalid (uppercase letters)
        ("-invalid-start", False),  # Invalid (starts with a hyphen)
        ("_invalid_start", False),  # Invalid (starts with an underscore)
        ("invalid:character", False),  # Invalid (contains `:`)
        ("invalid,name", False),  # Invalid (contains `,`)
        ("validindex123", True),  # Valid
        ("a" * 256, False),  # Invalid (too long)
    ]

    for name_tuple in test_index_names:
        valid_response = is_valid_opensearch_index_name(name_tuple[0])
        assert name_tuple[1] == valid_response
        success = name_tuple[1] == valid_response

    assert success


def test_is_valid_kubernetes_namespace() -> bool:
    # Test the function

    success = True
    test_namespaces = [
        ("valid-namespace", True),  # Valid
        ("InvalidNamespace", False),  # Invalid (uppercase letters)
        ("-invalid-start", False),  # Invalid (starts with hyphen)
        ("invalid-end-", False),  # Invalid (ends with hyphen)
        ("validnamespace123", True),  # Valid
        ("valid-namespace-name", True),  # Valid
        ("valid-namespace.v1", True),  # Valid
        ("a" * 254, False),  # Invalid (too long)
    ]

    for name_tuple in test_namespaces:
        valid_response = is_valid_kubernetes_namespace(name_tuple[0])
        assert name_tuple[1] == valid_response
        success = name_tuple[1] == valid_response

    assert success
