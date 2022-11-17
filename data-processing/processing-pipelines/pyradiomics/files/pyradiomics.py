import json
import os
from functools import partial
from pathlib import Path
from typing import List

import nibabel as nib
import numpy as np
from p_tqdm import p_map

# Some code ist taken from here:
# https://github.com/wasserth/TotalSegmentator/blob/6be46c65652265429ed95c34c42c2f368910783f/totalsegmentator/statistics.py

def get_radiomics_features(seg_file, img_file="ct.nii.gz"):
    from radiomics import featureextractor

    standard_features = [
        'shape_Elongation', 'shape_Flatness', 'shape_LeastAxisLength', 'shape_MajorAxisLength',
        'shape_Maximum2DDiameterColumn', 'shape_Maximum2DDiameterRow', 'shape_Maximum2DDiameterSlice',
        'shape_Maximum3DDiameter', 'shape_MeshVolume', 'shape_MinorAxisLength', 'shape_Sphericity',
        'shape_SurfaceArea', 'shape_SurfaceVolumeRatio', 'shape_VoxelVolume',
        'firstorder_10Percentile', 'firstorder_90Percentile', 'firstorder_Energy',
        'firstorder_Entropy', 'firstorder_InterquartileRange', 'firstorder_Kurtosis',
        'firstorder_Maximum', 'firstorder_MeanAbsoluteDeviation', 'firstorder_Mean',
        'firstorder_Median', 'firstorder_Minimum', 'firstorder_Range',
        'firstorder_RobustMeanAbsoluteDeviation', 'firstorder_RootMeanSquared', 'firstorder_Skewness',
        'firstorder_TotalEnergy', 'firstorder_Uniformity', 'firstorder_Variance',
        'glcm_Autocorrelation', 'glcm_ClusterProminence', 'glcm_ClusterShade', 'glcm_ClusterTendency',
        'glcm_Contrast', 'glcm_Correlation', 'glcm_DifferenceAverage', 'glcm_DifferenceEntropy',
        'glcm_DifferenceVariance', 'glcm_Id', 'glcm_Idm', 'glcm_Idmn', 'glcm_Idn', 'glcm_Imc1',
        'glcm_Imc2', 'glcm_InverseVariance', 'glcm_JointAverage', 'glcm_JointEnergy',
        'glcm_JointEntropy', 'glcm_MCC', 'glcm_MaximumProbability', 'glcm_SumAverage',
        'glcm_SumEntropy', 'glcm_SumSquares', 'gldm_DependenceEntropy', 'gldm_DependenceNonUniformity',
        'gldm_DependenceNonUniformityNormalized', 'gldm_DependenceVariance',
        'gldm_GrayLevelNonUniformity', 'gldm_GrayLevelVariance', 'gldm_HighGrayLevelEmphasis',
        'gldm_LargeDependenceEmphasis', 'gldm_LargeDependenceHighGrayLevelEmphasis',
        'gldm_LargeDependenceLowGrayLevelEmphasis', 'gldm_LowGrayLevelEmphasis',
        'gldm_SmallDependenceEmphasis', 'gldm_SmallDependenceHighGrayLevelEmphasis',
        'gldm_SmallDependenceLowGrayLevelEmphasis', 'glrlm_GrayLevelNonUniformity',
        'glrlm_GrayLevelNonUniformityNormalized', 'glrlm_GrayLevelVariance',
        'glrlm_HighGrayLevelRunEmphasis', 'glrlm_LongRunEmphasis',
        'glrlm_LongRunHighGrayLevelEmphasis', 'glrlm_LongRunLowGrayLevelEmphasis',
        'glrlm_LowGrayLevelRunEmphasis', 'glrlm_RunEntropy', 'glrlm_RunLengthNonUniformity',
        'glrlm_RunLengthNonUniformityNormalized', 'glrlm_RunPercentage', 'glrlm_RunVariance',
        'glrlm_ShortRunEmphasis', 'glrlm_ShortRunHighGrayLevelEmphasis',
        'glrlm_ShortRunLowGrayLevelEmphasis', 'glszm_GrayLevelNonUniformity',
        'glszm_GrayLevelNonUniformityNormalized', 'glszm_GrayLevelVariance',
        'glszm_HighGrayLevelZoneEmphasis', 'glszm_LargeAreaEmphasis',
        'glszm_LargeAreaHighGrayLevelEmphasis', 'glszm_LargeAreaLowGrayLevelEmphasis',
        'glszm_LowGrayLevelZoneEmphasis', 'glszm_SizeZoneNonUniformity',
        'glszm_SizeZoneNonUniformityNormalized', 'glszm_SmallAreaEmphasis',
        'glszm_SmallAreaHighGrayLevelEmphasis', 'glszm_SmallAreaLowGrayLevelEmphasis',
        'glszm_ZoneEntropy', 'glszm_ZonePercentage', 'glszm_ZoneVariance', 'ngtdm_Busyness',
        'ngtdm_Coarseness', 'ngtdm_Complexity', 'ngtdm_Contrast', 'ngtdm_Strength'
    ]

    try:
        if len(np.unique(nib.load(seg_file).get_fdata())) > 1:
            settings = {
                "resampledPixelSpacing": [3, 3, 3],
                "geometryTolerance": 1e-3,
                "featureClass": ["shape"]
            }
            extractor = featureextractor.RadiomicsFeatureExtractor(**settings)
            extractor.disableAllFeatures()
            extractor.enableFeatureClassByName("shape")
            extractor.enableFeatureClassByName("firstorder")
            features = extractor.execute(str(img_file), str(seg_file))

            features = {k.replace("original_", ""): v for k, v in features.items() if k.startswith("original_")}
        else:
            print("WARNING: Entire mask is 0 or 1. Setting all features to 0")
            features = {feat: 0 for feat in standard_features}
    except Exception as e:
        print(f"WARNING: radiomics raised an exception (settings all features to 0): {e}")
        features = {feat: 0 for feat in standard_features}

    features = {k: round(float(v), 4) for k, v in features.items()}  # round to 4 decimals and cast to python float

    return seg_file.name.split(".")[0], features


