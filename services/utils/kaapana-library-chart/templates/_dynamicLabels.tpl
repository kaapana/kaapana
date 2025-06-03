{{/* Used to set labels given to global.labels as name, value map */}}
{{- define "dynamicLabels" }}
{{- range $label := .Values.global.labels }}
{{ $label.name }}: "{{ $label.value }}"
{{- end }}
{{- end }}