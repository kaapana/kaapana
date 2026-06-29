#!/bin/bash
# Kaapana control helper: run `./kaapanactl.sh deploy|install|report [options]` to deploy the platform,
# prepare servers, or gather microk8s diagnostics without touching other scripts manually.
# if unusual home dir of user: sudo dpkg-reconfigure apparmor
set -euf -o pipefail

function main() {
    init_colors
    local subcommand="help"

    if [[ $# -gt 0 ]]; then
        case "$1" in
            help|--help|-h)
                subcommand="help"
                shift
                ;;
            deploy|install|report|offline-gpu)
                subcommand="$1"
                shift
                ;;
            --*|-*)
                subcommand="deploy"
                ;;
            *)
                echo -e "${RED}Unknown command: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    fi

    case "$subcommand" in
        help)
            print_usage
            ;;
        deploy)
            deploy "$@"
            ;;
        install)
            server_installation "$@"
            ;;
        report)
            create_report
            ;;
        offline-gpu)
            install_gpu_operator "$(dirname "$0")"
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

function print_usage() {
    local script_name
    script_name="$(basename "$0")"
    cat <<EOF
Usage: $script_name <command> [options]

Commands:
  deploy               Deploy or manage the Kaapana platform.
  install              Run the server installation helper.
  report               Generate a microk8s state report without deploying.
  offline-gpu          Install the GPU Operator for offline environments.

Run '$script_name <command> --help' for command-specific options.
EOF
}

function prompt_required_value() {
    local var_name="$1"
    local prompt="$2"
    local secret="${3:-false}"
    local quiet_flag="${4:-false}"
    local current=""

    if [[ -n ${!var_name-} ]]; then
        current="${!var_name}"
    fi

    if [[ -n "$current" ]]; then
        return
    fi

    if [[ "$quiet_flag" == true ]]; then
        echo -e "${RED}${prompt} is required when running in quiet mode.${NC}"
        exit 1
    fi

    local value=""
    if [[ "$secret" == true ]]; then
        read -s -p "$prompt" value
        echo
    else
        read -p "$prompt" value
    fi

    if [[ -z "$value" ]]; then
        echo -e "${RED}A value is required for ${prompt}.${NC}"
        exit 1
    fi

    printf -v "$var_name" '%s' "$value"
}

function parse_chart_reference() {
    local ref="$1"
    ref="${ref#oci://}"

    if [[ -z "$ref" || "$ref" != *:* ]]; then
        echo -e "${RED}Chart reference must be in the form <registry>/<path>/<chart>:<version>. Got '$1'.${NC}"
        exit 1
    fi

    local registry_and_chart="${ref%:*}"
    local version="${ref##*:}"

    if [[ -z "$version" ]]; then
        echo -e "${RED}Chart reference is missing the version part after ':'.${NC}"
        exit 1
    fi

    local chart_name="${registry_and_chart##*/}"
    if [[ -z "$chart_name" || "$registry_and_chart" == "$chart_name" ]]; then
        echo -e "${RED}Chart reference must include a chart name (last segment after '/').${NC}"
        exit 1
    fi

    local registry_url="${registry_and_chart%/$chart_name}"
    if [[ -z "$registry_url" ]]; then
        echo -e "${RED}Unable to determine registry URL from chart reference '$1'.${NC}"
        exit 1
    fi

    PLATFORM_NAME="$chart_name"
    PLATFORM_VERSION="$version"
    CONTAINER_REGISTRY_URL="$registry_url"
    CHART_REFERENCE="$ref"

    echo -e "${GREEN}Using chart ${PLATFORM_NAME}:${PLATFORM_VERSION} from ${CONTAINER_REGISTRY_URL}${NC}"
}

function normalize_release_family_name() {
    local release_name="$1"

    case "$release_name" in
        racoon-*|kaapana-*)
            echo "${release_name#*-}"
            ;;
        *)
            echo "$release_name"
            ;;
    esac
}

function find_release_name_conflict() {
    local target_release="$1"
    local release_list="$2"
    local target_family
    local release_name

    target_family="$(normalize_release_family_name "$target_release")"
    while IFS= read -r release_name; do
        [[ -z "$release_name" || "$release_name" == "$target_release" ]] && continue
        if [[ "$(normalize_release_family_name "$release_name")" == "$target_family" ]]; then
            echo "$release_name"
            return 0
        fi
    done <<< "$release_list"

    return 1
}

function resolve_extracted_chart_dependency_path() {
    local workdir="$1"
    local dependency_name="$2"
    local dependency_path=""

    dependency_path="$(find "$workdir" -type f -path "*/${dependency_name}/Chart.yaml" -print -quit 2>/dev/null || true)"
    if [[ -z "$dependency_path" ]]; then
        echo -e "${RED}Dependency chart '${dependency_name}' not found in extracted chart archive under ${workdir}.${NC}" >&2
        return 1
    fi

    dirname "$dependency_path"
}

function validate_hostpath_reclaim_policy() {
    # Keep the CLI and Helm chart validation aligned. The value is passed
    # directly into kaapana-storage-chart during storage-class setup.
    case "$HOSTPATH_RECLAIM_POLICY" in
        Delete|Retain)
            ;;
        *)
            echo -e "${RED}Invalid hostpath reclaim policy '${HOSTPATH_RECLAIM_POLICY}'. Use Delete or Retain.${NC}"
            exit 1
            ;;
    esac
}

function require_retain_hostpath_reclaim_policy_for_recovery() {
    # Recovery may delete/recreate PVCs and depends on retained hostpath PVs or
    # retained backing directories. Do not silently change deletion semantics.
    validate_hostpath_reclaim_policy

    if [[ "$HOSTPATH_RECLAIM_POLICY" == "Retain" ]]; then
        return 0
    fi

    echo -e "${RED}Post-reinstall recovery requires --hostpath-reclaim-policy Retain.${NC}"
    echo -e "${RED}Current effective hostpath reclaim policy is '${HOSTPATH_RECLAIM_POLICY}'.${NC}"
    echo -e "${RED}Rerun with --hostpath-reclaim-policy Retain to opt into retained hostpath PVs before recovery.${NC}"
    return 1
}

function deploy() {

    PLATFORM_NAME="${PLATFORM_NAME:-}"
    PLATFORM_VERSION="${PLATFORM_VERSION:-}"
    CONTAINER_REGISTRY_URL="${CONTAINER_REGISTRY_URL:-}"
    CONTAINER_REGISTRY_USERNAME="${CONTAINER_REGISTRY_USERNAME:-}"
    CONTAINER_REGISTRY_PASSWORD="${CONTAINER_REGISTRY_PASSWORD:-}"
    CHART_REFERENCE="${CHART_REFERENCE:-}"
    PLAIN_HTTP="${PLAIN_HTTP:-false}"
    POST_DEPLOY_RECONCILE_AFTER_MIGRATION=false
    # Optional comma-separated CIDRs overriding the default external LDAP
    # endpoint(s) that Keycloak may reach despite the admin namespace's
    # default deny-egress policy.
    KEYCLOAK_LDAP_EGRESS_CIDRS="${KEYCLOAK_LDAP_EGRESS_CIDRS:-}"

    if [[ -z ${http_proxy+x} || -z ${https_proxy+x} ]]; then
        http_proxy=""
        https_proxy=""
    fi
    export HELM_EXPERIMENTAL_OCI=1
    HELM_EXECUTABLE="${HELM_EXECUTABLE:-helm}"

    load_kaapana_config
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
    _Flag: --recover-after-reinstall, run detected post-reinstall recovery helper before chart install
    _Flag: --prefetch-bootstrap-images, prefetch selected bootstrap images before chart install
    _Flag: --no-reconcile-project-namespaces, skip post-deploy project namespace reconciliation
    _Flag: --post-deploy-reconcile, force enabling the post-deploy reconcile chart even without a migration
    _Flag: --no-migration, disable automatic migration between versions
    _Flag: --ignore-domain-reachability-check, continue deployment even if DOMAIN validation cannot be completed
    _Flag: --ignore-certificate-state, continue deployment even if existing certificate files or secrets have hostname/validity issues
    _Flag: --install-storage-classes, installs only kaapana storage classes
    _Flag: --check-system, check health of all resources in kaapana-admin-chart and kaapana-platform-chart
    _Flag: --report, create a report of the state of the microk8s cluster
    _Flag: --plain-http, use insecure HTTP when talking to the registry (default HTTPS)

    _Argument: --chart [registry/path/chart:version]
    _Argument: --platform-name [Helm chart name]
    _Argument: --platform-version [Helm chart version]
    _Argument: --registry-url [OCI registry URL]
    _Argument: --username [Docker registry username]
    _Argument: --password [Docker registry password]
    _Argument: --fast-data-dir [Path to fast data dir on host]
    _Argument: --slow-data-dir [Path to slow data dir on host]
    _Argument: --hostpath-reclaim-policy [Delete|Retain] (default: Delete)
    _Argument: --port [Set main https-port]
    _Argument: --chart-path [path-to-chart-tgz]
    _Argument: --import-images-tar [path-to-a-tarball]"

    QUIET=false
    IGNORE_CERTIFICATE_STATE=false

    while [[ $# -gt 0 ]]; do
        key="$1"

        case $key in

            -u|--username)
                CONTAINER_REGISTRY_USERNAME="$2"
                echo -e "${GREEN}SET CONTAINER_REGISTRY_USERNAME! $CONTAINER_REGISTRY_USERNAME ${NC}";
                shift 2
            ;;

            --platform-name)
                PLATFORM_NAME="$2"
                echo -e "${GREEN}SET PLATFORM_NAME: $PLATFORM_NAME ${NC}"
                shift 2
            ;;

            --platform-version)
                PLATFORM_VERSION="$2"
                echo -e "${GREEN}SET PLATFORM_VERSION: $PLATFORM_VERSION ${NC}"
                shift 2
            ;;

            --registry-url)
                CONTAINER_REGISTRY_URL="$2"
                echo -e "${GREEN}SET CONTAINER_REGISTRY_URL: $CONTAINER_REGISTRY_URL ${NC}"
                shift 2
            ;;

            --chart)
                CHART_REFERENCE="$2"
                parse_chart_reference "$CHART_REFERENCE"
                shift 2
            ;;

            -p|--password)
                CONTAINER_REGISTRY_PASSWORD="$2"
                echo -e "${GREEN}SET CONTAINER_REGISTRY_PASSWORD!${NC}";
                shift 2
            ;;

            --fast-data-dir)
                FAST_DATA_DIR="$2"
                echo -e "${GREEN}SET FAST_DATA_DIR: $FAST_DATA_DIR ${NC}";
                shift 2
            ;;

            --slow-data-dir)
                SLOW_DATA_DIR="$2"
                echo -e "${GREEN}SET SLOW_DATA_DIR: $SLOW_DATA_DIR ${NC}";
                shift 2
            ;;

            --hostpath-reclaim-policy)
                HOSTPATH_RECLAIM_POLICY="$2"
                validate_hostpath_reclaim_policy
                echo -e "${GREEN}SET HOSTPATH_RECLAIM_POLICY: $HOSTPATH_RECLAIM_POLICY ${NC}";
                shift 2
            ;;

            -d|--domain)
                DOMAIN="$2"
                echo -e "${GREEN}SET DOMAIN!${NC}";
                shift 2
            ;;

            --port)
                HTTPS_PORT="$2"
                echo -e "${GREEN}SET PORT!${NC}";
                shift 2
            ;;

            --chart-path)
                CHART_PATH="$2"
                echo -e "${GREEN}SET CHART_PATH: $CHART_PATH !${NC}";
                shift 2
            ;;

            --import-images-tar)
                TAR_PATH="$2"
                echo -e "${GREEN}SET TAR_PATH: $TAR_PATH !${NC}";
                import_container_images_tar
                exit 0
            ;;

            --quiet)
                QUIET=true
                shift
            ;;

            --offline)
                OFFLINE_MODE=true
                echo -e "${GREEN}Deploying in offline mode!${NC}"
                shift
            ;;

            --recover-after-reinstall|--recover)
                POST_REINSTALL_RECOVERY_REQUESTED=true
                echo -e "${GREEN}Post-reinstall recovery forced via CLI flag.${NC}"
                shift
            ;;

            --prefetch-bootstrap-images)
                BOOTSTRAP_IMAGE_PREFETCH_ENABLED=true
                echo -e "${GREEN}Bootstrap image prefetch enabled via CLI flag.${NC}"
                shift
            ;;

            --no-reconcile-project-namespaces)
                POST_DEPLOY_RECONCILE_ENABLED=false
                echo -e "${YELLOW}Post-deploy project namespace reconciliation disabled via CLI flag.${NC}"
                shift
            ;;

            --post-deploy-reconcile)
                POST_DEPLOY_RECONCILE_AFTER_MIGRATION=true
                echo -e "${GREEN}Post-deploy reconcile chart forced on via CLI flag.${NC}"
                shift
            ;;

            --plain-http)
                PLAIN_HTTP=true
                echo -e "${YELLOW}Using insecure plain HTTP for registry access.${NC}"
                shift
            ;;

            --no-migration)
                MIGRATION_ENABLED=false
                echo -e "${YELLOW}Migration disabled via CLI (--no-migration).${NC}"
                shift
            ;;

            --ignore-domain-reachability-check)
                IGNORE_DOMAIN_REACHABILITY_CHECK=true
                echo -e "${YELLOW}Domain validation failures will be ignored (override active).${NC}"
                shift
            ;;

            --ignore-certificate-state)
                IGNORE_CERTIFICATE_STATE=true
                echo -e "${YELLOW}Certificate state mismatches will be ignored (override active).${NC}"
                shift
            ;;

            --install-storage-classes)
                setup_storage_provider
                get_chart
                setup_storage_classes
                rm_chart_path
                exit 0
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

    setup_storage_provider

    if [[ -n "$CHART_PATH" ]]; then
        PLATFORM_VERSION=$( $HELM_EXECUTABLE show chart ${CHART_PATH} | grep '^version:' | awk '{print $2}' )
        PLATFORM_NAME=$( $HELM_EXECUTABLE show chart ${CHART_PATH} | grep '^name:' | awk '{print $2}' )
    fi

    if [[ "${OFFLINE_MODE,,}" == true ]]; then
        CONTAINER_REGISTRY_USERNAME=""
        CONTAINER_REGISTRY_PASSWORD=""
        prompt_required_value CONTAINER_REGISTRY_URL "Enter the container registry url: " false "$QUIET"
    fi

    if [[ -z "$PLATFORM_NAME" || -z "$PLATFORM_VERSION" || -z "$CONTAINER_REGISTRY_URL" ]]; then
        prompt_required_value CHART_REFERENCE "Enter the kaapana chart (registry/path/chart:version): " false "$QUIET"
        parse_chart_reference "$CHART_REFERENCE"
    fi

    if [[ "${OFFLINE_MODE,,}" != true ]]; then
        prompt_required_value CONTAINER_REGISTRY_USERNAME "Enter the container registry username: " false "$QUIET"
        prompt_required_value CONTAINER_REGISTRY_PASSWORD "Enter the container registry password: " true "$QUIET"
    fi

    if [[ -n "$INSTANCE_UID" ]]; then
        echo ""
        echo "Setting INSTANCE_UID: $INSTANCE_UID namespaces ..."
        SERVICES_NAMESPACE="$INSTANCE_UID-$SERVICES_NAMESPACE"
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

    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
    then
        echo "${GREEN}Nvidia GPU detected!${NC}"
        GPU_SUPPORT=true
    else
        echo "${YELLOW}No GPU detected...${NC}"
        GPU_SUPPORT=false
    fi

    preflight_checks

    ensure_helm_uses_microk8s_config

    if [[ "${POST_REINSTALL_RECOVERY_REQUESTED,,}" == "true" ]]; then
        require_retain_hostpath_reclaim_policy_for_recovery || exit 1
    fi

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

    conflicting_release="$(find_release_name_conflict "$PLATFORM_NAME" "$deployments" || true)"
    if [[ -n "$conflicting_release" ]]; then
        echo -e "${RED}Found existing release '$conflicting_release', which conflicts with requested platform name '$PLATFORM_NAME'.${NC}"
        echo -e "${RED}This script treats 'racoon-*' and 'kaapana-*' releases with the same suffix as the same installation.${NC}"
        if [[ "$QUIET" == true ]]; then
            echo -e "${RED}Use --platform-name $conflicting_release, or undeploy the existing release before switching names.${NC}"
            exit 1
        fi

        while true; do
            read -e -p "Undeploy conflicting release '$conflicting_release' now?" -i " no" yn
            case $yn in
                [Yy]* )
                    echo -e "${YELLOW}Starting undeployment of conflicting release ...${NC}"
                    PLATFORM_NAME="$conflicting_release"
                    delete_deployment
                    exit 0
                    ;;
                [Nn]* )
                    echo -e "${YELLOW}Abort. Re-run with --platform-name $conflicting_release if you want to reuse the existing release name.${NC}"
                    exit 1
                    ;;
                * ) echo "Please answer yes or no.";;
            esac
        done
    fi

    if [[ $deployments == *"$PLATFORM_NAME"* && $QUIET != true ]]; then
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
    elif [[ $deployments == *"$PLATFORM_NAME"* && $QUIET == true ]]; then
        echo -e "${RED}Project already deployed!${NC}"
        echo -e "${RED}abort.${NC}"
        exit 1

    else
        echo -e "${GREEN}No previous deployment found -> deploy ${NC}"
        deploy_chart
    fi
}

