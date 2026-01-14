#!/bin/bash
# WARNING: This script is deprecated and will be removed in the next Kaapana release.
# Please migrate to `./kaapanactl deploy`, which supports the same options.
set -euf -o pipefail
export HELM_EXPERIMENTAL_OCI=1
# if unusual home dir of user: sudo dpkg-reconfigure apparmor

######################################################
# Executable configurations
######################################################
HELM_EXECUTABLE="${HELM_EXECUTABLE:-helm}"

######################################################
# Main platform configuration
######################################################

PLATFORM_NAME="{{ platform_name }}" # name of the platform Helm chart
PLATFORM_VERSION="{{ platform_build_version }}" # Specific version or empty for dialog

CONTAINER_REGISTRY_URL="{{ container_registry_url|default('', true) }}" # empty for local build or registry-url like 'dktk-jip-registry.dkfz.de/kaapana' or 'registry.hzdr.de/kaapana/kaapana'
CONTAINER_REGISTRY_USERNAME="{{ container_registry_username|default('', true) }}"
CONTAINER_REGISTRY_PASSWORD="{{ container_registry_password|default('', true) }}"
PLAIN_HTTP={{ plain_http|default(false)|lower }} # Use plain HTTP for registry (insecure)

######################################################
# Deployment configuration
######################################################

 # dev-mode -> containers will always be re-downloaded after pod-restart
DEV_MODE={{ dev_mode|default(true)|lower }}
GPU_SUPPORT={{ gpu_support|default(false)|lower }}
# Adjust enable nvidia command if using GPU Operator below v25.10.0+
GPU_OPERATOR_VERSION="v25.10.0"
PREFETCH_EXTENSIONS={{prefetch_extensions|default('false')|lower}}
CHART_PATH=""
NO_HOOKS=""
OFFLINE_MODE=false

INSTANCE_UID=""
SERVICES_NAMESPACE="{{ services_namespace }}"
ADMIN_NAMESPACE="{{ admin_namespace }}"
EXTENSIONS_NAMESPACE="{{ extensions_namespace }}"
HELM_NAMESPACE="{{ helm_namespace }}"

OIDC_CLIENT_SECRET=$(echo $RANDOM | md5sum | base64 | head -c 32)

INCLUDE_REVERSE_PROXY=false
MIGRATION_ENABLED=true

######################################################
# Resource configurations
######################################################

# Memory percentages for PACS, Airflow, and OpenSearch.
PACS_PERCENT="30"
AIRFLOW_PERCENT="50"
OPENSEARCH_PERCENT="20"
TOTAL_PERCENT=$((PACS_PERCENT + AIRFLOW_PERCENT + OPENSEARCH_PERCENT))

# Get allocatable RAM (70% of total free memory)
TOTAL_MEMORY=$(free -m | awk '/^Mem:/{print $2}')
ALLOCATABLE_MEMORY=$((TOTAL_MEMORY * 70 / 100))

# Set max memory limits for components
PACS_MEMORY_LIMIT=$((ALLOCATABLE_MEMORY * PACS_PERCENT / TOTAL_PERCENT))
AIRFLOW_MEMORY_LIMIT=$((ALLOCATABLE_MEMORY * AIRFLOW_PERCENT / TOTAL_PERCENT))
OPENSEARCH_MEMORY_LIMIT=$((ALLOCATABLE_MEMORY * OPENSEARCH_PERCENT / TOTAL_PERCENT))

# Set memory min requests (1/3 of limit)
PACS_MEMORY_REQUEST=$((PACS_MEMORY_LIMIT / 3))
AIRFLOW_MEMORY_REQUEST=$((AIRFLOW_MEMORY_LIMIT / 3))
OPENSEARCH_MEMORY_REQUEST=$((OPENSEARCH_MEMORY_LIMIT / 3))

######################################################
# Individual platform configuration
######################################################
CREDENTIALS_MINIO_USERNAME="{{ credentials_minio_username|default('kaapanaminio', true) }}"
CREDENTIALS_MINIO_PASSWORD="{{ credentials_minio_password|default('Kaapana2020', true) }}"

GRAFANA_USERNAME="{{ credentials_grafana_username|default('admin', true) }}"
GRAFANA_PASSWORD="{{ credentials_grafana_password|default('admin', true) }}"

KEYCLOAK_ADMIN_USERNAME="{{ credentials_keycloak_admin_username|default('admin', true) }}"
KEYCLOAK_ADMIN_PASSWORD="{{ credentials_keycloak_admin_password|default('Kaapana2020', true) }}" #  Minimum policy for production: 1 specialChar + 1 upperCase + 1 lowerCase and 1 digit + min-length = 8

FAST_DATA_DIR="{{ fast_data_dir|default('/home/kaapana')}}" # Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
SLOW_DATA_DIR="{{ slow_data_dir|default('/home/kaapana')}}" # Directory on the server, where the DICOM images will be stored (can be slower)

HTTP_PORT="{{ http_port|default(80)|int }}"      # -> has to be 80
HTTPS_PORT="{{ https_port|default(443) }}"    # HTTPS port
DICOM_PORT="{{ dicom_port|default(11112) }}"  # configure DICOM receiver port

SMTP_HOST="{{ smtp_host|default('')}}"
SMTP_PORT="{{ smtp_port|default(0)|int }}"
EMAIL_ADDRESS_SENDER="{{ email_address_sender|default('')}}"
SMTP_USERNAME="{{ smtp_username|default('')}}"
SMTP_PASSWORD="{{ smtp_password|default('')}}"

VERSION_IMAGE_COUNT="20"
DEPLOYMENT_TIMESTAMP=`date  --iso-8601=seconds`
MOUNT_POINTS_TO_MONITOR="{{ mount_points_to_monitor }}"

INSTANCE_NAME="{{ instance_name|default('') }}"


STORAGE_PROVIDER="{{ smtp_host|default('hostpath')}}" # e.g. "hostpath" (microk8s) or "longhorn
# volume sizes relevant if STORAGE_PROVIDER is set to longhorn
VOLUME_SLOW_DATA="{{ volume_slow_data|default('100Gi') }}" #size of volumes in slow data dir (e.g. 100Gi or 100Ti)
REPLICA_COUNT=1
echo "Checking for storage provider: ${STORAGE_PROVIDER}"

is_provider_installed=false

case "${STORAGE_PROVIDER}" in
  "driver.longhorn.io"|"longhorn")
    # Check Longhorn CSI driver
    if microk8s.kubectl get csidriver driver.longhorn.io &>/dev/null; then
      is_provider_installed=true
    fi
    STORAGE_PROVIDER="driver.longhorn.io"
    ;;

  "microk8s.io/hostpath"|"hostpath"|"microk8s")
    # Check hostpath storage class
    if microk8s.kubectl get storageclass | grep -q "microk8s-hostpath"; then
      is_provider_installed=true
    fi
    STORAGE_PROVIDER="microk8s.io/hostpath"
    ;;

  *)
    echo "ERROR: Unknown storage provider '${STORAGE_PROVIDER}'."
    echo "Supported providers: microk8s.io/hostpath, longhorn"
    exit 1
    ;;
esac

if [ "$is_provider_installed" = false ]; then
  echo "ERROR: Storage provider '${STORAGE_PROVIDER}' is not installed in the cluster."
  echo "Please install it before proceeding."
  echo "Example: microk8s enable hostpath-storage   or   helm install longhorn longhorn/longhorn ..."
  exit 1
fi

echo "✅ Storage provider '${STORAGE_PROVIDER}' found."

