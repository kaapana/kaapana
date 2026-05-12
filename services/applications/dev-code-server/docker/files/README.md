# Development Code Server Extension

This extension provides a VS Code Server environment within the Kaapana platform for Python and R development. Users can explore and analyze data directly within the platform.

## Overview

This extension is designed for users who need an interactive coding environment similar to JupyterLab, but with the additional flexibility of VS Code. It utilizes [`code-server`](https://github.com/coder/code-server) to bring VS Code in the browser.

The environment is built for offline-capable deployments. A shared in-cluster
[Ollama](https://ollama.com) service provides AI-powered autocomplete and chat
via the [Continue](https://continue.dev) extension without any external
inference calls.

The environment includes:
* Python 3 and R support
* Preinstalled Python, R, Jupyter, and AI extensions in VS Code
* Cluster-local AI autocomplete and chat powered by Ollama + Continue
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

### R Environment

* Installed from the official CRAN repository
* Includes the languageserver package for IDE integration

### VS Code Extensions

Preinstalled extensions:

* `ms-python.python`
* `ms-toolsai.jupyter`
* `ms-toolsai.jupyter-keymap`
* `ms-toolsai.jupyter-renderers`
* `REditorSupport.r`
* `Continue.continue` — AI autocomplete and chat (pinned to v1.2.16)

## AI Autocomplete (Continue + Ollama)

The [Continue](https://continue.dev) extension connects to the shared
`ollama-service` in the `services` namespace and uses the
`qwen2.5-coder:7b` model for:

* **Inline autocomplete** — ghost-text suggestions appear as you type.
  Accept with `Tab`.
* **Manual trigger** — press `Ctrl+Alt+Space` to force an AI completion.
* **Chat / Edit / Apply** — use the Continue sidebar for interactive AI
  assistance.

All inference stays inside the Kaapana cluster; no external AI service is used.

### Browser Certificate Trust

The browser must trust the Kaapana platform TLS certificate. If the platform
certificate is untrusted, `code-server` webviews may fail to load and Continue
can appear broken even though the shared Ollama service is working.

The platform certificate can be exported from the cluster with:

```bash
microk8s.kubectl -n services get secret certificate -o jsonpath='{.data.tls\.crt}' | base64 -d > ~/kaapana.crt
```

Import `~/kaapana.crt` into the browser or OS trust store used by the browser.

## Project Storage and Data Access

The MinIO folder of the project (that was selected while the extension is installed in the UI) is automatically mounted within the workspace.
It supports bilateral sync to the folder /kaapana/minio/input


## Known Limitations

* **Jupyter in Chrome**: JupyterLab VS Code extension works as expected in
  Firefox, but in Chrome, notebook cells may fail to render with a Service
  Worker SSL error:
  ```
  Could not initialize webview: Error: Could not register service worker:
  SecurityError: Failed to register a ServiceWorker for scope (...)
  ```
  Known `code-server` issue: https://github.com/coder/code-server/issues/3410

* **Python interpreter**: The Jupyter extension does not automatically select
  the correct Python environment. Choose `/opt/venv/bin/python` as the
  interpreter each time a notebook is opened.

* **AI chat sidebar**: The chat panel introduced in newer `code-server`
  versions cannot be fully hidden via settings and must be closed manually.
  Known `code-server` issue: https://github.com/coder/code-server/issues/754

* **Browser clipboard**: Permission prompts may appear in certain
  browser/security setups. These affect copy/paste UX only and are unrelated
  to Continue model connectivity. The entrypoint disables the
  clipboard-based context snippet to prevent autocomplete hangs in the
  headless environment.
