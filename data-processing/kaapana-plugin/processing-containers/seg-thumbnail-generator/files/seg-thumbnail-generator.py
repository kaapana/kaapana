import os
from pathlib import Path

import SimpleITK as sitk
import numpy as np

def create_pngs(
        path_input_img: Path, path_input_seg: Path, path_output_dir: Path
):
    '''Create screenshot and save it for each label. Does not fail on all zero segs.'''
    # Read
    img = sitk.ReadImage(str(path_input_img))
    img_arr = sitk.GetArrayFromImage(img)
    seg = sitk.ReadImage(str(path_input_seg))
    seg_arr = sitk.GetArrayFromImage(seg)

    # Change voxels in 99 percentile to max_value
    percentile = np.percentile(img_arr, 99.9)
    print(f'Percentile chosen: {percentile}')
    img_arr[img_arr >= percentile] = percentile

    # Find relevant slice
    # Find indices where we have mass
    mass_x, mass_y, mass_z = np.where(seg_arr >= 1)
    # mass_x, mass_y, mass_z are the list of x indices and y indices of mass pixels
    cent_x = np.average(mass_x)
    cent_y = np.average(mass_y)
    cent_z = np.average(mass_z)
    # interesting slice is the one we want a picture of
    interesting_slice = round(cent_x) \
        if round(cent_x) <= len(seg_arr) - 1 \
        else len(seg_arr) - 1
    print(f'>> Slice to be used for screenshot: {interesting_slice}')
    # Slice image and seg accordingly
    img_arr_slice = img_arr[interesting_slice]
    seg_arr_slice = seg_arr[interesting_slice]
    # Create images
    img_slice = sitk.GetImageFromArray(img_arr_slice)
    seg_slice = sitk.GetImageFromArray(seg_arr_slice)
    # img to [0,255]
    img_slice_255 = sitk.Cast(
        sitk.IntensityWindowing(
            img_slice,
            windowMinimum=float(np.amin(img_slice)),
            windowMaximum=float(np.amax(img_slice)),
            outputMinimum=0.0,
            outputMaximum=200.0
        ),
        sitk.sitkUInt8
    )
    # segmentation to contour
    seg_slice_contour = sitk.LabelContour(seg_slice, fullyConnected=True)
    # Overlay the segmentation using default color map and an alpha value
    res_img = sitk.LabelOverlay(
        image=img_slice_255,
        labelImage=seg_slice_contour,
        opacity=0.8, backgroundValue=0
    )
    # Save
    output_path = os.path.join(
        path_output_dir,
        f'{path_input_seg.name.replace(".nii.gz", "")}.png'
    )
    print(f'Writing file {output_path}')
    sitk.WriteImage(res_img, output_path)

    # Save all slices
    all_slices_with_annotations = list(set(mass_x.tolist()))
    for sl in all_slices_with_annotations:
        img_slice = sitk.GetImageFromArray(img_arr[sl])
        seg_slice = sitk.GetImageFromArray(seg_arr[sl])
        # img to [0,255]
        img_slice_255 = sitk.Cast(
            sitk.IntensityWindowing(
                img_slice,
                windowMinimum=float(np.amin(img_slice)),
                windowMaximum=float(np.amax(img_slice)),
                outputMinimum=0.0,
                outputMaximum=200.0
            ),
            sitk.sitkUInt8
        )
        # segmentation to contour
        seg_slice_contour = sitk.LabelContour(
            seg_slice,
            fullyConnected=True
        )
        # Overlay the segmentation using default color map and an alpha value
        res_img = sitk.LabelOverlay(
            image=img_slice_255,
            labelImage=seg_slice_contour,
            opacity=0.8,
            backgroundValue=0.5
        )
        # Save
        output_path = os.path.join(
            path_output_dir,
            f'{path_input_seg.name.replace(".nii.gz", "")}_{sl}.png'
        )
        print(f'Writing file {output_path}')
        sitk.WriteImage(res_img, output_path)


if __name__ == "__main__":
    batch_folders = [*Path(os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"]).glob('*')]

    for batch_element_dir in batch_folders:
        seg_element_input_dir = batch_element_dir / os.environ['OPERATOR_IN_DIR']
        orig_element_input_dir = batch_element_dir / os.environ['ORIG_IMAGE_OPERATOR_DIR']
        element_output_dir = batch_element_dir / os.environ['OPERATOR_OUT_DIR']

        element_output_dir.mkdir(exist_ok=True)

        orig_input_element = list(orig_element_input_dir.glob('*.nii.gz'))[0]
        seg_element = list(seg_element_input_dir.glob('*.nii.gz'))[0]

        # The processing algorithm
        print(
            f'Creating a segmentation thumbnail for input '
            f'{orig_input_element} and seg {seg_element}.'
        )

        create_pngs(
            orig_input_element,
            seg_element,
            element_output_dir
        )