MAIN_NODE_NAME=$(microk8s.kubectl get pods -n kube-system -o jsonpath='{.items[0].spec.nodeName}')
echo "Main node is $MAIN_NODE_NAME"
STORAGE_NODE="storage"
microk8s.kubectl label nodes "$MAIN_NODE_NAME" "kaapana.io/node"="$STORAGE_NODE" --overwrite
# --- Set storage classes based on provider ---
case "${STORAGE_PROVIDER}" in
  "microk8s.io/hostpath")
    STORAGE_CLASS_SLOW="kaapana-hostpath-slow-data-dir"
    STORAGE_CLASS_FAST="kaapana-hostpath-fast-data-dir"
    STORAGE_CLASS_WORKFLOW="kaapana-hostpath-fast-data-dir"
    if [ -z "${VOLUME_SLOW_DATA}" ]; then
        VOLUME_SLOW_DATA="10Gi"
    fi
    ;;
  "driver.longhorn.io")
    STORAGE_CLASS_SLOW="kaapana-longhorn-slow-data"
    STORAGE_CLASS_FAST="kaapana-longhorn-fast-db"
    STORAGE_CLASS_WORKFLOW="kaapana-longhorn-fast-workflow"

    if [ -z "${VOLUME_SLOW_DATA}" ]; then
        echo "${VOLUME_SLOW_DATA}" must be set for Longhorn storage provider.
        exit 1
    fi

    FSID_DEFAULT=$(stat -fc %i /var/lib/longhorn)
    FSID_FAST=$(stat -fc %i "$(dirname "${FAST_DATA_DIR}")")
    FSID_SLOW=$(stat -fc %i "$(dirname "${SLOW_DATA_DIR}")")

    PATCH_DISKS="{}"
    DISK_NAME_FAST=""

    # FAST_DATA_DIR
    if [[ "$FSID_FAST" == "$FSID_DEFAULT" ]]; then
        echo "⚠️ fast-data shares filesystem with default Longhorn disk."
        PATCH_DISKS=$(jq ".disks.\"default-disk-${FSID_DEFAULT}\".tags += [\"fast-data\"]" <<< "$PATCH_DISKS")
        DISK_NAME_FAST="default-disk-${FSID_DEFAULT}"
    else
        PATCH_DISKS=$(jq ".disks.\"fast-data\" = {\"path\": \"${FAST_DATA_DIR}\", \"allowScheduling\": true, \"tags\": [\"fast-data\"]}" <<< "$PATCH_DISKS")
        DISK_NAME_FAST="fast-data"
    fi

    # SLOW_DATA_DIR
    if [[ "$FSID_SLOW" == "$FSID_FAST" ]]; then
        echo "⚠️ slow-data shares filesystem with fast-data."
        PATCH_DISKS=$(jq ".disks.\"$DISK_NAME_FAST\".tags += [\"slow-data\"]" <<< "$PATCH_DISKS")
    elif [[ "$FSID_SLOW" == "$FSID_DEFAULT" ]]; then
        echo "⚠️ slow-data shares filesystem with default Longhorn disk."
        PATCH_DISKS=$(jq ".disks.\"default-disk-${FSID_DEFAULT}\".tags += [\"slow-data\"]" <<< "$PATCH_DISKS")
    else
        PATCH_DISKS=$(jq ".disks.\"slow-data\" = {\"path\": \"${SLOW_DATA_DIR}\", \"allowScheduling\": true, \"tags\": [\"slow-data\"]}" <<< "$PATCH_DISKS")
    fi

    # Apply the patch
    microk8s.kubectl patch node.longhorn.io "${MAIN_NODE_NAME}" -n longhorn-system --type merge -p "{\"spec\":$PATCH_DISKS}"

    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to patch disks for ${MAIN_NODE_NAME}"
        exit 1
    fi
    echo "✅ Patched disks for ${MAIN_NODE_NAME}"

    echo "Patching Longhorn settings for overprovisioning and minimal free space..."

    # Allow thin provisioning (10× real capacity)
    if [ "${DEV_MODE,,}" == "true" ]; then
        THIN_PROVISIONING="1000"
    else
        THIN_PROVISIONING="1000000"
    fi

    microk8s.kubectl -n longhorn-system patch setting storage-over-provisioning-percentage \
    --type=merge -p "{\"value\":\"${THIN_PROVISIONING}\"}"

    # Allow scheduling even when less than 5% disk space is free
    microk8s.kubectl -n longhorn-system patch setting storage-minimal-available-percentage \
      --type=merge -p '{"value":"5"}'

    echo "✅ Longhorn overprovisioning settings applied successfully."

    # Detect how many Longhorn nodes are schedulable
    SCHEDULABLE_NODES=$(microk8s.kubectl -n longhorn-system get node.longhorn.io \
    -o jsonpath='{range .items[?(@.spec.allowScheduling==true)]}{.metadata.name}{"\n"}{end}' | wc -l)

    # Determine replica count based on node count
    if (( SCHEDULABLE_NODES > 1 )); then
        REPLICA_COUNT=2
    fi
    ;;
esac


{% for item in additional_env %}
{{ item.name }}="{{ item.default_value }}"{% if item.comment %} # {{item.comment}}{% endif %}
{%- endfor %}

######################################################

if [ -z ${http_proxy+x} ] || [ -z ${https_proxy+x} ]; then
    http_proxy=""
    https_proxy=""
fi


if [ ! -z $INSTANCE_UID ]; then
    echo ""
    echo "Setting INSTANCE_UID: $INSTANCE_UID namespaces ..."
    SERVICES_NAMESPACE="$INSTANCE_UID-$SERVICES_NAMESPACE"
    # ADMIN_NAMESPACE="$INSTANCE_UID-$ADMIN_NAMESPACE"
    EXTENSIONS_NAMESPACE="$INSTANCE_UID-$EXTENSIONS_NAMESPACE"
    HELM_NAMESPACE="$INSTANCE_UID-$HELM_NAMESPACE"

    FAST_DATA_DIR="$FAST_DATA_DIR-$INSTANCE_UID"
    SLOW_DATA_DIR="$SLOW_DATA_DIR-$INSTANCE_UID"

    INCLUDE_REVERSE_PROXY=true
fi
echo ""
echo "HELM_NAMESPACE:       $HELM_NAMESPACE "
echo "ADMIN_NAMESPACE:      $ADMIN_NAMESPACE "
echo "SERVICES_NAMESPACE:   $SERVICES_NAMESPACE "
echo "EXTENSIONS_NAMESPACE: $EXTENSIONS_NAMESPACE "
echo ""
echo "FAST_DATA_DIR: $FAST_DATA_DIR "
echo "SLOW_DATA_DIR: $SLOW_DATA_DIR "
echo ""

script_name=`basename "$0"`

# set default values for the colors
BOLD=""
underline=""
standout=""
NC=""
BLACK=""
RED=""
GREEN=""
YELLOW=""
BLUE=""
MAGENTA=""
CYAN=""
WHITE=""
# check if stdout is a terminal...
if test -t 1; then
    # see if it supports colors...
    ncolors=$(tput colors)

    if test -n "$ncolors" && test $ncolors -ge 8; then
        BOLD="$(tput bold)"
        underline="$(tput smul)"
        standout="$(tput smso)"
        NC="$(tput sgr0)"
        BLACK="$(tput setaf 0)"
        RED="$(tput setaf 1)"
        GREEN="$(tput bold)$(tput setaf 2)"
        YELLOW="$(tput bold)$(tput setaf 3)"
        BLUE="$(tput bold)$(tput setaf 4)"
        MAGENTA="$(tput bold)$(tput setaf 5)"
        CYAN="$(tput bold)$(tput setaf 6)"
        WHITE="$(tput bold)$(tput setaf 7)"
    fi
fi

if command -v nvidia-smi &> /dev/null && nvidia-smi
then
    echo "${GREEN}Nvidia GPU detected!${NC}"
    GPU_SUPPORT=true
else
    echo "${YELLOW}No GPU detected...${NC}"
    GPU_SUPPORT=false
fi

function delete_all_images_docker {
    while true; do
        read -e -p "Do you really want to remove all the Docker images from the system?" -i " no" yn
        case $yn in
            [Yy]* ) echo "${GREEN}Removing all images...${NC}" && docker system prune --volumes --all && echo "${GREEN}Done.${NC}"; break;;
            [Nn]* ) echo "${YELLOW}Images will be kept${NC}"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

function delete_all_images_microk8s {
    while true; do
        read -e -p "Do you really want to remove all the container images from Microk8s?" -i " no" yn
        case $yn in
            [Yy]* ) echo "${GREEN}Removing all images...${NC}" && microk8s.ctr images ls | awk {'print $1'} | xargs microk8s.ctr images rm && echo "${GREEN}Done.${NC}"; break;;
            [Nn]* ) echo "${YELLOW}Images will be kept${NC}"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}




function get_domain {

    if [ -z ${DOMAIN+x} ]; then
        echo -e ""
        echo -e "${YELLOW}Get Server IP ...${NC}";
        SERVER_IP=$(hostname -I | awk -F ' ' '{print $1}')
        echo -e "${YELLOW}SERVER_IP: $SERVER_IP${NC}";
        echo -e "${YELLOW}NS lookup DOMAIN ...${NC}";
        # get nslookup result, use || true to ensure script doesn't exit immediately is cmd fails
        NSLOOKUP_RESULT=$(nslookup "$SERVER_IP" || true)
        if [[ -z "$NSLOOKUP_RESULT" || "$NSLOOKUP_RESULT" == *"server can't find"* ]]; then
            echo -e "NS lookup failed, could not determine DOMAIN from SERVER_IP. Run the script with explicit domain name: ./deploy_platform.sh --domain <domain-name>"
            exit 1
        fi
        DOMAIN=$(echo "$NSLOOKUP_RESULT" | head -n 1 | awk -F '= ' '{print $2}')
        DOMAIN=${DOMAIN%.*}
        echo -e "${YELLOW}DOMAIN: $DOMAIN${NC}";
    else
        echo -e "${GREEN}Server domain (FQDN): $DOMAIN ${NC}" > /dev/stderr;
    fi

    if [ ! "$QUIET" = "true" ];then
        echo -e ""
        echo -e "${YELLOW}Please enter the domain (FQDN) of the server.${NC}" > /dev/stderr;
        echo -e "${YELLOW}The suggestion could be incorrect!${NC}" > /dev/stderr;
        echo -e "${YELLOW}The IP address should work as well (not recommended - will not work with valid certificates.)${NC}" > /dev/stderr;
        read -e -p "**** server domain (FQDN): " -i "$DOMAIN" DOMAIN
    else
        echo -e "${GREEN}QUIET: true -> DOMAIN: $DOMAIN ${NC}" > /dev/stderr;
    fi

    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}DOMAIN not set!";  > /dev/stderr;
        echo -e "Please restart the process. ${NC}";  > /dev/stderr;
        exit 1
    else
        echo -e "${GREEN}Server domain (FQDN): $DOMAIN ${NC}" > /dev/stderr;
    fi
}

