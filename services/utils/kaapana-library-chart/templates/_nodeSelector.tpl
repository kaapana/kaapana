{{- define "kaapana.nodeSelector" }}
nodeSelector:
  kaapana.io/node: {{ .Values.global.storage_node }}
{{- end }}