{{- define "dynamicSharedVolumes" }}
# Only use this if a volume shared across namespaces is needed:
# Dynamic Shared Volumes are not possible to create in Longhorn or microk8s hostpath provisioner,
# therefore for those shared volumes hostpaths have to be used.
# This template creates PersistentVolumes and PersistentVolumeClaims for those shared volumes with hostpaths.
# The attached pods must have a nodeSelector to ensure that they are scheduled on the same node where the hostpath exists.
{{- $global := .Values.global -}}
{{- $ns_project := $global.project_namespace }} 
{{- $ns_service := $global.services_namespace }}
{{- $namespace := default "default" (default $ns_service $ns_project) }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}
{{- range $volume := $global.sharedVolumes }}
{{- $storage := $volume.storage | default "1Mi" }}
{{- if $volume.host_path }}
{{- $volumeName := printf "%s-%s-pv" $namespace $volume.name }}
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ $volumeName }}
spec:
  capacity:
    storage: {{ $storage }}
  accessModes:
    - "ReadWriteOnce"
  persistentVolumeReclaimPolicy: Delete
  storageClassName: "kaapana-hostpath"
  hostPath:
    path: {{ $global.fast_data_dir }}{{ $volume.host_path }}
    type: DirectoryOrCreate

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $volume.name }}-pv-claim
  namespace: {{ $namespace }}
spec:
  storageClassName: "kaapana-hostpath"
  volumeName: {{ $volumeName }}
  accessModes:
    - "ReadWriteOnce"
  resources:
    requests:
      storage: {{ $storage }}


{{- end }}
{{- end }}
{{- end }}