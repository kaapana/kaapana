#https://github.com/pieper/SlicerDockers/blob/master/slicer-plus/install-slicer-extension.py
#import os
#extensionName = os.environ['EXTENSION_TO_INSTALL']

# order matters!
for extensionName in ['DCMQI', 'PETDICOMExtension', \
    'SlicerDevelopmentToolbox', 'DICOMwebBrowser', 'QuantitativeReporting']:
    print(f"installing {extensionName}")
    manager = slicer.app.extensionsManagerModel()
    if not manager.isExtensionInstalled(extensionName):
      extensionMetaData = manager.retrieveExtensionMetadataByName(extensionName)
      url = f"{manager.serverUrl().toString()}/api/v1/item/{extensionMetaData['_id']}/download"
      extensionPackageFilename = slicer.app.temporaryPath+'/'+extensionMetaData['_id']
      slicer.util.downloadFile(url, extensionPackageFilename)
      manager.installExtension(extensionPackageFilename)
exit()

