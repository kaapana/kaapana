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
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ $volume.name }}{{ $postfix }}-pv-volume
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
    path: {{ regexMatch "^(/minio|/dcm4che/dicom_data|/dcm4che/server_data)" $volume.host_path | ternary $.Values.global.slow_data_dir $.Values.global.fast_data_dir }}{{ $volume.host_path }}{{ $minio_mirror | ternary (printf "/%s" $release_name) ""}}
{{- end }}
  persistentVolumeReclaimPolicy: Retain
  claimRef:
    namespace: "{{ $namespace }}"
    name: {{ $volume.name }}{{ $postfix }}-pv-claim
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $volume.name }}{{ $postfix }}-pv-claim
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
  resources:
    requests:
      storage: {{ $volume.storage | default "1Mi" }}
  volumeName: {{ $volume.name }}{{ $postfix }}-pv-volume
---
{{- end }}
{{- end }}
{{- end }}