function server_installation() {
    init_colors
    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    OS_PRESENT=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
    OS_PRESENT="${OS_PRESENT%\"}"
    OS_PRESENT="${OS_PRESENT#\"}"
    REAL_USER=${SUDO_USER:-$USER}
    if [[ -v SUDO_USER ]]; then
        USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        USER_HOME="$HOME"
    fi

    if [[ "$EUID" -ne 0 ]]; then
        echo -e "Please run the script with root privileges!"
        exit 1
    fi
    echo ""
    echo -e "${GREEN}OS:        $OS_PRESENT ${NC}";
    echo -e "${GREEN}REAL_USER: $REAL_USER ${NC}";
    echo -e "${GREEN}USER_HOME: $USER_HOME ${NC}";
    echo ""

    DEFAULT_MICRO_VERSION=1.33/stable
    DEFAULT_HELM_VERSION=latest/stable

    ### Parsing command line arguments:
    usage="$(basename "$0")

    _Flag: -q   --quiet      will activate quiet mode (default: false)
    _Flag:      --uninstall  removes microk8s and helm from the system
    _Flag:      --offline    offline installation for snap packages (expects '*.snap' and '*.assert' files within the working dir)

    _Argument: -v --version [opt]
    where opt is:
        default: $DEFAULT_MICRO_VERSION

    _Argument: -os --operating-system [opt]
    where opt is:
        AlmaLinux --> AlmaLinux
        Ubuntu    --> Ubuntu
        default: $OS_PRESENT"

    QUIET="${QUIET:-NA}"
    OFFLINE_SNAPS="${OFFLINE_SNAPS:-NA}"
    DNS="${DNS:-}"

    if [[ -z "$DNS" && -n "${NAMESERVERS:-}" ]]; then
        DNS="$NAMESERVERS"
    fi

    while [[ $# -gt 0 ]]; do
        key="$1"

        case $key in

            -h|--help)
                echo -e "${YELLOW}$usage ${NC}";
                exit 0
            ;;

            -os|--operating-system)
                OS_PRESENT="$2"
                echo -e "${GREEN}OS set to: $OS_PRESENT ${NC}";
                shift 2
            ;;

            -v|--version)
                DEFAULT_MICRO_VERSION="$2"
                echo -e "${GREEN}Kubernetes version set to: $DEFAULT_MICRO_VERSION ${NC}";
                shift 2
            ;;

            -q|--quiet)
                echo -e "${GREEN}QUIET-MODE activated!${NC}";
                QUIET=true
                shift
            ;;

            --offline)
                OFFLINE_SNAPS=true
                echo -e "${GREEN}SET OFFLINE_SNAPS: $OFFLINE_SNAPS !${NC}";
                shift
            ;;

            --install-ubuntu-packages)
                install_packages_ubuntu
                exit 0
            ;;

            --install-almalinux-packages)
                install_packages_almalinux
                exit 0
            ;;

            --uninstall)
                uninstall
                exit 0
            ;;

            *)    # unknown option
                echo -e "${RED}UNKNOWN ARGUMENT: $key!${NC}";
                echo -e "$usage";
                exit 1
            ;;
        esac
    done


    case "$OS_PRESENT" in
        "AlmaLinux")
            echo -e "${GREEN}Starting AlmaLinux installation...${NC}";
            install_proxy_environment
            install_packages_almalinux
            install_core core20 # for microk8s
            install_core core24 # for helm
            install_snapd # for helm
            install_helm
            install_microk8s
        ;;

        "Ubuntu")
            echo -e "${GREEN}Starting Ubuntu installation...${NC}";
            install_proxy_environment
            install_packages_ubuntu
            install_core core20 # for microk8s
            install_core core24 # for helm
            install_snapd # for helm
            install_helm
            install_microk8s
        ;;

        *)
            echo "${RED}Your OS: $OS_PRESENT is not supported at the moment.${NC}"
            echo "${RED}This scripts suppors: Ubuntu and AlmaLinux${NC}"
            echo -e "$usage"
            exit 1
    esac
}

function install_proxy_environment {
    echo "${YELLOW}Checking proxy settings ...${NC}"
    if [[ "$QUIET" != true ]]; then
        if [[ ! -v http_proxy ]]; then
            echo "${RED}No proxy has been found!${NC}"
            while true; do
                read -p "Is this correct and you don't need a proxy?" yn
                    case $yn in
                        [Yy]* ) break;;
                        [Nn]* ) echo "please configure your system proxy (http_proxy + https_proxy -> /etc/environment)" && exit;;
                        * ) echo "Please answer yes or no.";;
                    esac
            done
        else
            echo "${GREEN}Proxy ok!${NC}"
            install_no_proxy_environment
        fi
    else
        echo "QUIET = true";
    fi
}


function install_no_proxy_environment {
    # Note: This script makes sure no_proxy configuration is configured correctly so microk8s doesn't send cluster traffic to the
    #       proxy server. The specific settings for ip ranges used by microk8s to request external resource might change in the future
    #       and are (currently) described here: https://microk8s.io/docs/install-proxy
    echo "${GREEN}Checking no_proxy settings${NC}"
    if [[ ! -v no_proxy && ! -v NO_PROXY ]]; then
        echo "${YELLOW}no_proxy not found, setting it and adding ${HOSTNAME}${NC}"
        echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        echo "no_proxy=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        sed -i "$ a\\${INSERTLINE}" /etc/environment && echo "Adding $HOSTNAME to no_proxy"
    else
        echo "${YELLOW}no_proxy | NO_PROXY found - check if complete ...!${NC}"

        no_proxy="${no_proxy:-$NO_PROXY}"

        # remove any " from no_proxy ENV
        no_proxy=$( echo $no_proxy | sed 's/"//g')

        if [[ $no_proxy == *"172.16.0.0/16"* ]]; then
            echo "${GREEN}NO_PROXY is already configured correctly ...${NC}"
            return
        fi

        if grep -Fq "NO_PROXY" /etc/environment; then
            sed -i "/NO_PROXY/c\NO_PROXY=$no_proxy,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" /etc/environment
        else
            echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        fi

        if grep -Fq "no_proxy" /etc/environment; then
            sed -i "/no_proxy/c\no_proxy=$no_proxy,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" /etc/environment
        else
            echo "no_proxy=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        fi
    fi
    echo "${GREEN}Source /etc/environment ${NC}"
    source /etc/environment
}

function install_packages_almalinux {
    echo "${YELLOW}Check packages...${NC}"
    sudo dnf install -y kernel-modules-extra-$(uname -r)
    if [ -x "$(command -v snap)" ] && [ -x "$(command -v jq)" ]; then
        echo "${GREEN}Snap installed.${NC}"
    else

        echo "${YELLOW}Enable epel-release${NC}"
        yum install -y epel-release
        echo "${YELLOW}YUM update & upgrade${NC}"
        yum check-update -y || true
        yum clean all -y
        yum update -y
	    yum upgrade -y

        echo "${YELLOW}Installing snap, nano, jq and curl${NC}"
        yum install -y snapd nano jq curl
    fi

    echo "${YELLOW}Enabling snap${NC}"
    systemctl enable --now snapd.socket
    systemctl start snapd

    echo "${YELLOW}Waiting for snap ...${NC}"
    snap wait system seed.loaded

    # If proxy is set, configure snapd systemd environment
    if [ -n "$http_proxy" ]; then
        echo "${YELLOW}Configuring snapd to use proxy ...${NC}"
        mkdir -p /etc/systemd/system/snapd.service.d/
        tee /etc/systemd/system/snapd.service.d/override.conf > /dev/null <<EOF
[Service]
Environment="http_proxy=$http_proxy"
Environment="https_proxy=$http_proxy"
EOF

        systemctl daemon-reload
        systemctl restart snapd

        snap set system proxy.http="$http_proxy"
        snap set system proxy.https="$http_proxy"
    else
        echo "${GREEN}No snap proxy needed${NC}"
    fi
}

function install_packages_ubuntu {
    if [ -x "$(command -v nano)" ] && [ -x "$(command -v jq)" ] && [ -x "$(command -v snap)" ]; then
        echo "${GREEN}snap,nano and jq already installed.${NC}"
    else
        echo "${YELLOW}Check if apt is locked ...${NC}"
        i=0
        tput sc

        while [ fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 ] || [ fuser /var/lib/dpkg/lock >/dev/null 2>&1 ]; do
            case $(($i % 4)) in
                0 ) j="-" ;;
                1 ) j="\\" ;;
                2 ) j="|" ;;
                3 ) j="/" ;;
            esac
            tput rc
            echo -en "\r[$j] Waiting for other software managers to finish ..."
            sleep 0.5
            ((i=i+1))
        done

        echo "${YELLOW}APT update & upgrade${NC}"
        apt update
        if [ ! "$QUIET" = "true" ]; then
            apt upgrade -y
        else
            # does not work
            export DEBIAN_FRONTEND=noninteractive
            apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
        fi

        echo "${YELLOW}Installing nano,jq,curl,net-tools ...${NC}"
        apt install -y nano jq curl net-tools

        if [ -x "$(command -v snap)" ]; then
            echo "${GREEN}Snap ok.${NC}"
        else
            echo "${YELLOW}Snap not installed! ${NC}"
            apt install -y snapd
            echo "${YELLOW}Snap has been installed -> reboot needed! ${NC}"
            echo "${YELLOW}Please restart this script afterwards. ${NC}"
            echo "${YELLOW}Please reboot now ${NC}"
            exit 0
        fi
    fi
}


function insert_text {
    search_string=$(echo "$1" | sed "s/--//")
    search_string=$(echo "$search_string" | sed "s/help/--help/")
    insert_string=$1
    filepath=$2
    rc=1

    echo "${YELLOW}Checking $insert_string in $filepath.. ${NC}"
    [ -f $filepath ] || { echo "$filepath does not exist! -> abort." && exit 1; }
    grep -q "$search_string" $filepath && echo "${YELLOW}SKIPPED: $insert_string ....${NC}" || { echo "${GREEN}Setting: $insert_string >> $filepath ${NC}" && rc=0 && sh -c "echo '$insert_string' >> $filepath"; }
    return $rc
}


function install_core {
    local package_name=$1
    echo "${YELLOW}Checking if ${package_name} is installed ... ${NC}"
    if ls -l /var/lib/snapd/snaps | grep ${package_name} ;
    then
        echo ""
        echo "${GREEN}${package_name} is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
    else
        echo "${YELLOW}${package_name} is not installed -> start installation ${NC}"
        if [ "$OFFLINE_SNAPS" = "true" ]; then
            echo "${YELLOW} -> ${package_name} offline installation! ${NC}"
            snap_path=$SCRIPT_DIR/${package_name}.snap
            assert_path=$SCRIPT_DIR/${package_name}.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)
            snap ack $assert_path
            snap install --classic $snap_path
        else
            echo "${YELLOW}${package_name} will be automatically installed ...${NC}"
        fi
    fi
}


function install_helm {
    if command -v helm &> /dev/null
    then
        echo ""
        echo "${GREEN}Helm is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
    else
        echo "${YELLOW}Helm is not installed -> start installation ${NC}"
        if [ "$OFFLINE_SNAPS" = "true" ];then
            echo "${YELLOW} -> Helm offline installation! ${NC}"
            snap_path=$SCRIPT_DIR/helm.snap
            assert_path=$SCRIPT_DIR/helm.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)
            snap ack $assert_path
            snap install --classic $snap_path
        else
            echo "${YELLOW}Installing Helm v$DEFAULT_HELM_VERSION ...${NC}"
            snap install helm --classic --channel=$DEFAULT_HELM_VERSION
        fi
    fi
}

