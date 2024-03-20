from os import getenv

test_seg_exists = getenv("TEST_SEG_EXISTS", "None")
test_seg_exists = False if test_seg_exists.lower() == "false" else True

if test_seg_exists is True:
    from eval import run_eval
    run_eval()
else:
    from eval_nnunet_predict import run_eval_nnunet_predict
    print("running for nnunet_predict segmentations")
    run_eval_nnunet_predict()
