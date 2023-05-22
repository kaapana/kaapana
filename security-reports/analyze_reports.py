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
        default=None,
        required=False,
        help="Plattform version: e.g.: 0.1.3-591-g6426ef53",
    )
    parser.add_argument(
        "-p",
        "--python",
        action="store_true",
        dest="python",
        default=False,
        help="Analyze python reports",
    )
    parser.add_argument(
        "-d",
        "--description",
        action="store_true",
        dest="description",
        default=False,
        help="Print description",
    )
    
    args = parser.parse_args()

    tag = args.tag
    python = args.python
    description = args.description

    # load report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), tag + "_compressed_vulnerability_report.json")

    if not os.path.exists(report_path):
        logger.error(f"Report {report_path} does not exist")
        exit(1)

    with open(report_path, "r") as f:
        reports = json.load(f)

    logger.info(f"Found {len(reports)} reports: ")
    for module in reports:
        print("---")
        print(module)
        print("")
        for issue in reports[module]:
            if issue == "Python":
                print(issue)
                print(reports[module][issue])
        print("---")