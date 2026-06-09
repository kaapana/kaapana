{{/* Used to set volumes dynamically given to global.dynamicVolumes as name, the pv-claim is automatically added */}}
{{- define "dynamicVolumes" }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}
{{- $dynamic := default (list) .Values.global.dynamicVolumes }}

{{- range $volume := $dynamic }}
{{- $postfix := (has "kaapanamultiinstallable" $keywords) | ternary (printf "-%s" $release_name) "" }}
- name: {{ $volume.name }}
  persistentVolumeClaim:
    claimName: {{ $volume.name }}{{ $postfix }}-pv-claim
{{- end }}

{{- if and .Values.global.workflow_configmap_name (ne .Values.global.workflow_configmap_name "") }}
- name: workflowconf
  configMap:
    name: {{ .Values.global.workflow_configmap_name }}
    items:
      - key: conf.json
        path: conf.json
{{- end }}
{{- end }}