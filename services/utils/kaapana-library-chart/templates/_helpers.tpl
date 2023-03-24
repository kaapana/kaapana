{{/* Used to set environmal variables given to global.envVars as name, value map */}}
{{- define "dynamicEnvs" }}
{{- range $envVar := .Values.global.envVars }}
- name: {{ $envVar.name }}
  value: "{{ $envVar.value }}"
{{- end }}
{{- end }}

{{/* The folloiwng three templates faciliate the use of volumes. To use them provide needed volume information as explained in the methods below as a map to global.dynamicVolumes as name. Possible values are: name, host_path, mount_path, storage. "name" is needed for "dynamicVolumes", "name" and "mount_path" is neeeded for "dynamicVolumeMounts", and "name", "host_path" and "storage" is needed for "dynamicPersistentVolumes" */}}

{{/* Used to set volumes dynamically given to global.dynamicVolumes as name, the pv-claim is automatically added */}}
{{- define "dynamicVolumes" }}
{{- $namespace := not .Values.global.namespace | ternary .Values.global.services_namespace (tpl (.Values.global.namespace | toString) .) }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}
{{- range $volume := .Values.global.dynamicVolumes }}
{{- $postfix := and (has "kaapanamultiinstallable" $keywords) (hasKey $volume "host_path") | ternary (printf "-%s" $release_name) "" }}
- name: {{ $volume.name }}
  persistentVolumeClaim:
    claimName: {{ $volume.name }}{{ $postfix }}-pv-claim
{{- end }}
{{- end }}

{{/* Used to set volumeMounts dynamically given to global.dynamicVolumes as name, mount_path map */}}
{{- define "dynamicVolumeMounts" }}
{{- range $volumeMount := .Values.global.dynamicVolumes }}
- name: {{ $volumeMount.name }}
  mountPath: "{{ $volumeMount.mount_path }}"
{{- end }}
{{- end }}

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
    path: {{ regexMatch "^(/minio|/dcm4che/dicom_data)" $volume.host_path | ternary $.Values.global.slow_data_dir $.Values.global.fast_data_dir }}{{ $volume.host_path }}
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
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: {{ $volume.storage | default "1Mi" }}
  volumeName: {{ $volume.name }}{{ $postfix }}-pv-volume
---
{{- end }}
{{- end }}
{{- end }}