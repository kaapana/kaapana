{{/* Used to set PersistentVolume and PersistentVolumeClaim dynamically by setting global.dynamicVolumes with a list of name, host_path, storage map */}}
{{- define "dynamicPersistentVolumes" }}
---
# Variables
{{- $namespace := not .Values.global.namespace | ternary .Values.global.services_namespace (tpl (.Values.global.namespace | toString) .) }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}
# Iteration
{{- range $volume := .Values.global.dynamicVolumes }}
{{- $postfix := and (has "kaapanamultiinstallable" $keywords) (hasKey $volume "host_path") | ternary (printf "-%s" $release_name) "" }}
{{- $minio_mirror := and (hasKey $volume "minio_mirror") ($volume.minio_mirror) }}
{{- if $volume.host_path }}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $volume.name }}{{ $postfix }}-pv-claim
  namespace: "{{ $namespace  }}"
  annotations:
    "helm.sh/resource-policy": keep
spec:
  storageClassName: {{ regexMatch "^(/minio|/dcm4che/dicom_data|/dcm4che/server_data)" $volume.host_path | ternary "kaapana-hostpath-slow-data-dir" "kaapana-hostpath-fast-data-dir"}}
  accessModes:
    - ReadWriteOnce
{{- end }}
  resources:
    requests:
      storage: {{ $volume.storage | default "1Mi" }}
  #volumeName: {{ $volume.name }}{{ $postfix }}-pv-volume
---
{{- end }}
{{- end }}
{{- end }}