function delete_deployment {
    echo -e "${YELLOW}Undeploy releases${NC}"
    for namespace in $ADMIN_NAMESPACE $HELM_NAMESPACE; do
        $HELM_EXECUTABLE -n $namespace ls --deployed --failed --pending --superseded --uninstalling --date --reverse | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -I % sh -c "$HELM_EXECUTABLE -n $namespace uninstall ${NO_HOOKS} --wait --timeout 5m30s %; sleep 2"
    done

    echo -e "${YELLOW}Waiting until everything is terminated ...${NC}"
    WAIT_UNINSTALL_COUNT=100
    for idx in $(seq 0 $WAIT_UNINSTALL_COUNT)
    do
        sleep 3
        if [ "$idx" -eq 2 ]; then
            echo "Deleting helm charts in 'uninstalling' state with --no-hooks"
            $HELM_EXECUTABLE -n $namespace ls --uninstalling | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -I % sh -c "$HELM_EXECUTABLE -n $namespace uninstall --no-hooks --wait --timeout 5m30s %; sleep 2"
        fi
        TERMINATING_PODS=$(/bin/bash -i -c "kubectl get pods --all-namespaces | grep -E 'Terminating' | awk '{print \$1 \"/\" \$2}'")
        echo -e ""
        UNINSTALL_TEST=$TERMINATING_PODS
        if [ -z "$UNINSTALL_TEST" ]; then
            break
        else
            echo -e "${YELLOW}Waiting for $TERMINATING_PODS ${NC}"
        fi
    done

    echo -e "${YELLOW}Cleaning up orphaned pods in Kubernetes namespaces ...${NC}"
    
    # Clean SERVICES_NAMESPACE
    if microk8s.kubectl get namespace $SERVICES_NAMESPACE &>/dev/null; then
        echo "Deleting all pods in $SERVICES_NAMESPACE"
        microk8s.kubectl delete pods --all -n $SERVICES_NAMESPACE --grace-period=0 --force 2>/dev/null || true
    fi
    
    # Clean all project-* namespaces
    PROJECT_NAMESPACES=$(microk8s.kubectl get namespaces --no-headers -o custom-columns=NAME:.metadata.name | grep "^project-")
    for ns in $PROJECT_NAMESPACES; do
        echo "Deleting all pods in $ns"
        microk8s.kubectl delete pods --all -n $ns --grace-period=0 --force 2>/dev/null || true
    done
    

    if [ "$idx" -eq "$WAIT_UNINSTALL_COUNT" ]; then
        echo "${RED}Something went wrong while undeployment please check manually if there are still namespaces or pods floating around. Everything must be delete before the deployment:${NC}"
        echo "${RED}kubectl get pods -A${NC}"
        echo "${RED}kubectl get namespaces${NC}"
        echo "${RED}Executing './deploy_platform.sh --no-hooks' is an option to force the resources to be removed.${NC}"
        echo "${RED}Once everything is deleted you can re-deploy the platform!${NC}"
        exit 1
    fi


    echo -e "${GREEN}####################################  UNDEPLOYMENT DONE  ############################################${NC}"
}

function nuke_pods {
    for namespace in $EXTENSIONS_NAMESPACE $SERVICES_NAMESPACE $ADMIN_NAMESPACE $HELM_NAMESPACE; do
        echo "${RED}Deleting all pods from namespaces: $namespace ...${NC}";
        for mypod in $(microk8s.kubectl get pods -n $namespace -o jsonpath="{.items[*].metadata.name}");
        do
            echo "${RED}Deleting: $mypod ${NC}";
            microk8s.kubectl delete pod -n $namespace $mypod --grace-period=0 --force
        done
    done
}


function clean_up_kubernetes {
    # for n in $EXTENSIONS_NAMESPACE; # $HELM_NAMESPACE;
    # do
    #     echo "${YELLOW}Deleting namespace ${n} with all its resources ${NC}"
    #     microk8s.kubectl delete --ignore-not-found namespace $n
    # done
    echo "${YELLOW}Deleting all deployments in namespace default ${NC}"
    microk8s.kubectl delete deployments --all
    echo "${YELLOW}Deleting all jobs in namespace default ${NC}"
    microk8s.kubectl delete jobs --all
    echo "${YELLOW}Removing remove-secret job${NC}"
    microk8s.kubectl -n $SERVICES_NAMESPACE delete job --ignore-not-found remove-secret
    #echo "${YELLOW}Removing all volumes in kubernetes ${NC}"
    #microk8s.kubectl delete volumes -A --all
}

function import_container_images_tar {
    echo "${RED}Importing the images from the tar, this might take a long time -> please be patient and wait.${NC}"
    microk8s.ctr images import $TAR_PATH
    echo "${GREEN}Finished image upload! You should now be able to deploy the platform by specifying the chart path.${NC}"
}

function run_migration_chart() {
    local FROM_VERSION="$1"
    local TO_VERSION="$2"

    echo -e "${YELLOW}Deploying migration chart: $FROM_VERSION -> $TO_VERSION${NC}"

    WORKDIR=$(mktemp -d)
    tar -xzf "$CHART_PATH" -C "$WORKDIR"

    MIGRATION_CHART_PATH="$WORKDIR/$PLATFORM_NAME/charts/migration-chart"
    if [[ ! -d "$MIGRATION_CHART_PATH" ]]; then
        echo -e "${RED}Migration chart not found inside chart package!${NC}"
        exit 1
    fi

    # Build helm command with optional --plain-http flag
    HELM_CMD="$HELM_EXECUTABLE -n $HELM_NAMESPACE upgrade --install"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_CMD="$HELM_CMD --plain-http"
    fi
    
    $HELM_CMD kaapana-migration "$MIGRATION_CHART_PATH" \
        --set-string global.credentials_registry_username="$CONTAINER_REGISTRY_USERNAME" \
        --set-string global.credentials_registry_password="$CONTAINER_REGISTRY_PASSWORD" \
        --set-string global.fast_data_dir="$FAST_DATA_DIR" \
        --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
        --set-string global.pull_policy_images="$PULL_POLICY_IMAGES" \
        --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
        --set-string global.kaapana_build_version="$PLATFORM_VERSION" \
        --set-string global.from_version="$FROM_VERSION" \
        --set-string global.to_version="$TO_VERSION"

    # Wait for migration job to finish
    local JOB_NAME="migration"
    local NAMESPACE="migration"
    local TIMEOUT=600
    local INTERVAL=5
    local ELAPSED=0

    cleanup() {
        echo -e "${YELLOW}Cleaning up migration helm chart...${NC}"
        $HELM_EXECUTABLE uninstall "kaapana-migration" -n "$HELM_NAMESPACE" || true
    }

    echo -e "${YELLOW}Waiting for migration job $JOB_NAME to complete...${NC}"
        while true; do
        local SUCCEEDED=$(microk8s.kubectl get job "$JOB_NAME" -n "$NAMESPACE" -o jsonpath='{.status.succeeded}')
        local FAILED=$(microk8s.kubectl get job "$JOB_NAME" -n "$NAMESPACE" -o jsonpath='{.status.failed}')

        if [[ "${SUCCEEDED:-0}" -ge 1 ]]; then
            echo -e "${GREEN}Migration job completed successfully!${NC}"
            PODS=$(microk8s.kubectl get pods -n "$NAMESPACE" -l job-name="$JOB_NAME" -o name)
            for pod in $PODS; do
                microk8s.kubectl logs "$pod" -n "$NAMESPACE"
            done
            cleanup
            break
        elif [[ "${FAILED:-0}" -ge 1 ]]; then
            VERSION_STATUS=""
            # Safely read the status from the version file
            if [ -f "$FAST_DATA_DIR/.version" ]; then
                VERSION_STATUS=$(cat "$FAST_DATA_DIR/.version")
            fi

            if [[ "$VERSION_STATUS" == *"- fresh deploy and redeploy-needed"* ]]; then
                echo -e "\n${YELLOW}================================================================${NC}"
                echo -e "${YELLOW}🚨 MIGRATION PAUSED: FRESH DEPLOYMENT REQUIRED 🚨${NC}"
                echo -e "${YELLOW}================================================================${NC}"
                echo "The existing PVCs are not configured for migration."
                echo "1. Complete the current deployment (let the platform fully start)."
                echo "2. Once the platform is functional, run the deployment script again."
                echo -e "\nDo you want to proceed with the required steps (Y/n) or start fresh (F)? [Y/n/F]"
                read -r USER_CHOICE

                case "$USER_CHOICE" in
                    [Yy]* )
                        echo "Continuing with the required redeployment path. Please run the script again after the initial deploy."
                        exit 0 # Exit successfully, but signal a partial completion/pause.
                        ;;
                    [Ff]* )
                        echo "Starting fresh. The data folder flag will be removed."
                        # Remove the flag, allowing the next deployment to proceed without migration attempts
                        if [ -f "$FAST_DATA_DIR/.version" ]; then
                            sed -i '' '/- fresh deploy and redeploy-needed/d' "$FAST_DATA_DIR/.version" 2>/dev/null || \
                            sed -i '/- fresh deploy and redeploy-needed/d' "$FAST_DATA_DIR/.version" # Linux/GNU sed fallback
                        fi
                        exit 0 # Exit successfully, allowing the main deploy to continue as a fresh install.
                        ;;
                    * )
                        echo "Exiting without changes. Please run the script again when ready."
                        exit 1
                        ;;
                esac
            else
                echo -e "${RED}Migration job failed!${NC}"
                PODS=$(microk8s.kubectl get pods -n "$NAMESPACE" -l job-name="$JOB_NAME" -o name)
                for pod in $PODS; do
                    microk8s.kubectl logs "$pod" -n "$NAMESPACE"
                done

                POD=$(microk8s.kubectl get pods -n "$NAMESPACE" -l job-name="$JOB_NAME" -o jsonpath='{.items[*].metadata.name}')
                microk8s.kubectl logs "$POD" -n "$NAMESPACE"
                cleanup
                exit 1
            fi
        fi

        sleep "$INTERVAL"
        ELAPSED=$((ELAPSED + INTERVAL))
        if [[ $ELAPSED -ge $TIMEOUT ]]; then
            echo -e "${RED}Migration job did not complete within ${TIMEOUT}s${NC}"
            exit 1
        fi
    done
}

