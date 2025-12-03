{{/* Used to define pairs of persistentVolumes and persistentVolumeClaims for project namespaces */}}
{{- define "projectPersistentVolumes" -}}
---
# Variables
{{- $namespace := .Values.global.project_namespace | default "project-admin" }}
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
  storageClassName: {{ default "kaapana-hostpath-fast-data-dir" (index $ "Values" "global" "storage_class_workflow") }}
  accessModes:
    - {{ eq (index $ "Values" "global" "storage_class_workflow") "kaapana-hostpath-fast-data-dir" | ternary "ReadWriteOnce" "ReadWriteMany" }}
  resources:
    requests:
      storage: {{ $volume.storage | default "1Gi" }}
---
{{- end }}
{{- end }}