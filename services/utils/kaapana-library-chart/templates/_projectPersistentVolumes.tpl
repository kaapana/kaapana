{{/* Used to define pairs of persistentVolumes and persistentVolumeClaims for project namespaces */}}
{{- define "projectPersistentVolumes" -}}
---
# Variables
{{- $namespace := .Values.global.project_namespace | default "project-admin" }}
{{- $global := .Values.global | default dict }}
{{- $noReadWriteManySupport := $global.no_read_write_many_support | default false }}
{{- $storageClassWorkflow := index $ "Values" "global" "storage_class_workflow" | default "kaapana-hostpath-fast-data-dir" }}
# Iteration
{{- range $volume := .Values.global.dynamicVolumes }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $volume.name }}-pv-claim
  namespace: "{{ $namespace }}"
  annotations:
    "helm.sh/resource-policy": keep
spec:
  storageClassName: {{ $storageClassWorkflow }}
  accessModes:
    - {{ if or (eq $storageClassWorkflow "kaapana-hostpath-fast-data-dir") $noReadWriteManySupport }}ReadWriteOnce{{ else }}ReadWriteMany{{ end }}
  resources:
    requests:
      storage: {{ $volume.storage | default "1Gi" }}
---
{{- end }}
{{- end }}
