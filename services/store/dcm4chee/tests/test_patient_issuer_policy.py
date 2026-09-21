"""The dcm4chee patient issuer policy, checked on what `helm template` renders.

Run from anywhere:
    pytest services/store/dcm4chee/tests/

Skipped without Helm. The chart's local dependencies are assembled into a
throwaway copy; only kaapana-library-chart, which belongs to the platform,
is taken from services/utils.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = next(p for p in Path(__file__).resolve().parents if (p / "platforms").is_dir())
CHART = REPO / "services/store/dcm4chee/dcm4chee-chart"
RULE_DN = "cn=KaapanaPatientIssuerPolicy,dicomAETitle=KAAPANA,dicomDeviceName=kaapana,cn=Devices,cn=DICOM Configuration,dc=dcm4che,dc=org"
POLICIES = ("archive_default", "patient_id_only", "fixed_issuer", "supplement_issuer")


@pytest.fixture(scope="module")
def chart(tmp_path_factory):
    if not shutil.which("helm"):
        pytest.skip("helm is not installed")
    chart = tmp_path_factory.mktemp("chart") / "dcm4chee-chart"
    shutil.copytree(CHART, chart)
    (chart / "requirements.yaml").unlink()
    (chart / "charts").mkdir()
    for dep in ("dcm4che-ldap", "dcm4che-postgres"):
        shutil.move(chart / "deps" / dep, chart / "charts" / dep)
    shutil.copytree(REPO / "services/utils/kaapana-library-chart", chart / "charts/kaapana-library-chart")
    return chart


def render(chart, policy="archive_default", value="", instance=""):
    values = chart.parent / "values.json"
    values.write_text(json.dumps({"global": {
        "hostname": "kaapana.example.org", "https_port": 443, "http_proxy": "",
        "services_namespace": "services", "registry_url": "registry.example.org",
        "kaapana_build_version": "0.0.0-test", "pull_policy_images": "IfNotPresent",
        "storage_node": "node-1", "pacs_memory_limit": "4Gi", "pacs_memory_request": "1Gi",
        "pacs_patient_issuer_policy": policy, "pacs_patient_issuer_value": value,
        "instance_name": instance,
    }}))
    return subprocess.run(["helm", "template", "test", str(chart), "-f", str(values)],
                          capture_output=True, text=True)


def rendered(chart, **kwargs):
    result = render(chart, **kwargs)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    configmap = next(d for d in docs if d.get("metadata", {}).get("name") == "dcm4che-iid-config")
    deployment = next(d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == "dcm4chee")
    return configmap["data"], deployment


def records(ldif):
    """The LDIF as a list of records, each a list of non-comment lines."""
    return [[l for l in block.splitlines() if l and not l.startswith("#")]
            for block in ldif.split("\n\n") if block.strip()]


@pytest.mark.parametrize("policy", POLICIES)
def test_every_policy_first_removes_the_previous_rule(chart, policy):
    data, _ = rendered(chart, policy=policy, value="UKHD")
    assert records(data["patient-issuer-policy.ldif"])[0] == ["version: 1", f"dn: {RULE_DN}", "changetype: delete"]
    assert "KaapanaPatientIssuerPolicy" not in data["dcm4che-iid.ldif"], "the ldap container must never import the policy"


def test_archive_default_installs_no_rule(chart):
    data, _ = rendered(chart, policy="archive_default")
    assert len(records(data["patient-issuer-policy.ldif"])) == 1


@pytest.mark.parametrize("policy, expected", [
    ("patient_id_only", {"dcmMergeAttribute: IssuerOfPatientID=", "dcmMergeAttribute: IssuerOfPatientIDQualifiersSequence="}),
    ("fixed_issuer", {"dcmMergeAttribute: IssuerOfPatientID=UKHD", "dcmMergeAttribute: IssuerOfPatientIDQualifiersSequence="}),
    ("supplement_issuer", {"dcmProperty: IssuerOfPatientID=", "dcmMergeAttribute: IssuerOfPatientID=UKHD",
                           "dcmMergeAttribute: IssuerOfPatientIDQualifiersSequence="}),
])
def test_the_rule_coerces_what_the_policy_says(chart, policy, expected):
    data, _ = rendered(chart, policy=policy, value="UKHD")
    _, add = records(data["patient-issuer-policy.ldif"])
    assert add[0] == f"dn: {RULE_DN}"
    for line in ("objectClass: dcmArchiveAttributeCoercion2", "dcmDIMSE: C_STORE_RQ",
                 "dicomTransferRole: SCU", "dcmRulePriority: -1", "dcmURI: merge-attrs:"):
        assert line in add
    assert {l for l in add if l.startswith(("dcmMergeAttribute:", "dcmProperty:"))} == expected


@pytest.mark.parametrize("kwargs, message", [
    # not one of the four policies
    (dict(policy="nullify"), "Unknown pacs_patient_issuer_policy"),
    # issuer is mandatory for fixed_issuer
    (dict(policy="fixed_issuer"), "pacs_patient_issuer_value"),
    # ... and for supplement_issuer, instance_name is no fallback
    (dict(policy="supplement_issuer", instance="my-site.example.org"), "pacs_patient_issuer_value"),
    # only the plain issuer name is allowed, not the HL7 "name&OID&ISO" form
    (dict(policy="fixed_issuer", value="UKHD&1.2.40&ISO"), "pacs_patient_issuer_value"),
    # dcm4chee would expand {PatientName} per image, the issuer must be a fixed string
    (dict(policy="fixed_issuer", value="{PatientName}"), "pacs_patient_issuer_value"),
    # leading/trailing space would make a different patient identity
    (dict(policy="fixed_issuer", value=" UKHD"), "pacs_patient_issuer_value"),
    # backslash needs escaping in LDIF and MessageFormat
    (dict(policy="supplement_issuer", value="site\\x"), "pacs_patient_issuer_value"),
])
def test_bad_settings_fail_the_render(chart, kwargs, message):
    result = render(chart, **kwargs)
    assert result.returncode != 0 and message in result.stderr


def test_the_init_container_applies_and_verifies_both_files(chart):
    _, deployment = rendered(chart, policy="fixed_issuer", value="UKHD")
    spec = deployment["spec"]["template"]["spec"]
    init = next(c for c in spec["initContainers"] if c["name"] == "apply-ldap-config")
    script = init["args"][0]
    assert "ldapmodify -a -c -f /import/dcm4che-iid.ldif" in script
    assert "ldapmodify -a -c -f /import/patient-issuer-policy.ldif" in script
    assert "exit 1" in script, "a policy that did not apply must stop the archive from starting"
    volume = next(v for v in spec["volumes"] if v["name"] == "ldif")
    assert volume["configMap"]["name"] == "dcm4che-iid-config"


@pytest.mark.parametrize("policy", POLICIES)
def test_the_rendered_ldif_parses(chart, policy, tmp_path):
    if not shutil.which("ldapmodify"):
        pytest.skip("install the OpenLDAP client tools to parse-check the LDIF")
    data, _ = rendered(chart, policy=policy, value="UKHD")
    for key, ldif in data.items():
        f = tmp_path / key
        f.write_text(ldif)
        parsed = subprocess.run(["ldapmodify", "-n", "-a", "-c", "-f", str(f), "-H", "ldap://127.0.0.1:1"],
                                capture_output=True, text=True)
        assert parsed.returncode == 0, f"{key}: {parsed.stdout}{parsed.stderr}"