function prompt_user_backup() {
    echo -e "${YELLOW}Please BACKUP your data directory first${NC}"
    echo "   cp -a $FAST_DATA_DIR /path/to/fast/backup"
    echo "   cp -a $SLOW_DATA_DIR /path/to/slow/backup"
    echo
    while true; do
        read -p "Proceed with migration? (yes/no/skip): " answer
        case "$answer" in
            [Yy][Ee][Ss]|[Yy])
                echo "✅ Proceeding with migration..."
                return 0
                ;;
            [Nn][Oo]|[Nn])
                echo "❌ Aborting deployment."
                exit 1
                ;;
            [Ss][Kk][Ii][Pp]|[Ss])
                echo "⚠️  Skipping migration - continuing without migration."
                return 1
                ;;
            *)
                echo "Please type 'yes', 'no', or 'skip'."
                ;;
        esac
    done
}

function migrate() {
    VERSION_FILE="$FAST_DATA_DIR/version"

    echo "${YELLOW}Checking ${VERSION_FILE} status...${NC}"

    if [[ ! -d "$FAST_DATA_DIR" || -z "$(ls -A "$FAST_DATA_DIR" 2>/dev/null)" ]]; then
        echo "${GREEN}Fresh installation detected.${NC}"
        echo "${GREEN}Skipping migration for fresh installation. Version file will be created during deployment.${NC}"

    elif [[ -f "$VERSION_FILE" ]]; then
        CURRENT_VERSION=$(cat "$VERSION_FILE")
        echo "${GREEN}Found version: $CURRENT_VERSION${NC}"
        echo "${GREEN}Target version: $PLATFORM_VERSION${NC}"
        
        # Extract major.minor (ignore patch and build metadata)
        CURRENT_MAJOR_MINOR=$(echo "$CURRENT_VERSION" | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')
        PLATFORM_MAJOR_MINOR=$(echo "$PLATFORM_VERSION" | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')

        if [[ "$CURRENT_MAJOR_MINOR" == "$PLATFORM_MAJOR_MINOR" ]]; then
            echo "${GREEN}Major.Minor version matches ($CURRENT_MAJOR_MINOR). Skipping migration.${NC}"
        else
            echo "${YELLOW}Major.Minor version mismatch: current=$CURRENT_MAJOR_MINOR, target=$PLATFORM_MAJOR_MINOR.${NC}"

            if [[ "$MIGRATION_ENABLED" == true ]]; then
                echo "${YELLOW}Migration enabled: $CURRENT_VERSION -> $PLATFORM_VERSION.${NC}"
                if prompt_user_backup; then
                    run_migration_chart "$CURRENT_VERSION" "$PLATFORM_VERSION"
                else
                    echo "${YELLOW}Migration skipped by user. Continuing deployment without migration.${NC}"
                fi
            else
                echo "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
                echo "${YELLOW}║                    ⚠️  WARNING                                 ║${NC}"
                echo "${YELLOW}║ Version mismatch detected but migration is DISABLED           ║${NC}"
                echo "${YELLOW}║ Current: $CURRENT_VERSION → Target: $PLATFORM_VERSION                                   ║${NC}"
                echo "${YELLOW}║                                                                ║${NC}"
                echo "${YELLOW}║ Migration can be enabled by removing the --no-migration flag  ║${NC}"
                echo "${YELLOW}║ Proceeding without migration may cause compatibility issues   ║${NC}"
                echo "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
            fi
        fi

    elif [[ -d "$FAST_DATA_DIR" && -n "$(ls -A "$FAST_DATA_DIR")" ]]; then
        echo "${YELLOW}No version file and directory is not empty!${NC}"
        
        if [[ "$MIGRATION_ENABLED" == true ]]; then
            echo "Options:"
            echo "  1. Let migration-chart autodetect version using $FAST_DATA_DIR/extensions/kaapana-platform-chart-<version>.tgz"
            echo "  2. Exit to manually create $VERSION_FILE with correct version and rerun the deploy script."
            echo "  Generate the file with:"
            echo "    echo \"<0.5.3>\" > $VERSION_FILE"
            read -p "Choose option (1/2): " choice
            if [[ "$choice" == "1" ]]; then
                if prompt_user_backup; then
                    run_migration_chart "autodetect" "$PLATFORM_VERSION"
                else
                    echo "${YELLOW}Migration skipped by user. Continuing deployment without migration.${NC}"
                fi
            else
                echo "${RED}Please create the version file manually and rerun.${NC}"
                exit 1
            fi
        else
            echo "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
            echo "${YELLOW}║                    ⚠️  WARNING                                 ║${NC}"
            echo "${YELLOW}║ Version file missing but directory is not empty               ║${NC}"
            echo "${YELLOW}║                                                                ║${NC}"
            echo "${YELLOW}║ Migration can be enabled with the --migration flag            ║${NC}"
            echo "${YELLOW}║ Continuing without migration - version file will be created   ║${NC}"
            echo "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
        fi
    else
        echo "Unexpected state. Please check $FAST_DATA_DIR."
        exit 1
    fi
}

function deploy_chart {
    if [ -z "$CONTAINER_REGISTRY_URL" ]; then
        echo "${RED}CONTAINER_REGISTRY_URL needs to be set! -> please adjust the deploy_platform.sh script!${NC}"
        echo "${RED}ABORT${NC}"
        exit 1
    fi

    if [ "${OFFLINE_MODE,,}" == true ] && [ -z "$CHART_PATH" ]; then
        echo "${RED}ERROR: CHART_PATH needs to be set when in OFFLINE_MODE!${NC}"
        exit 1
    fi

    get_domain

    if [ -z "$INSTANCE_NAME" ]; then
        INSTANCE_NAME=$DOMAIN
        echo "${YELLOW}No INSTANCE_NAME is set, setting it to $DOMAIN!${NC}"
    fi

    if [ "${GPU_SUPPORT,,}" == true ];then
        echo -e "${GREEN} -> GPU found ...${NC}"
    else
        if [ ! "$QUIET" = "true" ];then
            while true; do
                read -e -p "No Nvidia GPU detected - Enable GPU support anyway?" -i " no" yn
                case $yn in
                    [Yy]* ) echo -e "${GREEN}ENABLING GPU SUPPORT${NC}" && GPU_SUPPORT=true; break;;
                    [Nn]* ) echo -e "${YELLOW}SET NO GPU SUPPORT${NC}" && GPU_SUPPORT=false; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
        else
            echo -e "${YELLOW}QUIET-MODE active!${NC}"
        fi
    fi

    echo -e "${YELLOW}GPU_SUPPORT: $GPU_SUPPORT ${NC}"
    if [ "${GPU_SUPPORT,,}" == true ];then
        echo -e "-> enabling GPU in Microk8s ..."
        if [[ $deployments == *"gpu-operator"* ]];then
            echo -e "-> gpu-operator chart already exists"
        else
            if [ "${OFFLINE_MODE,,}" == true ];then
                SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
                OFFLINE_ENABLE_GPU_PATH=$SCRIPT_DIR/kaapanactl.sh
                [ -f $OFFLINE_ENABLE_GPU_PATH ] && echo "${GREEN}$OFFLINE_ENABLE_GPU_PATH exists ... ${NC}" || (echo "${RED}$OFFLINE_ENABLE_GPU_PATH does not exist -> exit ${NC}" && exit 1)
                $OFFLINE_ENABLE_GPU_PATH offline-gpu $SCRIPT_DIR
                if [ $? -eq 0 ]; then
                    echo "Offline GPU enabled!"
                else
                    echo "Offline GPU deployment failed!"
                    exit 1
                fi
            else
                
                microk8s enable nvidia --gpu-operator-driver host --gpu-operator-version $GPU_OPERATOR_VERSION \
                    --gpu-operator-set toolkit.env[3].name=RUNTIME_CONFIG_SOURCE --gpu-operator-set toolkit.env[3].value='file=/var/snap/microk8s/current/args/containerd.toml'
            fi
        fi
    fi

    if [ "${DEV_MODE,,}" == true ]; then
        KAAPANA_INIT_PASSWORD="kaapana"
    else
        KAAPANA_INIT_PASSWORD="Kaapana2020!"
    fi

    if [ "${OFFLINE_MODE,,}" == true ] || [ "${DEV_MODE,,}" == false ]; then
        PULL_POLICY_IMAGES="IfNotPresent"
    else
        PULL_POLICY_IMAGES="Always"
    fi

    # configmap kube-public/local-registry-hosting is used by EDK if installed inside Kaapana, therefore should not already exist
    echo "${YELLOW}Removing configmap kube-public/local-registry-hosting if exists...${NC}"
    microk8s.kubectl delete configmap -n kube-public local-registry-hosting --ignore-not-found=true

    if [ ! -z "$CHART_PATH" ]; then # Note: OFFLINE_MODE requires CHART_PATH
        echo -e "${YELLOW}We assume that that all images are already presented inside the microk8s.${NC}"
        echo -e "${YELLOW}Images are uploaded either with a previous deployment from a docker registry or uploaded from a tar or directly uploaded during building the platform.${NC}"

        if [ $(basename "$CHART_PATH") != "$PLATFORM_NAME-$PLATFORM_VERSION.tgz" ]; then
            echo "${RED} Version of chart_path $CHART_PATH differs from PROJECT_NAME: $PLATFORM_NAME and PLATFORM_VERSION: $PLATFORM_VERSION in the deployment script.${NC}"
            exit 1
        fi

        if [ ! "$QUIET" = "true" ];then
            while true; do
            echo -e "${YELLOW}You are deploying the platform in offline mode!${NC}"
                read -p "${YELLOW}Please confirm that you are sure that all images are present in microk8s (yes/no): ${NC}" yn
                    case $yn in
                        [Yy]* ) echo "${GREEN}Confirmed${NC}"; break;;
                        [Nn]* ) echo "${RED}Cancel${NC}"; exit;;
                        * ) echo "Please answer yes or no.";;
                    esac
            done
        else
            echo -e "${GREEN}QUIET: true -> SKIP USER INPUT ${NC}";
        fi

        echo -e "${YELLOW}Checking available images with version: $PLATFORM_VERSION ${NC}"
        set +e
        PRESENT_IMAGE_COUNT=$( microk8s.ctr images ls | grep $PLATFORM_VERSION | wc -l)
        set -e
        echo -e "${YELLOW}PRESENT_IMAGE_COUNT: $PRESENT_IMAGE_COUNT ${NC}"
        if [ "$PRESENT_IMAGE_COUNT" -lt "$VERSION_IMAGE_COUNT" ];then
            echo -e "${RED}There are only $PRESENT_IMAGE_COUNT present with the version $PLATFORM_VERSION - there seems to be an issue. ${NC}"
            exit 1
        else
            echo -e "${GREEN}PRESENT_IMAGE_COUNT: OK ${NC}"
        fi

        PREFETCH_EXTENSIONS=false
        CONTAINER_REGISTRY_USERNAME=""
        CONTAINER_REGISTRY_PASSWORD=""
    else
        echo "${YELLOW}Helm login registry...${NC}"
        check_credentials
        echo "${GREEN}Pulling platform chart from registry...${NC}"
        SCRIPT_PATH=$(dirname "$(realpath $0)")
        pull_chart "$PLATFORM_NAME" "$PLATFORM_VERSION" "$SCRIPT_PATH"
        CHART_PATH="$SCRIPT_PATH/$PLATFORM_NAME-$PLATFORM_VERSION.tgz"
    fi

    # Kubernetes API endpoint
    INTERNAL_CIDR=$(microk8s.kubectl get endpoints kubernetes -n default -o jsonpath="{.subsets[0].addresses[0].ip}/32")
    # Server IP
    if [[ "$DOMAIN" =~ ^(([1-9]?[0-9]|1[0-9][0-9]|2([0-4][0-9]|5[0-5]))\.){3}([1-9]?[0-9]|1[0-9][0-9]|2([0-4][0-9]|5[0-5]))$ ]]; then
        # external ip can differ from local ip, must be reachable due to keycloak (only in ip deployments)
        INTERNAL_CIDR="$DOMAIN/32,$INTERNAL_CIDR"
    fi
    SERVER_IP=$(hostname -I | awk -F ' ' '{print $1}')
    INTERNAL_CIDR="$SERVER_IP/32,$INTERNAL_CIDR"
    # MicroK8s https://microk8s.io/docs/change-cidr
    INTERNAL_CIDR="10.152.183.0/24,10.1.0.0/16,$INTERNAL_CIDR"

    
    echo "${GREEN}Checking for version difference and migration options...${NC}"
    migrate

    echo "${GREEN}Deploying $PLATFORM_NAME:$PLATFORM_VERSION${NC}"
    echo "${GREEN}CHART_PATH $CHART_PATH${NC}"
    
    # Build helm command with optional --plain-http flag
    HELM_INSTALL_CMD="$HELM_EXECUTABLE -n $HELM_NAMESPACE install --create-namespace"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_INSTALL_CMD="$HELM_INSTALL_CMD --plain-http"
    fi
    
    $HELM_INSTALL_CMD $CHART_PATH \
    --set-string global.base_namespace="base" \
    --set-string global.credentials_registry_username="$CONTAINER_REGISTRY_USERNAME" \
    --set-string global.credentials_registry_password="$CONTAINER_REGISTRY_PASSWORD" \
    --set-string global.credentials_minio_username="$CREDENTIALS_MINIO_USERNAME" \
    --set-string global.credentials_minio_password="$CREDENTIALS_MINIO_PASSWORD" \
    --set-string global.credentials_grafana_username="$GRAFANA_USERNAME" \
    --set-string global.credentials_grafana_password="$GRAFANA_PASSWORD" \
    --set-string global.credentials_keycloak_admin_username="$KEYCLOAK_ADMIN_USERNAME" \
    --set-string global.credentials_keycloak_admin_password="$KEYCLOAK_ADMIN_PASSWORD" \
    --set-string global.dicom_port="$DICOM_PORT" \
    --set-string global.fast_data_dir="$FAST_DATA_DIR" \
    --set-string global.services_namespace=$SERVICES_NAMESPACE \
    --set-string global.extensions_namespace=$EXTENSIONS_NAMESPACE \
    --set-string global.admin_namespace=$ADMIN_NAMESPACE \
    --set global.gpu_support=$GPU_SUPPORT \
    --set-string global.helm_namespace="$ADMIN_NAMESPACE" \
    --set global.oidc_client_secret=$OIDC_CLIENT_SECRET \
    --set global.include_reverse_proxy=$INCLUDE_REVERSE_PROXY \
    --set-string global.home_dir="$HOME" \
    --set-string global.hostname="$DOMAIN" \
    --set-string global.http_port="$HTTP_PORT" \
    --set-string global.https_port="$HTTPS_PORT" \
    --set global.internalCidrs="{$INTERNAL_CIDR}" \
    --set-string squid-proxy.upstreamHttpProxy="$http_proxy" \
    --set-string squid-proxy.upstreamHttpsProxy="$https_proxy" \
    --set global.offline_mode=$OFFLINE_MODE \
    --set global.prefetch_extensions=$PREFETCH_EXTENSIONS \
    --set-string global.pull_policy_images="$PULL_POLICY_IMAGES" \
    --set-string global.pull_policy_jobs="$PULL_POLICY_IMAGES" \
    --set-string global.pull_policy_pods="$PULL_POLICY_IMAGES" \
    --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
    --set-string global.release_name="$PLATFORM_NAME" \
    --set-string global.deployment_timestamp="$DEPLOYMENT_TIMESTAMP" \
    --set-string global.mount_points_to_monitor="$MOUNT_POINTS_TO_MONITOR" \
    --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
    --set-string global.instance_uid="$INSTANCE_UID" \
    --set-string global.instance_name="$INSTANCE_NAME" \
    --set global.dev_mode=$DEV_MODE \
    --set-string global.kaapana_init_password="$KAAPANA_INIT_PASSWORD" \
    --set-string global.pacs_memory_limit="$PACS_MEMORY_LIMIT" \
    --set-string global.airflow_memory_limit="$AIRFLOW_MEMORY_LIMIT" \
    --set-string global.opensearch_memory_limit="$OPENSEARCH_MEMORY_LIMIT" \
    --set-string global.pacs_memory_request="$PACS_MEMORY_REQUEST" \
    --set-string global.airflow_memory_request="$AIRFLOW_MEMORY_REQUEST" \
    --set-string global.opensearch_memory_request="$OPENSEARCH_MEMORY_REQUEST" \
    --set-string global.smtp_host="$SMTP_HOST" \
    --set-string global.smtp_port="$SMTP_PORT" \
    --set-string global.smtp_username="$SMTP_USERNAME" \
    --set-string global.smtp_password="$SMTP_PASSWORD" \
    --set-string global.email_address_sender="$EMAIL_ADDRESS_SENDER" \
    --set-string global.storage_class_fast="$STORAGE_CLASS_FAST" \
    --set-string global.storage_class_slow="$STORAGE_CLASS_SLOW" \
    --set-string global.storage_class_workflow="$STORAGE_CLASS_WORKFLOW" \
    --set-string global.main_node_name="$MAIN_NODE_NAME" \
    --set-string global.volume_slow_data="$VOLUME_SLOW_DATA" \
    --set-string global.replica_count="$REPLICA_COUNT"\
    --set-string global.storage_node="$STORAGE_NODE" \
    {% for item in additional_env -%}--set-string {{ item.helm_path }}="${{ item.name }}" \
    {% endfor -%}
    --name-template "$PLATFORM_NAME"

    # In case of timeout-issues in kube helm increase the default timeouts by setting
    # --set kube-helm-chart.timeouts.helmInstallTimeout=45 \
    # --set kube-helm-chart.timeouts.helmDeletionTimeout=60 \

    # pull_policy_jobs and pull_policy_pods only there for backward compatibility as of version 0.2.0
    if [ ! -z "$CONTAINER_REGISTRY_USERNAME" ] && [ ! -z "$CONTAINER_REGISTRY_PASSWORD" ]; then
        rm $CHART_PATH
    fi

    print_deployment_done
    update_coredns_rewrite
    CONTAINER_REGISTRY_USERNAME=""
    CONTAINER_REGISTRY_PASSWORD=""
}