function install_snapd {
    local package_name="snapd"
    echo "${YELLOW}Checking if ${package_name} is installed ... ${NC}"
    if ls -l /var/lib/snapd/snaps | grep "${package_name}\.snap" ;
    then
        echo ""
        echo "${GREEN}${package_name} is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
    else
        echo "${YELLOW}${package_name} is not installed -> start installation ${NC}"
        if [ "$OFFLINE_SNAPS" = "true" ]; then
            echo "${YELLOW} -> ${package_name} offline installation! ${NC}"
            snap_path=$SCRIPT_DIR/${package_name}.snap
            assert_path=$SCRIPT_DIR/${package_name}.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)
            snap ack $assert_path
            snap install --classic $snap_path
        else
            echo "${YELLOW}${package_name} will be automatically installed ...${NC}"
        fi
    fi
}


function dns_check {
    if [[ -n "$DNS" ]]; then
        echo "${GREEN}${NC}"
        echo "${GREEN}DNS has been manually configured to '$DNS' ...${NC}"
        echo "${GREEN}${NC}"
    else
        if [[ "$OFFLINE_SNAPS" != true ]]; then
            echo "${GREEN}Checking server DNS settings ...${NC}"
            
            if command -v nslookup &> /dev/null; then
                TOOL="nslookup"
            elif command -v dig &> /dev/null; then
                TOOL="dig"
            else
                echo -e "${RED}Neither nslookup nor dig is installed on this system.${NC}"
                echo -e "${RED}Please install nslookup (bind-utils on AlmaLinux/RHEL, dnsutils on Ubuntu/Debian) or dig.${NC}"
                exit 1
            fi
            
            if command -v $TOOL dkfz.de &> /dev/null; then
                echo "${GREEN}DNS lookup was successful ...${NC}"
            else
                echo ""
                echo "${RED}DNS lookup failed -> please check your servers DNS configuration ...${NC}"
                echo "${RED}You can test it with: '$TOOL dkfz.de'${NC}"
                echo ""
                exit 1
            fi
        fi

        echo "${GREEN}Get DNS settings nmcli ...${NC}"
        DNS=$( (nmcli dev list || nmcli dev show) 2>/dev/null | grep DNS | awk -F ' ' '{print $2}' | tr '\ ' ',' | sed 's/,$/\n/' || true )

        if [[ -z "$DNS" ]]; then
            echo "${YELLOW} Trying resolvectl ...${NC}"
            DNS=$(resolvectl status |grep 'DNS Servers' | awk -F ': ' '{print $2}' | tr '\ ' ',' | sed 's/,$/\n/')
        fi

        if [[ -z "$DNS" ]]; then
            echo "${YELLOW} Trying systemd-resolve...${NC}"
            DNS=$(systemd-resolve --status |grep 'DNS Servers' | awk -F ': ' '{print $2}' | tr '\ ' ',' | sed 's/,$/\n/')
        fi

        if [[ -z "$DNS" ]]; then
            if [[ "$OFFLINE_SNAPS" == true ]]; then
                echo "${YELLOW}No DNS found, setting fallback DNS...${NC}"
                DNS="8.8.8.8,8.8.4.4"
            else
                echo "${RED}DNS lookup failed.${NC}"
                exit 1
            fi
        fi

        ## Format DNS to be a comma separated list of IP addresses without spaces and newlines
        DNS=$(echo -e $DNS | tr -s ' \n,' ',' | sed 's/,$/\n/')
        echo "${YELLOW}Identified DNS: $DNS ${NC}"
    fi
}

function apply_calico_mtu {
    local mtu_value="$1"

    if [[ -z "$mtu_value" ]]; then
        echo "${YELLOW}Calico MTU not set, skipping configmap update.${NC}"
        return 0
    fi

    echo "${YELLOW}Setting Calico veth_mtu to ${mtu_value} ...${NC}"
    microk8s.kubectl -n kube-system patch configmap calico-config --type merge \
        -p "{\"data\":{\"veth_mtu\":\"${mtu_value}\"}}"

    # Also try to set the CNI plugin MTU if the placeholder exists
    local cni_cfg
    cni_cfg="$(microk8s.kubectl -n kube-system get cm calico-config -o jsonpath='{.data.cni_network_config}' 2>/dev/null || true)"
    if echo "$cni_cfg" | grep -q '"mtu":[[:space:]]*__CNI_MTU__'; then
        echo "${YELLOW}Patching Calico CNI config MTU to ${mtu_value} ...${NC}"
        # Escape JSON for patching
        local patched
        patched="$(echo "$cni_cfg" | sed "s/\"mtu\":[[:space:]]*__CNI_MTU__/\"mtu\": ${mtu_value}/")"
        # JSON-escape newlines and quotes for kubectl patch
        patched_escaped="$(printf '%s' "$patched" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
        microk8s.kubectl -n kube-system patch configmap calico-config --type merge \
            -p "{\"data\":{\"cni_network_config\":${patched_escaped}}}"
    fi

    echo "${YELLOW}Restarting calico-node to apply MTU ...${NC}"
    microk8s.kubectl -n kube-system rollout restart ds/calico-node
    microk8s.kubectl -n kube-system rollout status ds/calico-node --timeout=120s
}

function wait_for_microk8s_network_ready {
    local timeout_seconds="${1:-180}"
    local node_name=""
    local deadline=0
    local now=0
    local taint=""
    local network_unavailable=""
    local calico_ready=""
    local taint_cleared=false

    node_name="$(microk8s.kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
    if [[ -z "$node_name" ]]; then
        echo "${RED}Could not determine the microk8s node name.${NC}"
        exit 1
    fi

    echo "${YELLOW}Waiting for node ${node_name} network readiness ...${NC}"
    deadline=$((SECONDS + timeout_seconds))

    while (( SECONDS < deadline )); do
        taint="$(microk8s.kubectl get node "$node_name" -o jsonpath='{range .spec.taints[*]}{.key}={.effect}{"\n"}{end}' 2>/dev/null || true)"
        network_unavailable="$(microk8s.kubectl get node "$node_name" -o jsonpath='{range .status.conditions[?(@.type=="NetworkUnavailable")]}{.status}{end}' 2>/dev/null || true)"
        calico_ready="$(microk8s.kubectl -n kube-system get pods -l k8s-app=calico-node --field-selector "spec.nodeName=${node_name}" -o jsonpath='{range .items[*].status.conditions[?(@.type=="Ready")]}{.status}{end}' 2>/dev/null || true)"

        if [[ "$taint" != *"node.kubernetes.io/network-unavailable=NoSchedule"* && "$network_unavailable" != "True" ]]; then
            echo "${GREEN}Node ${node_name} network is ready.${NC}"
            return 0
        fi

        if [[ "$calico_ready" == "True" && "$taint" == *"node.kubernetes.io/network-unavailable=NoSchedule"* && "$taint_cleared" == false ]]; then
            echo "${YELLOW}Calico is ready but node ${node_name} still has a stale network-unavailable taint. Clearing it ...${NC}"
            microk8s.kubectl taint nodes "$node_name" node.kubernetes.io/network-unavailable:NoSchedule- || true
            taint_cleared=true
        fi

        sleep 5
    done

    echo "${RED}Timed out waiting for node ${node_name} network readiness.${NC}"
    microk8s.kubectl describe node "$node_name" || true
    exit 1
}

function detect_calico_mtu {
    # Returns a best-guess MTU for Calico VXLAN
    # Priority:
    #   1) existing vxlan.calico MTU (most truthful if calico already up)
    #   2) underlay iface MTU - VXLAN overhead (default 50)
    local overhead="${1:-50}"

    # Try to read MTU from vxlan.calico if it exists
    local vxlan_mtu
    vxlan_mtu="$(ip -o link show vxlan.calico 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="mtu"){print $(i+1); exit}}')"
    if [[ -n "$vxlan_mtu" && "$vxlan_mtu" =~ ^[0-9]+$ ]]; then
        echo "$vxlan_mtu"
        return 0
    fi

    # Fallback: detect primary interface used for default route
    local iface
    iface="$(ip route show default 0.0.0.0/0 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')"
    if [[ -z "$iface" ]]; then
        iface="eth0"
    fi

    local underlay_mtu
    underlay_mtu="$(ip -o link show "$iface" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="mtu"){print $(i+1); exit}}')"

    if [[ -z "$underlay_mtu" || ! "$underlay_mtu" =~ ^[0-9]+$ ]]; then
        # Conservative last resort
        echo "1400"
        return 0
    fi

    local guess=$((underlay_mtu - overhead))
    if (( guess < 576 )); then
        guess=576
    fi
    echo "$guess"
}

function compute_safer_mtu {
    # Lowers detected MTU by a margin, but never below a minimum
    local detected="$1"
    local margin="${2:-50}"
    local min_mtu="${3:-1200}"

    if [[ -z "$detected" || ! "$detected" =~ ^[0-9]+$ ]]; then
        detected="$min_mtu"
    fi

    local safer=$((detected - margin))
    if (( safer < min_mtu )); then
        safer="$min_mtu"
    fi
    echo "$safer"
}

function install_microk8s {
    if command -v microk8s &> /dev/null
    then
        echo ""
        echo "${GREEN}microk8s is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
        echo ""
        echo "${GREEN}If you want to start-over use the --uninstall parameter first! ${NC}"
        echo ""
        echo ""
        exit 0
    else
        echo "${YELLOW}microk8s is not installed -> start installation ${NC}"
        dns_check

        if [ "$OFFLINE_SNAPS" = "true" ];then
            echo "${YELLOW} -> offline installation! ${NC}"

            echo "${YELLOW}Installing microk8s...${NC}"
            snap_path=$SCRIPT_DIR/microk8s.snap
            assert_path=$SCRIPT_DIR/microk8s.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)

            snap ack $assert_path
            snap install --classic $snap_path
            MICROK8S_BASE_IMAGES_TAR_PATH="$SCRIPT_DIR/microk8s_base_images.tar"
            echo "${YELLOW}Start Microk8s image import from $MICROK8S_BASE_IMAGES_TAR_PATH ... ${NC}"
            [ -f $MICROK8S_BASE_IMAGES_TAR_PATH ] && echo "${GREEN}MICROK8S_BASE_IMAGES_TAR exists ... ${NC}" || (echo "${RED}Images tar does not exist -> exit ${NC}" && exit 1)
            echo "${RED}This can take a long time! -> please be patient and wait. ${NC}"
            microk8s.ctr images import $MICROK8S_BASE_IMAGES_TAR_PATH
            microk8s kubectl apply -f /var/snap/microk8s/current/args/cni-network/cni.yaml
            echo "${GREEN}Microk8s offline installation done!${NC}"
        else
            echo "${YELLOW}Installing microk8s v$DEFAULT_MICRO_VERSION ...${NC}"
            snap install microk8s --classic --channel=$DEFAULT_MICRO_VERSION
        fi

        echo "${YELLOW}Stopping microk8s for configuration ...${NC}"
        microk8s.stop

        echo "${YELLOW}Enable node_port-range=80-32000 ...${NC}";
        insert_text "--service-node-port-range=80-32000" /var/snap/microk8s/current/args/kube-apiserver || true
        echo "${YELLOW}Disable insecure port ...${NC}";
        insert_text "--insecure-port=0" /var/snap/microk8s/current/args/kube-apiserver || true
        insert_text "--runtime-config=admissionregistration.k8s.io/v1beta1=true" /var/snap/microk8s/current/args/kube-apiserver || true

        echo "${YELLOW}Set limit of completed pods to 200 ...${NC}";
        insert_text "--terminated-pod-gc-threshold=200" /var/snap/microk8s/current/args/kube-controller-manager || true

        echo "${YELLOW}Set vm.max_map_count=262144${NC}"
        sysctl -w vm.max_map_count=262144
        insert_text "vm.max_map_count=262144" /etc/sysctl.conf || true

        echo "${YELLOW}Reload systemct daemon ...${NC}"
        systemctl daemon-reload

        echo "${YELLOW}Set alias for kubectl: $USER_HOME/.bashrc ${NC}"
        insert_text "alias kubectl=\"microk8s.kubectl\"" "$USER_HOME/.bashrc" || true

        echo "${YELLOW}Set auto-completion for kubectl: $USER_HOME/.bashrc ${NC}"
        insert_text "# microk8s.kubectl --help > /dev/null 2>&1 && source <(microk8s.kubectl completion bash)" "$USER_HOME/.bashrc" || true

        echo "${YELLOW}Starting microk8s${NC}"
        microk8s.start
        echo "${YELLOW}Wait until microk8s is ready ...${NC}"
        microk8s.status --wait-ready >/dev/null 2>&1

        # MTU tuning
        # If CALICO_VETH_MTU is set externally, respect it.
        # Otherwise autodetect and subtract a safety margin.
        CALICO_MTU_SAFETY_MARGIN="${CALICO_MTU_SAFETY_MARGIN:-50}"
        CALICO_MTU_MIN="${CALICO_MTU_MIN:-1300}"
        VXLAN_OVERHEAD="${VXLAN_OVERHEAD:-50}"

        if [[ -n "${CALICO_VETH_MTU:-}" ]]; then
            echo "${YELLOW}CALICO_VETH_MTU is set externally to ${CALICO_VETH_MTU} (no autodetect).${NC}"
        else
            detected_mtu="$(detect_calico_mtu "$VXLAN_OVERHEAD")"
            safer_mtu="$(compute_safer_mtu "$detected_mtu" "$CALICO_MTU_SAFETY_MARGIN" "$CALICO_MTU_MIN")"
            CALICO_VETH_MTU="$safer_mtu"
            echo "${YELLOW}Autodetected Calico MTU: ${detected_mtu}. Applying safety margin ${CALICO_MTU_SAFETY_MARGIN} -> using ${CALICO_VETH_MTU}.${NC}"
        fi

        apply_calico_mtu "$CALICO_VETH_MTU"
        wait_for_microk8s_network_ready "${CALICO_NETWORK_READY_TIMEOUT_SECONDS:-180}"

        echo "${YELLOW}Enable microk8s RBAC ...${NC}"
        microk8s.enable rbac

        echo "${YELLOW}Enable microk8s DNS: '$DNS' ...${NC}"
        microk8s.enable dns:$DNS

        echo "${YELLOW}Waiting for DNS to be ready ...${NC}"
        microk8s.kubectl rollout status -n kube-system deployment coredns --timeout=120s

        echo "${YELLOW}Create dir: $USER_HOME/.kube ...${NC}"
        mkdir -p $USER_HOME/.kube

        echo "${YELLOW}Export Kube-Config to $USER_HOME/.kube/config ...${NC}"
        microk8s.kubectl config view --raw | tee $USER_HOME/.kube/config
        chmod 600 $USER_HOME/.kube/config

        echo "${YELLOW}Enable microk8s hostpath-storage ...${NC}"
        microk8s.enable hostpath-storage

        if [ "$REAL_USER" != "root" ]; then
            echo "${YELLOW} Setting non-root permissions ...${NC}"
            sudo usermod -a -G microk8s $REAL_USER
            sudo chown -f -R $REAL_USER $USER_HOME/.kube
        fi

        echo ""
        echo ""
        echo ""

        if [ "$REAL_USER" != "root" ]; then
            echo "${GREEN}           Installation successful.${NC}"
            echo "${GREEN}                 Please run:${NC}"
            echo ""
            echo "${RED}----->           newgrp microk8s           <-----${NC}"
            echo ""
            echo "${GREEN}           or reboot the system${NC}"
            echo ""
        fi
        echo ""
        echo "${GREEN}You can now continue with the platform deployment script.${NC}"
        echo ""
        echo ""
        echo ""

        create_post_reinstall_recovery_marker
    fi
    echo ""
    echo "${GREEN} DONE ${NC}"
    echo ""
}

