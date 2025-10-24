{{/* Used to define pairs of persistentVolumes and persistentVolumeClaims for project namespaces */}}
{{- define "projectPersistentVolumes" -}}
---
# Variables
{{- $namespace := .Values.global.project_namespace | default "project-admin" }}
# Iteration
{{- range $volume := .Values.global.dynamicVolumes }}
{{- $volumeName := printf "%s-%s-pv" $namespace $volume.name }}
{{- $volumeClaimName := printf "%s-%s-pv-claim" $namespace $volume.name }}
{{- if $volume.host_path }}
{{- $project_data_dir := $volume.host_path}}

apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: "{{ $volumeClaimName }}"
  namespace: "{{ $namespace  }}"
  annotations:
    "helm.sh/resource-policy": keep
spec:
  storageClassName: "kaapana-hostpath-fast-data-dir"
  accessModes:
    - ReadWriteOnce
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: {{ $volume.storage | default "1Mi" }}
  #volumeName: {{ $volumeName }}
---
{{- end }}
{{- end }}
{{- end }}