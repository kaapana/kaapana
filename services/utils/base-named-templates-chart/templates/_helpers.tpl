{{- define "dynamicEnvs" }}
{{- range $envVar := .Values.global.envVars }}
- name: {{ $envVar.name }}
  value: "{{ $envVar.value }}"
{{- end }}
{{- end }}

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

{{- define "dynamicVolumeMounts" }}
{{- range $volumeMount := .Values.global.dynamicVolumes }}
- name: {{ $volumeMount.name }}
  mountPath: "{{ $volumeMount.mount_path }}"
{{- end }}
{{- end }}

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