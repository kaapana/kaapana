"""
Structural guard for the dcm4chee LDAP bootstrap (dcm4che-ldap configmap).

Same scope as keycloak-setup/tests/test_chart_invariants.py: template content only, no
cluster, no helm, no network. It does not prove dcm4chee applies the rule at runtime.

Run from anywhere:
    pytest services/store/dcm4chee/tests/test_ldap_config.py
"""

from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "platforms").is_dir() and (parent / "services").is_dir():
            return parent
    raise RuntimeError("repo root not found")


LDIF_CONFIGMAP = (
    _repo_root()
    / "services/store/dcm4chee/dcm4chee-chart/deps/dcm4che-ldap/templates/configmap.yaml"
)


def test_ldif_replaces_hashed_issuer_supplement_with_nullified_issuer():
    text = LDIF_CONFIGMAP.read_text(encoding="utf-8")
    assert "dn: cn=SupplementIssuerOfPatientID,dicomAETitle=KAAPANA," in text, (
        "the archive's default SupplementIssuerOfPatientID rule must be deleted — it "
        "derives the issuer from PatientName and PatientBirthDate, splitting one "
        "PatientID into several patients when those differ between senders."
    )
    rule = text.split("dn: cn=NullifyIssuerOfPatientID,dicomAETitle=KAAPANA,", 1)
    assert len(rule) == 2, "a NullifyIssuerOfPatientID coercion on the KAAPANA AE is missing"
    for line in (
        "dcmDIMSE: C_STORE_RQ\n",
        "dcmURI: merge-attrs:\n",
        "dcmMergeAttribute: IssuerOfPatientID=\n",  # empty value = nullify the tag
    ):
        assert line in rule[1], f"NullifyIssuerOfPatientID must carry '{line.strip()}'"
