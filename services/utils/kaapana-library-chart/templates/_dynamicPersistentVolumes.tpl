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
  {{- if not $volume.use_existing_pvc }} 
    {{- $postfix := (has "kaapanamultiinstallable" $keywords) | ternary (printf "-%s" $release_name) "" }}
    {{- $storage_class := $global.storage_class_fast | default "default" -}}
    {{- $storage := $volume.storage -}}
    {{- $accessMode := "ReadWriteOnce" -}}

    {{- if eq $volume.storage_class "workflow" }}
      {{- $storage_class = $global.storage_class_workflow -}}
      {{- if ne $global.storage_class_workflow "kaapana-hostpath-fast-data-dir" }}
        {{- $accessMode = "ReadWriteMany" -}}
      {{- end }}

    {{- else if eq $volume.storage_class "slow" }}
      {{- $storage_class = $global.storage_class_slow -}}
      {{- $storage = $volume.storage | default $global.volume_slow_data -}}
    {{- end }}

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $volume.name }}{{ $postfix }}-pv-claim
  namespace: "{{ $namespace }}"
  {{- if not (has "kaapanamultiinstallable" $keywords) }}
  annotations:
    "helm.sh/resource-policy": "keep"
  {{- end }}
spec:
  storageClassName: {{ $storage_class }}
  accessModes:
    - {{ $accessMode }}
  resources:
    requests:
      storage: {{ $storage | default "10Gi" }}
  {{- end }}
{{- end }}  
{{- end }}
