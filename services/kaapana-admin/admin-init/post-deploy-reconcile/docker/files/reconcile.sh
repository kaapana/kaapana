#!/bin/bash
set -euo pipefail

ADMIN_NAMESPACE="${ADMIN_NAMESPACE}"
SERVICES_NAMESPACE="${SERVICES_NAMESPACE}"

wait_for_deployment() {
    local namespace="$1"
    local deployment="$2"
    local timeout="${3:-600s}"

    kubectl get deploy -n "$namespace" "$deployment" >/dev/null 2>&1
    kubectl rollout status -n "$namespace" "deploy/$deployment" --timeout="$timeout" >/dev/null
}

patch_msad_account_control_mapper() {
    local db_deploy="keycloak-database"
    local keycloak_deploy="keycloak"
    local update_output
    local updated_count
    local verify_output
    local remaining_count

    wait_for_deployment "$ADMIN_NAMESPACE" "$db_deploy" "600s"

    update_output=$(kubectl exec -n "$ADMIN_NAMESPACE" -c postgres "deploy/$db_deploy" -- \
        psql -v ON_ERROR_STOP=1 -U keycloak -d keycloak -At -c "
            WITH updated AS (
                UPDATE component_config
                SET value = 'false'
                WHERE name = 'always.read.enabled.value.from.ldap'
                  AND component_id IN (
                      SELECT id
                      FROM component
                      WHERE provider_id = 'msad-user-account-control-mapper'
                  )
                  AND value <> 'false'
                RETURNING component_id
            )
            SELECT count(*) FROM updated;
        ")

    updated_count=$(echo "$update_output" | tail -n1 | tr -d '[:space:]')
    if [[ -z "$updated_count" || ! "$updated_count" =~ ^[0-9]+$ ]]; then
        echo "ERROR: Could not determine whether the LDAP mapper patch was applied."
        return 1
    fi

    echo "Patched $updated_count MSAD account control mapper(s)."

    if [[ "$updated_count" -eq 0 ]]; then
        echo "LDAP mapper already in the expected state."
        return 0
    fi

    kubectl get deploy -n "$ADMIN_NAMESPACE" "$keycloak_deploy" >/dev/null 2>&1
    echo "Restarting $ADMIN_NAMESPACE/$keycloak_deploy to reload mapper configuration..."
    kubectl rollout restart -n "$ADMIN_NAMESPACE" "deploy/$keycloak_deploy" >/dev/null
    kubectl rollout status -n "$ADMIN_NAMESPACE" "deploy/$keycloak_deploy" --timeout=180s >/dev/null

    verify_output=$(kubectl exec -n "$ADMIN_NAMESPACE" -c postgres "deploy/$db_deploy" -- \
        psql -v ON_ERROR_STOP=1 -U keycloak -d keycloak -At -c "
            SELECT count(*)
            FROM component_config
            WHERE name = 'always.read.enabled.value.from.ldap'
              AND value <> 'false'
              AND component_id IN (
                  SELECT id
                  FROM component
                  WHERE provider_id = 'msad-user-account-control-mapper'
              );
        ")

    remaining_count=$(echo "$verify_output" | tail -n1 | tr -d '[:space:]')
    if [[ -z "$remaining_count" || ! "$remaining_count" =~ ^[0-9]+$ ]]; then
        echo "ERROR: Could not verify the LDAP mapper patch state."
        return 1
    fi
    if [[ "$remaining_count" -ne 0 ]]; then
        echo "ERROR: LDAP mapper patch verification failed. $remaining_count mapper entries are still not set to false."
        return 1
    fi

    echo "Verified LDAP mapper patch state."
}

migrate_legacy_aii_admin_roles() {
    local keycloak_db_deploy="keycloak-database"
    local aii_db_deploy="access-information-interface-database"
    local excluded_ids
    local excluded_cte
    local project_system_ids
    local project_system_cte
    local migration_output
    local legacy_count
    local deleted_duplicate_count
    local updated_count
    local remaining_count
    local admin_role_count
    local scientist_role_count
    local pi_role_count
    local excluded_count

    wait_for_deployment "$ADMIN_NAMESPACE" "$keycloak_db_deploy" "600s"
    wait_for_deployment "$SERVICES_NAMESPACE" "$aii_db_deploy" "600s"

    echo "Resolving excluded Keycloak user IDs for AII role migration..."
    excluded_ids=$(kubectl exec -n "$ADMIN_NAMESPACE" -c postgres "deploy/$keycloak_db_deploy" -- \
        psql -v ON_ERROR_STOP=1 -U keycloak -d keycloak -At -c "
            SELECT id
            FROM user_entity
            WHERE (
                    username = 'system'
                AND first_name = 'System'
                AND last_name = 'User'
               )
               OR (
                    username = 'kaapana'
                AND first_name = 'Default'
                AND last_name = 'User'
               )
            ORDER BY id;
        ")

    if [[ -n "$excluded_ids" ]]; then
        excluded_cte=$(printf "%s\n" "$excluded_ids" | awk '
            BEGIN {
                printf "excluded_users(keycloak_id) AS (VALUES "
            }
            {
                gsub(/\047/, "\047\047", $0)
                if (NR > 1) {
                    printf ","
                }
                printf "(\047%s\047)", $0
            }
            END {
                printf "),"
            }
        ')
    else
        excluded_cte="excluded_users(keycloak_id) AS (SELECT NULL::varchar WHERE FALSE),"
    fi

    echo "Resolving Keycloak IDs for legacy project system users..."
    project_system_ids=$(kubectl exec -n "$ADMIN_NAMESPACE" -c postgres "deploy/$keycloak_db_deploy" -- \
        psql -v ON_ERROR_STOP=1 -U keycloak -d keycloak -At -c "
            SELECT id
            FROM user_entity
            WHERE username LIKE 'project-%-system-user'
              AND lower(coalesce(last_name, '')) = 'system'
            ORDER BY id;
        ")

    if [[ -n "$project_system_ids" ]]; then
        project_system_cte=$(printf "%s\n" "$project_system_ids" | awk '
            BEGIN {
                printf "project_system_users(keycloak_id) AS (VALUES "
            }
            {
                gsub(/\047/, "\047\047", $0)
                if (NR > 1) {
                    printf ","
                }
                printf "(\047%s\047)", $0
            }
            END {
                printf "),"
            }
        ')
    else
        project_system_cte="project_system_users(keycloak_id) AS (SELECT NULL::varchar WHERE FALSE),"
    fi

    echo "Migrating legacy AII admin role mappings via AII database..."
    migration_output=$(kubectl exec -n "$SERVICES_NAMESPACE" -c postgres "deploy/$aii_db_deploy" -- \
        psql -v ON_ERROR_STOP=1 -U kaapanauser -d kaapanauser -At -F '|' -c "
            WITH
            ${excluded_cte}
            ${project_system_cte}
            admin_role AS (
                SELECT id
                FROM roles
                WHERE name = 'admin'
            ),
            scientist_role AS (
                SELECT id
                FROM roles
                WHERE name = 'scientist'
            ),
            principal_investigator_role AS (
                SELECT id
                FROM roles
                WHERE name = 'principal-investigator'
            ),
            -- Legacy project system users should keep the elevated role that is
            -- assigned to newly created project system users.
            legacy_admin_rows AS (
                SELECT
                    upr.id,
                    upr.project_id,
                    upr.keycloak_id,
                    CASE
                        WHEN psu.keycloak_id IS NOT NULL THEN (SELECT id FROM principal_investigator_role)
                        ELSE (SELECT id FROM scientist_role)
                    END AS target_role_id
                FROM users_projects_roles upr
                JOIN admin_role ar ON upr.role_id = ar.id
                LEFT JOIN excluded_users eu ON eu.keycloak_id = upr.keycloak_id
                LEFT JOIN project_system_users psu ON psu.keycloak_id = upr.keycloak_id
                WHERE eu.keycloak_id IS NULL
            ),
            duplicate_rows AS (
                SELECT lar.id
                FROM legacy_admin_rows lar
                JOIN users_projects_roles upr
                  ON upr.project_id = lar.project_id
                 AND upr.keycloak_id = lar.keycloak_id
                 AND upr.role_id = lar.target_role_id
            ),
            deleted_duplicates AS (
                DELETE FROM users_projects_roles
                WHERE id IN (SELECT id FROM duplicate_rows)
                RETURNING id
            ),
            updated_rows AS (
                UPDATE users_projects_roles upr
                SET role_id = lar.target_role_id
                FROM legacy_admin_rows lar
                WHERE upr.id = lar.id
                  AND lar.id NOT IN (SELECT id FROM duplicate_rows)
                RETURNING upr.id
            ),
            remaining_legacy_rows AS (
                SELECT upr.id
                FROM users_projects_roles upr
                JOIN admin_role ar ON upr.role_id = ar.id
                LEFT JOIN excluded_users eu ON eu.keycloak_id = upr.keycloak_id
                WHERE eu.keycloak_id IS NULL
            )
            SELECT
                (SELECT count(*) FROM legacy_admin_rows),
                (SELECT count(*) FROM deleted_duplicates),
                (SELECT count(*) FROM updated_rows),
                (SELECT count(*) FROM remaining_legacy_rows),
                (SELECT count(*) FROM admin_role),
                (SELECT count(*) FROM scientist_role),
                (SELECT count(*) FROM principal_investigator_role);
        ")
    migration_output=$(echo "$migration_output" | tail -n1)

    IFS='|' read -r legacy_count deleted_duplicate_count updated_count remaining_count admin_role_count scientist_role_count pi_role_count <<< "$migration_output"

    if [[ -z "$legacy_count" || ! "$legacy_count" =~ ^[0-9]+$ ]]; then
        echo "ERROR: Could not determine the AII role migration result."
        return 1
    fi
    if [[ "$admin_role_count" -ne 1 || "$scientist_role_count" -ne 1 || "$pi_role_count" -ne 1 ]]; then
        echo "ERROR: Expected exactly one admin role, one scientist role and one principal-investigator role in AII."
        return 1
    fi
    if [[ "$remaining_count" -ne 0 ]]; then
        echo "ERROR: Verification failed for AII role migration. $remaining_count legacy admin mappings remain for non-excluded users."
        return 1
    fi

    excluded_count=$(printf "%s\n" "$excluded_ids" | sed '/^$/d' | wc -l | tr -d '[:space:]')
    echo "Excluded $excluded_count Keycloak users from AII role migration."
    echo "Found $legacy_count legacy admin mappings for non-excluded users."
    echo "Deleted $deleted_duplicate_count duplicate legacy admin mappings."
    echo "Updated $updated_count legacy admin mappings to their target roles."
    echo "Verified AII role migration state."
}

main() {
    patch_msad_account_control_mapper
    migrate_legacy_aii_admin_roles
}

main
