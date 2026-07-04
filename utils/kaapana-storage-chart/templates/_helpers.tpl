{{/*
Validate the reclaim policy used by Kaapana-owned hostpath StorageClasses.
Allowed values are Delete and Retain. The chart's values.yaml default is Delete.
*/}}
{{- define "kaapana-storage-chart.hostpathReclaimPolicy" -}}
{{- $policy := default "Delete" .Values.global.hostpath_reclaim_policy -}}
{{- if not (or (eq $policy "Delete") (eq $policy "Retain")) -}}
{{- fail (printf "global.hostpath_reclaim_policy must be either Delete or Retain, got %q" $policy) -}}
{{- end -}}
{{- $policy -}}
{{- end -}}
