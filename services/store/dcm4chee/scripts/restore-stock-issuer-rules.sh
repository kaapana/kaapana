#!/usr/bin/env bash
# Restore dcm4chee's stock patient issuer rules in the archive's LDAP directory.
#
# Puts the KAAPANA AE back to the state a stock Kaapana ships: the archive's own
# SupplementIssuerOfPatientID rule present, and neither of the rules Kaapana has
# installed since (cn=NullifyIssuerOfPatientID from the draft of MR !1106, and
# cn=KaapanaPatientIssuerPolicy from the configurable policy). Safe to run on a
# stock instance, where it changes nothing, and safe to run twice.
#
# dcm4chee reads its configuration at boot, so restart it afterwards; its init
# container then re-applies the policy configured in kaapanactl.sh:
#     kubectl -n services rollout restart deploy/dcm4chee
#
# Usage:  restore-stock-issuer-rules.sh [--check]
#   --check        report the current state, change nothing
# Environment:
#   NAMESPACE      namespace of the ldap deployment (default: services)
#   KUBECTL        kubectl command (default: kubectl)
#   LDAP_ROOTPASS  LDAP admin password (default: secret, the dcm4che image default)
set -euo pipefail

NAMESPACE=${NAMESPACE:-services}
KUBECTL=${KUBECTL:-kubectl}
LDAP_ROOTPASS=${LDAP_ROOTPASS:-secret}
CHECK_ONLY=false
[ "${1:-}" = "--check" ] && CHECK_ONLY=true

AE_DN="dicomAETitle=KAAPANA,dicomDeviceName=kaapana,cn=Devices,cn=DICOM Configuration,dc=dcm4che,dc=org"
STOCK_DN="cn=SupplementIssuerOfPatientID,$AE_DN"
NULLIFY_DN="cn=NullifyIssuerOfPatientID,$AE_DN"
POLICY_DN="cn=KaapanaPatientIssuerPolicy,$AE_DN"

# Run an OpenLDAP client tool inside the ldap pod as the directory admin.
ldap() {
    local tool=$1; shift
    $KUBECTL -n "$NAMESPACE" exec -i deploy/ldap -- \
        "$tool" -x -H ldap://localhost:389 -D cn=admin,dc=dcm4che,dc=org -w "$LDAP_ROOTPASS" "$@"
}

# present | absent, or abort: anything but "no such object" (32) is a connection or
# permission problem, and guessing would risk acting on the wrong directory.
state() {
    local rc=0
    ldap ldapsearch -b "$1" -s base dn >/dev/null 2>&1 || rc=$?
    case $rc in
        0)  echo present ;;
        32) echo absent ;;
        *)  echo "cannot read $1 (exit $rc): check NAMESPACE, LDAP_ROOTPASS and kubectl access" >&2; exit 1 ;;
    esac
}

if [ "$(state "$AE_DN")" != present ]; then
    echo "the KAAPANA AE does not exist in LDAP of namespace $NAMESPACE; is this a Kaapana ldap deployment?" >&2
    exit 1
fi

stock=$(state "$STOCK_DN"); nullify=$(state "$NULLIFY_DN"); policy=$(state "$POLICY_DN")
echo "SupplementIssuerOfPatientID (stock):   $stock"
echo "NullifyIssuerOfPatientID (draft !1106): $nullify"
echo "KaapanaPatientIssuerPolicy (policy):    $policy"

if [ "$stock" = present ] && [ "$nullify" = absent ] && [ "$policy" = absent ]; then
    echo "already in stock state, nothing to do"
    exit 0
fi
if $CHECK_ONLY; then
    echo "not in stock state (run without --check to restore it)"
    exit 2
fi

[ "$nullify" = present ] && { ldap ldapdelete "$NULLIFY_DN"; echo "deleted $NULLIFY_DN"; }
[ "$policy" = present ]  && { ldap ldapdelete "$POLICY_DN";  echo "deleted $POLICY_DN"; }
if [ "$stock" = absent ]; then
    # The rule as shipped in the pinned slapd-dcm4chee 2.6.7-33.1 image.
    ldap ldapmodify -a <<LDIF
dn: $STOCK_DN
objectClass: dcmArchiveAttributeCoercion2
cn: SupplementIssuerOfPatientID
dcmDIMSE: C_STORE_RQ
dicomTransferRole: SCU
dcmURI: merge-attrs:
dcmProperty: IssuerOfPatientID!=.+
dcmMergeAttribute: IssuerOfPatientID=DCM4CHEE.{PatientName,hash}.{PatientBirthDate,hash}
LDIF
    echo "restored $STOCK_DN"
fi

if [ "$(state "$STOCK_DN")" = present ] && [ "$(state "$NULLIFY_DN")" = absent ] && [ "$(state "$POLICY_DN")" = absent ]; then
    echo "stock state restored; restart dcm4chee to re-apply the configured policy:"
    echo "    $KUBECTL -n $NAMESPACE rollout restart deploy/dcm4chee"
else
    echo "directory is still not in stock state, inspect it with: $0 --check" >&2
    exit 1
fi
