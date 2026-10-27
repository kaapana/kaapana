{{- define "kaapana.nodeSelector" }}
{{- if .Values.global.storage_node }}
nodeSelector:
  kaapana.io/node: {{ .Values.global.storage_node | quote }}
{{- end }}
{{- end }}