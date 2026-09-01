# docker-bake.hcl
#
# Every container image built by the kaapana-build system (build_cli),
# generated from the LABEL REGISTRY / LABEL IMAGE metadata that
# build_cli/build_cli/container/container.py:Container.from_dockerfile()
# reads out of each Dockerfile, using the same discovery rules as
# build_cli/build_cli/container/container_helper.py:collect_containers()
# (rglob for Dockerfile* under the repo root, filtered by the default
# --build-ignore-patterns "*templates_and_examples/*,*ci/*,*lib/task_api/*"
# and by any Dockerfile carrying LABEL BUILD_IGNORE=true).
#
# Usage:
#   docker buildx bake                                     # build everything
#   docker buildx bake base-python-cpu                     # build one target (+ its deps)
#   REGISTRY=my.registry/kaapana TAG=1.2.3 docker buildx bake --print
#
# Local-only base images (LABEL REGISTRY="local-only" in the Dockerfile)
# are never pushed; they are wired into the images that FROM them via
# `contexts = { "local-only/<name>:<tag>" = "target:<name>" }`, mirroring
# the OCI-layout bridge build_cli itself uses for cache-enabled builds
# (see Container._build_with_cache_bridge in container.py).

variable "REGISTRY" {
  default = "local-only"
}

variable "CACHE_REGISTRY" {
  default = "${REGISTRY}"
}

variable "TAG" {
  default = "latest"
}

variable "CACHE_TO" {
  default = "False"
}

variable "CACHE_FROM" {
  default = "False"
}

variable "BUILD_ONLY" {
  default = "False"
}

# Registry-cache export for the target named `name`, e.g.
# { type = "registry", ref = "myregistry/foo:cache" }. Only active when
# CACHE_TO is "True"/"true", so plain builds don't pay for a cache push
# nobody wants.
function "cache_to" {
  params = [name]
  result = contains(["True", "true"], CACHE_TO) ? [
    { type = "registry", ref = "${CACHE_REGISTRY}/${name}:cache", mode = "max" }
  ] : []
}

# Registry-cache import for the target named `name`. Only active when
# CACHE_FROM is "True"/"true".
function "cache_from" {
  params = [name]
  result = contains(["True", "true"], CACHE_FROM) ? [
    { type = "registry", ref = "${CACHE_REGISTRY}/${name}:cache"}
  ] : []
}

# Shared push policy, applied via `inherits` to every target that is not a
# local-only base image: push everything unless BUILD_ONLY is "True"/"true".
# Local-only base images never inherit this target, so they are never pushed.
target "_pushable" {
  output = ["type=image,push=${contains(["True", "true"], BUILD_ONLY) ? "false" : "true"}"]
  # Buildx auto-attaches provenance/SBOM attestations to any type=image push,
  # which wraps the image in a manifest list plus an extra attestation blob.
  # Registries like GitLab's Container Registry can race their blob GC against
  # that extra manifest, which surfaces as "blob unknown to registry" on push.
  # We don't need attestations here, so turn them off.
  attest = ["type=provenance,disabled=true", "type=sbom,disabled=true"]
}

group "default" {
  targets = [
    "access-information-interface",
    "advanced-collect-metadata-federated",
    "airflow",
    "airflow-dag-sync",
    "alert-manager",
    "alertmanager-forwarder",
    "auth-backend",
    "base-desktop",
    "base-installer",
    "base-landing-page",
    "base-minio-mc",
    "base-mitk",
    "base-model-installer",
    "base-nnunet-v2",
    "base-python-cpu",
    "base-python-cpu-3-10",
    "base-python-gpu",
    "base-python-gpu-3-10",
    "bin2dcm",
    "boa-output-check",
    "body-and-organ-analysis",
    "bodypartregression",
    "buildah",
    "busybox",
    "cca",
    "cert-init",
    "classification-inference",
    "classification-preprocessing",
    "classification-training",
    "cleanup-expired-workflows",
    "clear-validation-results",
    "code-server",
    "collabora",
    "create-dashboard-user",
    "create-project-user",
    "ctp",
    "dag-advanced-collect-metadata",
    "dag-advanced-collect-metadata-federated",
    "dag-body-and-organ-analysis",
    "dag-bodypartregression",
    "dag-classification-training-workflow",
    "dag-extract-scanparameters",
    "dag-federated-setup-central-test",
    "dag-federated-setup-node-test",
    "dag-mitk-flow",
    "dag-nnunet",
    "dag-nnunet-federated",
    "dag-radiomics",
    "dag-radiomics-federated",
    "dag-total-segmentator-v2",
    "dag-wsiconv",
    "data-api",
    "data-ui",
    "dcm4che-postgres",
    "dcm4chee-arc",
    "dcm4chee-ldap",
    "dcmodify",
    "dcmqi",
    "dcmqr",
    "dcmsend",
    "delete-from-meta",
    "delete-from-pacs",
    "desktop-container",
    "dev-code-server",
    "dice-evaluation",
    "dicom-init",
    "dicom-validator",
    "dicom-web-filter",
    "dummy",
    "dummy-task",
    "edk",
    "extension-api",
    "extension-manager-ui",
    "federated-setup-central-test",
    "get-body-and-organ-analysis-models",
    "get-input",
    "get-input-task",
    "get-ref-series",
    "get-totalsegmentator-v2-models",
    "grafana",
    "init-meta",
    "init-projects",
    "itk2dcm",
    "json2meta",
    "jupyterlab",
    "jupyterlab-reporting",
    "kaapana-backend",
    "kaapana-documentation",
    # "kaapana-extension-collection",
    "kaapana-plugin",
    "kaapana-wopi",
    "keycloak",
    "keycloak-setup",
    "kube-dashboard",
    "kube-helm",
    "kube-state-metrics",
    "landing-page-kaapana",
    "local-registry",
    "local-registry-ui",
    "loki",
    "maintenance-page-kaapana",
    "mask2nifti",
    "merge-masks",
    "metrics-scraper",
    "migration",
    "minio",
    "minio-init",
    "minio-mirror",
    "minio-operator",
    "mitk-fileconverter",
    "mitk-flow",
    "mitk-radiomics",
    "mitk-resample",
    "mitk-tools",
    "mitk-workbench",
    "nginx",
    "nnunet-analysis-scripts",
    "nnunet-federated",
    "nnunet-gpu",
    "nnunet-model-download-from-pacs",
    "nnunet-model-management",
    "node-exporter",
    "node-exporter-textfile-collector",
    "notification-service",
    "notify",
    "nrrd-to-dicom",
    "oauth2-proxy",
    "ohif",
    "open-policy-agent",
    "openedc",
    "opensearch",
    "opensearch-certs",
    "os-dashboards",
    "pdf2dcm",
    "postgres-18-4-alpine",
    "postgres-base",
    "project-management-ui",
    "project-runtime",
    "prometheus",
    "promtail",
    "pyradiomics",
    "rabbitmq",
    "radiomics-federated",
    "radiomics-federated-analysis",
    "redis",
    "scanparam2json",
    "seg-check",
    "seg-eval",
    "send-dicoms",
    "service-checker",
    "slicer-workbench",
    "slim",
    "squid",
    "statistics2pdf",
    "statsd-exporter",
    "tensorboard",
    "thumbnail-generator",
    "total-segmentator-v2",
    "traefik",
    "train-test-split",
    "update-seginfo",
    "workflow-api",
    "workflow-cleaner",
    "workflow-installer",
    "workflow-ui",
    "wsiconv",
    "zip-unzip",
  ]
}

