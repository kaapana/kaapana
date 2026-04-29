import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


WORKFLOW_DIR = Path(__file__).parents[1]
REPO_ROOT = WORKFLOW_DIR.parents[2]
TASK_API_PATH = REPO_ROOT / "lib" / "task_api"
CONTAINER_DIR = WORKFLOW_DIR / "processing-containers" / "wsi-fetcher"
PROCESSING_CONTAINER_JSON = CONTAINER_DIR / "processing-container.json"


def task_api_env():
    env = os.environ.copy()
    pythonpath = str(TASK_API_PATH)
    if env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath
    return env


def run_cli(args, cwd=None):
    return subprocess.run(
        ["python3", "-m", "task_api.cli", *args],
        cwd=cwd or REPO_ROOT,
        env=task_api_env(),
        capture_output=True,
        text=True,
    )


def skip_if_cli_dependencies_missing(testcase, result):
    missing_dependency_markers = (
        "ModuleNotFoundError: No module named 'dotenv'",
        "ModuleNotFoundError: No module named 'task_api'",
        "ModuleNotFoundError: No module named 'typer'",
        "ModuleNotFoundError: No module named 'pydantic'",
        "ModuleNotFoundError: No module named 'kubernetes'",
    )
    combined_output = result.stdout + result.stderr
    if any(marker in combined_output for marker in missing_dependency_markers):
        testcase.skipTest(
            "Task API CLI dependencies are not installed in this Python environment."
        )


def load_wsi_fetcher_template():
    processing_container = json.loads(PROCESSING_CONTAINER_JSON.read_text())
    for template in processing_container["templates"]:
        if template["identifier"] == "wsi-fetcher":
            return template
    raise AssertionError("wsi-fetcher task template not found")


class FetchWsiTaskApiCliTest(unittest.TestCase):
    def test_processing_container_json_validates_with_task_api_cli(self):
        result = run_cli(
            ["validate", str(PROCESSING_CONTAINER_JSON), "--schema", "pc"]
        )
        skip_if_cli_dependencies_missing(self, result)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("valid processing_container.json", result.stdout)

    def test_generated_task_json_validates_with_task_api_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            task_json = tmp_path / "task.json"
            task_json.write_text(
                json.dumps(
                    {
                        "name": "wsi-fetcher-offline-test",
                        "api_version": 1,
                        "image": "wsi-fetcher:test",
                        "taskTemplate": load_wsi_fetcher_template(),
                        "inputs": [],
                        "outputs": [
                            {
                                "name": "wsi",
                                "volume_source": {"host_path": str(tmp_path / "output")},
                            }
                        ],
                        "env": [
                            {"name": "WSI_SOURCE", "value": "filesystem"},
                            {
                                "name": "WORKFLOW_CONFIG_PATH",
                                "value": "/kaapana/mounted/wsi/conf.json",
                            },
                            {
                                "name": "WSI_INPUT_DIR",
                                "value": "/kaapana/mounted/wsi/source",
                            },
                        ],
                        "config": {"type": "docker"},
                    },
                    indent=2,
                )
            )

            result = run_cli(["validate", str(task_json), "--schema", "task"])
            skip_if_cli_dependencies_missing(self, result)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("valid task", result.stdout)

    def test_can_run_wsi_fetcher_task_with_task_api_cli_and_docker(self):
        image = os.getenv("WSI_FETCHER_IMAGE")
        if not image:
            self.skipTest(
                "Set WSI_FETCHER_IMAGE to a built wsi-fetcher image to run Docker CLI test."
            )
        if shutil.which("docker") is None:
            self.skipTest("Docker CLI is not installed.")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "output"
            source_dir = output_dir / "source"
            source_dir.mkdir(parents=True)
            (source_dir / "SLIDE_001.svs").write_bytes(b"svs")
            (output_dir / "conf.json").write_text(
                json.dumps({"slide_ids": ["SLIDE_001"]})
            )

            task_json = tmp_path / "task.json"
            task_run = tmp_path / "task_run.pkl"
            task_json.write_text(
                json.dumps(
                    {
                        "name": "wsi-fetcher-docker-test",
                        "api_version": 1,
                        "image": image,
                        "taskTemplate": load_wsi_fetcher_template(),
                        "inputs": [],
                        "outputs": [
                            {
                                "name": "wsi",
                                "volume_source": {"host_path": str(output_dir)},
                            }
                        ],
                        "env": [
                            {"name": "WSI_SOURCE", "value": "filesystem"},
                            {
                                "name": "WORKFLOW_CONFIG_PATH",
                                "value": "/kaapana/mounted/wsi/conf.json",
                            },
                            {
                                "name": "WSI_INPUT_DIR",
                                "value": "/kaapana/mounted/wsi/source",
                            },
                        ],
                        "config": {"type": "docker"},
                    },
                    indent=2,
                )
            )

            result = run_cli(
                [
                    "run",
                    str(task_json),
                    "--mode",
                    "docker",
                    "--watch",
                    "--output",
                    str(task_run),
                ],
                cwd=tmp_path,
            )
            skip_if_cli_dependencies_missing(self, result)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((output_dir / "SLIDE_001.svs").exists())
            manifest = json.loads((output_dir / "manifest.json").read_text())
            self.assertEqual(manifest["items"][0]["slide_id"], "SLIDE_001")


if __name__ == "__main__":
    unittest.main()
