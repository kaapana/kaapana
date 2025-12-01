{{/* Used to set volumeMounts dynamically given to global.dynamicVolumes as name, mount_path map */}}
{{- define "dynamicVolumeMounts" }}
{{- $dynamic := default (list) .Values.global.dynamicVolumes }}
{{- $shared := default (list) .Values.global.sharedVolumes }}
{{- $Volumes := concat $dynamic $shared }}

{{- range $volumeMount := $Volumes }}
- name: {{ $volumeMount.name }}
  mountPath: "{{ $volumeMount.mount_path }}"
{{- end }}
{{- if and .Values.global.workflow_config_mount_path (ne .Values.global.workflow_config_mount_path "") }}
- name: workflowconf
  mountPath: {{ .Values.global.workflow_config_mount_path}}
  subPath: conf.json
{{- end }}
{{- end }}