#!/usr/bin/env python3
import argparse
import logging
import os
import json

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

logger.addHandler(c_handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--tag",
        dest="tag",
        default="0.2.6-181-g64481e7ab",
        required=False,
        help="Plattform version: e.g.: 0.1.3-591-g6426ef53",
    )
    args = parser.parse_args()

    tag = args.tag

    dir_path = os.path.dirname(os.path.realpath(__file__))

    # read json file
    with open(os.path.join(dir_path, f"{tag}_vulnerability_reports.json"), "r") as f:
        data = json.load(f)

    print(f"Number of modules: {len(data)}")

    for module in data:
        if "Results" not in data[module]:
            continue
        print(module)