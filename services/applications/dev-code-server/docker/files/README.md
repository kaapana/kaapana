# Development Code Server Extension

This extension provides a VS Code Server environment within the Kaapana platform for Python and R development. Users can explore and analyze data directly within the platform.

## Overview

This extension is designed for users who need an interactive coding environment similar to JupyterLab, but with the additional flexibility of VS Code. It utilizes [`code-server`]([https://](https://github.com/coder/code-server)) to bring VSCode in the browser.

The environment includes:
* Python 3 and R support
* Preinstalled Python, R, and Jupyter extensions in VSCode
* AI autocomplete and chat that run inside the platform (see below)
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
* `Continue.continue` (AI assistant, pinned to 1.2.16)

## AI Autocomplete and Chat

The [Continue](https://continue.dev) extension uses the platform's shared Ollama service (`ollama-service` in the services namespace). No request leaves the platform, so it also works offline.

* **Autocomplete** (`qwen2.5-coder:1.5b`): suggestions appear as grey text while typing; accept with `Tab`. `Ctrl+Alt+Space` asks for one explicitly.
* **Chat, edit and apply** (`qwen2.5-coder:7b`): in the Continue sidebar.

The models run on the CPU and are shared by all users of the platform, so answers can take a few seconds.

The Continue sidebar is a web view, and web views only load when the browser trusts the platform's TLS certificate. If the sidebar stays empty, import the platform certificate into the browser:

```bash
microk8s.kubectl -n services get secret certificate -o jsonpath='{.data.tls\.crt}' | base64 -d > kaapana.crt
```

## Project Storage and Data Access

The MinIO folder of the project (that was selected while the extension is installed in the UI) is automatically mounted within the workspace.
It supports unilateral sync:

* Input data from MinIO: /kaapana/minio/input
* Output data to MinIO : /kaapana/minio/output
* Project MinIO bucket: project-<project_name>


## Known Limitations of The Environment
* JupyterLab VSCode Extension works as expected in Firefox, but in Chrome, Jupyter notebook cells may fail to render with a Service Worker SSL error:
```
Could not initialize webview: Error: Could not register service worker:
SecurityError: Failed to register a ServiceWorker for scope (...)
```
This is a known issue with `code-server`: https://github.com/coder/code-server/issues/3410

* The Jupyter extension does not automatically select the correct Python environment, therefore the users must manually choose `/opt/venv/bin/python` as the interpreter each time they open a notebook.

* The built-in AI chat/agent sidebar of newer `code-server` versions (not Continue) cannot be turned off via settings; it appears at the start and must be closed manually.

This is a known issue of `code-server`: https://github.com/coder/code-server/issues/754