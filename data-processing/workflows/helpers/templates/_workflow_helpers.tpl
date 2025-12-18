{{/*
Generate a hash suffix based on workflow files content
*/}}
{{- define "workflow.configMapHash" -}}
{{- $data := "" -}}
{{- range $path, $_ := .Files.Glob "files/**" -}}
{{- $data = print $data ($.Files.Get $path) -}}
{{- end -}}
{{- $data | sha256sum | trunc 8 -}}
{{- end }}

{{/*
Create a full ConfigMap manifest for workflow files.
Automatically includes all files from the files/ directory.
*/}}
{{- define "workflow.configMap" -}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Chart.Name }}-configmap-{{ include "workflow.configMapHash" . }}
  namespace: {{ .Values.global.services_namespace }}
  labels:
    app: {{ .Chart.Name }}
data:
{{- range $path, $_ := .Files.Glob "files/**" }}
  {{ base $path }}: |
{{ $.Files.Get $path | indent 4 }}
{{- end }}
{{- end }}

{{/*
Create a Job manifest for workflow installation
*/}}
{{- define "workflow.installerJob" -}}
---
apiVersion: batch/v1
kind: Job
metadata:
  name: workflow-installer-{{ .Chart.Name }}-{{ .Release.Revision }}
  namespace: {{ .Values.global.services_namespace }}
  labels:
    app: {{ .Chart.Name }}
    component: workflow-installer
spec:
  ttlSecondsAfterFinished: 300
  template:
    metadata:
      labels:
        app: {{ .Chart.Name }}
        component: workflow-installer
    spec:
      initContainers:
        - name: service-checker
          image: "{{ .Values.global.registry_url }}/service-checker:{{ .Values.global.kaapana_build_version }}"
          imagePullPolicy: {{ .Values.global.pull_policy_images }}
          env:
            - name: WAIT
              value: "workflow-api,workflow-api.{{ .Values.global.services_namespace }}.svc,80,/v1/health"
            - name: DELAY
              value: "2"
            - name: TIMEOUT
              value: "10"
      containers:
        - name: workflow-installer
          image: "{{ .Values.global.registry_url }}/workflow-installer:{{ .Values.global.kaapana_build_version }}"
          imagePullPolicy: {{ .Values.global.pull_policy_images }}
          env:
            - name: WORKFLOW_API_URL
              value: "http://workflow-api.{{ .Values.global.services_namespace }}.svc:80/v1"
          volumeMounts:
            - name: workflow-files
              mountPath: /workflows
      volumes:
        - name: workflow-files
          configMap:
            name: {{ .Chart.Name }}-configmap-{{ include "workflow.configMapHash" . }}
      restartPolicy: Never
      imagePullSecrets:
        - name: registry-secret
  backoffLimit: 1
{{- end }}
