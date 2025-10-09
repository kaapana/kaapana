.. _data_upload:

Data Upload
^^^^^^^^^^^

There are two ways of getting images into the platform either sending them directly via DICOM or uploading them via the web browser.

Option 1: Sending images via DICOM DIMSE (preferred)
"""""""""""""""""""""""""""""""""""""""""""""""""""""

Images can directly be send via DICOM DIMSE to the DICOM receiver port ``11112`` of the platform.
If you have images locally you can use e.g. `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_.
However, any tool that sends images to a DICOM receiver can be used. 

Here is an example of sending images with DCMTK:

.. code-block:: bash
 
  dcmsend -v <ip-address-or-hostname-of-server> 11112 --aetitle kp-<dataset-name> --call kp-<project-name> --scan-directories --scan-pattern '*.dcm' --recurse <data-dir-of-DICOM-images>

.. hint::
    | The `aetitle` is used to specify the :term:`dataset`. If the dataset already exist on the platform the new images will be appended.
    | The `call` is used to specify the :term:`project`. That project has to exist, use `admin` as a default.

.. note::
    Visit the :Code:`Data Upload` wizard page within the :code:`Workflows` menu of the Web interface to get command tailored to its deployment.

Option 2: Uploading images via the Web Interface (experimental)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

To upload images via the webfrontend, visit the :Code:`Data Upload` wizard page within the :code:`Workflows` menu of the Web interface. You can upload 
arbitrary data here and access and manage it via minio. Additionally you can import uploaded DICOM or NIfTI data into the internal *PACS*.

Dicom Data
''''''''''

DICOM data should be uploaded in a single compressed zip-file containing folder(s) with DICOM files. The default expected file-extension for DICOMs is 
:code:`.dcm`, but can be configured when triggering the :code:`import-dicoms-from-data-upload` workflow.

.. _import-uploaded-nifti-files:

.. note::
  When DICOM data is sent to the DICOM receiver of the platform multiple things happen:

  #. The incoming data is **saved to the local PACS**
  #. **Metadata** of the incoming data is stored in the OpenSearch index of the associated :term:`project` as well as the _admin_ project.
  #. Series-Project mappings are created for all incoming series to the associated :term:`project` and the _admin_ project.
  #. Thumbnails are generated for all series and stored in MinIO.
  #. The dicom data is validated. Validation warnings and errors are stored as metadata and visible in the Gallery View. HTML reports are stored in MinIO.


NIfTI data
''''''''''

NIfTI data will be converted to DICOM data before being imported into the internal PACS. The workflow for converting NIfTI data to DICOM and uploading it to PACS expects the NIfTI data to be structured in one of the following formats. 
The first format is referred to as the "basic format," while the second format is the " `nnUnetv2 <https://github.com/MIC-DKFZ/nnUNet>`_ data format."

In the basic format, it is assumed that you will place all your images with a unique identifier into a folder, along with the :code:`meta_data.json` file and, if necessary, the :code:`seg_info.json` file.

The basic format allows you to provide metadata for the images and, if applicable, for the segmentations. This additional information is provided within two JSON files:

.. code-block::

    meta-data.json
    seg-info.json




Example: Images without SEG:
////////////////////////////

If your data does not contain segmentations, the directory should be structured as follows:

.. code-block::

    ├───OnlyMRs
    │       Case00.nii.gz
    │       Case02.nii.gz
    │       Case03.nii.gz
    │       meta_data.json

An exemplary :code:`meta_data.json` could  look like this:

.. code-block::

    meta_data.json

        {
            "global_tags": {
                "0008|0060": "MR"
            },
            "series_tags": {
                "Case00.nii": {
                    "0008|103e": "I am unique"
                }
            }
        }

As shown in the example, the :code:`meta_data.json` file allows you to set DICOM tags for the entire dataset using the :code:`"global_tags"` field, and for each series using the :code:`"series_tags"`. The respective file path serves as the identifier.            

Images with SEGs:
/////////////////

If your data also contains segmentations, the import pipeline will convert them and associate them with their respective volumes. Metadata specific to the segmentations is provided by the :code:`seg_info.json` file. Here is a minimal example:

.. code-block::

    seg_info.json

        {
            "algorithm": "Ground truth",
            "seg_info": [
                {
                    "label_name": "prostate",
                    "label_int": "1"
                }
            ]   
        }

The :code:`"algorithm"` field specifies the algorithm or model used to create the segmentation. If the segmentation is provided by a clinician, use :code:`"Ground truth"` as the value. 
The :code:`"seg_info"` field is a list that contains segmentation information for each segmented region or organ. Each block in the :code:`"seg_info"` list includes the :code:`"label_name"` field, which specifies the name of the region or organ, 
and the :code:`"label_int"` field, which represents the respective integer in the segmentation file. If the segmentation includes multiple regions, you need to add a block to the :code:`"seg_info"` list for each region. You can use the following template as a basis:


.. code-block::

    seg_info_template.json (Todo check in code if this is all correct)

        {
            "task_body_part": "<optional - body part>",
            "algorithm": "<optional - algorithm name>",
            "seg_info": [
                {
                    "label_name": "<label 1 name>",
                    "label_int": "<label 1 encoding integer>"
                },
                {
                    "label_name": "<label 2 name>",
                    "label_int": "<label 2 encoding integer>"
                }

            ]
        }

You can use one of the following options to structure your data in a way that allows the parser to associate the cases with their respective segmentations:

.. code-block::

    Option One:

        ├───MRsWithSegmentationsSameFolder
        │       Case11.nii.gz
        │       Case11_segmentation.nii.gz
        │       Case12.nii.gz
        │       Case12_segmentation.nii.gz
        │       seg_info.json

    Option Two:

        ├───MRsWithSegmentationsTwoFolders
        │   │   seg_info.json
        │   │
        │   ├───cases
        │   │       Case03.nii.gz
        │   │       Case04.nii.gz
        │   │
        │   └───segs
        │           Case03.nii.gz
        │           Case04.nii.gz


Images in nnU-Net v2 formatting:
////////////////////////////////

Additonally to the described `basic` format, we also support the `nnU-Net v2` format that was build upon the `medical segmentation decathlon`. This file format combines segmentation meta-data and general meta-data within one file calles :code:`dataset.json`.

.. code-block::

    dataset.json

        {
            "description": "Left and right hippocampus segmentation",
            "file_ending": ".nii.gz",
            "labels": {
                "Anterior": 1,
                "Posterior": 2,
                "background": 0
            },
            "licence": "CC-BY-SA 4.0",
            "channel_names": {
                "0": "MRI"
            },
            "name": "Hippocampus",
            "numTraining": 260,
            "reference": " Vanderbilt University Medical Center",
            "relase": "1.0 04/05/2018"
        }


.. code-block::

    ├───Dataset004_Hippocampus
    │   │   dataset.json
    │   │
    │   ├───imagesTr
    │   │       hippocampus_001_0000.nii.gz
    │   │       hippocampus_003_0000.nii.gz
    │   │       hippocampus_004_0000.nii.gz
    │   │       hippocampus_006_0000.nii.gz
    │   │
    │   ├───imagesTs
    │   │       hippocampus_002_0000.nii.gz
    │   │       hippocampus_005_0000.nii.gz
    │   │       hippocampus_009_0000.nii.gz
    │   │       hippocampus_010_0000.nii.gz
    │   │
    │   └───labelsTr
    │           hippocampus_001.nii.gz
    │           hippocampus_003.nii.gz
    │           hippocampus_004.nii.gz
    │           hippocampus_006.nii.gz

.. hint::

    Please note that the :code:`nnU-Net v2` format is particularly suitable for importing data with multiple channels per case. However, it is important to mention that the :code:`basic` parser currently does not support this case.

If you want to import data with multiple channels per case, such as MRI data with FLAIR, T1w, T1gb, and T2w sequences, your data structure will look like this:

.. code-block::

    nnUNet_raw/Dataset001_BrainTumour/
    ├── dataset.json
    ├── imagesTr
    │   ├── BRATS_001_0000.nii.gz
    │   ├── BRATS_001_0001.nii.gz
    │   ├── BRATS_001_0002.nii.gz
    │   ├── BRATS_001_0003.nii.gz
    │   ├── BRATS_002_0000.nii.gz
    │   ├── BRATS_002_0001.nii.gz
    │   ├── BRATS_002_0002.nii.gz
    │   ├── BRATS_002_0003.nii.gz
    │   ├── ...
    ├── imagesTs
    │   ├── BRATS_485_0000.nii.gz
    │   ├── BRATS_485_0001.nii.gz
    │   ├── BRATS_485_0002.nii.gz
    │   ├── BRATS_485_0003.nii.gz
    │   ├── BRATS_486_0000.nii.gz
    │   ├── BRATS_486_0001.nii.gz
    │   ├── BRATS_486_0002.nii.gz
    │   ├── BRATS_486_0003.nii.gz
    │   ├── ...
    └── labelsTr
        ├── BRATS_001.nii.gz
        ├── BRATS_002.nii.gz
        ├── ...
