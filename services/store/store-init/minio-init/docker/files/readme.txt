# Uploads buckets

All files and folders that you drop here are available for workflow execution.

### Convention for files and folders that should be converted to DICOM objects:

Put your dataset inside as zip file into the minio bucket uploads/itk as follows:

        path
        |----dataset
        |    | meta_data.json
        |    | seg_info.json
        |    | series1.nii.gz
        |    | series1_seg.nii.gz
        |    | series2.nii.gz
        |    | series2_seg.nii.gz
        |    | ...

or a Dataset directory structure of the nnU-Net (https://github.com/MIC-DKFZ/nnUNet) 

The meta_data.json can be used to set DICOM tags. The expected structure is as follows:

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

where global tags are written to all dicoms and series tags only to the specific file specified by the filename. 

In case of the Dataset directory structure of the nnU-Net, the file is created automatically based on the dataset.json.

Good to know:
- Unique identifier for series: study_id, parent folder_name and filename!
- Enforce same study instance uid by specifying the study_id (0020|0010)!