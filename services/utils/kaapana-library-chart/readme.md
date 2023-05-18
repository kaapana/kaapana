# kaapana-library-chart

The chart provides a collection of useful snippets. To make them available in your chart you need to add them as dependency in the requirements.yaml to chart that is installed:

    ---
    dependencies:
    - name: kaapana-library-chart
      version: 0.0.0
      repository: file://<relativ path to your chart>

where the repository is only needed in case you want to debug your helm chart (see section below).

To use snippets for persisent volumes do the following:
1. Add a global.dynamicVolumes object to the values.yaml, e.g.:


        dynamicVolumes:
        - name: hello-world
          mount_path: /kaapana/mounted/hello-world
          host_path: /hello-world
          storage: "1Mi"

    Depending of which template you use, more or less values are required. For usage inside the development the name of the persisent volume is created by appending pv-claim to the name: e.g. hello-world-pv-claim.  

2. Create a file called persistent_volumes.yaml with the following content:

        {{ include "dynamicPersistentVolumes" $ }}

    This will render the template inside your persistent volume

3. If your extensions uses a namespace different than the services_namespace, you will need to define the namespace also in your value.yaml:

        namespace: "{{ .Values.global.services_namespace }}"

4. In your deployment you can make use of the "dynamicVolumeMounts" template and the "dynamicVolumes":

                volumeMounts:
        {{ include "dynamicVolumeMounts" $ | indent 10 }}
            volumes:
        {{ include "dynamicVolumes" $ | indent 6 }}

    or add the persistent volumes in the normal way:


            volumeMounts:
            - name: hello-world-data
            mountPath: "kaapana/mounted/hello-world
        volumes:
        - name: hello-world-data
            persistentVolumeClaim:
            claimName: hello-world-pv-claim

5. Do check if everything looks correct you can use inside of your helm-chart directory

        helm install --dry-run --debug .
        helm template .
