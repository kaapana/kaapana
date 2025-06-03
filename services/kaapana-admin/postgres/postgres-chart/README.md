# Kaapana postgres-chart

This chart packages a postgres deployment.

## Usage 

Add the following lines to the `requirements.yaml` file of the parent chart:

```yaml
---
dependencies:
  - name: kaapana_database
    version: 0.0.0
```

Add the following lines to the `values.yaml` file of your parent chart:

```yaml
kaapana_database:
  admin: false ### Whether the postgres deployment should run in the admin-namespace or the services-namespace
  postgres_user: <User of the postgres database>
  postgres_password: <Password of the postgres_user>
  postgres_db: <Name of the postgres_db>
  appName: <Value of app.kubernetes.io/name of the parent chart>
```

Note, that the Kubernetes service for the postgres database matches to pods with these two labels:
```yaml
spec:
  selector:
    app.kubernetes.io/name: {{ .Values.appName | default .Chart.Name }}
    app.kubernetes.io/component: database
```
Hence, Pods and Services in the parent chart should also use these both labels to match Pod and Service together.