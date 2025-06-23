.. _failed_to_install_extension:


Failed to Install or Uninstall an Extension
*******************************************

If you encounter this issue, follow these steps:

1. Wait for approximately 30 seconds to see if the page updates. The overall extension list is refreshed every 30 seconds.

2. If there are still no updates, it indicates a possible installation/uninstallation failure. To further debug, check the console logs in the frontend. However, the main information is likely in the logs of the kube-helm pod. To access these logs:

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