function uninstall {
    echo ""
    echo "${YELLOW}Uninstalling Helm ...${NC}"
    snap remove helm --purge && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"

    echo "${YELLOW}Uninstalling microk8s ...${NC}"
    snap remove microk8s --purge && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"
    echo ""
    echo ""
    echo "${YELLOW}UNINSTALLATION DONE ${NC}"
    echo ""
    echo ""

}

install_gpu_operator() {
  local script_dir="$1"

  if [[ -z "${script_dir}" ]]; then
    echo "install_gpu_operator: missing required argument: script_dir" >&2
    return 1
  fi

  # Constants
  local chart_name="gpu-operator"
  local chart_version="v25.3.0"
  local helm="/snap/bin/helm"
  local containerd_socket="/var/snap/microk8s/common/run/containerd.sock"
  local containerd_toml="/var/snap/microk8s/current/args/containerd-template.toml"

  local chart_path="${script_dir%/}/gpu-operator.tgz"

  if [[ ! -f "${chart_path}" ]]; then
    echo "install_gpu_operator: chart not found at ${chart_path}" >&2
    return 1
  fi

  # Match Python: only distinguish by presence of nvidia-smi (OSError equivalent)
  local driver
  if command -v nvidia-smi >/dev/null 2>&1; then
    driver="host"
  else
    driver="operator"
  fi

  local driver_enabled
  if [[ "${driver}" == "operator" ]]; then
    driver_enabled="true"
  else
    driver_enabled="false"
  fi

  # Feed JSON values to Helm via stdin (equivalent to -f - in the Python script)
  cat <<EOF | "${helm}" install "${chart_name}" "${chart_path}" \
    --version="${chart_version}" \
    --create-namespace \
    --namespace="${chart_name}-resources" \
    -f -
{
  "operator": {
    "defaultRuntime": "containerd"
  },
  "driver": {
    "enabled": "${driver_enabled}"
  },
  "toolkit": {
    "enabled": "true",
    "env": [
      { "name": "CONTAINERD_CONFIG", "value": "${containerd_toml}" },
      { "name": "CONTAINERD_SOCKET", "value": "${containerd_socket}" },
      { "name": "CONTAINERD_SET_AS_DEFAULT", "value": "1" }
    ]
  }
}
EOF
}


function init_colors {
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
}

function load_kaapana_config {
    ######################################################
    # Deployment configuration
    ######################################################

    # dev-mode -> containers will always be re-downloaded after pod-restart
    DEV_MODE=true
    GPU_SUPPORT=false
    # Adjust enable nvidia command if using GPU Operator below v25.10.0+
    GPU_OPERATOR_VERSION="v25.10.0"
    PREFETCH_EXTENSIONS=false
    CHART_PATH=""
    NO_HOOKS=""
    OFFLINE_MODE=false
    IGNORE_DOMAIN_REACHABILITY_CHECK=false
    POST_REINSTALL_RECOVERY_REQUESTED="${POST_REINSTALL_RECOVERY_REQUESTED:-false}"
    POST_REINSTALL_RECOVERY_MARKER=""
    POST_REINSTALL_PLATFORM_RELEASE_NAME="${POST_REINSTALL_PLATFORM_RELEASE_NAME:-kaapana-platform-chart}"
    # Bootstrap pull auto-heal defaults are intentionally conservative and scoped.
    IMAGE_PULL_AUTOHEAL_ENABLED="${IMAGE_PULL_AUTOHEAL_ENABLED:-true}"
    IMAGE_PULL_AUTOHEAL_TIMEOUT_SECONDS="${IMAGE_PULL_AUTOHEAL_TIMEOUT_SECONDS:-1200}"
    IMAGE_PULL_AUTOHEAL_INTERVAL_SECONDS="${IMAGE_PULL_AUTOHEAL_INTERVAL_SECONDS:-30}"
    IMAGE_PULL_AUTOHEAL_NAMESPACES="${IMAGE_PULL_AUTOHEAL_NAMESPACES:-admin services}"
    IMAGE_PULL_AUTOHEAL_POD_REGEX="${IMAGE_PULL_AUTOHEAL_POD_REGEX:-^(kube-helm-deployment-|init-extensions-|init-collections-|keycloak-|auth-backend-|oauth2-proxy-|ollama-).*$}"
    # Bootstrap image prefetch is opt-in via --prefetch-bootstrap-images.
    BOOTSTRAP_IMAGE_PREFETCH_ENABLED="${BOOTSTRAP_IMAGE_PREFETCH_ENABLED:-false}"
    BOOTSTRAP_IMAGE_PREFETCH_IMAGES="${BOOTSTRAP_IMAGE_PREFETCH_IMAGES:-service-checker kube-helm auth-backend keycloak keycloak-init oauth2-proxy ollama}"
    # Project namespace reconciliation defaults to enabled and can be skipped via --no-reconcile-project-namespaces.
    POST_DEPLOY_RECONCILE_ENABLED="${POST_DEPLOY_RECONCILE_ENABLED:-true}"
    POST_DEPLOY_RECONCILE_WAIT_SECONDS="${POST_DEPLOY_RECONCILE_WAIT_SECONDS:-1200}"

    INSTANCE_UID=""
    SERVICES_NAMESPACE="services"
    ADMIN_NAMESPACE="admin"
    EXTENSIONS_NAMESPACE="extensions"
    HELM_NAMESPACE="default"

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
    CREDENTIALS_MINIO_USERNAME="kaapanaminio"
    CREDENTIALS_MINIO_PASSWORD="Kaapana2020"

    GRAFANA_USERNAME="admin"
    GRAFANA_PASSWORD="admin"

    KEYCLOAK_ADMIN_USERNAME="admin"
    KEYCLOAK_ADMIN_PASSWORD="Kaapana2020" #  Minimum policy for production: 1 specialChar + 1 upperCase + 1 lowerCase and 1 digit + min-length = 8

    FAST_DATA_DIR="/home/kaapana" # Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
    SLOW_DATA_DIR="/home/kaapana" # Directory on the server, where the DICOM images will be stored (can be slower)

    HTTP_PORT="80"      # -> has to be 80
    HTTPS_PORT="443"    # HTTPS port
    DICOM_PORT="11112"  # configure DICOM receiver port

    SMTP_HOST=""
    SMTP_PORT="0"
    EMAIL_ADDRESS_SENDER=""
    SMTP_USERNAME=""
    SMTP_PASSWORD=""

    VERSION_IMAGE_COUNT="20"
    DEPLOYMENT_TIMESTAMP=$(date --iso-8601=seconds)
    MOUNT_POINTS_TO_MONITOR=""

    INSTANCE_NAME=""

    ######################################################
    # Storage
    ######################################################
    STORAGE_PROVIDER="hostpath" # e.g. "hostpath" (microk8s) or "longhorn"
    # kaapanactl default: Delete. Use --hostpath-reclaim-policy Retain to opt
    # into retained hostpath PVs and post-reinstall recovery.
    HOSTPATH_RECLAIM_POLICY="${HOSTPATH_RECLAIM_POLICY:-Delete}" # Delete or Retain for Kaapana hostpath StorageClasses
    VOLUME_SLOW_DATA="100Gi" # size of volumes in slow data dir (e.g. 100Gi or 100Ti)
}

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

function is_ipv4 {
    local ip="${1:-}"
    [[ "$ip" =~ ^(([1-9]?[0-9]|1[0-9][0-9]|2([0-4][0-9]|5[0-5]))\.){3}([1-9]?[0-9]|1[0-9][0-9]|2([0-4][0-9]|5[0-5]))$ ]]
}

function create_post_reinstall_recovery_marker {
    local real_user_home="$HOME"
    local marker_path
    [[ -n "${SUDO_USER:-}" ]] && real_user_home="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
    marker_path="${real_user_home}/.kaapana/post-reinstall-recovery-pending"
    if [[ -n "${SUDO_USER:-}" && "$EUID" -eq 0 ]]; then
        sudo -u "$SUDO_USER" mkdir -p "$(dirname "$marker_path")"
        sudo -u "$SUDO_USER" touch "$marker_path"
    else
        mkdir -p "$(dirname "$marker_path")"
        : > "$marker_path"
    fi
    echo -e "${YELLOW}Marked fresh server install for optional post-reinstall recovery: ${marker_path}${NC}"
}

function clear_post_reinstall_recovery_marker {
    local real_user_home="$HOME"
    local marker_path
    [[ -n "${SUDO_USER:-}" ]] && real_user_home="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
    marker_path="${POST_REINSTALL_RECOVERY_MARKER:-${real_user_home}/.kaapana/post-reinstall-recovery-pending}"
    if [[ -f "$marker_path" ]]; then
        if rm -f "$marker_path" 2>/dev/null; then
            echo -e "${GREEN}Cleared post-reinstall recovery marker: ${marker_path}${NC}"
        else
            echo -e "${YELLOW}Could not clear post-reinstall recovery marker without sudo: ${marker_path}${NC}"
        fi
    fi
}

# FLAGGED: recovery-content detection depends on real data-dir layout and should not be simplified without validating live installs.
function data_dir_has_recovery_content {
    local data_dir="$1"

    if [ -z "$data_dir" ] || [ ! -d "$data_dir" ]; then
        return 1
    fi

    if find "$data_dir" -maxdepth 3 \
        \( -name 'extensions' -o -name 'project-*' -o -name '*pvc-*' -o -name '*pv-claim*' \) \
        -print -quit 2>/dev/null | grep -q .; then
        return 0
    fi

    return 1
}

function recovery_data_detected {
    data_dir_has_recovery_content "$FAST_DATA_DIR" || data_dir_has_recovery_content "$SLOW_DATA_DIR"
}

# FLAGGED: cluster-state detection depends on live helm/kubectl state and should not be collapsed without runtime verification.
function platform_state_already_exists {
    if $HELM_EXECUTABLE -n "$ADMIN_NAMESPACE" ls --short 2>/dev/null | grep -q .; then
        return 0
    fi

    if $HELM_EXECUTABLE -n "$HELM_NAMESPACE" ls --short 2>/dev/null | grep -q .; then
        return 0
    fi

    if microk8s.kubectl get namespace "$ADMIN_NAMESPACE" >/dev/null 2>&1; then
        return 0
    fi

    if microk8s.kubectl get namespace "$SERVICES_NAMESPACE" >/dev/null 2>&1; then
        return 0
    fi

    if microk8s.kubectl get ns --no-headers 2>/dev/null | awk '{print $1}' | grep -q '^project-'; then
        return 0
    fi

    return 1
}

# Delegate post-reinstall recovery work to the helper script before deploy.
function run_post_reinstall_recovery {
    local script_dir
    local post_reinstall_script
    local chart_ref
    local recovery_cmd=()

    require_retain_hostpath_reclaim_policy_for_recovery || return 1

    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    post_reinstall_script="${script_dir}/utils/post-server-reinstall.sh"
    if [[ ! -r "${post_reinstall_script}" ]]; then
        post_reinstall_script="${script_dir}/../utils/post-server-reinstall.sh"
    fi

    if [[ ! -r "${post_reinstall_script}" ]]; then
        echo -e "${RED}Post-reinstall recovery helper missing or not readable: ${post_reinstall_script}${NC}"
        return 1
    fi

    chart_ref="${CONTAINER_REGISTRY_URL}/${PLATFORM_NAME}:${PLATFORM_VERSION}"

    echo -e "${YELLOW}Running delegated post-reinstall recovery before deployment...${NC}"
    recovery_cmd=(
        # Run helpers through bash so deployments do not depend on the executable bit.
        bash "$post_reinstall_script"
        --chart "$chart_ref"
        --registry-username "$CONTAINER_REGISTRY_USERNAME"
        --registry-password "$CONTAINER_REGISTRY_PASSWORD"
        --fast-dir "$FAST_DATA_DIR"
        --slow-dir "$SLOW_DATA_DIR"
        --hostpath-reclaim-policy "$HOSTPATH_RECLAIM_POLICY"
        --admin-release-name "$PLATFORM_NAME"
        --platform-release-name "$POST_REINSTALL_PLATFORM_RELEASE_NAME"
    )

    "${recovery_cmd[@]}"

    POST_DEPLOY_RECONCILE_ENABLED=true
    echo -e "${GREEN}Post-reinstall recovery finished. Project namespace reconciliation will run after deploy.${NC}"
    clear_post_reinstall_recovery_marker
}