group "base-images" {
  targets = [
    "base-desktop",
    "base-installer",
    "base-landing-page",
    "base-minio-mc",
    "base-mitk",
    "base-model-installer",
    "base-nnunet-v2",
    "base-python-cpu",
    "base-python-cpu-3-10",
    "base-python-gpu",
    "base-python-gpu-3-10",
    "postgres-base",
  ]
}

target "access-information-interface" {
  context    = "services/data-separation/access-information-interface/docker/backend"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/access-information-interface:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("access-information-interface")
  cache-from = cache_from("access-information-interface")
}

target "advanced-collect-metadata-federated" {
  context    = "data-processing/processing-pipelines/advanced_collect_metadata_federated/processing-containers"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/advanced-collect-metadata-federated:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("advanced-collect-metadata-federated")
  cache-from = cache_from("advanced-collect-metadata-federated")
}

target "airflow" {
  context    = "services/flow/airflow/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    "lib" = "lib"
  }
  tags = ["${REGISTRY}/airflow:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("airflow")
  cache-from = cache_from("airflow")
}

target "airflow-dag-sync" {
  context    = "services/flow/airflow/dag-sync-docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/airflow-dag-sync:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("airflow-dag-sync")
  cache-from = cache_from("airflow-dag-sync")
}

target "alert-manager" {
  context    = "services/monitoring/alert-manager/docker/alert-manager"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/alert-manager:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("alert-manager")
  cache-from = cache_from("alert-manager")
}

target "alertmanager-forwarder" {
  context    = "services/monitoring/alert-manager/docker/forwarder"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/alertmanager-forwarder:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("alertmanager-forwarder")
  cache-from = cache_from("alertmanager-forwarder")
}

target "auth-backend" {
  context    = "services/kaapana-admin/auth-backend/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/auth-backend:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("auth-backend")
  cache-from = cache_from("auth-backend")
}

target "base-desktop" {
  context    = "services/utils/base-desktop"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
  }
  tags = ["local-only/base-desktop"]
  cache-to   = cache_to("base-desktop")
  cache-from = cache_from("base-desktop")
}

target "base-installer" {
  context    = "services/utils/base-installer"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["local-only/base-installer"]
  cache-to   = cache_to("base-installer")
  cache-from = cache_from("base-installer")
}

target "base-landing-page" {
  context    = "services/utils/base-landing-page"
  dockerfile = "Dockerfile"
  tags = ["local-only/base-landing-page"]
  cache-to   = cache_to("base-landing-page")
  cache-from = cache_from("base-landing-page")
}

target "base-minio-mc" {
  context    = "services/utils/minio-mirror/base-image"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["local-only/base-minio-mc"]
  cache-to   = cache_to("base-minio-mc")
  cache-from = cache_from("base-minio-mc")
}

target "base-mitk" {
  context    = "data-processing/base-images/base-mitk"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["local-only/base-mitk"]
  cache-to   = cache_to("base-mitk")
  cache-from = cache_from("base-mitk")
}

target "base-model-installer" {
  context    = "services/utils/base-model-installer/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["local-only/base-model-installer"]
  cache-to   = cache_to("base-model-installer")
  cache-from = cache_from("base-model-installer")
}

target "base-nnunet-v2" {
  context    = "data-processing/base-images/base-nnunet-v2"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
    constraints = "constraints"
  }
  tags = ["local-only/base-nnunet-v2"]
  cache-to   = cache_to("base-nnunet-v2")
  cache-from = cache_from("base-nnunet-v2")
}

