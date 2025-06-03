{{/* Used to set volumes dynamically given to global.dynamicVolumes as name, the pv-claim is automatically added */}}
{{- define "dynamicVolumes" }}
{{- $namespace := not .Values.global.namespace | ternary .Values.global.services_namespace (tpl (.Values.global.namespace | toString) .) }}
{{- $release_name := .Release.Name }}
{{- $keywords := .Chart.Keywords }}
{{- range $volume := .Values.global.dynamicVolumes }}
{{- $postfix := and (has "kaapanamultiinstallable" $keywords) (hasKey $volume "host_path") | ternary (printf "-%s" $release_name) "" }}
- name: {{ $volume.name }}
  persistentVolumeClaim:
    claimName: {{ $volume.name }}{{ $postfix }}-pv-claim
{{- end }}
{{- end }}