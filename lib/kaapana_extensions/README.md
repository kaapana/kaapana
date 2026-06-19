# kaapana_extensions — OCI Extension Toolchain

A Python library and CLI for packaging, publishing, and consuming Kaapana extensions as OCI artifacts stored in any standard container registry.

## Installation

```bash
pip install -e lib/kaapana_containers
pip install -e lib/kaapana_extensions
```

The `extensionctl` command is available immediately after installation.

---

## Extension manifest

Every extension directory must contain an `extension_manifest.json` at its root:

```json
{
  "name": "my-extension",
  "id": "aaaaaaaa-0000-0000-0000-000000000001",
  "version": "1.0.0",
  "contents": [
    {
      "name": "my-workflow",
      "contentType": "workflow-v1",
      "files": [
        { "path": "workflow_definition.py" },
        { "path": "workflow.json" }
      ]
    }
  ]
}
```

- `name` — human-readable identifier, alphanumeric plus `-` and `_`.
- `id` — stable UUID used to derive the registry tag. Generated automatically on first local `build` and written back into the file — **commit it**. Required before pushing from a URL.
- `version` — semver string (`MAJOR.MINOR.PATCH`).
- `contents[].name` — name of the subfolder containing the content files.
- `contents[].files[].path` — file path **relative to the content subfolder**.

The on-disk layout matching the manifest above:

```
my-extension/
├── extension_manifest.json
└── my-workflow/
    ├── workflow_definition.py
    └── workflow.json
```

---

## CLI reference

All commands that talk to a registry accept `--registry`, `--repo`, `--user`, and `--password`. After running `extensionctl login` these are saved to `~/.kaapana/credentials.json` and can be omitted.

### Authentication

```bash
# Save credentials (required once before push/pull/list)
extensionctl login \
  --registry https://registry.example.com \
  --repo     kaapana/extensions \
  --user     myuser \
  --password mytoken

extensionctl whoami    # show active session
extensionctl logout    # clear saved credentials
```

---

### `build` — create a `.tar.gz` archive

Packages an extension directory into a distributable archive.
The archive name is always derived from the manifest: `<name>-v<version>.tar.gz`.

```bash
# Single extension directory
extensionctl build ./my-extension

# Write to a specific output directory
extensionctl build ./my-extension --output ./dist/

# All extensions in a directory tree
extensionctl build ./extensions/ --recursive --output ./dist/

# From a remote git repository (pip-style VCS URL: git+URL[@ref][#subdir])
extensionctl build git+https://git.example.com/repo.git
extensionctl build git+https://git.example.com/repo.git@main
extensionctl build git+https://git.example.com/repo.git@main#my-extension
extensionctl build git+https://git.example.com/repo.git@a705abd#my-extension
extensionctl build git+https://git.example.com/repo.git#my-extension    # default branch, subdir only

# Build and push in one step
extensionctl build git+https://git.example.com/repo.git@main#my-extension --push
extensionctl build ./my-extension --push --bump patch
extensionctl build ./my-extension --push --overwrite
```

The `#ref:subdir` fragment mirrors the Docker build URL syntax:
- `ref` — branch name, tag, or commit SHA (empty = default branch)
- `subdir` — path inside the repo (empty = repo root)

**Note:** pushing from a git URL requires `id` to be present in the committed manifest. Run `extensionctl build` on a local copy first, then commit the updated manifest.

**Output**

```
  Source:  ./my-extension
  Archive: ./dist/my-extension-v1.0.0.tar.gz
  Pushed:  aaaaaaaa-0000-0000-0000-000000000001-v1.0.0
```

---

### `push` — upload an archive to the registry

Accepts only `.tar.gz` archives produced by `build`.

```bash
extensionctl push ./my-extension-v1.0.0.tar.gz

# Bump patch version before pushing
extensionctl push ./my-extension-v1.0.0.tar.gz --bump patch

# Allow overwriting an existing tag
extensionctl push ./my-extension-v1.0.0.tar.gz --overwrite
```

The registry tag is always `<id>-v<version>` — derived from the manifest inside the archive.

---

### `pull` — download extension files from the registry

```bash
extensionctl pull <tag> ./downloads/
```

---

### `list` — list all extension tags

```bash
extensionctl list           # print one tag per line
extensionctl list --full    # print full metadata JSON for each tag
```

---

### `info` — inspect a tag (debug)

```bash
extensionctl info <tag>    # show config JSON stored for the tag
```

---

### `delete` — remove a tag from the registry

```bash
extensionctl delete <tag>           # delete a single tag
extensionctl delete --all           # delete all tags (prompts for confirmation)
extensionctl delete --all --yes     # skip confirmation
```

---

## Python API

`ExtensionUtilityLibrary` exposes every operation the CLI uses.
`build()` is a plain static method. All registry operations are **async** and require the client to be used as an `async with` context manager.

```python
import asyncio
from pathlib import Path
from kaapana_extensions.extensions import ExtensionUtilityLibrary

# Build — synchronous static method, no registry credentials needed
# Returns [(source_str, archive_path), ...]
archives = ExtensionUtilityLibrary.build(
    "git+https://git.example.com/repo.git@main#my-extension",
    output=Path("dist/"),
)
archives = ExtensionUtilityLibrary.build(Path("my-extension"), output=Path("dist/"))
archives = ExtensionUtilityLibrary.build(Path("extensions/"), output=Path("dist/"), recursive=True)

# Version bumping — also synchronous
new_ver = ExtensionUtilityLibrary.bump_version("1.2.3", "patch")  # → "1.2.4"
new_ver = ExtensionUtilityLibrary.bump_version("1.2.3", "minor")  # → "1.3.0"
new_ver = ExtensionUtilityLibrary.bump_version("1.2.3", "major")  # → "2.0.0"

# All registry operations are async — use async with
async def main():
    async with ExtensionUtilityLibrary(
        registry="https://registry.example.com",
        repo="kaapana/extensions",
        username="myuser",
        password="mytoken",
    ) as lib:
        # Push
        tag = await lib.push(Path("dist/my-extension-v1.0.0.tar.gz"))
        tag = await lib.push(Path("dist/my-extension-v1.0.0.tar.gz"), bump="patch")
        tag = await lib.push(Path("dist/my-extension-v1.0.0.tar.gz"), overwrite=True)

        # Build + push in one call
        results = await lib.publish("my-extension/", bump="minor")       # [(source, tag), ...]
        results = await lib.publish("git+https://git.example.com/repo.git@main#my-extension")

        # Pull
        out = await lib.pull("aaaaaaaa-0000-0000-0000-000000000001-v1.0.0", Path("downloads/"))

        # List / inspect
        tags = await lib.list_tags()
        manifest = await lib.get_extension(tags[0])       # extension_manifest dict
        manifests = await lib.get_extensions()            # list of all manifests
        config = await lib.get(tags[0])                   # full registry config blob
        all_meta = await lib.get_all_metadata()           # [(tag, config), ...]

        # Delete
        await lib.delete_tag("aaaaaaaa-0000-0000-0000-000000000001-v1.0.0")

asyncio.run(main())
```

---

## Development

```bash
pip install -e lib/kaapana_containers
pip install -e "lib/kaapana_extensions[test]"

# Unit tests only
pytest lib/kaapana_extensions/tests/ -m "not integration"

# Integration tests (requires Docker)
pytest lib/kaapana_extensions/tests/ -m integration

# All tests
pytest lib/kaapana_extensions/tests/
```

The integration tests spin up a local `registry:2` container via `pytest-docker`. Set `KAAPANA_TEST_REGISTRY=http://localhost:5001` to point the integration tests at a registry you started manually.