function pull_chart {
    local chart_name=$1
    local chart_version=$2
    local dest_dir=$3

    MAX_RETRIES=30
    i=1
    while [ $i -le $MAX_RETRIES ];
    do
        echo -e "${YELLOW}Pulling chart: ${CONTAINER_REGISTRY_URL}/${chart_name} with version ${chart_version} ${NC}"
        $HELM_EXECUTABLE pull --plain-http oci://${CONTAINER_REGISTRY_URL}/${chart_name} \
            --version ${chart_version} -d ${dest_dir} \
            && break \
            || ( echo -e "${RED}Failed -> retry${NC}" && sleep 1 )
        ((i++))
    done

    if [ ! -f "${dest_dir}/${chart_name}-${chart_version}.tgz" ]; then
        echo -e "${RED}Could not pull chart! -> abort${NC}"
        echo -e "${YELLOW}This can be related to issues on the registry side or connection issues.${NC}"
        echo -e "${YELLOW}Retrying the deployment script might solve this issue.${NC}"
        exit 1
    fi
}

function check_credentials {
    while true; do
        if [ -z "$CONTAINER_REGISTRY_USERNAME" ] || [ -z "$CONTAINER_REGISTRY_PASSWORD" ]; then
            echo -e "${YELLOW}Please enter the credentials for the Container-Registry!${NC}"
            read -p '**** username: ' CONTAINER_REGISTRY_USERNAME
            read -s -p '**** password: ' CONTAINER_REGISTRY_PASSWORD
        else
            echo -e "${GREEN}Credentials found!${NC}"
            break
        fi
    done
    STRIPPED_CONTAINER_REGISTRY_URL=$(echo "$CONTAINER_REGISTRY_URL" | sed -E 's~^https?://~~' | cut -d'/' -f1)
    
    # Build helm registry login command with optional --plain-http flag
    HELM_LOGIN_CMD="$HELM_EXECUTABLE registry login"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_LOGIN_CMD="$HELM_LOGIN_CMD --plain-http"
    fi
    
    $HELM_LOGIN_CMD -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $(echo "$CONTAINER_REGISTRY_URL" | cut -d/ -f1)
}

