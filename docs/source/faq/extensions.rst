.. _faq_extensions:

.. _failed_to_install:

Failed to Install or Launch an Extension
****************************************

If you encounter this issue, follow these steps:

1. Wait for approximately 30 seconds to see if the page updates. The overall extension list is refreshed every 30 seconds.

2. If there are still no updates, it indicates a possible installation failure. To further debug, check the console logs in the frontend. However, the main information is likely in the logs of the kube-helm pod. To access these logs:

    a. Go to `<hostname>/kubernetes/#/pod?namespace=admin`.

    b. Look for the pod named `kube-helm-deployment-<random-generated-id>`.

    c. Click on the pod name and find the "View Logs" button on the upper right side of the screen. Download the log file to access all logs.

3. One possible cause of the issue might be a failed `hook` during installation or a previous uninstallation, which leaves a helm release in an uninstallable state. To check charts in such states, run the following command:

   ::
   
       helm ls --uninstalling --pending --failed

4. To delete, use the following command:

   ::
   
       helm uninstall <release-name>

5. If the release still persists, run the command explicitly with the `no-hooks` option:

   ::
   
       helm uninstall --no-hooks <release-name>


.. _failed_to_uninstall:

Failed to Uninstall or Delete an Extension
******************************************

Follow the same steps as for the installation failure. Check the logs and run the same commands to manually uninstall the extension. It is also possible to force uninstall an extension if it is stuck in a Pending state.

.. _extension_not_available:

No Extensions Available
***********************

If there are no extensions available on the frontend, it is possible that the folder `<FAST_DATA_DIR>/extensions` is empty. To resolve this issue, try the following:

1. Click on the cloud refresh icon next to the **Applications and Workflows** title. This fetches all the chart files inside the Kaapana extension collection.

2. Wait for a minute or so. The extensions should now be visible on the webpage.

.. _extension_stuck:

Extensions Page Stuck in Loading
********************************

This issue is most likely due to having too many `.tgz` files in the extensions folder `<FAST_DATA_DIR>/extensions`. This can occur if the platform is redeployed with multiple versions consecutively. If different versions exist for many extensions, it may take a long time to gather all the information. 
To resolve this issue, manually delete some of the unused older versions of chart files.

Note that there is no hard limit for the number of extensions or versions that will cause this issue. It will vary based on the state of resources for every instance.

.. _extension_chart_upload_fail:

Chart Upload Failed
*******************

The upload component only accepts valid `.tgz` files for charts. If the issue is due to an unsupported file type, check the webpage console logs for more information.

Additionally, if any Kubernetes resource inside the Helm package is configured to run under the `admin` namespace, the platform will raise an error. By default, this is not allowed.

If the issue persists, check the logs by going to `<hostname>/kubernetes/#/pod?namespace=admin` and searching for the pod named `kube-helm-deployment-<random-id>`.

.. _extension_container_upload_fail:

Container Upload Failed
***********************

The upload component only accepts valid `.tar` files for containers. If the issue is related to unsupported file types, check the browser console logs for more information.

If the upload completes to 100% but you can not access the container, it is possible that the import is failed. Check logs on the browser once again and see if "import failed" error message exists.

Otherwise, the backend service logs should be checked via accessing `<hostname>/kubernetes/#/pod?namespace=admin` and looking for the pod `kube-helm-deployment-<random-id>`.

If it is possible to access a terminal by an admin user, the following steps can be followed:

1. check if the container is imported into microk8s ctr correctly via  :code:`microk8s ctr images ls | grep <image-tag>` and see if the image tag is listed there.
2. If the image is not listed, then manually import via :code:`microk8s ctr image import --digests <tar-file-path>` where :code:`<tar-file-path>` is :code:`FAST_DATA_DIR/extensions/<tar-file>`. 