target "base-python-cpu" {
  context    = "data-processing/base-images/base-python-cpu"
  dockerfile = "Dockerfile"
  contexts = {
    constraints = "constraints"
  }
  tags = ["local-only/base-python-cpu"]
  cache-to   = cache_to("base-python-cpu")
  cache-from = cache_from("base-python-cpu")
}

target "base-python-cpu-3-10" {
  context    = "data-processing/base-images/base-python-cpu-3.10"
  dockerfile = "Dockerfile"
  contexts = {
    constraints = "constraints"
  }
  tags = ["local-only/base-python-cpu-3.10"]
  cache-to   = cache_to("base-python-cpu-3-10")
  cache-from = cache_from("base-python-cpu-3-10")
}

target "base-python-gpu" {
  context    = "data-processing/base-images/base-python-gpu"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["local-only/base-python-gpu"]
  cache-to   = cache_to("base-python-gpu")
  cache-from = cache_from("base-python-gpu")
}

target "base-python-gpu-3-10" {
  context    = "data-processing/base-images/base-python-gpu-3.10"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu-3.10" = "target:base-python-cpu-3-10"
  }
  tags = ["local-only/base-python-gpu-3.10"]
  cache-to   = cache_to("base-python-gpu-3-10")
  cache-from = cache_from("base-python-gpu-3-10")
}

target "bin2dcm" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcmtk-bin2dcm"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/bin2dcm:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("bin2dcm")
  cache-from = cache_from("bin2dcm")
}

target "boa-output-check" {
  context    = "data-processing/processing-pipelines/body-and-organ-analysis/processing-containers/boa-output-check"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/boa-output-check:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("boa-output-check")
  cache-from = cache_from("boa-output-check")
}

target "body-and-organ-analysis" {
  context    = "data-processing/processing-pipelines/body-and-organ-analysis/processing-containers/body-and-organ-analysis"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu-3.10" = "target:base-python-cpu-3-10"
    "local-only/base-python-gpu-3.10" = "target:base-python-gpu-3-10"
  }
  tags = ["${REGISTRY}/body-and-organ-analysis:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("body-and-organ-analysis")
  cache-from = cache_from("body-and-organ-analysis")
}

target "bodypartregression" {
  context    = "data-processing/processing-pipelines/bodypartregression/processing-containers/bodypart-regression"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/bodypartregression:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("bodypartregression")
  cache-from = cache_from("bodypartregression")
}

target "buildah" {
  context    = "services/applications/edk/docker/buildah"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/buildah:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("buildah")
  cache-from = cache_from("buildah")
}

target "busybox" {
  context    = "services/utils/busybox/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/busybox:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("busybox")
  cache-from = cache_from("busybox")
}

target "cca" {
  context    = "data-processing/kaapana-plugin/processing-containers/3d-cca"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/cca:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("cca")
  cache-from = cache_from("cca")
}

target "cert-init" {
  context    = "services/kaapana-admin/admin-init/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/cert-init:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("cert-init")
  cache-from = cache_from("cert-init")
}

target "classification-inference" {
  context    = "data-processing/processing-pipelines/classification-workflow/processing-containers/classification-inference"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/classification-inference:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("classification-inference")
  cache-from = cache_from("classification-inference")
}

target "classification-preprocessing" {
  context    = "data-processing/processing-pipelines/classification-workflow/processing-containers/classification-preprocessing"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/classification-preprocessing:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("classification-preprocessing")
  cache-from = cache_from("classification-preprocessing")
}

target "classification-training" {
  context    = "data-processing/processing-pipelines/classification-workflow/processing-containers/classification-training"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/classification-training:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("classification-training")
  cache-from = cache_from("classification-training")
}

target "cleanup-expired-workflows" {
  context    = "data-processing/kaapana-plugin/processing-containers/cleanup-expired-workflows"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/cleanup-expired-workflows:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("cleanup-expired-workflows")
  cache-from = cache_from("cleanup-expired-workflows")
}

target "clear-validation-results" {
  context    = "data-processing/kaapana-plugin/processing-containers/clear-validation-results"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/clear-validation-results:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("clear-validation-results")
  cache-from = cache_from("clear-validation-results")
}

target "code-server" {
  context    = "services/applications/code-server/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
  }
  tags = ["${REGISTRY}/code-server:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("code-server")
  cache-from = cache_from("code-server")
}

target "collabora" {
  context    = "services/applications/collabora/docker/collabora"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/collabora:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("collabora")
  cache-from = cache_from("collabora")
}

target "create-dashboard-user" {
  context    = "services/meta/os-dashboards/docker/create-dashboard-user"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/create-dashboard-user:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("create-dashboard-user")
  cache-from = cache_from("create-dashboard-user")
}

target "create-project-user" {
  context    = "services/data-separation/project-namespace/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/create-project-user:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("create-project-user")
  cache-from = cache_from("create-project-user")
}

target "ctp" {
  context    = "services/flow/ctp/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/ctp:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("ctp")
  cache-from = cache_from("ctp")
}

target "dag-advanced-collect-metadata" {
  context    = "data-processing/processing-pipelines/advanced-collect-metadata/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-advanced-collect-metadata:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-advanced-collect-metadata")
  cache-from = cache_from("dag-advanced-collect-metadata")
}

target "dag-advanced-collect-metadata-federated" {
  context    = "data-processing/processing-pipelines/advanced_collect_metadata_federated/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-advanced-collect-metadata-federated:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-advanced-collect-metadata-federated")
  cache-from = cache_from("dag-advanced-collect-metadata-federated")
}

