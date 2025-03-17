{{/* Used to set environmal variables with valueFrom secretKeyRef given to global.envVars as name, value map */}}
{{- define "dynamicEnvsFromSecretRef" }}
{{- range $envVar := .Values.global.envVarsFromSecretRef }}
- name: {{ $envVar.name }}
  valueFrom:
    secretKeyRef:
      name: "{{ $envVar.secretName }}"
      key: "{{ $envVar.secretKey }}"
{{- end }}
{{- end }}