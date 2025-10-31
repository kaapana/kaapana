{{/* Used to set PersistentVolume and PersistentVolumeClaim dynamically by setting global.dynamicVolumes with a list of name, storage map */}}
{{- define "dynamicPersistentVolumes" }}
---
# Variables
{{- $global := .Values.global -}}
{{- $namespace := not $global.namespace | ternary $global.services_namespace (tpl ($global.namespace | toString) .) }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}

# Iterate over all volumes
{{- range $volume := .Values.global.dynamicVolumes }}
  {{- $postfix := or (has "kaapanamultiinstallable" $keywords) (hasKey $volume "minio_mirror") | ternary (printf "-%s" $release_name) "" }}
  {{- $storage_class := $global.storage_class_fast | default "default" -}}
  {{- $storage := $volume.storage -}}
  {{- if eq $volume.storage_class "workflow" -}}
    {{- $storage_class = $global.storage_class_workflow -}}
  {{- else if eq $volume.storage_class "slow" -}}
    {{- $storage_class = $global.storage_class_slow -}}
    {{- $storage = $volume.storage | default $global.volume_slow_data -}}
  {{- end }}

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $volume.name }}{{ $postfix }}-pv-claim
  namespace: "{{ $namespace }}"
  annotations:
    "helm.sh/resource-policy": keep
spec:
  storageClassName: {{ $storage_class }}
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {{ $storage | default "10Gi" }}
{{- end }}
{{- end }}
