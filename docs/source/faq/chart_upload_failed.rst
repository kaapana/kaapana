.. _extension_chart_upload_fail:

Chart Upload Failed
*******************

The upload component only accepts valid `.tgz` files for charts. If the issue is due to an unsupported file type, check the webpage console logs for more information.

Additionally, if any Kubernetes resource inside the Helm package is configured to run under the `admin` namespace, the platform will raise an error. By default, this is not allowed.

If the issue persists, check the logs by going to `<hostname>/kubernetes/#/pod?namespace=admin` and searching for the pod named `kube-helm-deployment-<random-id>`.