target "dag-body-and-organ-analysis" {
  context    = "data-processing/processing-pipelines/body-and-organ-analysis/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-body-and-organ-analysis:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-body-and-organ-analysis")
  cache-from = cache_from("dag-body-and-organ-analysis")
}

target "dag-bodypartregression" {
  context    = "data-processing/processing-pipelines/bodypartregression/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-bodypartregression:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-bodypartregression")
  cache-from = cache_from("dag-bodypartregression")
}

target "dag-classification-training-workflow" {
  context    = "data-processing/processing-pipelines/classification-workflow/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-classification-training-workflow:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-classification-training-workflow")
  cache-from = cache_from("dag-classification-training-workflow")
}

target "dag-extract-scanparameters" {
  context    = "data-processing/processing-pipelines/extract-scanparameter/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-extract-scanparameters:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-extract-scanparameters")
  cache-from = cache_from("dag-extract-scanparameters")
}

target "dag-federated-setup-central-test" {
  context    = "data-processing/processing-pipelines/federated-setup-central-test/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-federated-setup-central-test:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-federated-setup-central-test")
  cache-from = cache_from("dag-federated-setup-central-test")
}

target "dag-federated-setup-node-test" {
  context    = "data-processing/processing-pipelines/federated-setup-node-test/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-federated-setup-node-test:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-federated-setup-node-test")
  cache-from = cache_from("dag-federated-setup-node-test")
}

target "dag-mitk-flow" {
  context    = "data-processing/processing-pipelines/mitk-flow/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-mitk-flow:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-mitk-flow")
  cache-from = cache_from("dag-mitk-flow")
}

target "dag-nnunet" {
  context    = "data-processing/processing-pipelines/nnunet/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-nnunet:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-nnunet")
  cache-from = cache_from("dag-nnunet")
}

target "dag-nnunet-federated" {
  context    = "data-processing/processing-pipelines/nnunet-federated/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-nnunet-federated:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-nnunet-federated")
  cache-from = cache_from("dag-nnunet-federated")
}

target "dag-radiomics" {
  context    = "data-processing/processing-pipelines/radiomics/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-radiomics:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-radiomics")
  cache-from = cache_from("dag-radiomics")
}

target "dag-radiomics-federated" {
  context    = "data-processing/processing-pipelines/radiomics-federated/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-radiomics-federated:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-radiomics-federated")
  cache-from = cache_from("dag-radiomics-federated")
}

target "dag-total-segmentator-v2" {
  context    = "data-processing/processing-pipelines/total-segmentator-v2/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-total-segmentator-v2:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-total-segmentator-v2")
  cache-from = cache_from("dag-total-segmentator-v2")
}

target "dag-wsiconv" {
  context    = "data-processing/processing-pipelines/wsiconv/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/dag-wsiconv:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dag-wsiconv")
  cache-from = cache_from("dag-wsiconv")
}

target "data-api" {
  context    = "services/base/data-api/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/data-api:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("data-api")
  cache-from = cache_from("data-api")
}

target "data-ui" {
  context    = "services/base/data-ui/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-landing-page" = "target:base-landing-page"
  }
  tags = ["${REGISTRY}/data-ui:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("data-ui")
  cache-from = cache_from("data-ui")
}

target "dcm4che-postgres" {
  context    = "services/store/dcm4chee/docker/postgres"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    "local-only/postgres-base" = "target:postgres-base"
  }
  tags = ["${REGISTRY}/dcm4che-postgres:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcm4che-postgres")
  cache-from = cache_from("dcm4che-postgres")
}

target "dcm4chee-arc" {
  context    = "services/store/dcm4chee/docker/dcm4chee"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/dcm4chee-arc:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcm4chee-arc")
  cache-from = cache_from("dcm4chee-arc")
}

target "dcm4chee-ldap" {
  context    = "services/store/dcm4chee/docker/ldap"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/dcm4chee-ldap:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcm4chee-ldap")
  cache-from = cache_from("dcm4chee-ldap")
}

target "dcmodify" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcmtk-dcmodify"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/dcmodify:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcmodify")
  cache-from = cache_from("dcmodify")
}

target "dcmqi" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcmqi"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/dcmqi:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcmqi")
  cache-from = cache_from("dcmqi")
}

target "dcmqr" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcmqr"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/dcmqr:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcmqr")
  cache-from = cache_from("dcmqr")
}

target "dcmsend" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcmtk-dcmsend"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/dcmsend:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dcmsend")
  cache-from = cache_from("dcmsend")
}

target "delete-from-meta" {
  context    = "data-processing/kaapana-plugin/processing-containers/delete-from-meta"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/delete-from-meta:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("delete-from-meta")
  cache-from = cache_from("delete-from-meta")
}

target "delete-from-pacs" {
  context    = "data-processing/kaapana-plugin/processing-containers/delete-from-pacs"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/delete-from-pacs:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("delete-from-pacs")
  cache-from = cache_from("delete-from-pacs")
}

target "desktop-container" {
  context    = "services/applications/desktop-container/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
    "local-only/base-desktop" = "target:base-desktop"
  }
  tags = ["${REGISTRY}/desktop-container:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("desktop-container")
  cache-from = cache_from("desktop-container")
}

target "dev-code-server" {
  context    = "services/applications/dev-code-server/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
  }
  tags = ["${REGISTRY}/dev-code-server:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dev-code-server")
  cache-from = cache_from("dev-code-server")
}