function install_certs {
    if [ "$EUID" -ne 0 ]
    then echo -e "The installation of certs requires root privileges!";
        exit 1
    fi

    if [ ! -f ./tls.key ] || [ ! -f ./tls.crt ]; then
        echo -e "${RED}tls.key or tls.crt could not been found in this directory.${NC}"
        echo -e "${RED}Please rename and copy the files first!${NC}"
        exit 1
    else
        echo -e "files found!"
        echo -e "Creating cluster secret ..."
        microk8s.kubectl delete secret certificate -n $ADMIN_NAMESPACE
        microk8s.kubectl create secret tls certificate --namespace $ADMIN_NAMESPACE --key ./tls.key --cert ./tls.crt
        auth_proxy_pod=$(microk8s.kubectl get pods -n $ADMIN_NAMESPACE |grep oauth2-proxy  | awk '{print $1;}')
        echo "auth_proxy_pod pod: $auth_proxy_pod"
        microk8s.kubectl -n $ADMIN_NAMESPACE delete pod $auth_proxy_pod
        cp ./tls.key ./tls.crt $FAST_DATA_DIR/tls/
    fi

    echo -e "${GREEN}DONE${NC}"
}

function print_deployment_done {
    echo -e "${GREEN}Deployment done."
    print_resource_configs
    echo -e "Please wait till all components have been downloaded and started."
    echo -e "You can check the progress with:"
    echo -e "watch microk8s.kubectl get pods -A"
    echo -e "When all pod are in the \"running\" or \"completed\" state,${NC}"

    if [ -v DOMAIN ];then
        echo -e "${GREEN}you can visit: https://$DOMAIN:$HTTPS_PORT/"
        echo -e "You should be welcomed by the login page."
        echo -e "Initial credentials:"
        echo -e "username: kaapana"
        echo -e "password: ${KAAPANA_INIT_PASSWORD} ${NC}"
    fi
}

function print_resource_configs {
    echo "Total memory of the node: $(awk "BEGIN {printf \"%.2f\", $TOTAL_MEMORY/1024}") Gi"
    echo "Allocatable memory of the node: $(awk "BEGIN {printf \"%.2f\", $ALLOCATABLE_MEMORY/1024}") Gi"
    echo ""
    echo "PACS minimum memory request: $(awk "BEGIN {printf \"%.2f\", $PACS_MEMORY_REQUEST/1024}") Gi"
    echo "PACS maximum memory limit: $(awk "BEGIN {printf \"%.2f\", $PACS_MEMORY_LIMIT/1024}") Gi"
    echo ""
    echo "Airflow minimum memory request: $(awk "BEGIN {printf \"%.2f\", $AIRFLOW_MEMORY_REQUEST/1024}") Gi"
    echo "Airflow maximum memory limit: $(awk "BEGIN {printf \"%.2f\", $AIRFLOW_MEMORY_LIMIT/1024}") Gi"
    echo ""
    echo "Opensearch minimum memory request: $(awk "BEGIN {printf \"%.2f\", $OPENSEARCH_MEMORY_REQUEST/1024}") Gi"
    echo "Opensearch maximum memory limit: $(awk "BEGIN {printf \"%.2f\", $OPENSEARCH_MEMORY_LIMIT/1024}") Gi"
    echo ""
}



