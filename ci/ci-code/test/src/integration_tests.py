import unittest
from base_utils.utils_workflows import (
    CostumTestCase,
    collect_all_testcases,
    read_payload_from_yaml,
)
from argparse import ArgumentParser
from base_utils.logger import get_logger
import logging, os, sys

logger = get_logger(__name__, logging.DEBUG)


def parser():
    p = ArgumentParser(prog="API-workflow-tests")
    p.add_argument(
        "--test-dir",
        help="Directory of files with testcases",
        default="integration_tests/testcases/",
    )
    p.add_argument("--host", default=None, help="Host URL of the Kaapana instance.")
    p.add_argument(
        "--files",
        help="Collect testcases from a list of files instead of test_directory",
        nargs="*",
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="The client secret of the kaapana client in keycloak.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parser()
    host = args.host
    client_secret = args.client_secret or os.environ.get("CLIENT_SECRET", None)
    if not client_secret:
        logger.error(
            "A client secret has to be specified by command line flag or as environment variable CLIENT_SECRET"
        )
        sys.exit(1)

    if (files := args.files) and len(files) != 0:
        testcases = []
        for file in args.files:
            testcases += read_payload_from_yaml(file)
    else:
        testdir = os.path.join(os.getcwd(), args.test_dir)
        testcases = collect_all_testcases(testdir)

    testsuite = unittest.TestSuite()
    for testcase in testcases:
        if not testcase.get("ci_ignore_testcase", False):
            testsuite.addTest(CostumTestCase(testcase, host, client_secret))

    runner = unittest.TextTestRunner()
    runner.run(testsuite)
