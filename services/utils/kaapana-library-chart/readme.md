# kaapana-library-chart

The chart provides a collection of helm templates. To make them available in your chart you need to add them as dependency in the `requirements.yaml` to chart that is installed:

```yaml
---
dependencies:
- name: kaapana-library-chart
  version: 0.0.0
  repository: file://<relativ path to your chart> ### Only required, if you package the chart manually.
```
Note, that this entry in `requirements.yaml` is not necessary if the chart is used as a dependency in another chart that already depends on the kaapana-library-chart, i.e.
* Extensions that want to use any of the provided templates require this entry.
* Charts that are part of the kaapana-admin-chart or the kaapana-platform-chart can use the templates without specifying the kaapana-library-chart as a dependency.

The field `repository` is only required in case you want to debug your helm chart (see section below).

### Developing a new standalone chart 
To check if everything looks correct you can run the following commands inside your helm-chart directory

```bash
helm install --dry-run --debug .
helm template .
```

## Templates

### dynamicPersistentVolumes

To use the template for persisent volumes do the following:
1. Add a `global.dynamicVolumes` object to the values.yaml, e.g.:

```yaml
global:
  namespace: <namespace> ### The namespace in which the volume should live.
  dynamicVolumes:
  - name: hello-world
    mount_path: /kaapana/mounted/hello-world
    host_path: /hello-world
    storage: "1Mi" ### optional
    minior_mirror: true ### Used in combination with a minio-mirror container
```
Depending on which template you use, more or less values are required. 

2. Create a file called persistent_volumes.yaml with the following content:
```yaml
{{ include "dynamicPersistentVolumes" $ }}
```
This will render the template inside your persistent volume.

**Note:**
If `host_path` matches `"^(/minio|/dcm4che/dicom_data|/dcm4che/server_data)"` the volume will be mounted in the `SLOW_DATA_DIR`, otherwise in the `FAST_DATA_DIR`.

### dynamicVolumeMounts & dynamicVolumes

In your `deployment.yaml` you can make use of the `dynamicVolumeMounts` template and the `dynamicVolumes`:

```yaml
spec:
  template:
    spec:
      containers:
        - name: <container-name>
          volumeMounts:
{{ include "dynamicVolumeMounts" $ | indent 10 }}
      volumes:
{{ include "dynamicVolumes" $ | indent 6 }}
```

This will render the following parts correpsonding to the `hello-world` dynamicVolume.
```yaml
spec:
  template:
    spec:
      containers:
        - name: <container-name>
          volumeMounts:
            - name: hello-world-data
            mountPath: "kaapana/mounted/hello-world"
      volumes:
      - name: hello-world-data
          persistentVolumeClaim:
          claimName: hello-world-pv-claim
```

These template do **not** work for the `devPersistentVolumes` template.

### devPersistentVolumes

This template can be used to mount a volume from the host machine into a container.
This is usually used to develop backends and frontends without having to rebuild and redeploy a new image everytime the code was changed.
Just include the following into `values.yaml`

```yaml
global:
  dev_files: <false or path to the directory on the host machine that should be mounted>
admin: false ### Boolean that determines, if the PV and PVC should be created in "{{ .Values.global.admin_namespace }}" or "{{ .Values.global.services_namespace }}"
```

1. In `templates/persistent_volumes.yaml` include
```yaml
{{- if .Values.global.dev_files }}
---
{{ include "devPersistentVolumes" $ }}
{{- end }}
```

2. In `templates/deployment.yaml` include
```yaml
spec:
  template:
    spec:
      containers:
        - name: <container-name>
          volumeMounts:
{{- if .Values.global.dev_files }}
          - name: dev-volume
            mountPath: <path to mount in container>
{{- end }}
      volumes:
{{- if .Values.global.dev_files }}
      - name: dev-volume
        persistentVolumeClaim:
          claimName: {{ .Chart.Name }}-dev-pv-claim
{{- end }}
```

3. You can also adapt the command executed in your container to depend whether dev_files is set or not.
One way to do this is by adding an env variable to your container and adapt the command corresponding whether the variable is set or not.
```yaml
spec:
  template:
    spec:
      containers:
        - name: <container-name>
          env:
{{- if .Values.global.dev_files }}
          - name: DEV_FILES
            value: "True"
{{- end }}
```

### projectPersistentVolumes
This template is used in multiinstallable applications like jupyterlab or tensorboard.
The usage is the same as for `dynamicPersistentVolumes`.
The difference is that the `host_path` and `claimName` will automatically include the project context.

### dynamicEnvs & dynamicEnvsFromSecretRef & dynamicLabels

Used by the dev-server-chart to render env variables and labels that where parsed to the kube-helm-backend from the KaapanaBaserOperator to start a dev-server.