def get_radiomics_features_for_entire_dir(ct_file: Path, mask_dir: Path, file_out: Path):
    masks = sorted(list(mask_dir.glob("*.nii.gz")))
    stats = p_map(partial(get_radiomics_features, img_file=ct_file),
                  masks, num_cpus=1, disable=False)
    stats = {mask_name: stats for mask_name, stats in stats}
    with open(file_out, "w") as f:
        json.dump(stats, f, indent=4)


batch_folders: List[Path] = sorted([*Path('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME']).glob('*')])

for batch_element_dir in batch_folders:

    element_input_dir = batch_element_dir / os.environ['OPERATOR_IN_DIR']
    element_output_dir = batch_element_dir / os.environ['OPERATOR_OUT_DIR']
    segmentation_input_dir = batch_element_dir / os.environ['OPERATOR_IN_SEGMENATIONS_DIR']

    element_output_dir.mkdir(exist_ok=True)
    # The processing algorithm
    print(
        f'Computing radiomics for nifit files in {str(element_input_dir)} '
        f'and writing results to {str(element_output_dir)}'
    )

    if len([*segmentation_input_dir.glob("*.nii.gz")]) == 0:
        print("No segmentations found!")
        exit(0)
    else:
        print(f"# running pyradiomics")
        try:
            input_file = [*element_input_dir.glob('*.nii.gz')][0]
            get_radiomics_features_for_entire_dir(
                input_file,
                segmentation_input_dir,
                element_output_dir / input_file.name.replace('.nii.gz', '.json')
            )
        except Exception as e:
            print("Processing failed with exception: ", e)
