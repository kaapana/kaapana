{{- define "kaapana.nodeSelector" }}
nodeSelector:
  kubernetes.io/hostname: {{ .Values.global.main_node_name | quote }}
{{- end }}