function maybe_run_post_reinstall_recovery {
    local marker_path
    local has_marker=false
    local has_data=false
    local force_recovery="${POST_REINSTALL_RECOVERY_REQUESTED:-false}"
    local answer=""

    local real_user_home="$HOME"
    [[ -n "${SUDO_USER:-}" ]] && real_user_home="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
    marker_path="${real_user_home}/.kaapana/post-reinstall-recovery-pending"
    POST_REINSTALL_RECOVERY_MARKER="$marker_path"

    if [ -f "$marker_path" ]; then
        has_marker=true
    fi

    if recovery_data_detected; then
        has_data=true
    fi

    if [[ "${force_recovery,,}" == "true" ]]; then
        echo -e "${YELLOW}Post-reinstall recovery requested explicitly.${NC}"
        run_post_reinstall_recovery || exit 1
        return 0
    fi

    if [[ "$has_marker" != true ]]; then
        return 0
    fi

    if [[ "$has_data" != true ]]; then
        echo -e "${YELLOW}Fresh server-install marker found, but no Kaapana data was detected in the configured data dirs.${NC}"
        clear_post_reinstall_recovery_marker
        return 0
    fi

    if platform_state_already_exists; then
        echo -e "${YELLOW}Post-reinstall recovery marker found, but platform state already exists in the cluster. Skipping automatic recovery.${NC}"
        clear_post_reinstall_recovery_marker
        return 0
    fi

    # Marker-based recovery is automatic, so keep it conservative: notify the
    # operator instead of enabling Retain implicitly.
    if [[ "$HOSTPATH_RECLAIM_POLICY" != "Retain" ]]; then
        echo -e "${YELLOW}Post-reinstall recovery marker found, but hostpath reclaim policy is '${HOSTPATH_RECLAIM_POLICY}'.${NC}"
        echo -e "${YELLOW}Skipping automatic recovery. Rerun deploy with --hostpath-reclaim-policy Retain --recover-after-reinstall to opt into retained hostpath PVs.${NC}"
        return 0
    fi

    if [[ "${QUIET,,}" == "true" ]]; then
        echo -e "${RED}Detected a post-reinstall recovery situation, but quiet mode cannot ask for confirmation.${NC}"
        echo -e "${RED}Re-run deploy with --recover-after-reinstall to execute recovery explicitly.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Detected a fresh server install plus existing Kaapana data directories.${NC}"
    echo -e "${YELLOW}Run post-reinstall recovery now before Helm deploy? [yes/no]${NC}"
    read -r answer
    case "${answer,,}" in
        y|yes)
            run_post_reinstall_recovery || exit 1
            ;;
        n|no)
            echo -e "${YELLOW}Skipping post-reinstall recovery. The marker will be kept so you can retry on the next deploy.${NC}"
            ;;
        *)
            echo -e "${RED}Please answer yes or no. Re-run deploy to choose again, or pass --recover-after-reinstall.${NC}"
            exit 1
            ;;
    esac
}

function check_domain_reachable_to_host {
    local domain="${1:-}"
    local ignore_domain_check="${IGNORE_DOMAIN_REACHABILITY_CHECK:-false}"
    local resolved_ips=""
    local resolved_ip_csv=""
    local local_ips_raw=""
    local local_ip_csv=""
    local resolved_ip=""
    local host_ip=""
    local match=false
    local -a local_ips=()

    function _domain_check_fail_or_override {
        if [[ "${ignore_domain_check,,}" == "true" ]]; then
            echo -e "${YELLOW}WARNING: Continuing because --ignore-domain-reachability-check is set.${NC}" > /dev/stderr
            return 0
        fi
        return 1
    }

    if [ -z "$domain" ]; then
        echo -e "${RED}================================================================================${NC}" > /dev/stderr
        echo -e "${RED}ERROR: DOMAIN reachability check failed because DOMAIN is not set.${NC}" > /dev/stderr
        echo -e "${RED}================================================================================${NC}" > /dev/stderr
        if ! _domain_check_fail_or_override; then
            return 1
        fi
        return 0
    fi

    if is_ipv4 "$domain"; then
        echo -e "${GREEN}INFO: Skipping DNS reachability check because DOMAIN is an IP address: $domain${NC}" > /dev/stderr
        return 0
    fi

    if ! command -v getent &> /dev/null; then
        echo -e "${RED}================================================================================${NC}" > /dev/stderr
        echo -e "${RED}ERROR: Could not validate DOMAIN reachability because 'getent' is unavailable.${NC}" > /dev/stderr
        echo -e "${RED}ERROR: Install libc-bin / glibc-common (distribution dependent) to enable checks.${NC}" > /dev/stderr
        echo -e "${RED}================================================================================${NC}" > /dev/stderr
        if ! _domain_check_fail_or_override; then
            return 1
        fi
        return 0
    fi

    resolved_ips=$(getent ahostsv4 "$domain" 2>/dev/null | awk '{print $1}' | sort -u || true)
    if [ -z "$resolved_ips" ]; then
        echo -e "${RED}================================================================================${NC}" > /dev/stderr
        echo -e "${RED}ERROR: DOMAIN reachability check failed.${NC}" > /dev/stderr
        echo -e "${RED}ERROR: Could not resolve DOMAIN '$domain' to an IPv4 address.${NC}" > /dev/stderr
        echo -e "${RED}ERROR: Please fix DNS or use a correct --domain value.${NC}" > /dev/stderr
        echo -e "${RED}================================================================================${NC}" > /dev/stderr
        if ! _domain_check_fail_or_override; then
            return 1
        fi
        return 0
    fi

    local_ips_raw=$(hostname -I 2>/dev/null || true)
    for host_ip in $local_ips_raw; do
        if is_ipv4 "$host_ip" && [[ ! "$host_ip" =~ ^127\. ]]; then
            if ! printf '%s\n' "${local_ips[@]}" | grep -qx "$host_ip"; then
                local_ips+=("$host_ip")
            fi
        fi
    done

    if [ "${#local_ips[@]}" -eq 0 ]; then
        echo -e "${YELLOW}================================================================================${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: DOMAIN validation could not compare DNS to local IPv4 addresses.${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Could not determine non-loopback local IPv4 addresses.${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Continuing because DOMAIN resolved successfully and routed installs can terminate on an upstream IP.${NC}" > /dev/stderr
        echo -e "${YELLOW}================================================================================${NC}" > /dev/stderr
        return 0
    fi

    for resolved_ip in $resolved_ips; do
        for host_ip in "${local_ips[@]}"; do
            if [ "$resolved_ip" = "$host_ip" ]; then
                match=true
                break 2
            fi
        done
    done

    if [ "$match" = "false" ]; then
        resolved_ip_csv=$(echo "$resolved_ips" | tr '\n' ',' | sed 's/,$//')
        local_ip_csv=$(printf '%s\n' "${local_ips[@]}" | tr '\n' ',' | sed 's/,$//')

        # In routed/NAT deployments the published clinic-side or RACOON-side IP
        # can legitimately differ from the VM's own interface addresses. Treat
        # the mismatch as informational as long as DNS resolution itself works.
        echo -e "${YELLOW}================================================================================${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: DOMAIN resolves to a non-local IPv4 address.${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Entered DOMAIN: $domain${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Resolved IPv4: $resolved_ip_csv${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Local IPv4:    $local_ip_csv${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Continuing because routed/NAT/RAS deployments can forward DOMAIN traffic to this VM via an upstream IP.${NC}" > /dev/stderr
        echo -e "${YELLOW}WARNING: Verify that the required ports are forwarded from the published DOMAIN endpoint to this host.${NC}" > /dev/stderr
        echo -e "${YELLOW}================================================================================${NC}" > /dev/stderr
        return 0
    fi

    echo -e "${GREEN}INFO: DOMAIN reachability check passed: $domain resolves to this host.${NC}" > /dev/stderr
    return 0
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
            echo -e "NS lookup failed, could not determine DOMAIN from SERVER_IP. Run the script with explicit domain name: ./kaapanactl.sh deploy --domain <domain-name>"
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
    fi

    check_domain_reachable_to_host "$DOMAIN"
    # Validate any persisted cert files or certificate secrets against the
    # chosen hostname before Helm starts. This catches stale TLS state from
    # previous deployments or reinstalls early, while still allowing fresh
    # installs where no certificate state exists yet.
    analyze_existing_certificate_state "$DOMAIN"

        echo -e "${GREEN}Server domain (FQDN): $DOMAIN ${NC}" > /dev/stderr;
}

function analyze_existing_certificate_state {
    local expected_hostname="$1"
    local script_dir=""
    local reset_script=""
    local analysis_status=0

    if [[ -z "$expected_hostname" ]]; then
        return 0
    fi

    script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    reset_script="${script_dir}/utils/reset_certificate_state.sh"
    if [[ ! -f "$reset_script" ]]; then
        reset_script="${script_dir}/../utils/reset_certificate_state.sh"
    fi

    if [[ ! -f "$reset_script" ]]; then
        echo -e "${YELLOW}Certificate analysis helper not found, skipping existing certificate check.${NC}" > /dev/stderr
        return 0
    fi

    echo -e "${GREEN}Analyzing existing certificate state for hostname ${expected_hostname}...${NC}" > /dev/stderr
    # This preflight is informational only. Fresh installs legitimately have no
    # certificate files or secrets yet because cert-init generates them later.
    if [[ "${IGNORE_CERTIFICATE_STATE,,}" == "true" ]]; then
        # Keep the analysis visible in override mode so operators still see the
        # mismatch details even when they intentionally force the deployment.
        echo -e "${YELLOW}WARNING: Continuing because --ignore-certificate-state is set.${NC}" > /dev/stderr
        bash "$reset_script" \
            --analyze-only \
            --hostname "$expected_hostname" \
            --fast-dir "$FAST_DATA_DIR" \
            --kubectl microk8s.kubectl \
            --admin-namespace "$ADMIN_NAMESPACE" \
            --services-namespace "$SERVICES_NAMESPACE" || \
            echo -e "${YELLOW}Existing certificate analysis reported an execution problem, continuing deploy anyway.${NC}" > /dev/stderr
        return 0
    fi

    # Exit code 2 from the helper means "certificate issues found" and is used
    # to block deploy with a guided reset message. Other non-zero exits are
    # treated as helper execution problems and do not hard-fail the deploy.
    analysis_status=0
    bash "$reset_script" \
        --analyze-only \
        --fail-on-issues \
        --hostname "$expected_hostname" \
        --fast-dir "$FAST_DATA_DIR" \
        --kubectl microk8s.kubectl \
        --admin-namespace "$ADMIN_NAMESPACE" \
        --services-namespace "$SERVICES_NAMESPACE" || analysis_status=$?

    if [[ "$analysis_status" -eq 0 ]]; then
        return 0
    fi

    if [[ "$analysis_status" -eq 2 ]]; then
        echo -e "${RED}Existing certificate state does not match the selected hostname or validity requirements.${NC}" > /dev/stderr
        echo -e "${RED}Clear the persisted certificate state before deploying, for example:${NC}" > /dev/stderr
        echo -e "${RED}  sudo bash ${reset_script} --yes${NC}" > /dev/stderr
        # Installing a foreign certificate is safer after the reset so no stale
        # Kaapana-generated files or OpenSearch trust artifacts survive.
        echo -e "${RED}If you want to use a foreign certificate, reset first and then run ./kaapanactl.sh deploy --install-certs before deploying again.${NC}" > /dev/stderr
        echo -e "${RED}Or re-run deploy with --ignore-certificate-state to override this preflight.${NC}" > /dev/stderr
        exit 1
    fi

    echo -e "${YELLOW}Existing certificate analysis reported an execution problem, continuing deploy anyway.${NC}" > /dev/stderr
}

function delete_deployment {
    ensure_helm_uses_microk8s_config

    HELM_UNINSTALL_TIMEOUT="${HELM_UNINSTALL_TIMEOUT:-15m0s}"
    HELM_UNINSTALL_BASE_FLAGS="${NO_HOOKS} --ignore-not-found --timeout ${HELM_UNINSTALL_TIMEOUT}"
    if $HELM_EXECUTABLE version --short 2>/dev/null | grep -qE '^v4\.' && [[ "${HELM_UNINSTALL_BASE_FLAGS}" != *"--no-hooks"* ]]; then
        # Helm v4 waits for uninstall hooks by default (hookOnly), which can stall undeploy.
        HELM_UNINSTALL_BASE_FLAGS="--no-hooks ${HELM_UNINSTALL_BASE_FLAGS}"
    fi

    cleanup_orphaned_pods_for_undeploy

    echo -e "${YELLOW}Undeploy releases${NC}"
    for namespace in $ADMIN_NAMESPACE $HELM_NAMESPACE; do
        # Do not block undeploy on one chart uninstall.
        $HELM_EXECUTABLE -n "$namespace" ls --deployed --failed --pending --superseded --uninstalling --date --reverse --short | xargs -r -I % sh -c "$HELM_EXECUTABLE -n $namespace uninstall ${HELM_UNINSTALL_BASE_FLAGS} %; sleep 2" || true
    done

    echo -e "${YELLOW}Waiting until everything is terminated ...${NC}"
    WAIT_UNINSTALL_COUNT=100
    for idx in $(seq 0 $WAIT_UNINSTALL_COUNT)
    do
        sleep 3
        if [ "$idx" -eq 2 ]; then
            echo "Deleting helm charts in 'uninstalling' state with --no-hooks"
            for namespace in $ADMIN_NAMESPACE $HELM_NAMESPACE; do
                $HELM_EXECUTABLE -n "$namespace" ls --uninstalling --short | xargs -r -I % sh -c "$HELM_EXECUTABLE -n $namespace uninstall --no-hooks --ignore-not-found --wait --timeout ${HELM_UNINSTALL_TIMEOUT} %; sleep 2" || true
            done
        fi
        TERMINATING_PODS=$(microk8s.kubectl get pods --all-namespaces --no-headers 2>/dev/null | awk '$4 == "Terminating" { print $1 "/" $2 }')
        UNINSTALLING_RELEASES=""
        for namespace in $ADMIN_NAMESPACE $HELM_NAMESPACE; do
            NS_UNINSTALLING=$($HELM_EXECUTABLE -n "$namespace" ls --uninstalling --short 2>/dev/null || true)
            if [ -n "$NS_UNINSTALLING" ]; then
                while IFS= read -r release; do
                    if [ -n "$release" ]; then
                        UNINSTALLING_RELEASES="${UNINSTALLING_RELEASES}${namespace}/${release} "
                    fi
                done <<< "$NS_UNINSTALLING"
            fi
        done
        echo -e ""
        # Undeploy is done only when no pods are terminating and no Helm release
        # remains in uninstalling state.
        UNINSTALL_TEST="${TERMINATING_PODS}${UNINSTALLING_RELEASES}"
        if [ -z "$UNINSTALL_TEST" ]; then
            break
        else
            if [ -n "$TERMINATING_PODS" ]; then
                echo -e "${YELLOW}Waiting for terminating pods: $TERMINATING_PODS ${NC}"
            fi
            if [ -n "$UNINSTALLING_RELEASES" ]; then
                echo -e "${YELLOW}Waiting for uninstalling releases: $UNINSTALLING_RELEASES ${NC}"
            fi
        fi
    done

    cleanup_orphaned_pods_for_undeploy

    if [ "$idx" -eq "$WAIT_UNINSTALL_COUNT" ]; then
        echo "${RED}Something went wrong while undeployment please check manually if there are still namespaces or pods floating around. Everything must be delete before the deployment:${NC}"
        echo "${RED}kubectl get pods -A${NC}"
        echo "${RED}kubectl get namespaces${NC}"
        echo "${RED}Executing './kaapanactl.sh deploy --no-hooks' is an option to force the resources to be removed.${NC}"
        echo "${RED}Once everything is deleted you can re-deploy the platform!${NC}"
        exit 1
    fi


    echo -e "${GREEN}####################################  UNDEPLOYMENT DONE  ############################################${NC}"
}

