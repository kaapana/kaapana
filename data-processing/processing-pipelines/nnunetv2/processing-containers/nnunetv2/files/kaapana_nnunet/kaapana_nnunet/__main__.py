"""python -m kaapana_nnunet <step>   (the step can also come from NNUNET_STEP)"""

import importlib
import os
import sys

from kaapana_nnunet.context import main

STEPS = ("create_dataset", "plan_preprocess", "train", "find_best_config", "predict", "refresh", "harmonize")


def entry():
    step = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NNUNET_STEP", "")).replace("-", "_")
    if step not in STEPS:
        sys.exit(f"usage: python -m kaapana_nnunet {{{','.join(STEPS)}}}")
    module = importlib.import_module(f"kaapana_nnunet.steps.{step}")
    main(module.run)


if __name__ == "__main__":
    entry()