target "dice-evaluation" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/dice-evaluation"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/dice-evaluation:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dice-evaluation")
  cache-from = cache_from("dice-evaluation")
}

target "dicom-init" {
  context    = "services/store/store-init/dicom-init/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/dicom-init:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dicom-init")
  cache-from = cache_from("dicom-init")
}

target "dicom-validator" {
  context    = "data-processing/kaapana-plugin/processing-containers/dicom-validator"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/dicom-validator:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dicom-validator")
  cache-from = cache_from("dicom-validator")
}

target "dicom-web-filter" {
  context    = "services/data-separation/dicom-web-filter/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/dicom-web-filter:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dicom-web-filter")
  cache-from = cache_from("dicom-web-filter")
}

target "dummy" {
  context    = "data-processing/workflows/dummy-workflow/processing-containers/dummy"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/dummy:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dummy")
  cache-from = cache_from("dummy")
}

target "dummy-task" {
  context    = "data-processing/kaapana-plugin/processing-containers/dummy-task"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/dummy-task:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("dummy-task")
  cache-from = cache_from("dummy-task")
}

target "edk" {
  context    = "services/applications/edk/docker/edk"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
  }
  tags = ["${REGISTRY}/edk:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("edk")
  cache-from = cache_from("edk")
}

target "extension-api" {
  context    = "services/base/extension-manager-service/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    "lib" = "lib"
  }
  tags = ["${REGISTRY}/extension-api:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("extension-api")
  cache-from = cache_from("extension-api")
}

target "extension-manager-ui" {
  context    = "services/base/extension-manager-ui/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-landing-page" = "target:base-landing-page"
  }
  tags = ["${REGISTRY}/extension-manager-ui:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("extension-manager-ui")
  cache-from = cache_from("extension-manager-ui")
}

target "federated-setup-central-test" {
  context    = "data-processing/processing-pipelines/federated-setup-central-test/processing-containers/federated-setup-central-test"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/federated-setup-central-test:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("federated-setup-central-test")
  cache-from = cache_from("federated-setup-central-test")
}

target "get-body-and-organ-analysis-models" {
  context    = "data-processing/processing-pipelines/body-and-organ-analysis/processing-containers/models"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-model-installer" = "target:base-model-installer"
  }
  tags = ["${REGISTRY}/get-body-and-organ-analysis-models:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("get-body-and-organ-analysis-models")
  cache-from = cache_from("get-body-and-organ-analysis-models")
}

target "get-input" {
  context    = "data-processing/kaapana-plugin/processing-containers/get-input"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/get-input:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("get-input")
  cache-from = cache_from("get-input")
}

target "get-input-task" {
  context    = "data-processing/workflows/registration-workflow/processing-containers/download"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/get-input-task:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("get-input-task")
  cache-from = cache_from("get-input-task")
}

target "get-ref-series" {
  context    = "data-processing/kaapana-plugin/processing-containers/get-ref-series"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/get-ref-series:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("get-ref-series")
  cache-from = cache_from("get-ref-series")
}

target "get-totalsegmentator-v2-models" {
  context    = "data-processing/processing-pipelines/total-segmentator-v2/processing-containers/models"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-model-installer" = "target:base-model-installer"
  }
  tags = ["${REGISTRY}/get-totalsegmentator-v2-models:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("get-totalsegmentator-v2-models")
  cache-from = cache_from("get-totalsegmentator-v2-models")
}

target "grafana" {
  context    = "services/monitoring/grafana/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/grafana:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("grafana")
  cache-from = cache_from("grafana")
}

target "init-meta" {
  context    = "services/meta/meta-init/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/init-meta:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("init-meta")
  cache-from = cache_from("init-meta")
}

target "init-projects" {
  context    = "services/data-separation/access-information-interface/docker/init-project"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/init-projects:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("init-projects")
  cache-from = cache_from("init-projects")
}

target "itk2dcm" {
  context    = "data-processing/kaapana-plugin/processing-containers/itk2dcm"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/itk2dcm:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("itk2dcm")
  cache-from = cache_from("itk2dcm")
}

target "json2meta" {
  context    = "data-processing/kaapana-plugin/processing-containers/json2meta"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/json2meta:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("json2meta")
  cache-from = cache_from("json2meta")
}

target "jupyterlab" {
  context    = "services/applications/jupyterlab/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/jupyterlab:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("jupyterlab")
  cache-from = cache_from("jupyterlab")
}

target "jupyterlab-reporting" {
  context    = "data-processing/kaapana-plugin/processing-containers/jupyterlab-reporting"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/jupyterlab-reporting:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("jupyterlab-reporting")
  cache-from = cache_from("jupyterlab-reporting")
}

target "kaapana-backend" {
  context    = "services/base/kaapana-backend/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/kaapana-backend:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kaapana-backend")
  cache-from = cache_from("kaapana-backend")
}

target "kaapana-documentation" {
  context    = "docs"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/kaapana-documentation:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kaapana-documentation")
  cache-from = cache_from("kaapana-documentation")
}

target "kaapana-extension-collection" {
  context    = "collections/kaapana-collection"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
    charts = "build/kaapana-admin-chart/kaapana-extension-collection"
  }
  tags       = ["${REGISTRY}/kaapana-extension-collection:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kaapana-extension-collection")
  cache-from = cache_from("kaapana-extension-collection")
}

target "kaapana-plugin" {
  context    = "data-processing/kaapana-plugin/extension/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-installer" = "target:base-installer"
  }
  tags = ["${REGISTRY}/kaapana-plugin:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kaapana-plugin")
  cache-from = cache_from("kaapana-plugin")
}

