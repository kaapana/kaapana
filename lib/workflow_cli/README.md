# Kaapana Workflow CLI

Clean, modular CLI tool for creating, validating, and packaging Kaapana workflows.

## Installation

```bash
# From repository (development)
cd lib/workflow_cli

# Copy schemas first
python3 setup.py develop

# Then install
pip install -e .
```

The `setup.py develop` command copies schemas from workflow-api and shows a message during the process.

## Usage

### 1. Create New Workflow Template

```bash
workflow-cli create my-workflow --engine airflow
```

Supported engines: `airflow`

### 2. Validate Workflow

```bash
workflow-cli validate ./my-workflow

# Strict mode (warnings = errors)
workflow-cli validate ./my-workflow --strict
```

### 3. Package Workflow

```bash
# Requires Helm installed
workflow-cli package ./my-workflow

# With linting
workflow-cli package ./my-workflow --lint
```

## Schema Management

**Schemas are automatically copied during `pip install`** from:
- **Source:** `services/base/workflow-api/docker/files/app/schemas.py`
- **Destination:** `workflow_cli/schemas.py`

The `setup.py` automatically copies schemas during build, ensuring they stay in sync.

## Architecture

The CLI has three focused modules:

1. **generator.py** - Creates workflow templates
2. **validators.py** - Validates structure, metadata, UI forms
3. **packager.py** - Packages into Helm charts (requires helm)

All use simple, linear logic with intermediate variables for clarity.

## Development

```bash
# Format code
black workflow_cli/

# Type check
mypy workflow_cli/

# Run CLI
python -m workflow_cli.cli create test-workflow
```
