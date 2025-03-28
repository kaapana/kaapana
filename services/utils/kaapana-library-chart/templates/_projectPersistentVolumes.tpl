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
kind: PersistentVolume
metadata:
  name: "{{ $volumeName }}"
  labels:
    type: local
spec:
  capacity:
    storage: {{ $volume.storage | default "1Mi" }}
{{- if $.Values.global.enable_nfs }}
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  nfs:
    server: "10.152.183.15"
    path: {{ $volume.host_path }}
{{- else }}
  storageClassName: host-dir
  accessModes:
    - ReadWriteOnce
  hostPath: 
    path: {{ $.Values.global.fast_data_dir }}{{ $project_data_dir }}
{{- end }}
  persistentVolumeReclaimPolicy: Retain
  claimRef:
    namespace: "{{ $namespace }}"
    name: {{ $volumeClaimName }}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: "{{ $volumeClaimName }}"
  namespace: "{{ $namespace  }}"
spec:
{{- if $.Values.global.enable_nfs }}
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
{{- else }}
  storageClassName: host-dir
  accessModes:
    - ReadWriteOnce
{{- end }}
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: {{ $volume.storage | default "1Mi" }}
  volumeName: {{ $volumeName }}
---
{{- end }}
{{- end }}
{{- end }}