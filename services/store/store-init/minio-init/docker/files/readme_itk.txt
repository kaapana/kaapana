Put your dataset inside the minio bucket uploads/itk as follows:

        uploads/itk
        |----dataset1
        |    | meta_data.json
        |    | seg_info.json (optional)
        |    | series1.nii.gz
        |    | series1_seg.nii.gz
        |    | series2.nii.gz
        |    | series2_seg.nii.gz
        |    | ...


        The meta_data.json can be used to set values for patient ids, study uids, series ids and also arbitrary dicom tags. The expected structure is as follows:

        {
            'Patients': 'all_same' | 'all_different' | [name1, name2, ..., nameN],
            'Study UIDs': 'all_same' | 'all_different' | [study1, study2, ..., studyN],
            'Modality': 'MR' | 'CT' | 'OT' | ...   # any valid value listed under dicom tag (0008,0060) 
            'Series instance UID': [series_instance_uid1, series_instance_uid1, ..., series_instance_uidN]
            'Series descriptions': some_description | [desc1, desc2, ..., descN],
            
            'add_tags': {
                '/some/path/*nii.gz':{
                    '(xxxx|xxxx)': tag_value,
                    ...
                }
                
            }

            'seg_args': {
                'input_type': 'multi_label_seg' | 'single_label_segs',
                'single_label_seg_info': 'prostate',
                'multi_label_seg_info_json': 'seg_info.json'

            }

        }
        All fields are optional, but it is highly recommended, to at least set the modality since the default is set to "OT" i.e. "Other" which will omit necessary positioning data for image processing.
        The field "add_tags" allows to set specific tags on all series matching the given file name pattern. At the moment this is just a simple glob pattern matching.
        If needed we could also add regex syntax here, but for now this seems unnecessarily complex.

        The 'seg_args' parameter passes arguments to the Itk2DcmSegOperator which is responsible for the conversion of the segmentation objects if any are present.
        If there are no segmentation files 'seg_args' will be ignored.