function preflight_checks {
    echo -e "${GREEN}#################################  RUNNING PREFLIGHT CHECKS  #########################################${NC}"

    # Holds the state of the setup after preflight checks:
    # 0 = OK
    # 100=POTENTIAL PROBLEMS - could lead to upstream problems
    # 200=MANIFESTED PROBLEMS - very probably lead to problems
    # 300=CATASTROPHIC PROBLEMS - definitely leads to problems, continuation not possible

    # Since bash has no support for multidimensional arrays every test needs to add exactly one element to this arrays
    SEVERITY=()
    TEST_FAILDS=()
    TEST_NAMES=()
    RESULT_MSGS=()

    # ------ Tests
    SEVERITY+=(200)
    TEST_NAMES+=("Check if user is non-root")
    if [ "$EUID" -eq 0 ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Please run the script without root privileges!")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("(user: $USER)")
    fi

    SEVERITY+=(200)
    TEST_NAMES+=("Check if enough disk-space")
    SIZE="$(df -k --output=size /var/snap | tail -n1)"
    if [ "$SIZE" -lt 81920000 ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Your disk space is too small to deploy the system.\nThere should be at least 80 GiBytes available @ /var/snap")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("(size: $SIZE)")
    fi

    SEVERITY+=(300)
    TEST_NAMES+=("Check that helm is available")
    if ! [ -x "$(command -v helm)" ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Install server dependencies first!")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(300)
    TEST_NAMES+=("Check that kubectl is installed")
    if ! [ -x $(command -v microk8s.kubectl >/dev/null 2>&1) ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Install server dependencies first!")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(100)
    TEST_NAMES+=("Check that \$KUBECONFIG is untouched")
    if [ -v KUBECONFIG ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("In your environment the \$KUBECONFIG variable is set, this is unconventional and can cause to problems (KUBECONFIG=$KUBECONFIG)")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(100)
    TEST_NAMES+=("Check if ~/.kube/config matches microk8s config")
    if [ "$(cat /home/$USER/.kube/config)" == "$(microk8s.kubectl config view --raw)" ]; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Your kubeconfig differs from the microk8s version.")
    fi

    SEVERITY+=(100)
    GROUPNAME="microk8s"
    TEST_NAMES+=("Check if user is member of $GROUPNAME...")
    if id -nG "$USER" | grep -qw "$GROUPNAME"; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(300)
    TEST_NAMES+=("Check if kubectl is working")
    microk8s.kubectl get pods --all-namespaces &> /dev/null
    if [ $? -eq 0 ]; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Kubectl could not communicate with the server.\nHave a look at the output,\nCheck if the correct server certificate file is in place @ ~/.kube/config,\nCheck if the IP address in the certificate matches the IP address of the server\nand try again.")
    fi


    # Reporting Table
    printf "%-4s %-60s %-15s\n" "Sev" "Test" "Result"
    for i in ${!SEVERITY[@]}; do

        if [ "${TEST_FAILDS[$i]}" = true ]; then
            if [ "${SEVERITY[$i]}" -ge 200 ]; then
                STATUS="${RED}failed${NC}"
            else
                STATUS="${YELLOW}failed${NC}"
            fi
        else
            STATUS="${GREEN}ok${NC}"
        fi

        printf "%-4d %-60s %-15s\n" "${SEVERITY[$i]}" "${TEST_NAMES[$i]}" "$STATUS"

        if [ ! -z "${RESULT_MSGS[$i]}" ]; then
            if [ "${TEST_FAILDS[$i]}" = true ]; then
                if [ "${SEVERITY[$i]}" -ge 200 ]; then
                    echo -e "${RED}${RESULT_MSGS[$i]}${NC}"
                else
                     echo -e "${YELLOW}${RESULT_MSGS[$i]}${NC}"
                fi
            else
                echo -e "${GREEN}${RESULT_MSGS[$i]}${NC}"
            fi
        fi
    done

    # Act on Test Results
    MAX_SEVERITY=0
    for i in ${!SEVERITY[@]}; do
        # Maximum Severity of a failed test
        if [ "${TEST_FAILDS[$i]}" = true ]; then
            TEST_SEVERITY="${SEVERITY[$i]}"
            MAX_SEVERITY=$((MAX_SEVERITY>TEST_SEVERITY? MAX_SEVERITY : TEST_SEVERITY))
        fi
    done


    echo " "
    if [ "$MAX_SEVERITY" -gt 0 ]; then
        echo -e "${YELLOW}##################################  PREFLIGHT CHECK REPORT ##########################################${NC}"
    else
        echo -e "${GREEN}###################################  PREFLIGHT CHECK REPORT ###########################################${NC}"
    fi
    echo " "

    TERMINATE=false
    if [ "$MAX_SEVERITY" -ge 300 ]; then
        # 300-and growing
        echo -e "${RED}Problems with a very high severity have been found! ${NC}"
        echo -e "${RED}A continuation of this script is not possible.${NC}"
        echo -e "${RED}Please fix the failed tests first! ${NC}"
        #exit 1
        TERMINATE=true
    elif [ "$MAX_SEVERITY" -ge 200 ]; then
        # 200-299
        echo -e "${RED}Problems with a high severity have been found! ${NC}"
        echo -e "${RED}This will most probably lead to problems in the operation or even installation of the platform.${NC}"
        echo -e "${RED}Please consider fixing this problems before continuing, it is highly recommended.${NC}"
        TERMINATE=true
    elif [ "$MAX_SEVERITY" -ge 100 ]; then
        # 100-199
        echo -e "${YELLOW}Problems with a medium severity have been found! ${NC}"
        echo -e "${YELLOW}Since your system is out of the specified constraints for the platform, problems during operation or the installation can occur.${NC}"
        echo -e "${YELLOW}Please consider fixing this problems before continuing, it is highly recommended.${NC}"
        TERMINATE=true
    elif [ "$MAX_SEVERITY" -ge 1 ]; then
        # 1-99
        echo -e "${YELLOW}Problems with a low severity have been found! ${NC}"
        echo -e "${YELLOW}Please consider fixing this problems before continuing, it is highly recommended.${NC}"
    else
        echo -e "${GREEN}No major problems have been found! ${NC}"
    fi

    echo " "

    if [ "$TERMINATE" = "true" ]; then
        if [ "$QUIET" = "false" ] ; then
            while true; do
                read -e -p "Do you want to fix the problems before continuing? (Recommended)" -i " no" yn
                case $yn in
                    [Yy]* ) echo "${RED}exiting...${NC}" && exit 1; break;;
                    [Nn]* ) echo "${YELLOW}continuing (be aware that you leaving the supported path, its dangerous here watch your step!)${NC}"; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
        else
            echo -e "${RED}Exiting since you run in quiet mode${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}################################  PREFLIGHT CHECKS COMPLETED  #########################################${NC}"
}

function update_coredns_rewrite() {
    # Get the hostname from helm values
    local hostname=$DOMAIN # $(helm get values kaapana-platform-chart -o json | jq -r ".global.hostname")
    if [ -z "$hostname" ]; then
        echo "Error: hostname not"
        return 1
    fi

    # If hostname starts with a number it is considerd an IP and dns rewrite is skipped
    if [[ "$hostname" =~ ^[0-9] ]]; then
        echo "Skipped DNS rewrite because ${hostname} seems to be an IP Adress"
        return 0
    fi

    # Build the new rewrite rule.
    # Ensure both hostname and target are FQDNs (with trailing dots).
    local new_rule="rewrite name exact ${hostname}. oauth2-proxy-service.$ADMIN_NAMESPACE.svc.cluster.local."

    echo "Updating CoreDNS rewrite rule for hostname ${hostname}"

    # Retrieve the current CoreDNS ConfigMap and update the Corefile:
    # - Split the Corefile into lines.
    # - If a rewrite rule for our hostname exists, update it.
    # - Otherwise, insert the new rule before the first line starting with "kubernetes"
    microk8s.kubectl get configmap coredns -n kube-system -o json | jq --arg new_rule "$new_rule" --arg ns "$ADMIN_NAMESPACE"  '
    .data.Corefile |= (
        # Remove any rewrite lines for oauth2-proxy-service.<namespace>.svc.cluster.local.
        gsub("(?m)^[[:space:]]*rewrite name exact [^\\n]+ oauth2-proxy-service\\." + $ns + "\\.svc\\.cluster\\.local\\.";"") |
        split("\n") as $lines |
        ($lines | to_entries) as $entries |
        ( $entries
          | map(select(.value | test("^[[:space:]]*kubernetes ")))
          | .[0].key // ($lines | length)
        ) as $kube_index |
        ($lines[0:$kube_index] + [$new_rule] + $lines[$kube_index:]) | join("\n")
    )
    | del(.metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"])
    | del(.metadata.managedFields)
    ' > /tmp/coredns.json

    # Replace the ConfigMap entirely.
    microk8s.kubectl replace -f /tmp/coredns.json
    if [ $? -eq 0 ]; then
        echo "CoreDNS ConfigMap updated successfully."
    else
        echo "Failed to update CoreDNS ConfigMap."
        return 1
    fi

    # Restart the CoreDNS deployment to load the new configuration.
    microk8s.kubectl rollout restart deployment coredns -n kube-system
    if [ $? -eq 0 ]; then
        echo "CoreDNS deployment restarted successfully."
    else
        echo "Failed to restart CoreDNS deployment."
        return 1
    fi
}

function check_system() {
    release="$1"
    helm_ns="${2:-default}"

    # Extract all resources from the Helm manifest
    resources=$(
    $HELM_EXECUTABLE get manifest "$release" -n "$helm_ns" \
        | microk8s.kubectl apply --dry-run=client -f - -o json \
        | jq -r '.items[] | "\(.kind)/\(.metadata.namespace)/\(.metadata.name)"'
    )

    all_healthy=true

    for res in $resources; do
    kind=$(echo "$res" | cut -d'/' -f1)
    ns=$(echo "$res" | cut -d'/' -f2)
    name=$(echo "$res" | cut -d'/' -f3)

    case $kind in
        Deployment)
        if ! microk8s.kubectl rollout status "deployment/$name" -n "$ns"; then
            echo "❌ Deployment $name not healthy"
            all_healthy=false
        fi
        ;;
        StatefulSet)
        if ! microk8s.kubectl rollout status "statefulset/$name" -n "$ns"; then
            echo "❌ StatefulSet $name not healthy"
            all_healthy=false
        fi
        ;;
        Pod)
        phase=$(microk8s.kubectl get pod "$name" -n "$ns" -o jsonpath='{.status.phase}')
        if [[ "$phase" != "Running" && "$phase" != "Succeeded" ]]; then
            echo "❌ Pod $name is $phase"
            all_healthy=false
        fi
        ;;
        Job)
        if ! job=$(microk8s.kubectl get job "$name" -n "$ns" -o json 2>/dev/null); then
            echo "ℹ️ Job $name already completed and removed"
            continue
        fi
        succeeded=$(microk8s.kubectl get job "$name" -n "$ns" -o jsonpath='{.status.succeeded}')
        if [[ "$succeeded" != "1" ]]; then
            echo "❌ Job $name not successful"
            all_healthy=false
        fi
        ;;
        *)
        ;;
    esac
    done

    if [ "$all_healthy" = true ]; then
        echo "✅ All resources healthy"
    else
        echo "❌ Some resources are unhealthy"
        exit 1
    fi

}


