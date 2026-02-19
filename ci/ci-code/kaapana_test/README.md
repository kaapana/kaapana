# kaapana_test

**kaapana_test** is an automated testing package for the [Kaapana](https://github.com/kaapana/kaapana) platform. It provides networking, access, extension, workflow and data tests as well as utilities for authentication and browser automation, to ensure the reliability and correctness of Kaapana deployments.

---

## Features

- **Integration Tests:** Validate core workflows and data flows in Kaapana.
- **Extension Tests:** Automate installation and verification of Kaapana extensions.
- **Port Scanning:** Check open ports and network accessibility.
- **Authentication Utilities:** Automate login and session management.
- **Playwright Automation:** Browser-based testing using Playwright.
- **Test Data Management:** Includes sample datasets and extension parameters.

---

## Directory Structure

```
kaapana_test/
  ├── data.py
  ├── extensions.py
  ├── login.py
  ├── scan_ports.py
  ├── workflows.py
  └── utils/
      ├── KaapanaAuth.py
      ├── KaapanaPlaywrightDriver.py
      └── logger.py
data/
  ├── extension_params.json
  └── download-info/
tests/
  ├── conftest.py
  ├── test_first_login.py
  ├── test_install_extensions.py
  ├── test_integration_tests.py
  ├── test_scan_ports.py
  └── test_send_data.py
```

---

## Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/kaapana/kaapana.git
cd kaapana/ci/ci-code/kaapana_test
pip install -r requirements.txt
```

> **Note:** Make sure you have Python 3.8+ and [Playwright](https://playwright.dev/python/) installed.

---

## Usage

### Test Variables

There are multiple test variables defined in the `conftest.py`, that can be set and have reasonable defaults. Consult `conftest.py` to see the fixtures. Those are used in the tests automatically. You can set those variables in various ways:

**Ways to set variables:**
- **CLI:** Pass as pytest arguments, e.g. `pytest --host=http://...`
- **Environment:** Export before running, e.g. `export HOST=http://...`
- **Defaults:** If not set, auto-detected or fallback values are used.

**Tip:** For manual runs, set variables at the top of `start_tests_manually.sh` or export them in your shell.

### Run All Tests

From the `kaapana_test` directory, run:

```bash
pytest tests/
```

### Run a Specific Test

```bash
pytest tests/test_first_login.py
```

### Manually Start Tests

```bash
bash tests/start_tests_manually.sh
```

---

## Configuration

- **Authentication:** Update credentials in your environment or via test fixtures.
- **Test Data:** Place additional test data in `data/download-info/`.
- **Extension Parameters:** Configure extension installation via `data/extension_params.json`.
- **Workflows:** Add `config-ci` into your chart directory
---

## Utilities

- `utils/KaapanaAuth.py`: Handles authentication and session tokens.
- `utils/KaapanaPlaywrightDriver.py`: Playwright browser automation helpers.
- `utils/logger.py`: Logging utilities for test runs.