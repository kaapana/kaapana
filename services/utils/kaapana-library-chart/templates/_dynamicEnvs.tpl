{{/* Used to set environmal variables given to global.envVars as name, value map */}}
{{/* Values are escaped with quote. Otherwise a double quote or a backslash in a value would break the YAML. */}}
{{- define "dynamicEnvs" }}
{{- range $envVar := .Values.global.envVars }}
- name: {{ $envVar.name }}
  value: {{ $envVar.value | quote }}
{{- end }}
{{- end }}