target "kaapana-wopi" {
  context    = "services/applications/collabora/docker/wopi"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/kaapana-wopi:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kaapana-wopi")
  cache-from = cache_from("kaapana-wopi")
}

target "keycloak" {
  context    = "services/kaapana-admin/keycloak/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/keycloak:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("keycloak")
  cache-from = cache_from("keycloak")
}

target "keycloak-setup" {
  context    = "services/kaapana-admin/keycloak/keycloak-setup/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/keycloak-setup:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("keycloak-setup")
  cache-from = cache_from("keycloak-setup")
}

target "kube-dashboard" {
  context    = "services/kaapana-admin/kubernetes-dashboard/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/kube-dashboard:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kube-dashboard")
  cache-from = cache_from("kube-dashboard")
}

target "kube-helm" {
  context    = "services/kaapana-admin/kube-helm/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/kube-helm:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kube-helm")
  cache-from = cache_from("kube-helm")
}

target "kube-state-metrics" {
  context    = "services/monitoring/kube_state_metrics/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/kube-state-metrics:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("kube-state-metrics")
  cache-from = cache_from("kube-state-metrics")
}

target "landing-page-kaapana" {
  context    = "services/base/landing-page-kaapana/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-landing-page" = "target:base-landing-page"
  }
  tags = ["${REGISTRY}/landing-page-kaapana:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("landing-page-kaapana")
  cache-from = cache_from("landing-page-kaapana")
}

target "local-registry" {
  context    = "services/applications/edk/docker/registry"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/local-registry:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("local-registry")
  cache-from = cache_from("local-registry")
}

target "local-registry-ui" {
  context    = "services/applications/edk/docker/registry-ui"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/local-registry-ui:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("local-registry-ui")
  cache-from = cache_from("local-registry-ui")
}

target "loki" {
  context    = "services/monitoring/loki/docker/loki"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/loki:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("loki")
  cache-from = cache_from("loki")
}

target "maintenance-page-kaapana" {
  context    = "services/kaapana-admin/maintenance-page/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/maintenance-page-kaapana:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("maintenance-page-kaapana")
  cache-from = cache_from("maintenance-page-kaapana")
}

target "mask2nifti" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcm-seg-rtstruct2nifti"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/mask2nifti:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mask2nifti")
  cache-from = cache_from("mask2nifti")
}

target "merge-masks" {
  context    = "data-processing/kaapana-plugin/processing-containers/merge-masks"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/merge-masks:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("merge-masks")
  cache-from = cache_from("merge-masks")
}

target "metrics-scraper" {
  context    = "services/kaapana-admin/metrics-scraper/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/metrics-scraper:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("metrics-scraper")
  cache-from = cache_from("metrics-scraper")
}

target "migration" {
  context    = "utils/migration-chart/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/migration:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("migration")
  cache-from = cache_from("migration")
}

target "minio" {
  context    = "services/store/minio/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/minio:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("minio")
  cache-from = cache_from("minio")
}

target "minio-init" {
  context    = "services/store/store-init/minio-init/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-minio-mc" = "target:base-minio-mc"
  }
  tags = ["${REGISTRY}/minio-init:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("minio-init")
  cache-from = cache_from("minio-init")
}

target "minio-mirror" {
  context    = "services/utils/minio-mirror"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-minio-mc" = "target:base-minio-mc"
  }
  tags = ["${REGISTRY}/minio-mirror:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("minio-mirror")
  cache-from = cache_from("minio-mirror")
}

target "minio-operator" {
  context    = "data-processing/kaapana-plugin/processing-containers/minio-operator"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/minio-operator:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("minio-operator")
  cache-from = cache_from("minio-operator")
}

target "mitk-fileconverter" {
  context    = "data-processing/kaapana-plugin/processing-containers/mitk-fileconverter"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
  }
  tags = ["${REGISTRY}/mitk-fileconverter:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mitk-fileconverter")
  cache-from = cache_from("mitk-fileconverter")
}

target "mitk-flow" {
  context    = "data-processing/processing-pipelines/mitk-flow/processing-containers/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-desktop" = "target:base-desktop"
  }
  tags = ["${REGISTRY}/mitk-flow:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mitk-flow")
  cache-from = cache_from("mitk-flow")
}

target "mitk-radiomics" {
  context    = "data-processing/processing-pipelines/radiomics/processing-containers/radiomics"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/mitk-radiomics:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mitk-radiomics")
  cache-from = cache_from("mitk-radiomics")
}

target "mitk-resample" {
  context    = "data-processing/kaapana-plugin/processing-containers/mitk-resample"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
  }
  tags = ["${REGISTRY}/mitk-resample:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mitk-resample")
  cache-from = cache_from("mitk-resample")
}

target "mitk-tools" {
  context    = "data-processing/workflows/registration-workflow/processing-containers/mitk-tools"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
  }
  tags = ["${REGISTRY}/mitk-tools:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mitk-tools")
  cache-from = cache_from("mitk-tools")
}

target "mitk-workbench" {
  context    = "services/applications/mitk-workbench/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
    "local-only/base-desktop" = "target:base-desktop"
  }
  tags = ["${REGISTRY}/mitk-workbench:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("mitk-workbench")
  cache-from = cache_from("mitk-workbench")
}

target "nginx" {
  context    = "services/applications/collabora/docker/nginx"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/nginx:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nginx")
  cache-from = cache_from("nginx")
}

