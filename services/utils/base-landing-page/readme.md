
# Landing-page development setup

1. Start kaapana
2. Go to `services/utils/base-landing-page/Dockerfile` and uncomment the `Dev` part.
3. Build the Dockerfile and push it to the registry. Don't forget to tag it.
   `docker build -t <registry>/base-landing-page:0.1.3-dev .`
   `docker push <registry>/base-landing-page:0.1.3-dev`
4. Replace `services/base/landing-page-kaapana/landing-page-kaapana-chart/templates/deployments.yaml` by the following:
   ```
   kind: Deployment
   apiVersion: apps/v1
   metadata:
    name: landingpage
    namespace: base
    labels:
     k8s-app: landingpage
   spec:
    replicas: 1
    selector:
     matchLabels:
      app-name: landingpage
    template:
     metadata:
      labels:
       app-name: landingpage
     spec:
      containers:
      - name: landingpage
       image: <registry>/base-landing-page:0.1.3-dev
       imagePullPolicy: Always
       command:
       - sh
       args:
       - dev.sh
       ports:
       - name: landing-http
        containerPort: 5000
       livenessProbe:
        httpGet:
         path: /
         port: landing-http
        initialDelaySeconds: 10
        periodSeconds: 20
       resources:
        requests:
         memory: 10Gi
        limits:
         memory: 10Gi
       volumeMounts:
        - name: common-data-file
         mountPath: /app/jsons
        - name: landing-dev-files
         mountPath: /landing/app/src
      volumes:
      - name: common-data-file
       configMap:
        name: landing-page-config
      - name: landing-dev-files
       hostPath:
        path: /path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src
        type: DirectoryOrCreate
      imagePullSecrets:
      - name: registry-secret
    ```
5. Within the just replaced `deployment.yaml`, adjust the following parameters:
  - `spec.containers.image` : `<registry>/base-landing-page:0.1.3-dev`
  - `spec.template.volumes.hostpath.path`:  `/path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src`
6. Run `kubectl apply -f deployment.yaml`
7. Sanity check: Any changes in `/path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src` should (almost) instantly update in the browser.

