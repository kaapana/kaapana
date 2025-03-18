{{- define "devPersistentVolumes" }}
{{- $is_admin_namespace := .Values.admin | default false }}
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ .Chart.Name }}-dev-pv-volume
  labels:
    type: local
spec:
  capacity:
    storage: "1Mi"
{{- if .Values.global.enable_nfs }}
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  nfs:
    server: "10.152.183.15"
    path: /dev_{{ .Chart.Name }}
{{- else }}
  storageClassName: host-dir
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "{{ .Values.global.dev_files }}"
{{- end }}
  persistentVolumeReclaimPolicy: Retain
  claimRef:
    namespace: "{{ ternary .Values.global.admin_namespace .Values.global.services_namespace $is_admin_namespace }}"
    name: {{ .Chart.Name }}-dev-pv-claim
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ .Chart.Name }}-dev-pv-claim
  namespace: "{{ ternary .Values.global.admin_namespace .Values.global.services_namespace $is_admin_namespace }}"
spec:
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: "1Mi"
  volumeName: "{{ .Chart.Name }}-dev-pv-volume"
{{- end }}