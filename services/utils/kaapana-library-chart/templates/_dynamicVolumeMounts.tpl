{{/* Used to set volumeMounts dynamically given to global.dynamicVolumes as name, mount_path map */}}
{{- define "dynamicVolumeMounts" }}
{{- range $volumeMount := .Values.global.dynamicVolumes }}
- name: {{ $volumeMount.name }}
  mountPath: "{{ $volumeMount.mount_path }}"
{{- end }}
{{- end }}