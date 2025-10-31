{{/* Used to set volumes dynamically given to global.dynamicVolumes as name, the pv-claim is automatically added */}}
{{- define "dynamicVolumes" }}
{{- $namespace := not .Values.global.namespace | ternary .Values.global.services_namespace (tpl (.Values.global.namespace | toString) .) }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}
{{- range $volume := .Values.global.dynamicVolumes }}
{{- $postfix := or (has "kaapanamultiinstallable" $keywords) (hasKey $volume "minio_mirror") | ternary (printf "-%s" $release_name) "" }}
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