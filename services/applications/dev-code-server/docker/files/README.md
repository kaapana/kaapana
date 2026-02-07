# Development Code Server Extension

This extension provides a VS Code Server environment within the Kaapana platform for Python and R development. Users can explore and analyze data directly within the platform.

## Overview

This extension is designed for users who need an interactive coding environment similar to JupyterLab, but with the additional flexibility of VS Code. It utilizes [`code-server`]([https://](https://github.com/coder/code-server)) to bring VSCode in the browser.

⚠️ Note that this extension is intended to be used with online deployments. If the container can not access the internet, an `OFFLINE_WARNING.txt` will appear next to this `README.md` file.

The environment includes:
* Python 3 and R support
* Preinstalled Python, R, and Jupyter extensions in VSCode
* Access to the project’s MinIO storage
* Ability to install additional Python or R packages

## Preinstalled Components

### Python Environment

* Python version: 3.x (installed via Ubuntu python3-full)
* Virtual environment path: /opt/venv

Default packages:
* numpy
* pandas
* scipy
* matplotlib
* jupyterlab
* torch, torchvision, torchaudio

### R Environment

* Installed from the official CRAN repository
* Includes the languageserver package for IDE integration

### VS Code Extensions

Preinstalled extensions:

Extension
* `ms-python.python`
* `ms-toolsai.jupyter`
* `REditorSupport.r`
* `ms-toolsai.jupyter-keymap`
* `ms-toolsai.jupyter-renderers`

## Project Storage and Data Access

The MinIO folder of the project (that was selected while the extension is installed in the UI) is automatically mounted within the workspace.
It supports unilateral sync:

* Input data from MinIO: /kaapana/minio/input
* Output data to MinIO : /kaapana/minio/output
* Project MinIO bucket: project-<project_name>


## GPU Support

This code-server runs **without a dedicated GPU** to avoid blocking GPU resources while editing code. To run GPU workloads (training, inference, etc.), use the `gpu-run` command which launches a separate GPU-enabled job.

### Using gpu-run

The `gpu-run` command creates a Kubernetes Job with GPU access that runs your script using the same codebase:

```bash
# Run a Python training script
gpu-run train.py --epochs 10 --batch-size 32

# Run a script in a subdirectory
gpu-run scripts/inference.py --model weights.pth

# Run a shell script
gpu-run my_experiment.sh

# Run an R script
gpu-run analysis.R
```

### Managing GPU Jobs

```bash
# List all GPU jobs for this code-server
gpu-run --list

# View logs from a specific job
gpu-run --logs gpu-job-abc123

# Delete a specific job
gpu-run --delete gpu-job-abc123

# Clean up all completed jobs
gpu-run --clean

# Show help
gpu-run --help
```

### How it Works

1. When you run `gpu-run <script>`, it creates a Kubernetes Job with GPU access
2. The job uses the same container image and mounts the same workspace volume
3. Your script runs with full GPU access in the job's container
4. Output is streamed back to your terminal in real-time
5. The job is automatically cleaned up after completion (TTL: 10 minutes)

### Tips

- **Code changes**: Since the GPU job shares the same volume, any code changes you make in the code-server are immediately available to the GPU job
- **Output files**: Files written by the GPU job to `/kaapana/minio` will be visible in your code-server workspace
- **Multiple jobs**: You can run multiple GPU jobs in parallel (subject to GPU availability)
- **Long-running jobs**: If a job takes a long time, you can close the terminal and check on it later with `gpu-run --logs <job-name>`
- **Real-time output**: Python scripts run with `-u` (unbuffered) automatically; other programs use `stdbuf -oL` for line-buffered output, so logs stream in real time
- **Log files**: Every GPU job's output is saved to `/kaapana/minio/.gpu-logs/<job-name>.log` so you can review it later from the code-server workspace


## Known Limitations of The Environment
* JupyterLab VSCode Extension works as expected in Firefox, but in Chrome, Jupyter notebook cells may fail to render with a Service Worker SSL error:
```
Could not initialize webview: Error: Could not register service worker:
SecurityError: Failed to register a ServiceWorker for scope (...)
```
This is a known issue with `code-server`: https://github.com/coder/code-server/issues/3410

* The Jupyter extension does not automatically select the correct Python environment, therefore the users must manually choose `/opt/venv/bin/python` as the interpreter each time they open a notebook.

* The AI chat/agent sidebar introduced in newer `code-server` versions cannot currently be turned off via settings.
Even with configuration options such as:
```
"chat.disableAIFeatures": true,
"chat.agent.enabled": false
```

the panel still appears in the beginning and must be manually closed.

This is a known issue of `code-server`: https://github.com/coder/code-server/issues/754