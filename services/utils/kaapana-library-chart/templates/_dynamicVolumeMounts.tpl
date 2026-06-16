{{/* Used to set volumeMounts dynamically given to global.dynamicVolumes as name, mount_path map */}}
{{/* Can be called with the root context, or with (dict "root" $ "mountPropagation" "HostToContainer") */}}
{{/* to set a mountPropagation mode on the dynamic volume mounts, e.g. for FUSE mount sidecars. */}}
{{- define "dynamicVolumeMounts" }}
{{- $root := default . .root }}
{{- $propagation := .mountPropagation | default "" }}
{{- $dynamic := default (list) $root.Values.global.dynamicVolumes }}

{{- range $volumeMount := $dynamic }}
- name: {{ $volumeMount.name }}
  mountPath: "{{ $volumeMount.mount_path }}"
{{- if $volumeMount.sub_path }}
  subPath: "{{ $volumeMount.sub_path }}"
{{- end }}
{{- if $propagation }}
  mountPropagation: {{ $propagation }}
{{- end }}
{{- end }}

{{- if and $root.Values.global.workflow_config_mount_path (ne $root.Values.global.workflow_config_mount_path "") }}
- name: workflowconf
  mountPath: {{ $root.Values.global.workflow_config_mount_path }}
  subPath: conf.json
{{- end }}
{{- end }}
