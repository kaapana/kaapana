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

The directory of the project bucket that was selected when the application was launched is mounted at `/kaapana/minio`.
Files are read from and written to MinIO directly, nothing is copied in advance:

* Files saved here are in MinIO as soon as they are written.
* Changes made in MinIO (e.g. by a workflow) appear here after up to 30 seconds; refresh the explorer to see them.


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