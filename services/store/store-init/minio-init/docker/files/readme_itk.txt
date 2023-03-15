Put your dataset inside the minio bucket uploads/itk as follows:

        path
        |----dataset
        |    | meta_data.json
        |    | seg_info.json
        |    | series1.nii.gz
        |    | series1_seg.nii.gz
        |    | series2.nii.gz
        |    | series2_seg.nii.gz
        |    | ...

        The meta_data.json can be used to set values for patient ids, study uids, series ids and also arbitrary dicom tags. The expected structure is as follows:
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

        Good to know:
        - Unique identifier for series: study_id, parent folder_name and filename!
        - Enforce same study instance uid by specifying the study_id (0020|0010)!

        All fields are optional, but it is highly recommended, to at least set the modality since the default is set to "OT" i.e. "Other" which will omit necessary positioning data for image processing.
        The field "add_tags" allows to set specific tags on all series matching the given file name pattern. At the moment this is just a simple glob pattern matching.
        If needed we could also add regex syntax here, but for now this seems unnecessarily complex.

        The 'seg_args' parameter passes arguments to the Itk2DcmSegOperator which is responsible for the conversion of the segmentation objects if any are present.
        If there are no segmentation files 'seg_args' will be ignored.