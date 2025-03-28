{{/* Used to set environmal variables given to global.envVars as name, value map */}}
{{- define "dynamicEnvs" }}
{{- range $envVar := .Values.global.envVars }}
- name: {{ $envVar.name }}
  value: "{{ $envVar.value }}"
{{- end }}
{{- end }}