function cleanup_orphaned_pods_for_undeploy {
    echo -e "${YELLOW}Cleaning up orphaned pods in Kubernetes namespaces ...${NC}"

    # Clean SERVICES_NAMESPACE
    if microk8s.kubectl get namespace $SERVICES_NAMESPACE &>/dev/null; then
        echo "Deleting all pods in $SERVICES_NAMESPACE"
        microk8s.kubectl delete pods --all -n $SERVICES_NAMESPACE --grace-period=0 --force 2>/dev/null || true
    fi

    # Clean all project-* namespaces
    PROJECT_NAMESPACES=$(microk8s.kubectl get namespaces --no-headers -o custom-columns=NAME:.metadata.name | grep "^project-" || true)
    for ns in $PROJECT_NAMESPACES; do
        echo "Deleting all pods in $ns"
        microk8s.kubectl delete pods --all -n $ns --grace-period=0 --force 2>/dev/null || true
    done
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
    echo "${YELLOW}Deleting all deployments in namespace default ${NC}"
    microk8s.kubectl delete deployments --all
    echo "${YELLOW}Deleting all jobs in namespace default ${NC}"
    microk8s.kubectl delete jobs --all
    echo "${YELLOW}Removing remove-secret job${NC}"
    microk8s.kubectl -n $SERVICES_NAMESPACE delete job --ignore-not-found remove-secret
}

function import_container_images_tar {
    echo "${RED}Importing the images from the tar, this might take a long time -> please be patient and wait.${NC}"
    microk8s.ctr images import $TAR_PATH
    echo "${GREEN}Finished image upload! You should now be able to deploy the platform by specifying the chart path.${NC}"
}

function run_migration_chart() {
    local FROM_VERSION="$1"
    local TO_VERSION="$2"
    local WORKDIR
    local MIGRATION_CHART_PATH
    local HELM_CMD

    echo -e "${YELLOW}Deploying migration chart: $FROM_VERSION -> $TO_VERSION${NC}"

    WORKDIR=$(mktemp -d)
    tar -xzf "$CHART_PATH" -C "$WORKDIR"

    MIGRATION_CHART_PATH="$(resolve_extracted_chart_dependency_path "$WORKDIR" "migration-chart")"

    # Build helm command with optional --plain-http flag
    HELM_CMD="$HELM_EXECUTABLE -n $HELM_NAMESPACE upgrade --install"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_CMD="$HELM_CMD --plain-http"
    fi

    # Keep migration-created Helm ownership aligned with the final admin/platform
    # release names so namespace reconciliation does not block the follow-up install.
    $HELM_CMD kaapana-migration "$MIGRATION_CHART_PATH" \
        --set-string global.credentials_registry_username="$CONTAINER_REGISTRY_USERNAME" \
        --set-string global.credentials_registry_password="$CONTAINER_REGISTRY_PASSWORD" \
        --set-string global.fast_data_dir="$FAST_DATA_DIR" \
        --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
        --set-string global.storage_provider="$STORAGE_PROVIDER" \
        --set-string global.storage_class_slow="$STORAGE_CLASS_SLOW" \
        --set-string global.storage_class_fast="$STORAGE_CLASS_FAST" \
        --set-string global.storage_class_workflow="$STORAGE_CLASS_WORKFLOW" \
        --set-string global.services_namespace="$SERVICES_NAMESPACE" \
        --set-string global.admin_namespace="$ADMIN_NAMESPACE" \
        --set-string global.admin_release_name="$PLATFORM_NAME" \
        --set-string global.platform_release_name="$POST_REINSTALL_PLATFORM_RELEASE_NAME" \
        --set-string global.pull_policy_images="$PULL_POLICY_IMAGES" \
        --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
        --set-string global.kaapana_build_version="$PLATFORM_VERSION" \
        --set-string global.volume_slow_data="$VOLUME_SLOW_DATA"\
        --set-string global.from_version="$FROM_VERSION" \
        --set-string global.to_version="$TO_VERSION" \
        --set-string global.credentials_keycloak_admin_username="$KEYCLOAK_ADMIN_USERNAME" \
        --set-string global.credentials_keycloak_admin_password="$KEYCLOAK_ADMIN_PASSWORD"

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
            POST_DEPLOY_RECONCILE_AFTER_MIGRATION=true
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
    # # ------------------------------------------------------------------
    # # Experimental migration warning for < 0.6.1
    # # ------------------------------------------------------------------

    # # Extract numeric parts, default missing patch to 0
    # IFS='.' read -r P_MAJOR P_MINOR P_PATCH <<<"$PLATFORM_VERSION"
    # P_PATCH=${P_PATCH:-0}

    # if [[ "$P_MAJOR" -eq 0 && "$P_MINOR" -eq 6 && "$P_PATCH" -lt 1 ]]; then
    #     echo
    #     echo "${RED}╔════════════════════════════════════════════════════════════════════╗${NC}"
    #     echo "${RED}║                        ⚠️  EXPERIMENTAL MIGRATION                  ║${NC}"
    #     echo "${RED}║                                                                    ║${NC}"
    #     echo "${RED}║ You are migrating to Kaapana ${PLATFORM_VERSION}.                  ║${NC}"
    #     echo "${RED}║                                                                    ║${NC}"
    #     echo "${RED}║ Migration versions < 0.6.1 are HIGHLY EXPERIMENTAL.                ║${NC}"
    #     echo "${RED}║                                                                    ║${NC}"
    #     echo "${RED}║ - Data loss is possible                                            ║${NC}"
    #     echo "${RED}║ - Rollback may NOT be possible                                     ║${NC}"
    #     echo "${RED}║ - Production use is NOT recommended                                ║${NC}"
    #     echo "${RED}║                                                                    ║${NC}"
    #     echo "${RED}║ Type 'I UNDERSTAND' to continue, anything else to abort.           ║${NC}"
    #     echo "${RED}╚════════════════════════════════════════════════════════════════════╝${NC}"
    #     echo

    #     read -p "Confirmation: " confirm
    #     if [[ "$confirm" != "I UNDERSTAND" ]]; then
    #         echo "${RED}Aborting migration.${NC}"
    #         exit 1
    #     fi
    # fi
    echo -e "${YELLOW}Please BACKUP your data directory first${NC}"
    echo "   cp -a $FAST_DATA_DIR /path/to/fast/backup"
    echo "   cp -a $SLOW_DATA_DIR /path/to/slow/backup"
    echo

    if [[ "${QUIET:-false}" == true ]]; then
        echo -e "${YELLOW}QUIET-MODE active: skipping backup confirmation prompt and proceeding with migration.${NC}"
        return 0
    fi

    while true; do
        read -p "Proceed with migration? (yes/no/skip): " answer
        case "$answer" in
            [Yy][Ee][Ss]|[Yy])
                echo "✅ Proceeding with migration..."
                return 0
                ;;
            [Nn][Oo]|[Nn])
                echo "❌ Aborting migration."
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

function setup_storage_provider() {
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
    REPLICA_COUNT=1
    microk8s.kubectl label nodes "$MAIN_NODE_NAME" "kaapana.io/node"="$STORAGE_NODE" --overwrite
    # --- Set storage classes based on provider ---
    case "${STORAGE_PROVIDER}" in
      "microk8s.io/hostpath")
        STORAGE_CLASS_SLOW="kaapana-hostpath-slow-data-dir"
        STORAGE_CLASS_FAST="kaapana-hostpath-fast-data-dir"
        STORAGE_CLASS_WORKFLOW="kaapana-hostpath-fast-data-dir"
        VOLUME_SLOW_DATA="${VOLUME_SLOW_DATA:-10Gi}"
        ;;
      "driver.longhorn.io")
        STORAGE_CLASS_SLOW="kaapana-longhorn-slow-data"
        STORAGE_CLASS_FAST="kaapana-longhorn-fast-db"
        STORAGE_CLASS_WORKFLOW="kaapana-longhorn-fast-workflow"

        if [[ -z "${VOLUME_SLOW_DATA}" ]]; then
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
}

function migrate() {
    VERSION_FILE="$FAST_DATA_DIR/version"

    echo "${YELLOW}Checking ${VERSION_FILE} status...${NC}"

    if [[ ! -d "$FAST_DATA_DIR" ]] || ! fast_data_dir_has_migration_content "$FAST_DATA_DIR"; then
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

    elif [[ -d "$FAST_DATA_DIR" ]] && fast_data_dir_has_migration_content "$FAST_DATA_DIR"; then
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

# Check whether the fast data dir contains content that should trigger migration handling.
# Ignore the recovery quarantine dir because post-reinstall recovery may create it before
# migrate() runs, which must not turn an otherwise fresh install into a migration case.
function fast_data_dir_has_migration_content() {
    local data_dir="$1"

    if [[ -z "$data_dir" || ! -d "$data_dir" ]]; then
        return 1
    fi

    if find "$data_dir" -mindepth 1 -maxdepth 1 \
        ! -name 'recover-data-quarantine' \
        -print -quit 2>/dev/null | grep -q .; then
        return 0
    fi

    return 1
}

function patch_existing_kaapana_hostpath_pvs_to_retain() {
    validate_hostpath_reclaim_policy

    if [[ "$HOSTPATH_RECLAIM_POLICY" != "Retain" ]]; then
        return 0
    fi

    # StorageClass reclaimPolicy only affects newly provisioned PVs. When an
    # operator opts into Retain, update existing Kaapana hostpath PVs too, but
    # never patch PVs back to Delete.
    local pv_name
    local storage_class
    local reclaim_policy
    local patched=false

    echo "${YELLOW}Ensuring existing Kaapana hostpath PVs use Retain reclaim policy.${NC}"
    while IFS=$'\t' read -r pv_name storage_class reclaim_policy; do
        [[ -z "$pv_name" ]] && continue

        case "$storage_class" in
            kaapana-hostpath-fast-data-dir|kaapana-hostpath-slow-data-dir)
                ;;
            *)
                continue
                ;;
        esac

        if [[ "$reclaim_policy" == "Delete" ]]; then
            echo "${YELLOW}Patching PV ${pv_name} from Delete to Retain.${NC}"
            microk8s.kubectl patch pv "$pv_name" -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}' >/dev/null
            patched=true
        fi
    done < <(microk8s.kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.storageClassName}{"\t"}{.spec.persistentVolumeReclaimPolicy}{"\n"}{end}' 2>/dev/null || true)

    if [[ "$patched" != true ]]; then
        echo "${GREEN}No existing Kaapana hostpath PVs needed reclaim-policy patching.${NC}"
    fi
}

function setup_storage_classes() {
    ensure_helm_uses_microk8s_config
    validate_hostpath_reclaim_policy

    local WORKDIR
    local KAAPANA_STORAGE_CHARTPATH

    WORKDIR=$(mktemp -d)
    tar -xzf "$CHART_PATH" -C "$WORKDIR"
    KAAPANA_STORAGE_CHARTPATH="$(resolve_extracted_chart_dependency_path "$WORKDIR" "kaapana-storage-chart")"

    echo "${YELLOW}Refreshing Kaapana StorageClass definitions while preserving PVCs/PVs/data.${NC}"
    microk8s.kubectl delete storageclass \
        kaapana-hostpath-fast-data-dir \
        kaapana-hostpath-slow-data-dir \
        kaapana-longhorn-fast-db \
        kaapana-longhorn-slow-data \
        kaapana-longhorn-fast-workflow \
        --ignore-not-found

    $HELM_EXECUTABLE -n kaapana-system upgrade --install kaapana-storageclass $KAAPANA_STORAGE_CHARTPATH \
        --create-namespace \
        --set-string global.main_node_name="$MAIN_NODE_NAME" \
        --set-string global.replica_count="$REPLICA_COUNT" \
        --set-string global.fast_data_dir="$FAST_DATA_DIR" \
        --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
        --set-string global.hostpath_reclaim_policy="$HOSTPATH_RECLAIM_POLICY"

    # Apply Retain to already existing hostpath PVs only when Retain is the
    # explicit effective policy for this deploy invocation.
    patch_existing_kaapana_hostpath_pvs_to_retain
}

function get_chart {
    if [[ -n "$CHART_PATH" ]]; then # Note: OFFLINE_MODE requires CHART_PATH
        echo -e "${YELLOW}We assume that that all images are already presented inside the microk8s.${NC}"
        echo -e "${YELLOW}Images are uploaded either with a previous deployment from a docker registry or uploaded from a tar or directly uploaded during building the platform.${NC}"

        if [[ $(basename "$CHART_PATH") != "$PLATFORM_NAME-$PLATFORM_VERSION.tgz" ]]; then
            echo "${RED} Version of chart_path $CHART_PATH differs from PROJECT_NAME: $PLATFORM_NAME and PLATFORM_VERSION: $PLATFORM_VERSION in the deployment script.${NC}"
            exit 1
        fi

        if [[ "$QUIET" != true ]]; then
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
        PRESENT_IMAGE_COUNT=$(microk8s.ctr images ls | grep "$PLATFORM_VERSION" | wc -l || true)
        echo -e "${YELLOW}PRESENT_IMAGE_COUNT: $PRESENT_IMAGE_COUNT ${NC}"
        if [[ "$PRESENT_IMAGE_COUNT" -lt "$VERSION_IMAGE_COUNT" ]]; then
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
}

