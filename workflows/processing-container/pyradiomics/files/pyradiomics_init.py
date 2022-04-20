import os
from pathlib import Path
import SimpleITK as sitk

from radiomics import featureextractor, logger
import logging

logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# TODO: multiple labels for this and radiomics
# TODO: output file format

def setup_paths():
    try:
        workflow_dir = Path(os.environ["WORKFLOW_DIR"])
        batch_name = os.environ["BATCH_NAME"]
        input_dir = os.environ["OPERATOR_IN_DIR"]
        mask_dir = os.environ["MASK_OPERATOR_DIR"]
        output_dir = os.environ["OPERATOR_OUT_DIR"]
    except KeyError as e:
        logger.error("environment variable {0} could not be found".format(e))
        exit()

    for root, dirs, files in os.walk(workflow_dir, topdown=True):
        for name in files:
            logger.debug(os.path.join(root, name))
        for name in dirs:
            logger.debug(os.path.join(root, name))

    logger.debug("start pyradiomics operator with")
    logger.debug(f"{workflow_dir=}")
    logger.debug(f"{batch_name=}")
    logger.debug(f"{input_dir=}")
    logger.debug(f"{mask_dir=}")
    logger.debug(f"{output_dir=}")

    batch = workflow_dir / batch_name
    batch_names = [p for p in batch.iterdir()]
    batchp = batch_names[0]
    logger.debug(f"{batch_names=}")
    logger.debug(f"{batchp=}")

    inputp = batchp / input_dir
    maskp = batchp / mask_dir
    logger.debug(f"{batchp=}")
    logger.debug(f"{inputp=}")
    logger.debug(f"{maskp=}")

    return inputp, maskp, batchp, output_dir

if __name__ == "__main__":
    inputp, maskp, batchp, output_dir = setup_paths()

    base_img = list(inputp.glob("*.nrrd"))[0]
    masks = list(maskp.glob("*.nrrd"))

    for m in masks:
        mask_img_1 = [m for m in masks if "--1--" in m.name][0]

    assert mask_img_1.exists() and base_img.exists()

    base_img_path = "./" + str(base_img)
    mask_img_path = "./" + str(mask_img)

    logger.debug("pyradiomics img {0}".format(
        sitk.ReadImage(base_img_path))
    )
    logger.debug("pyradiomics mask {0}".format(
        sitk.ReadImage(mask_img_path))
    )

    settings = {}
    settings['binWidth'] = 25
    settings['resampledPixelSpacing'] = None
    settings['interpolator'] = sitk.sitkBSpline
    settings['correctMask'] = True

    extractor = featureextractor.RadiomicsFeatureExtractor(**settings)

    # Disable all classes except firstorder
    extractor.disableAllFeatures()

    # Only enable mean and skewness in firstorder
    extractor.enableFeaturesByName(firstorder=['Mean', 'Skewness'])

    logger.info("Calculating features")
    featureVector = extractor.execute(base_img_path, mask_img_path)

    _dir = batchp / output_dir
    logger.debug(f"{_dir=}")
    logger.debug(f"{mask_img.stem=}")

    os.mkdir(_dir)

    with open("{0}/{1}_pyradiomics.txt".format(str(_dir), mask_img.stem), "w") as f:
        for featureName in featureVector.keys():
            f.write("Computed {0}: {1}\n".format(
                featureName, featureVector[featureName])
            )

    logger.info("Pyradiomics operator completed")