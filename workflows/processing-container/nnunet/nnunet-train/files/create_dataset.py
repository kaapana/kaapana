import sys, os
import glob
import json
import shutil
from pathlib import Path
import random

def move_file(source, target):
    Path(os.path.dirname(target)).mkdir(parents=True, exist_ok=True)
    if copy_target_data:
        shutil.copy2(source, target)
    else:
        shutil.move(source, target)

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    batches_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'])
    input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
    task_dir = os.path.join(output_dir, "nnUNet_raw_data", os.environ['TASK_ID'])

    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")
    print("Starting DatsetSplitOperator:")
    print("")

    if len(modality) != len(input_operators):
        print("")
        print("len(modality) != len(input_operators)")
        print("You have to specify {} input_operators!".format(len(modality)))
        print("Expected modalities:")
        print(json.dumps(modality, indent=4, sort_keys=True))
        print("")
        print("")
        exit(1)

    template_dataset_json = {
        "name": training_name,
        "description": training_description,
        "reference": training_reference,
        "licence": licence,
        "relase": version,
        "tensorImageSize": tensor_size,
        "modality": modality,
        "labels": labels,
        "numTraining": training_count,
        "numTest": test_count,
        "training": [],
        "test": []
    }

    series_list = [f.path for f in os.scandir(batches_input_dir) if f.is_dir()]
    series_list.sort()

    series_count = len(series_list)
    test_count = round((series_count/100)*test_percentage)
    train_count = series_count - test_count

    template_dataset_json["numTraining"] = train_count
    template_dataset_json["numTest"] = test_count

    print("")
    print("All series count:  {}".format(series_count))
    print("Train-datset-size: {}".format(train_count))
    print("Test-datset-size:  {}".format(test_count))
    print("")

    if (train_count + test_count) != series_count:
        print("Something went wrong! -> dataset-splits != series-count!")
        exit(1)

    print("Using shuffle-seed: {}".format(shuffle_seed))
    random.seed(shuffle_seed)
    random.shuffle(series_list)
    print("")

    train_series = series_list[:train_count]
    test_series = series_list[train_count:]

    for series in train_series:
        print("Preparing train series: {}".format(series))
        base_file_path = os.path.join("imagesTr", f"{os.path.basename(series)}.nii.gz")
        base_seg_path = os.path.join("labelsTr", f"{os.path.basename(series)}.nii.gz")

        for i in range(0, len(input_operators)):
            modality_nifti_dir = os.path.join(series, input_operators[i].operator_out_dir)

            modality_nifti = glob.glob(os.path.join(modality_nifti_dir, "*.nii.gz"), recursive=True)
            if len(modality_nifti) != 1:
                print("")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                print("Error with training image-file!")
                print("Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
                print("Expected only one file! -> abort.")
                print("")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                exit(1)

            target_modality_path = os.path.join(task_dir, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
            move_file(source=modality_nifti[0], target=target_modality_path)


        seg_dir=os.path.join(series, seg_input_operator.operator_out_dir)
        seg_nifti=glob.glob(os.path.join(seg_dir, "*.nii.gz"), recursive=True)
        if len(seg_nifti) != 1:
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            print("Error with training seg-file!")
            print("Found {} files at: {}".format(len(seg_nifti), seg_dir))
            print("Expected only one file! -> abort.")
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            exit(1)

        target_seg_path=os.path.join(task_dir, base_seg_path)
        move_file(source=seg_nifti[0], target=target_seg_path)

        template_dataset_json["training"].append(
            {
                "image": os.path.join("./", base_file_path),
                "label": os.path.join("./", base_seg_path)
            }
        )

    for series in test_series:
        print("Preparing test series: {}".format(series))
        base_file_path=os.path.join("imagesTs", f"{os.path.basename(series)}.nii.gz")
        base_seg_path=os.path.join("labelsTr", f"{os.path.basename(series)}.nii.gz")

        for i in range(0, len(input_operators)):
            modality_nifti_dir=os.path.join(series, input_operators[i].operator_out_dir)

            modality_nifti=glob.glob(os.path.join(modality_nifti_dir, "*.nii.gz"), recursive=True)
            if len(modality_nifti) != 1:
                print("")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                print("Error with test image-file!")
                print("Found {} files at: {}".format(len(modality_nifti), modality_nifti_dir))
                print("Expected only one file! -> abort.")
                print("")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print("")
                exit(1)

            target_modality_path=os.path.join(task_dir, base_file_path.replace(".nii.gz", f"_{i:04}.nii.gz"))
            move_file(source=modality_nifti[0], target=target_modality_path)


        # seg_dir = os.path.join(series, seg_input_operator.operator_out_dir)
        # seg_nifti = glob.glob(os.path.join(seg_dir, "*.nii.gz"), recursive=True)
        # if len(seg_nifti) != 1:
        #     print("")
        #     print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        #     print("")
        #     print("Error with test seg-file!")
        #     print("Found {} files at: {}".format(len(seg_nifti), seg_dir))
        #     print("Expected only one file! -> abort.")
        #     print("")
        #     print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        #     print("")
        #     exit(1)
        # target_seg_path = os.path.join(task_dir, base_seg_path)
        # move_file(source=seg_nifti[0], target=target_seg_path)

        template_dataset_json["test"].append(os.path.join("./", base_file_path))

    with open(os.path.join(task_dir, 'dataset.json'), 'w') as fp:
        json.dump(template_dataset_json, fp, indent=4, sort_keys=True)

print("#############################################################")
print("")
print("  Dataset preparation done!")
print("")
print("#############################################################")