target "nnunet-analysis-scripts" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/nnunet-analysis"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-minio-mc" = "target:base-minio-mc"
  }
  tags = ["${REGISTRY}/nnunet-analysis-scripts:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nnunet-analysis-scripts")
  cache-from = cache_from("nnunet-analysis-scripts")
}

target "nnunet-federated" {
  context    = "data-processing/processing-pipelines/nnunet-federated/processing-containers/nnunet-federated"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-nnunet-v2" = "target:base-nnunet-v2"
  }
  tags = ["${REGISTRY}/nnunet-federated:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nnunet-federated")
  cache-from = cache_from("nnunet-federated")
}

target "nnunet-gpu" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/nnunet"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-nnunet-v2" = "target:base-nnunet-v2"
  }
  tags = ["${REGISTRY}/nnunet-gpu:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nnunet-gpu")
  cache-from = cache_from("nnunet-gpu")
}

target "nnunet-model-download-from-pacs" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/model-download-from-pacs"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/nnunet-model-download-from-pacs:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nnunet-model-download-from-pacs")
  cache-from = cache_from("nnunet-model-download-from-pacs")
}

target "nnunet-model-management" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/model-management"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/nnunet-model-management:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nnunet-model-management")
  cache-from = cache_from("nnunet-model-management")
}

target "node-exporter" {
  context    = "services/monitoring/node-exporter/docker/node-exporter"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/node-exporter:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("node-exporter")
  cache-from = cache_from("node-exporter")
}

target "node-exporter-textfile-collector" {
  context    = "services/monitoring/node-exporter/docker/textfile-collector"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/node-exporter-textfile-collector:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("node-exporter-textfile-collector")
  cache-from = cache_from("node-exporter-textfile-collector")
}

target "notification-service" {
  context    = "services/base/notification-service/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/notification-service:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("notification-service")
  cache-from = cache_from("notification-service")
}

target "notify" {
  context    = "data-processing/kaapana-plugin/processing-containers/notify"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/notify:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("notify")
  cache-from = cache_from("notify")
}

target "nrrd-to-dicom" {
  context    = "data-processing/workflows/registration-workflow/processing-containers/nrrd-to-dicom"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/nrrd-to-dicom:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("nrrd-to-dicom")
  cache-from = cache_from("nrrd-to-dicom")
}

target "oauth2-proxy" {
  context    = "services/kaapana-admin/oAuth2-proxy/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/oauth2-proxy:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("oauth2-proxy")
  cache-from = cache_from("oauth2-proxy")
}

target "ohif" {
  context    = "services/store/ohif-viewer/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/ohif:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("ohif")
  cache-from = cache_from("ohif")
}

target "open-policy-agent" {
  context    = "services/kaapana-admin/open-policy-agent/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/open-policy-agent:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("open-policy-agent")
  cache-from = cache_from("open-policy-agent")
}

target "openedc" {
  context    = "services/applications/openEDC/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/openedc:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("openedc")
  cache-from = cache_from("openedc")
}

target "opensearch" {
  context    = "services/meta/opensearch/docker/opensearch"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/opensearch:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("opensearch")
  cache-from = cache_from("opensearch")
}

target "opensearch-certs" {
  context    = "services/meta/opensearch/docker/init-certificates"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/opensearch-certs:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("opensearch-certs")
  cache-from = cache_from("opensearch-certs")
}

target "os-dashboards" {
  context    = "services/meta/os-dashboards/docker/os-dashboard"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/os-dashboards:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("os-dashboards")
  cache-from = cache_from("os-dashboards")
}

target "pdf2dcm" {
  context    = "data-processing/kaapana-plugin/processing-containers/dcmtk-pdf2dcm"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/pdf2dcm:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("pdf2dcm")
  cache-from = cache_from("pdf2dcm")
}

target "postgres-18-4-alpine" {
  context    = "services/kaapana-admin/postgres/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/postgres-base" = "target:postgres-base"
  }
  tags = ["${REGISTRY}/postgres-18.4-alpine:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("postgres-18-4-alpine")
  cache-from = cache_from("postgres-18-4-alpine")
}

target "postgres-base" {
  context    = "services/kaapana-admin/postgres/docker/base-image"
  dockerfile = "Dockerfile"
  tags = ["local-only/postgres-base"]
  cache-to   = cache_to("postgres-base")
  cache-from = cache_from("postgres-base")
}

target "project-management-ui" {
  context    = "services/data-separation/project-management-ui/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-landing-page" = "target:base-landing-page"
  }
  tags = ["${REGISTRY}/project-management-ui:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("project-management-ui")
  cache-from = cache_from("project-management-ui")
}

target "project-runtime" {
  context    = "services/data-separation/project-runtime/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/project-runtime:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("project-runtime")
  cache-from = cache_from("project-runtime")
}

target "prometheus" {
  context    = "services/monitoring/prometheus/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/prometheus:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("prometheus")
  cache-from = cache_from("prometheus")
}

target "promtail" {
  context    = "services/monitoring/loki/docker/promtail"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/promtail:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("promtail")
  cache-from = cache_from("promtail")
}

target "pyradiomics" {
  context    = "data-processing/kaapana-plugin/processing-containers/pyradiomics"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/pyradiomics:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("pyradiomics")
  cache-from = cache_from("pyradiomics")
}

target "rabbitmq" {
  context    = "services/kaapana-admin/rabbitmq/rabbitmq-3.8"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/rabbitmq:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("rabbitmq")
  cache-from = cache_from("rabbitmq")
}

