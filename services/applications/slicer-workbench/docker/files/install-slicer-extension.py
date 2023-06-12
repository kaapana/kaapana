# https://github.com/Slicer/SlicerDocker/blob/10a8f38f6086f8d97a2a9cf81446974da2053001/slicer-notebook/install.sh#L41-L76
em = slicer.app.extensionsManagerModel()
for extensionName in [
    "DCMQI",
    "PETDICOMExtension",
    "SlicerDevelopmentToolbox",
    "DICOMwebBrowser",
    "QuantitativeReporting",
]:
    print(f"installing {extensionName}")
    if int(slicer.app.revision) >= 30893:
        # Slicer-5.0.3 or later
        em.updateExtensionsMetadataFromServer(True, True)
        if not em.downloadAndInstallExtensionByName(extensionName, True):
            raise ValueError(f"Failed to install {extensionName} extension")
        # Wait for installation to complete
        # (in Slicer-5.4 downloadAndInstallExtensionByName has a waitForComplete flag
        # so that could be enabled instead of running this wait loop)
        import time

        while not em.isExtensionInstalled(extensionName):
            slicer.app.processEvents()
            time.sleep(0.1)
    else:
        # Older than Slicer-5.0.3
        extensionMetaData = em.retrieveExtensionMetadataByName(extensionName)
        # Prevent showing popups for installing dependencies
        # (this is not needed right now for SlicerJupyter, but we still add this line here
        # because this docker image may be used by other projects as a starting point)
        em.interactive = False
        if slicer.app.majorVersion * 100 + slicer.app.minorVersion < 413:
            # Slicer-4.11
            itemId = extensionMetaData["item_id"]
            url = f"{em.serverUrl().toString()}/download?items={itemId}"
            extensionPackageFilename = f"{slicer.app.temporaryPath}/{itemId}"
            slicer.util.downloadFile(url, extensionPackageFilename)
        else:
            # Slicer-4.13
            itemId = extensionMetaData["_id"]
            url = f"{em.serverUrl().toString()}/api/v1/item/{itemId}/download"
            extensionPackageFilename = f"{slicer.app.temporaryPath}/{itemId}"
            slicer.util.downloadFile(url, extensionPackageFilename)
        em.installExtension(extensionPackageFilename)
exit()