function ensure_chart_for_deploy {
    if [[ "${OFFLINE_MODE,,}" == true ]]; then
        if [[ -z "$CHART_PATH" || ! -f "$CHART_PATH" ]]; then
            echo "${RED}ERROR: Expected chart archive not found in offline mode: $CHART_PATH${NC}"
            echo "${RED}Provide a valid --chart-path file and retry.${NC}"
            exit 1
        fi
        return 0
    fi

    # Online mode: keep existing chart if it still exists.
    if [[ -n "$CHART_PATH" && -f "$CHART_PATH" ]]; then
        return 0
    fi

    # Post-reinstall recovery can trigger nested storage-class setup which removes
    # the previously pulled local chart archive. Refresh it before migration/install.
    CHART_PATH=""
    get_chart

    if [[ -z "$CHART_PATH" || ! -f "$CHART_PATH" ]]; then
        echo "${RED}ERROR: Chart archive missing after refresh: $CHART_PATH${NC}"
        exit 1
    fi
}

function rm_chart_path {
    if [[ -n "$CONTAINER_REGISTRY_USERNAME" && -n "$CONTAINER_REGISTRY_PASSWORD" ]]; then
        rm "$CHART_PATH"
    fi
}

# Pre-apply chart CRDs and wait until the Kubernetes API reports them as established.
# This avoids a race where Helm has submitted the CRD declaration, but the API server
# has not yet registered the new kind. Without this preflight, the same install can
# fail with "no matches for kind ..." for resources that depend on freshly created CRDs.
# Params: none.
# Returns: 0 when all bundled CRDs are ready or no CRDs are bundled.
# Side effects: applies CRD manifests to the cluster and waits on each CRD name.
# Wait until a CRD is usable, tolerating a CRD whose `Established` condition lags
# under control-plane load and failing fast with actionable guidance when a CRD is
# stuck terminating or the control plane is not progressing — instead of the opaque
# multi-minute `kubectl wait` timeout that aborts the whole deploy via `set -e`.
function wait_for_crd_established() {
    local crd_name="$1"
    local timeout="${2:-180s}"
    local deletion_ts=""

    # A CRD left mid-deletion can never become Established; detect it up front so we
    # surface the fix immediately rather than blocking for the full timeout.
    deletion_ts="$(microk8s.kubectl get crd "$crd_name" -o jsonpath='{.metadata.deletionTimestamp}' 2>/dev/null || true)"
    if [[ -n "$deletion_ts" ]]; then
        echo "${RED}CRD ${crd_name} is stuck terminating (deletionTimestamp=${deletion_ts}).${NC}"
        echo "${RED}It cannot be re-established while a delete is pending. Clear its finalizers, then redeploy:${NC}"
        echo "  microk8s.kubectl patch crd ${crd_name} --type=merge -p '{\"metadata\":{\"finalizers\":[]}}'"
        exit 1
    fi

    echo "${GREEN}Waiting for CRD ${crd_name} to become Established (timeout ${timeout})...${NC}"
    # `|| true` keeps a non-zero wait from tripping `set -e`; we classify the result ourselves.
    if microk8s.kubectl wait --for=condition=Established "crd/${crd_name}" --timeout="${timeout}" >/dev/null 2>&1; then
        return 0
    fi

    # The condition did not flip in time. Tolerate the common case where the CRD is in
    # fact already served (Established can lag/flap under control-plane load) by probing
    # the API directly — if the resource type answers, it is usable and we continue.
    if microk8s.kubectl get "$crd_name" >/dev/null 2>&1; then
        echo "${YELLOW}CRD ${crd_name} did not report Established within ${timeout}, but the API is already serving it -> continuing.${NC}"
        return 0
    fi

    # Genuinely not served: dump the conditions and give the control-plane remediation.
    echo "${RED}CRD ${crd_name} is neither Established nor served after ${timeout}.${NC}"
    echo "${RED}Current conditions:${NC}"
    microk8s.kubectl get crd "$crd_name" -o jsonpath='{range .status.conditions[*]}  {.type}={.status} ({.reason}) {.message}{"\n"}{end}' 2>/dev/null || true
    echo "${RED}This usually means the microk8s control plane (apiextensions / k8s-dqlite) is not progressing.${NC}"
    echo "${RED}Restart microk8s, then redeploy:${NC}"
    echo "  sudo microk8s stop && sudo microk8s start && microk8s status --wait-ready"
    exit 1
}

function apply_chart_crds() {
    local crd_manifest=""
    local -a crd_names=()
    local crd_name=""

    if ! crd_manifest="$($HELM_EXECUTABLE show crds "$CHART_PATH" 2>/dev/null)"; then
        echo "${RED}Failed to read CRDs from chart archive: $CHART_PATH${NC}"
        exit 1
    fi

    if [[ -z "$crd_manifest" ]]; then
        echo "${YELLOW}No bundled CRDs found in chart archive.${NC}"
        return 0
    fi

    echo "${GREEN}Pre-applying bundled chart CRDs before platform install to avoid API registration races...${NC}"
    printf '%s\n' "$crd_manifest" | microk8s.kubectl apply -f -
    echo "${YELLOW}If CRDs were already created by a previous attempt, kubectl apply will reconcile them and Helm may later skip existing CRDs.${NC}"

    # Wait for each declared CRD so Helm does not race the API registration.
    mapfile -t crd_names < <(
        printf '%s\n' "$crd_manifest" | awk '
            $1 == "kind:" { kind = $2; next }
            kind == "CustomResourceDefinition" && $1 == "name:" { print $2; kind = "" }
        '
    )

    for crd_name in "${crd_names[@]}"; do
        [[ -n "$crd_name" ]] || continue
        wait_for_crd_established "$crd_name" "${CRD_ESTABLISH_TIMEOUT:-180s}"
    done
}

# Deploy the platform chart after validating runtime prerequisites and cluster settings.
# Params: none.
# Returns: exits with non-zero status when deployment prerequisites or Helm install fail.
# Side effects: may enable GPU support, install storage classes, apply CRDs, and create cluster resources.
function deploy_chart {
    if [[ -z "$CONTAINER_REGISTRY_URL" ]]; then
        echo "${RED}CONTAINER_REGISTRY_URL needs to be set! -> please adjust the kaapanactl.sh script!${NC}"
        echo "${RED}ABORT${NC}"
        exit 1
    fi

    if [[ "${OFFLINE_MODE,,}" == true && -z "$CHART_PATH" ]]; then
        echo "${RED}ERROR: CHART_PATH needs to be set when in OFFLINE_MODE!${NC}"
        exit 1
    fi

    get_domain

    if [[ -z "$INSTANCE_NAME" ]]; then
        INSTANCE_NAME=$DOMAIN
        echo "${YELLOW}No INSTANCE_NAME is set, setting it to $DOMAIN!${NC}"
    fi

    if [[ "${GPU_SUPPORT,,}" == true ]]; then
        echo -e "${GREEN} -> GPU found ...${NC}"
    else
        if [[ "$QUIET" != true ]]; then
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
                install_gpu_operator "$SCRIPT_DIR"
                if [ $? -eq 0 ]; then
                    echo "Offline GPU enabled!"
                else
                    echo "Offline GPU deployment failed!"
                    exit 1
                fi
            else

                microk8s enable nvidia --gpu-operator-driver host --gpu-operator-version $GPU_OPERATOR_VERSION \
                    --gpu-operator-set cdi.enabled=false \
                    --gpu-operator-set toolkit.env[3].name=RUNTIME_CONFIG_SOURCE --gpu-operator-set \
                    toolkit.env[3].value='file=/var/snap/microk8s/current/args/containerd.toml'
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

    get_chart

    # Kubernetes API endpoint
    INTERNAL_CIDR=$(microk8s.kubectl get endpoints kubernetes -n default -o jsonpath="{.subsets[0].addresses[0].ip}/32")
    # Server IP
    if is_ipv4 "$DOMAIN"; then
        # external ip can differ from local ip, must be reachable due to keycloak (only in ip deployments)
        INTERNAL_CIDR="$DOMAIN/32,$INTERNAL_CIDR"
    fi
    SERVER_IP=$(hostname -I | awk -F ' ' '{print $1}')
    INTERNAL_CIDR="$SERVER_IP/32,$INTERNAL_CIDR"
    # MicroK8s https://microk8s.io/docs/change-cidr
    INTERNAL_CIDR="10.152.183.0/24,10.1.0.0/16,$INTERNAL_CIDR"

    echo " Installing kaapana strorage class ..."
    setup_storage_classes

    maybe_run_post_reinstall_recovery

    ensure_chart_for_deploy

    echo "${GREEN}Checking for version difference and migration options...${NC}"
    migrate

    prefetch_bootstrap_images || true

    echo "${GREEN}Deploying $PLATFORM_NAME:$PLATFORM_VERSION${NC}"
    echo "${GREEN}CHART_PATH $CHART_PATH${NC}"
    apply_chart_crds

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
    ${KEYCLOAK_LDAP_EGRESS_CIDRS:+--set global.keycloak_ldap_egress_cidrs="{$KEYCLOAK_LDAP_EGRESS_CIDRS}"} \
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
    --set-string global.storage_node="$STORAGE_NODE" \
    --set post-deploy-reconcile-chart.enabled=$POST_DEPLOY_RECONCILE_ENABLED \
    --name-template "$PLATFORM_NAME"

    # In case of timeout-issues in kube helm increase the default timeouts by setting
    # --set kube-helm-chart.timeouts.helmInstallTimeout=45 \
    # --set kube-helm-chart.timeouts.helmDeletionTimeout=60 \

    # pull_policy_jobs and pull_policy_pods only there for backward compatibility as of version 0.2.0
    rm_chart_path

    print_deployment_done
    update_coredns_rewrite
    autoheal_bootstrap_imagepullbackoff || true
    run_post_deploy_reconcile
    CONTAINER_REGISTRY_USERNAME=""
    CONTAINER_REGISTRY_PASSWORD=""
}

