import pytest

from app import utils, validation

RELEASE_NAME_REGEX = r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"


def airflow_release_name(run_id):
    """Builds the release name in the same way as the Airflow operators do."""
    return "kaapanaint-" + utils.cure_invalid_name(run_id, RELEASE_NAME_REGEX, max_length=42)


def collection_release_name(collection):
    """Builds the release name in the same way as execute_update_extensions does."""
    return utils.cure_invalid_name(
        "-".join(collection.split("/")[-1].split(":")),
        RELEASE_NAME_REGEX,
        max_length=53,
    )


@pytest.mark.parametrize(
    "value",
    [
        "project-abcd1234",
        "demo-chart-0123456789abcdef0123",
        "pull-docker-chart-0123456789abcdef0123",
        "prefetch-dag-chart-0123456789abcdef0123",
        airflow_release_name("manual__2026-11-16T10:00:00.123456+00:00"),
        airflow_release_name("scheduled__2026-11-16T10:00:00+00:00-with-a-very-long-suffix-for-the-name"),
        collection_release_name("registry.example.com/kaapana/kaapana-extension-collection:0.7.0-216-g933306328"),
        "a",
        "a" * 53,
    ],
)
def test_release_names_of_legitimate_callers_pass(value):
    assert validation.check_release_name(value) == value


@pytest.mark.parametrize(
    "value",
    ["", "a" * 54, "-demo", "demo-", "Demo", "demo_chart", "demo chart", "demo;id", "--all", "demo\n", None, 5],
)
def test_invalid_release_names_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_release_name(value)
    assert not validation.is_release_name(value)


@pytest.mark.parametrize("value", ["default", "admin", "project-abcd1234", "a" * 63])
def test_namespaces_pass(value):
    assert validation.check_namespace(value) == value


@pytest.mark.parametrize("value", ["", "a" * 64, "Admin", "admin.ns", "-admin", "admin;id", "admin\n"])
def test_invalid_namespaces_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_namespace(value)


@pytest.mark.parametrize(
    "value",
    ["demo-chart", "kaapana_database", "oAuth2-proxy-chart", "model_installer_chart", "pull-docker-chart"],
)
def test_chart_names_pass(value):
    assert validation.check_chart_name(value) == value


@pytest.mark.parametrize("value", ["", "../demo", "demo/../x", "a..b", "-demo", ".demo", "demo chart", "demo\n"])
def test_invalid_chart_names_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_chart_name(value)


@pytest.mark.parametrize(
    "value",
    ["0.0.0", "0.7.0", "0.7.0-216-g933306328", "1.2.3-rc.1+build.5", "v1.2.3", "1.2"],
)
def test_chart_versions_pass(value):
    assert validation.check_chart_version(value) == value


@pytest.mark.parametrize("value", ["", "latest", "1.0.0/../../x", "1.0.0 --dry-run", "-1.0.0", "1.0.0\n", "1.0.0-"])
def test_invalid_chart_versions_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_chart_version(value)


@pytest.mark.parametrize(
    "value",
    [
        "global.registry_url",
        "global.envVars[0].value",
        "global.dynamicVolumes[1].mount_path",
        "global.envVarsFromSecretRef[0].secretKey",
        "kube_helm_collection",
        r"global.annotations.kaapana\.ai/type",
    ],
)
def test_set_keys_pass(value):
    assert validation.check_set_key(value) == value


@pytest.mark.parametrize("value", ["", "a,b", "a=b", "a b", "-a", "--set", "a\nb", "a{b}"])
def test_invalid_set_keys_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_set_key(value)


@pytest.mark.parametrize(
    "value",
    [
        "kaapanaapplication",
        "kaapanaworkflow",
        "kaapanaworkflow-v2",
        "kaapanamultiinstallable",
        "kaapanaplatform",
        "kaapanaint",
        "kaapanaexperimental",
        "gpurequired",
    ],
)
def test_keywords_pass(value):
    assert validation.check_keyword(value) == value


@pytest.mark.parametrize("value", ["", "a=b", "a,b", "a b", "a/b", "-a", "a" * 64])
def test_invalid_keywords_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_keyword(value)


@pytest.mark.parametrize("value", ["image.tar", "image 1.0.tar", "image;1.tar"])
def test_file_names_pass(value):
    assert validation.check_file_name(value) == value


@pytest.mark.parametrize("value", ["", ".", "..", "../image.tar", "dir/image.tar", "/image.tar", "image\0.tar"])
def test_paths_are_rejected_as_file_names(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_file_name(value)


def test_path_must_stay_inside_directory(tmp_path):
    assert validation.check_path_inside(f"{tmp_path}/demo-0.1.0.tgz", tmp_path) == f"{tmp_path}/demo-0.1.0.tgz"
    with pytest.raises(validation.InvalidValueError):
        validation.check_path_inside(f"{tmp_path}/../demo-0.1.0.tgz", tmp_path)


@pytest.mark.parametrize("value, expected", [("", []), ("--no-hooks", ["--no-hooks"])])
def test_known_delete_addons_pass(value, expected):
    assert validation.check_delete_addons(value) == expected


@pytest.mark.parametrize("value", ["--dry-run", "--no-hooks --wait", " --no-hooks", ["--no-hooks"], None])
def test_other_delete_addons_are_rejected(value):
    with pytest.raises(validation.InvalidValueError):
        validation.check_delete_addons(value)