target "radiomics-federated" {
  context    = "data-processing/processing-pipelines/radiomics-federated/processing-containers/radiomics-federated"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/radiomics-federated:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("radiomics-federated")
  cache-from = cache_from("radiomics-federated")
}

target "radiomics-federated-analysis" {
  context    = "data-processing/processing-pipelines/radiomics-federated/processing-containers/radiomics-federated-analysis"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-minio-mc" = "target:base-minio-mc"
  }
  tags = ["${REGISTRY}/radiomics-federated-analysis:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("radiomics-federated-analysis")
  cache-from = cache_from("radiomics-federated-analysis")
}

target "redis" {
  context    = "services/kaapana-admin/oAuth2-proxy/redis-docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/redis:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("redis")
  cache-from = cache_from("redis")
}

target "scanparam2json" {
  context    = "data-processing/processing-pipelines/extract-scanparameter/processing-containers/scanparam2json"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/scanparam2json:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("scanparam2json")
  cache-from = cache_from("scanparam2json")
}

target "seg-check" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/seg-check"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-mitk" = "target:base-mitk"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/seg-check:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("seg-check")
  cache-from = cache_from("seg-check")
}

target "seg-eval" {
  context    = "data-processing/kaapana-plugin/processing-containers/seg-eval"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/seg-eval:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("seg-eval")
  cache-from = cache_from("seg-eval")
}

target "send-dicoms" {
  context    = "data-processing/workflows/registration-workflow/processing-containers/send-dicoms"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/send-dicoms:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("send-dicoms")
  cache-from = cache_from("send-dicoms")
}

target "service-checker" {
  context    = "services/utils/service_checker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/service-checker:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("service-checker")
  cache-from = cache_from("service-checker")
}

target "slicer-workbench" {
  context    = "services/applications/slicer-workbench/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-desktop" = "target:base-desktop"
  }
  tags = ["${REGISTRY}/slicer-workbench:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("slicer-workbench")
  cache-from = cache_from("slicer-workbench")
}

target "slim" {
  context    = "services/applications/slim-viewer/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/slim:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("slim")
  cache-from = cache_from("slim")
}

target "squid" {
  context    = "services/kaapana-admin/squid/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/squid:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("squid")
  cache-from = cache_from("squid")
}

target "statistics2pdf" {
  context    = "data-processing/processing-pipelines/nnunet/processing-containers/statistics2pdf"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/statistics2pdf:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("statistics2pdf")
  cache-from = cache_from("statistics2pdf")
}

target "statsd-exporter" {
  context    = "services/flow/airflow/statsd-exporter-docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/statsd-exporter:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("statsd-exporter")
  cache-from = cache_from("statsd-exporter")
}

target "tensorboard" {
  context    = "services/applications/tensorboard/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/tensorboard:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("tensorboard")
  cache-from = cache_from("tensorboard")
}

target "thumbnail-generator" {
  context    = "data-processing/kaapana-plugin/processing-containers/thumbnail-generator"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/thumbnail-generator:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("thumbnail-generator")
  cache-from = cache_from("thumbnail-generator")
}

target "total-segmentator-v2" {
  context    = "data-processing/processing-pipelines/total-segmentator-v2/processing-containers/total-segmentator"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/total-segmentator-v2:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("total-segmentator-v2")
  cache-from = cache_from("total-segmentator-v2")
}

target "traefik" {
  context    = "services/kaapana-admin/traefik/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/traefik:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("traefik")
  cache-from = cache_from("traefik")
}

target "train-test-split" {
  context    = "data-processing/kaapana-plugin/processing-containers/train-test-split"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/train-test-split:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("train-test-split")
  cache-from = cache_from("train-test-split")
}

target "update-seginfo" {
  context    = "data-processing/kaapana-plugin/processing-containers/update-seginfo"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/update-seginfo:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("update-seginfo")
  cache-from = cache_from("update-seginfo")
}

target "workflow-api" {
  context    = "services/base/workflow-api/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
    constraints = "constraints"
  }
  tags = ["${REGISTRY}/workflow-api:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("workflow-api")
  cache-from = cache_from("workflow-api")
}

target "workflow-cleaner" {
  context    = "data-processing/kaapana-plugin/processing-containers/workflow-cleaner"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/workflow-cleaner:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("workflow-cleaner")
  cache-from = cache_from("workflow-cleaner")
}

target "workflow-installer" {
  context    = "data-processing/workflows/workflow-installer/docker"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/workflow-installer:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("workflow-installer")
  cache-from = cache_from("workflow-installer")
}

target "workflow-ui" {
  context    = "services/base/workflow-ui/docker"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-landing-page" = "target:base-landing-page"
  }
  tags = ["${REGISTRY}/workflow-ui:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("workflow-ui")
  cache-from = cache_from("workflow-ui")
}

target "wsiconv" {
  context    = "data-processing/processing-pipelines/wsiconv/processing-containers/wsiconv"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-gpu" = "target:base-python-gpu"
  }
  tags = ["${REGISTRY}/wsiconv:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("wsiconv")
  cache-from = cache_from("wsiconv")
}

target "zip-unzip" {
  context    = "data-processing/kaapana-plugin/processing-containers/zip-unzip"
  dockerfile = "Dockerfile"
  contexts = {
    "local-only/base-python-cpu" = "target:base-python-cpu"
  }
  tags = ["${REGISTRY}/zip-unzip:${TAG}"]
  inherits   = ["_pushable"]
  cache-to   = cache_to("zip-unzip")
  cache-from = cache_from("zip-unzip")
}

