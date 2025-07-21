.. _extension_container_upload_fail:

Container Upload Failed
***********************

The upload component only accepts valid `.tar` files for containers. If the issue is related to unsupported file types, check the browser console logs for more information.

If the upload completes to 100% but you can not access the container, it is possible that the import is failed. Check logs on the browser once again and see if "import failed" error message exists.

Otherwise, the backend service logs should be checked via accessing `<hostname>/kubernetes/#/pod?namespace=admin` and looking for the pod `kube-helm-deployment-<random-id>`.

If it is possible to access a terminal by an admin user, the following steps can be followed:

1. check if the container is imported into microk8s ctr correctly via  :code:`microk8s ctr images ls | grep <image-tag>` and see if the image tag is listed there.
2. If the image is not listed, then manually import via :code:`microk8s ctr image import --digests <tar-file-path>` where :code:`<tar-file-path>` is :code:`FAST_DATA_DIR/extensions/<tar-file>`. 