function create_report {
    # Dont abort report generation on error
    set +euf +o pipefail
    # Pipe output also to file
    exec > >(tee -ia "kaapana-report-$(date +'%Y-%m-%d').log")

    # https://stackoverflow.com/a/17366594
    trap_fn() {
    [[ $DEBUG && $BASH_COMMAND != "unset DEBUG" &&  $BASH_COMMAND != "--- "* ]] && \
        printf "[%s:%s] %s\n" "$BASH_SOURCE" "$LINENO" "$BASH_COMMAND"
    return 0 # do not block execution in extdebug mode
    }

    trap trap_fn DEBUG

    function --- {
        unset DEBUG
        echo ""
        echo ""
        echo "-----------------------------------------------"
        echo "$1"
        echo "-----------------------------------------------"
        DEBUG=1
    }
cat << "EOF"


                           .=#%@@@%#-
                          .@@@@@@@@@@
                     .::::*@@@@@@@@+      :+##*+=.
                 .+%@@@@@@#  -@@@-       *@@@@@@@@#:
                -@@@@@@@@@+   #@#       -@@@@@@@@@@@=.=#%*=
                #@@@@@@@@#. :#@@@#=---=#@@@@@@@@@@@#+#@@@@@@*
           .:::=@@@@@@@%- -%@@@@@@@@@@@+.   .-===-.   #@@@@@@%
         +@@@@@@-:+@@@=  +@@@@@@@@@@@@=                +@@@@@@=
       :@@@@@@@#   %@=   @@@@@@@@@@@@@=                 .#@@@#  =##=
       %@@@@@@@=  =@@%.  +@@@@@@@@@@@@@+.    .:---.       +@%  :@@@@%
       *@@@@@@= .#@@@@@=  -%@@@@@@@@##*#@@@@@@@@@@@@*.    .@#  :@@@@@*
 .*@@#. #@@@*. +@@@@@@@@%.  -%@@@=.      *@@@@@@@@@@@@-  .#@@+  %@@@@@
.@@@@@#  %@=  *@@@@@@@@@@*   .@@=         +@@@@@@@@@@@@ -@@@@@#..%@@@#
#@@@@@%  %@.  %@@@@@@@@@@*   -@@+          *@@@@@@@@@@@:@@@@@@@@  %@@.
%@@@@@= *@@%: +@@@@@@@@@@.  =@@@@*.         -%@@@@@@@%:=@@@@@@@@= .@-
=@@@@=.%@@@@@+ =@@@@@@@*. -%@@@@@@@=          :=+**+-  .@@@@@@@@- :@.
 .-:  %@@@@@@@+  :===-   +@@@@@@@@@@#             .::.  =@@@@@@#:*@@*
     .@@@@@@@@%   :-:   .@@@@@@@@@@@@-         -#@@@@@@#-.-++=.*@@@@@-
      %@@@@@@@+ =@@@@@*..@@@@@@@@@@@@:        +@@@@@@@@@@%-   +@@@@@@+
       *@@@@@*  @@@@@@@% =@@@@@@@@@@#        .@@@@@@@@@@@@@@%@@@@@@@@=
        .---    +@@@@@@@  :#@@@@@@@@#:----.   @@@@@@@@@@@@+:.:#@@@@@%
                 -#@@@*.     :---..%@@@@@@@%= :@@@@@@@@@@:     :#@%+
                                   @@@@@@@@@@%  =#@@@@@@:
                                  :@@@@@@@@@@@#   .-#@@*
                                   #@@@@@@@@@@@*     +@%
 | |/ /                                   +@@@@@@@@@@@%+--+@@@@*-
 | ' / __ _  __ _ _ __   __ _ _ __   __ _  -+*#*+=-::+@@@@@@@@@@#
 |  < / _` |/ _` | '_ \ / _` | '_ \ / _` |            :@@@@@@@@@@:
 | . \ (_| | (_| | |_) | (_| | | | | (_| |             +@@@@@@@@=
 |_|\_\__,_|\__,_| .__/ \__,_|_| |_|\__,_|              #@@@@@*.
                 | |
  _   _          |_|       _____                       _
 | \ | |         | |      |  __ \                     | |
 |  \| | ___   __| | ___  | |__) |___ _ __   ___  _ __| |_ ___ _ __
 | . ` |/ _ \ / _` |/ _ \ |  _  // _ \ '_ \ / _ \| '__| __/ _ \ '__|
 | |\  | (_) | (_| |  __/ | | \ \  __/ |_) | (_) | |  | ||  __/ |
 |_| \_|\___/ \__,_|\___| |_|  \_\___| .__/ \___/|_|   \__\___|_|
                                     | |
                                     |_|
EOF
echo "Version: {{ platform_build_version }}"
echo "Report created on $(date +'%Y-%m-%d')"

--- "Basics"
uptime
free

--- "Last 2H Log"
journalctl --since "2 hours ago"

--- "Pod Status"
microk8s.kubectl get pods -A

--- "External Internet Access"
ping -c3 -i 0.2 www.dkfz-heidelberg.de

--- "Check Registry"
openssl s_client -connect $CONTAINER_REGISTRY_URL:443

--- "Check Registry Credentials"
if [ "$PLAIN_HTTP" = true ]; then
    $HELM_EXECUTABLE registry login --plain-http -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $CONTAINER_REGISTRY_URL
else
    $HELM_EXECUTABLE registry login -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $CONTAINER_REGISTRY_URL
fi

--- "Systemd Status"
systemd status

--- "Kernel Modules"
lsmod

--- "Storage"
df -h

--- "Snaps"
snap list

--- "k8s Pods"
microk8s.kubectl get pods -A

--- "k8s Describe Pods"
microk8s.kubectl describe pods -A

--- "k8s Node Status"
microk8s.kubectl describe node

--- "GPU Hardware"
lshw -C Display

--- "GPU Kernel Module"
modinfo nvidia | grep ^version

--- "GPU"
nvidia-smi

--- "Resource Health"
check_system kaapana-admin-chart default
check_system kaapana-platform-chart default
check_system project-admin admin

--- "END"
}

### MAIN programme body:
echo "${YELLOW:-}${BOLD:-}WARNING:${NC:-} deploy_platform.sh is deprecated and will be removed in the next Kaapana release."
echo "${YELLOW:-}${BOLD:-}Please use './kaapanactl deploy' instead; it accepts the same options as this script.${NC:-}"

### Parsing command line arguments:
usage="$(basename "$0")

_Flag: --undeploy undeploys the current platform
_Flag: --no-hooks will purge all kubernetes deployments and jobs as well as all helm charts. Use this if the undeployment fails or runs forever.
_Flag: --install-certs set new HTTPS-certificates for the platform
_Flag: --remove-all-images-ctr will delete all images from Microk8s (containerd)
_Flag: --remove-all-images-docker will delete all Docker images from the system
_Flag: --nuke-pods will force-delete all pods of the Kaapana deployment namespaces.
_Flag: --quiet, meaning non-interactive operation
_Flag: --offline, using prebuilt tarball and chart (--chart-path required!)
_Flag: --no-migration, disable automatic migration between versions
_Flag: --check-system, check health of all resources in kaapana-admin-chart and kaapana-platform-chart
_Flag: --report, create a report of the state of the microk8s cluster

_Argument: --username [Docker registry username]
_Argument: --password [Docker registry password]
_Argument: --port [Set main https-port]
_Argument: --chart-path [path-to-chart-tgz]
_Argument: --import-images-tar [path-to-a-tarball]"

QUIET=NA

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -u|--username)
            CONTAINER_REGISTRY_USERNAME="$2"
            echo -e "${GREEN}SET CONTAINER_REGISTRY_USERNAME! $CONTAINER_REGISTRY_USERNAME ${NC}";
            shift # past argument
            shift # past value
        ;;

        -p|--password)
            CONTAINER_REGISTRY_PASSWORD="$2"
            echo -e "${GREEN}SET CONTAINER_REGISTRY_PASSWORD!${NC}";
            shift # past argument
            shift # past value
        ;;

        -d|--domain)
            DOMAIN="$2"
            echo -e "${GREEN}SET DOMAIN!${NC}";
            shift # past argument
            shift # past value
        ;;

        --port)
            HTTPS_PORT="$2"
            echo -e "${GREEN}SET PORT!${NC}";
            shift # past argument
            shift # past value
        ;;

        --chart-path)
            CHART_PATH="$2"
            echo -e "${GREEN}SET CHART_PATH: $CHART_PATH !${NC}";
            shift # past argument
            shift # past value
        ;;

        --import-images-tar)
            TAR_PATH="$2"
            echo -e "${GREEN}SET TAR_PATH: $TAR_PATH !${NC}";
            import_container_images_tar
            exit 0
        ;;

        --quiet)
            QUIET=true
            shift # past argument
        ;;

        --offline)
            OFFLINE_MODE=true
            echo -e "${GREEN}Deploying in offline mode!${NC}"
            shift # past argument
        ;;

        --no-migration)
            MIGRATION_ENABLED=false
            echo -e "${YELLOW}Migration disabled via CLI (--no-migration).${NC}"
            shift # past argument
        ;;

        --install-certs)
            install_certs
            exit 0
        ;;

        --remove-all-images-ctr)
            delete_all_images_microk8s
            exit 0
        ;;

        --remove-all-images-docker)
            delete_all_images_docker
            exit 0
        ;;

        --no-hooks)
            echo -e "${YELLOW}Starting undeployment ...${NC}"
            NO_HOOKS="--no-hooks"
            echo -e "${YELLOW}Using --no-hooks${NC}"
            delete_deployment
            clean_up_kubernetes
            exit 0
        ;;

        --nuke-pods)
            while true; do
                read -e -p "Do you really want to nuke all pods? -> Not recommended!" -i " no" yn
                case $yn in
                    [Yy]* )
                    nuke_pods
                    delete_deployment
                    clean_up_kubernetes
                    break;;
                    [Nn]* ) echo "${YELLOW}Pods will be kept${NC}"; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
            exit 0
        ;;

        --undeploy)
            delete_deployment
            exit 0
        ;;

        --re-deploy)
            delete_deployment
            deploy_chart
            exit 0
        ;;

        --report)
            create_report
            exit 0
        ;;

        --check-system)
            check_system kaapana-admin-chart default
            check_system kaapana-platform-chart admin
            check_system project-admin admin
            exit 0
        ;;

        *)    # unknown option
            echo -e "${RED}unknown parameter: $key ${NC}"
            echo -e "${YELLOW}$usage${NC}"
            exit 1
        ;;


    esac
done

preflight_checks

echo -e "${YELLOW}Get helm deployments...${NC}"
deployments=$(
  # Helm 3 vs Helm 4:
  # - Helm 3 needs `helm list -a` to show all releases (no --no-headers flag).
  # - Helm 4 removed `-a` and `helm list` already lists all statuses by default.
  #   See: https://helm.sh/docs/v3/helm/helm_list/ and https://helm.sh/docs/helm/helm_list/
  #
  # Try Helm 3 syntax first; if it fails (e.g. unknown flag -a), fall back to Helm 4 syntax.
  $HELM_EXECUTABLE -n "$HELM_NAMESPACE" ls --short -a 2>/dev/null || \
  $HELM_EXECUTABLE -n "$HELM_NAMESPACE" ls --short --no-headers 2>/dev/null
)
echo "Current deployments: "
echo $deployments

if [[ $deployments == *"$PLATFORM_NAME"* ]] && [[ ! $QUIET = true ]];then
    echo -e "${YELLOW}$PLATFORM_NAME already deployed!${NC}"
    PS3='select option: '
    options=("Un- and Re-deploy" "Undeploy" "Quit")
    select opt in "${options[@]}"
    do
        case $opt in
            "Un- and Re-deploy")
                echo -e "${YELLOW}Starting Un- and Re-deployment ...${NC}"
                delete_deployment
                deploy_chart
                break
                ;;
            "Undeploy")
                echo -e "${YELLOW}Starting undeployment ...${NC}"
                delete_deployment
                exit 0
                ;;
            "Quit")
                echo -e "${YELLOW}abort.${NC}"
                exit 0
                ;;
            *) echo "invalid option $REPLY";;
        esac
    done
elif [[ $deployments == *"$PLATFORM_NAME"* ]] && [[ $QUIET = true ]];then
    echo -e "${RED}Project already deployed!${NC}"
    echo -e "${RED}abort.${NC}"
    exit 1

else
    echo -e "${GREEN}No previous deployment found -> deploy ${NC}"
    deploy_chart
fi
