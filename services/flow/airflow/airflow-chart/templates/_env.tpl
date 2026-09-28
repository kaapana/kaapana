{{- define "airflow.env.common" }}
- name: ADMIN_NAMESPACE
  value: "{{ .Values.global.admin_namespace }}"
- name: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
  value: postgresql+psycopg2://{{ .Values.kaapana_database.postgres_user }}:{{ .Values.kaapana_database.postgres_password }}@{{ .Values.kaapana_database.appName | default .Chart.Name }}-database-service.{{ .Values.global.services_namespace }}.svc:5432/{{ .Values.kaapana_database.postgres_db }}
- name: AIRFLOW_HOME
  value: "/kaapana/mounted/workflows"
- name: DEFAULT_REGISTRY
  value: "{{ .Values.global.registry_url }}"
- name: EXTENSIONS_NAMESPACE
  value: "{{ .Values.global.extensions_namespace }}"
- name: HOSTDOMAIN
  value: "{{ .Values.global.hostname }}"
- name: HTTPS_PORT
  value: "{{ .Values.global.https_port }}"
- name: INSTANCE_NAME
  value: "{{ .Values.global.instance_name }}"
- name: KAAPANA_BUILD_VERSION
  value: "{{ .Values.global.kaapana_build_version }}"
- name: PLATFORM_PREFIX
  value: "{{ required `global.platform_prefix is required` .Values.global.platform_prefix }}"
- name: MINIOUSER
  value: "{{ .Values.global.credentials_minio_username }}"
- name: MINIOPASSWORD
  value: "{{ .Values.global.credentials_minio_password }}"
- name: PULL_POLICY_IMAGES
  value: "{{ .Values.global.pull_policy_images }}"
- name: SERVICES_NAMESPACE
  value: "{{ .Values.global.services_namespace }}"
- name: SQLALCHEMY_SILENCE_UBER_WARNING
  value: "1"
- name: OIDC_CLIENT_SECRET
  value: "{{ .Values.global.oidc_client_secret }}"
- name: SYSTEM_USER_PASSWORD
  valueFrom:
    secretKeyRef:
      name: system-user-password
      key: system-user-password
- name: OPENSEARCH_HOST
  value: "opensearch-service.{{ .Values.global.services_namespace }}.svc"
- name: OPENSEARCH_PORT
  value: "9200"
- name: KEYCLOAK_URL
  value: "http://keycloak-external-service.{{ .Values.global.admin_namespace }}.svc:80"
- name: KUBE_HELM_URL
  value: "http://kube-helm-service.{{ .Values.global.admin_namespace }}.svc:9000"
- name: OPENSEARCH_URL
  value: "opensearch-service.{{ .Values.global.services_namespace }}.svc:9200"
- name: DICOM_WEB_FILTER_URL
  value: "http://dicom-web-filter-service.{{ .Values.global.services_namespace }}.svc:8080"
- name: NOTIFICATION_URL
  value: "http://notification-service.{{ .Values.global.services_namespace }}.svc:80"
- name: AII_URL
  value: "http://aii-service.{{ .Values.global.services_namespace }}.svc:8080"
- name: KAAPANA_BACKEND_URL
  value: "http://kaapana-backend-service.{{ .Values.global.services_namespace }}.svc:5000"
- name: MINIO_URL
  value: "http://minio-service.{{ .Values.global.services_namespace }}.svc:9000"
{{- end }}

{{- define "airflow.env.taskRuntime" }}
- name: GPU_SUPPORT
  value: "{{ .Values.global.gpu_support }}"
- name: MODELDIR
  value: "{{ .Values.global.fast_data_dir }}/workflows/models"
- name: PROXY
  value: "{{ .Values.global.http_proxy }}"
- name: http_proxy
  value: "{{ .Values.global.http_proxy }}"
- name: https_proxy
  value: "{{ .Values.global.http_proxy }}"
- name: no_proxy
  value: ".svc,.svc.cluster,.svc.cluster.local,{{ .Values.global.hostname }}"
- name: SMTP_HOST
  value: "{{ .Values.global.smtp_host }}"
- name: SMTP_PORT
  value: "{{ .Values.global.smtp_port }}"
- name: EMAIL_ADDRESS_SENDER
  value: "{{ .Values.global.email_address_sender }}"
- name: SMTP_USERNAME
  value: "{{ .Values.global.smtp_username }}"
- name: SMTP_PASSWORD
  value: "{{ .Values.global.smtp_password }}"
- name: KAAPANA_PROJECT_USER_NAME
  value: "system"
{{- end }}