function pull_chart {
    local chart_name=$1
    local chart_version=$2
    local dest_dir=$3
    local HELM_PULL_CMD="$HELM_EXECUTABLE pull"

    if [ "$PLAIN_HTTP" = true ]; then
        HELM_PULL_CMD="$HELM_PULL_CMD --plain-http"
    fi

    MAX_RETRIES=30
    i=1
    while [ $i -le $MAX_RETRIES ];
    do
        echo -e "${YELLOW}Pulling chart: ${CONTAINER_REGISTRY_URL}/${chart_name} with version ${chart_version} ${NC}"
        $HELM_PULL_CMD oci://${CONTAINER_REGISTRY_URL}/${chart_name} \
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
    then echo -e "${RED}The installation of certs requires root privileges!";
        exit 1
    fi

    if [ ! -f ./tls.key ] || [ ! -f ./tls.crt ]; then
        echo -e "${RED}tls.key or tls.crt not found in this directory.${NC}"
        echo -e "${RED}Rename and copy the files first.${NC}"
        exit 1
    fi

    # update cert and restart pods in a namespace
    update_namespace() {
        local ns=$1
        echo -e "\nUpdating certificate in namespace: ${ns}"

        microk8s.kubectl delete secret certificate -n "$ns" 2>/dev/null || true
        microk8s.kubectl create secret tls certificate --namespace "$ns" --key ./tls.key --cert ./tls.crt

        # get app.kubernetes.io/name of all pods that mount the certificate secret in the namespace
        local app_labels=$(microk8s.kubectl get pods -n "$ns" -o json | \
            jq -r '.items[] | select(.spec.volumes[]?.secret?.secretName == "certificate") | .metadata.labels."app.kubernetes.io/name" // empty' | sort -u)

        if [ -n "$app_labels" ]; then
            echo -e "Restarting pods using certificate:"
            echo -e "$app_labels" | while read label; do
                if [ -n "$label" ]; then
                    echo -e "  - app.kubernetes.io/name=$label"
                    if ! microk8s.kubectl -n "$ns" delete pod -l "app.kubernetes.io/name=$label" --grace-period=120 2>/dev/null; then
                        echo -e "${YELLOW} Warning: Failed to restart pods with label $label${NC}"
                    fi
                fi
            done
        else
            echo -e "No pods found mounting certificate secret"
        fi
    }

    update_namespace "$ADMIN_NAMESPACE"
    update_namespace "$SERVICES_NAMESPACE"

    # copy certificates
    if [ -n "$FAST_DATA_DIR" ]; then
        mkdir -p "$FAST_DATA_DIR/tls"
        cp ./tls.key ./tls.crt "$FAST_DATA_DIR/tls/"
        chmod 600 "$FAST_DATA_DIR/tls/tls.key"
    fi

    # Manual certificate installation deliberately does not infer an expected
    # hostname or CA trust model here, so point operators to the explicit
    # analysis helper when they need to validate the installed certificate.
    echo -e "\n${YELLOW}WARNING: The installed certificate was not checked here for hostname match or validity.${NC}"
    echo -e "${YELLOW}If you run into certificate issues, verify it manually with:${NC}"
    echo -e "${YELLOW}  bash $(dirname "${BASH_SOURCE[0]}")/utils/reset_certificate_state.sh --analyze-only --hostname <expected-hostname>${NC}"
    echo -e "\n${GREEN}DONE${NC}"
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

# Compare the user kubeconfig against the canonical microk8s view so harmless
# formatting differences do not fail the preflight.
#
# Helm falls back to http://localhost:8080 when the invoking user's kubeconfig is
# missing or stale. Pin Helm to the live MicroK8s config before cluster-facing
# Helm calls so undeploy/redeploy also work when they bypass the preflight.
function ensure_helm_uses_microk8s_config {
    local helm_kubeconfig_path="${TMPDIR:-/tmp}/kaapanactl-helm-${USER}.kubeconfig"

    if ! microk8s.kubectl config view --raw > "$helm_kubeconfig_path" 2>/dev/null; then
        echo -e "${RED}Failed to export the current MicroK8s kubeconfig for Helm.${NC}"
        echo -e "${RED}Check that microk8s is running and that your user can access microk8s.kubectl.${NC}"
        exit 1
    fi

    chmod 600 "$helm_kubeconfig_path" 2>/dev/null || true
    export KUBECONFIG="$helm_kubeconfig_path"
}

function kubeconfig_matches_microk8s {
    local kubeconfig_path="${HOME}/.kube/config"
    local normalized_user_kubeconfig
    local normalized_microk8s_kubeconfig

    if [[ ! -f "$kubeconfig_path" ]]; then
        return 1
    fi

    # Canonicalize both kubeconfigs through kubectl so formatting-only
    # differences like `preferences: {}` do not fail the preflight.
    if ! normalized_user_kubeconfig="$(microk8s.kubectl config view --raw --kubeconfig="$kubeconfig_path" 2>/dev/null)"; then
        return 1
    fi

    if ! normalized_microk8s_kubeconfig="$(microk8s.kubectl config view --raw 2>/dev/null)"; then
        return 1
    fi

    [[ "$normalized_user_kubeconfig" == "$normalized_microk8s_kubeconfig" ]]
}

# Explain why the normalized kubeconfig comparison failed so operators can see
# the likely culprit without running a manual diff first.
function describe_kubeconfig_mismatch {
    local kubeconfig_path="${HOME}/.kube/config"
    local normalized_user_kubeconfig
    local normalized_microk8s_kubeconfig
    local diff_excerpt

    if [[ ! -f "$kubeconfig_path" ]]; then
        echo "Expected kubeconfig file not found at $kubeconfig_path."
        return
    fi

    if ! normalized_user_kubeconfig="$(microk8s.kubectl config view --raw --kubeconfig="$kubeconfig_path" 2>&1)"; then
        echo "Failed to parse $kubeconfig_path with microk8s.kubectl: $normalized_user_kubeconfig"
        return
    fi

    if ! normalized_microk8s_kubeconfig="$(microk8s.kubectl config view --raw 2>&1)"; then
        echo "Failed to read the current microk8s kubeconfig: $normalized_microk8s_kubeconfig"
        return
    fi

    # Show only the first changed lines to keep the preflight output readable.
    diff_excerpt="$(
        diff -u \
            <(printf '%s\n' "$normalized_user_kubeconfig") \
            <(printf '%s\n' "$normalized_microk8s_kubeconfig") |
            sed -n '/^[+-][^+-]/p' |
            head -n 4
    )"

    if [[ -n "$diff_excerpt" ]]; then
        echo -e "Normalized diff excerpt:\n$diff_excerpt"
    else
        echo "The normalized kubeconfig still differs, but no concise diff excerpt could be generated."
    fi
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
    if kubeconfig_matches_microk8s; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Your kubeconfig differs from the microk8s version.\n$(describe_kubeconfig_mismatch)")
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

        if [[ "${TEST_FAILDS[$i]}" == true ]]; then
            if [[ "${SEVERITY[$i]}" -ge 200 ]]; then
                STATUS="${RED}failed${NC}"
            else
                STATUS="${YELLOW}failed${NC}"
            fi
        else
            STATUS="${GREEN}ok${NC}"
        fi

        printf "%-4d %-60s %-15s\n" "${SEVERITY[$i]}" "${TEST_NAMES[$i]}" "$STATUS"

        if [[ -n "${RESULT_MSGS[$i]}" ]]; then
            if [[ "${TEST_FAILDS[$i]}" == true ]]; then
                if [[ "${SEVERITY[$i]}" -ge 200 ]]; then
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

function list_imagepullbackoff_pods {
    local namespace="$1"
    microk8s.kubectl get pods -n "$namespace" --no-headers 2>/dev/null \
        | awk '$3 == "ImagePullBackOff" || $3 == "Init:ImagePullBackOff" { print $1 }' || true
}

function list_bootstrap_imagepullbackoff_pods {
    local namespace="$1"
    list_imagepullbackoff_pods "$namespace" | grep -E "$IMAGE_PULL_AUTOHEAL_POD_REGEX" || true
}

function reset_bootstrap_imagepullbackoff_once {
    local namespaces="$1"
    local deleted=0

    for namespace in $namespaces; do
        local pods
        pods=$(list_bootstrap_imagepullbackoff_pods "$namespace")
        if [ -z "$pods" ]; then
            continue
        fi

        # Keep helper output numeric on stdout so callers can use command substitution safely.
        echo -e "${YELLOW}Resetting ImagePullBackOff in namespace $namespace:${NC}" >&2
        while IFS= read -r pod; do
            if [ -z "$pod" ]; then
                continue
            fi
            echo "  - deleting pod/$pod" >&2
            microk8s.kubectl -n "$namespace" delete pod "$pod" --ignore-not-found=true --grace-period=0 --force >/dev/null 2>&1 || true
            deleted=$((deleted + 1))
        done <<< "$pods"
    done

    echo "$deleted"
}

function check_bootstrap_pull_progress {
    local kube_helm_running=false
    local init_extensions_backoff=0
    local init_collections_backoff=0

    if microk8s.kubectl -n "$ADMIN_NAMESPACE" get pods -l app.kubernetes.io/name=kube-helm --no-headers 2>/dev/null | awk '$3 == "Running" { found=1 } END { exit(found ? 0 : 1) }'; then
        kube_helm_running=true
    fi

    init_extensions_backoff=$(microk8s.kubectl -n "$ADMIN_NAMESPACE" get pods -l job-name=init-extensions --no-headers 2>/dev/null | awk '$3 == "ImagePullBackOff" || $3 == "Init:ImagePullBackOff" { c++ } END { print c+0 }')
    init_collections_backoff=$(microk8s.kubectl -n "$ADMIN_NAMESPACE" get pods -l job-name=init-collections --no-headers 2>/dev/null | awk '$3 == "ImagePullBackOff" || $3 == "Init:ImagePullBackOff" { c++ } END { print c+0 }')

    echo "kube_helm_running=${kube_helm_running}, init_extensions_backoff=${init_extensions_backoff}, init_collections_backoff=${init_collections_backoff}"
}

function prefetch_bootstrap_images {
    if [[ "${BOOTSTRAP_IMAGE_PREFETCH_ENABLED,,}" != "true" ]]; then
        echo -e "${YELLOW}Bootstrap image prefetch disabled (BOOTSTRAP_IMAGE_PREFETCH_ENABLED=${BOOTSTRAP_IMAGE_PREFETCH_ENABLED}).${NC}"
        return 0
    fi

    if [ -z "${CONTAINER_REGISTRY_USERNAME:-}" ] || [ -z "${CONTAINER_REGISTRY_PASSWORD:-}" ]; then
        echo -e "${YELLOW}Bootstrap image prefetch skipped: missing registry credentials.${NC}"
        return 0
    fi

    local image_version="$PLATFORM_VERSION"
    local images="$BOOTSTRAP_IMAGE_PREFETCH_IMAGES"

    if [ -z "$image_version" ] || [ -z "$images" ]; then
        return 0
    fi

    echo -e "${YELLOW}Prefetching bootstrap images into microk8s containerd (version=${image_version}).${NC}"
    for image_name in $images; do
        local image_ref="${CONTAINER_REGISTRY_URL}/${image_name}:${image_version}"
        local pull_ok=false

        if microk8s ctr images ls 2>/dev/null | awk '{print $1}' | grep -Fxq "$image_ref"; then
            echo -e "${GREEN}Bootstrap image already cached:${NC} $image_ref"
            continue
        fi

        for attempt in 1 2; do
            echo -e "${YELLOW}Prefetch attempt ${attempt}: ${image_ref}${NC}"
            if microk8s ctr images pull --user "${CONTAINER_REGISTRY_USERNAME}:${CONTAINER_REGISTRY_PASSWORD}" "$image_ref"; then
                pull_ok=true
                break
            fi
            sleep 2
        done

        if [[ "$pull_ok" != true ]]; then
            echo -e "${YELLOW}Bootstrap image prefetch failed for ${image_ref}. Deployment will continue.${NC}"
        fi
    done
}

function autoheal_bootstrap_imagepullbackoff {
    if [[ "${IMAGE_PULL_AUTOHEAL_ENABLED,,}" != "true" ]]; then
        echo -e "${YELLOW}Image pull auto-heal disabled (IMAGE_PULL_AUTOHEAL_ENABLED=${IMAGE_PULL_AUTOHEAL_ENABLED}).${NC}"
        return 0
    fi

    local timeout="$IMAGE_PULL_AUTOHEAL_TIMEOUT_SECONDS"
    local interval="$IMAGE_PULL_AUTOHEAL_INTERVAL_SECONDS"
    local namespaces="$IMAGE_PULL_AUTOHEAL_NAMESPACES"
    local start_ts
    local now_ts
    local cycle=0
    local total_deleted=0
    local remaining

    start_ts=$(date +%s)
    echo -e "${YELLOW}Starting bootstrap image pull auto-heal (timeout=${timeout}s, interval=${interval}s).${NC}"
    echo -e "${YELLOW}Namespaces: ${namespaces}${NC}"
    echo -e "${YELLOW}Pod regex: ${IMAGE_PULL_AUTOHEAL_POD_REGEX}${NC}"

    while true; do
        cycle=$((cycle + 1))
        remaining=""

        for namespace in $namespaces; do
            local pods
            pods=$(list_bootstrap_imagepullbackoff_pods "$namespace")
            if [ -n "$pods" ]; then
                while IFS= read -r pod; do
                    [ -z "$pod" ] && continue
                    remaining="${remaining} ${namespace}/${pod}"
                done <<< "$pods"
            fi
        done

        if [ -z "$remaining" ]; then
            echo -e "${GREEN}Bootstrap image pull auto-heal finished: no matching ImagePullBackOff pods left.${NC}"
            echo -e "${GREEN}Progress: $(check_bootstrap_pull_progress)${NC}"
            return 0
        fi

        echo -e "${YELLOW}[auto-heal cycle ${cycle}] remaining:${NC}${remaining}"
        local deleted_this_cycle
        deleted_this_cycle=$(reset_bootstrap_imagepullbackoff_once "$namespaces")
        total_deleted=$((total_deleted + deleted_this_cycle))
        echo -e "${YELLOW}[auto-heal cycle ${cycle}] deleted pods: ${deleted_this_cycle}, total deleted: ${total_deleted}${NC}"
        echo -e "${YELLOW}[auto-heal cycle ${cycle}] progress: $(check_bootstrap_pull_progress)${NC}"

        now_ts=$(date +%s)
        if [ $((now_ts - start_ts)) -ge "$timeout" ]; then
            echo -e "${RED}Bootstrap image pull auto-heal timed out after ${timeout}s.${NC}"
            echo -e "${RED}Remaining:${NC}${remaining}"
            return 1
        fi

        sleep "$interval"
    done
}

# Run the post-deploy project namespace reconciliation step when enabled.
# Params: none.
# Returns: 0 when reconciliation is disabled or succeeds; 1 on reconciliation failures.
# Side effects: waits for core deployments, runs the reconciliation helper, and prints retry guidance.
function run_post_deploy_reconcile {
    if [[ "${POST_DEPLOY_RECONCILE_ENABLED,,}" != "true" ]]; then
        echo -e "${YELLOW}Post-deploy project reconciliation disabled via --no-reconcile-project-namespaces.${NC}"
        return 0
    fi

    local timeout_seconds="${POST_DEPLOY_RECONCILE_WAIT_SECONDS}"
    local start_ts
    local deadline_ts
    local script_dir
    local reconcile_script

    print_reconcile_retry_hint() {
        echo -e "${YELLOW}Reconciliation may have failed because the platform is still coming up.${NC}"
        echo -e "${YELLOW}Wait until pods are in Running/Completed state, then run:${NC}"
        echo -e "${YELLOW}  bash ./kaapana/utils/reconcile_project_namespaces.sh${NC}"
    }

    wait_for_deployment_ready() {
        local ns="$1"
        local dep="$2"
        local deadline="$3"
        local now
        local remaining
        local attempt=0

        while true; do
            now=$(date +%s)
            remaining=$((deadline - now))

            if (( remaining <= 0 )); then
                echo -e "${RED}Timed out waiting for deployment/${dep} in namespace ${ns}.${NC}"
                print_reconcile_retry_hint
                return 1
            fi

            if microk8s.kubectl -n "${ns}" get deployment "${dep}" >/dev/null 2>&1; then
                echo ""
                echo -e "${YELLOW}Waiting for deployment/${dep} in namespace ${ns} (remaining=${remaining}s)...${NC}"
                if microk8s.kubectl -n "${ns}" rollout status "deployment/${dep}" --timeout="${remaining}s"; then
                    return 0
                fi
                echo -e "${RED}Required deployment not ready for reconciliation: ${ns}/${dep}${NC}"
                print_reconcile_retry_hint
                return 1
            fi

            attempt=$((attempt + 1))
            printf "\r${YELLOW}Waiting for deployment/%s in namespace %s to appear (attempt %d, %ss remaining)...${NC}" "${dep}" "${ns}" "${attempt}" "${remaining}"
            if (( attempt % 12 == 0 )); then
                echo ""
                echo -e "${YELLOW}Still waiting for deployment/${dep} in namespace ${ns}...${NC}"
            fi
            sleep 5
        done
    }

    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    reconcile_script="${script_dir}/utils/reconcile_project_namespaces.sh"
    if [[ ! -r "${reconcile_script}" ]]; then
        reconcile_script="${script_dir}/../utils/reconcile_project_namespaces.sh"
    fi

    if [[ ! -r "${reconcile_script}" ]]; then
        echo -e "${RED}Post-deploy reconcile script missing or not readable: ${reconcile_script}${NC}"
        return 1
    fi

    echo -e "${YELLOW}Running post-deploy project reconciliation (timeout=${timeout_seconds}s)...${NC}"
    start_ts=$(date +%s)
    deadline_ts=$((start_ts + timeout_seconds))

    for dep_ref in \
        "${SERVICES_NAMESPACE}/airflow-webserver" \
        "${SERVICES_NAMESPACE}/access-information-interface" \
        "${ADMIN_NAMESPACE}/kube-helm-deployment"; do
        local ns="${dep_ref%%/*}"
        local dep="${dep_ref##*/}"

        if ! wait_for_deployment_ready "${ns}" "${dep}" "${deadline_ts}"; then
            return 1
        fi
    done

    # Invoke the helper through bash so a missing executable bit does not block recovery.
    if ! SERVICES_NAMESPACE="${SERVICES_NAMESPACE}" ADMIN_NAMESPACE="${ADMIN_NAMESPACE}" WAIT_TIMEOUT_SECONDS="${timeout_seconds}" bash "${reconcile_script}"; then
        echo -e "${RED}Post-deploy project reconciliation failed.${NC}"
        print_reconcile_retry_hint
        return 1
    fi

    echo -e "${GREEN}Post-deploy project reconciliation finished successfully.${NC}"
    return 0
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
echo "Version: 0.5.3-latest"
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
main $@
