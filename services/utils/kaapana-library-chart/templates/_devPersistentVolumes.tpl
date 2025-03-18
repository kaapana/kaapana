{{- define "devPersistentVolumes" }}
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ .Release.Name }}-dev-pv-volume
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
    path: "/dev_{{ .Release.Name }}"
{{- else }}
  storageClassName: host-dir
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "{{ .Values.global.dev_files }}"
{{- end }}
  persistentVolumeReclaimPolicy: Retain
  claimRef:
    namespace: "{{ .Values.global.services_namespace }}"
    name: {{ .Release.Name }}-dev-pv-claim
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ .Release.Name }}-dev-pv-claim
  namespace: "{{ .Values.global.services_namespace }}"
spec:
  storageClassName: nfs
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: "1Mi"
  volumeName: "{{ .Release.Name }}-dev-pv-volume"
{{- end }}