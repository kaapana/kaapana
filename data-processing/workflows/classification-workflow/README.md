# Classification workflow

This directory contains the Task API version of the classification workflow. It provides two workflows:

- `classification-training` trains a ResNet18 classifier on tagged DICOM series.
- `classification-inference` tags DICOM series with a trained model.

Both workflows are packaged as one OCI extension for the experimental extension manager
(`classification-workflow-extension/`). The legacy version under
`data-processing/processing-pipelines/classification-workflow/` still exists.

## Build and install

The platform build only builds containers that a Helm chart references. This extension has no Helm chart, so a
platform build or release does not contain its containers. Build and push them by hand, then publish the
extension.

1. Build the five processing containers and push them to the registry of the platform. Use the same commit as the
   platform build, because the DAGs pull `<registry>/<image>:<platform build version>`.

   ```bash
   kaapana-build --default-registry <registry> \
     --containers-to-build classification-preprocessing-task \
     --containers-to-build classification-training-task \
     --containers-to-build classification-inference-task \
     --containers-to-build persist-model \
     --containers-to-build model-download
   ```

   The workflows also use `get-input-task` and `mitk-tools`. These containers are part of every platform build.

2. Build the extension and push it to an OCI registry with `extensionctl` (see `lib/kaapana_extensions/README.md`):

   ```bash
   extensionctl login --registry <url> --repo <repo> --user <user> --password <password>
   extensionctl build data-processing/workflows/classification-workflow/classification-workflow-extension --push
   ```

3. In the extension manager, add the registry under **Repositories**. Then install
   `classification-workflow-extension` from the **Catalog**.
