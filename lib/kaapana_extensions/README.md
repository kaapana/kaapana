# kaapana_extensions — OCI Extension Toolchain

A Python library and CLI for packaging, publishing, and consuming Kaapana extensions as OCI artifacts stored in any standard container registry.

## Installation

```bash
pip install -e lib/kaapana_extensions
```

The `extensionctl` command is available immediately after installation.

---

## Extension manifest

Every extension directory must contain an `extension_manifest.json` at its root:

```json
{
  "name": "my-extension",
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
  ],
  "dependencies": []
}
```

- `name` — unique identifier, alphanumeric plus `-` and `_`.
- `version` — semver string (`MAJOR.MINOR.PATCH`).
- `contents[].name` — name of the subfolder containing the content files.
- `contents[].files[].path` — file path **relative to the content subfolder**.

The on-disk layout matching the manifest above:

```
example-extension/
├── extension_manifest.json
└── <content-name>/
    ├── <content_file>
    └── <content_file>
```

---

## CLI reference

All commands that talk to a registry accept `--registry`, `--repo`, `--user`, and `--password`. After running `extensionctl login` these are saved to `~/.kaapana/credentials.json` and can be omitted.

### Authentication

```bash
# Save credentials (required once before push/pull/publish/list)
extensionctl login \
  --registry registry.example.com \
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
# Single extension directory → archive next to the source, expects extension_manifest.json in the root of the extension directory
extensionctl build ./my-extension

# Write to a specific output directory
extensionctl build ./my-extension --output ./dist/

# All extensions inside a directory tree, searches recursively for extension_manifest.json
extensionctl build ./extensions/ --recursive --output ./dist/

# From a remote git repository
extensionctl build --git https://git.example.com/repo.git --output ./dist/

# Specific branch, tag, or commit hash
extensionctl build --git https://git.example.com/repo.git \
  --ref main --output ./dist/

extensionctl build --git https://git.example.com/repo.git \
  --ref a705abd809993d8b01a6b69adb410c7f4c6bd60c \
  --output ./dist/

# Extension lives in a subdirectory of the repo
extensionctl build --git https://git.example.com/repo.git \
  --subdir extensions/my-extension --output ./dist/

# Every extension in the repo
extensionctl build --git https://git.example.com/repo.git \
  --recursive --output ./dist/
```

**Output**

```
  Source:  ./my-extension
  Archive: ./dist/my-extension-v1.0.0.tar.gz
```

---

### `push` — upload an archive to the registry

Accepts only `.tar.gz` archives produced by `build`.

```bash
# Tag is always derived from the manifest: <name>-v<version>
extensionctl push ./my-extension-v1.0.0.tar.gz

# Bump patch version before pushing
extensionctl push ./my-extension-v1.0.0.tar.gz --bump patch

# Allow overwriting an existing tag
extensionctl push ./my-extension-v1.0.0.tar.gz --overwrite
```

---

### `publish` — build and push in one step

`publish` = `build` + `push`.  All options from both commands are available.

```bash
# From a local directory
extensionctl publish ./my-extension

# Bump minor version on publish
extensionctl publish ./my-extension --bump minor

# From a git repo, specific commit
extensionctl publish --git https://git.example.com/repo.git \
  --ref a705abd --bump patch

# Every extension in the repo
extensionctl publish --git https://git.example.com/repo.git \
  --recursive
```

**Output**

```
  Source:    https://git.example.com/repo.git :: my-extension
  Published: my-extension-v1.2.0
```

---

### `pull` — download an extension from the registry

```bash
# Download archive
extensionctl pull my-extension-v1.0.0 ./downloads/

# Download and extract into a directory
extensionctl pull my-extension-v1.0.0 ./extracted/ --extract
```

---

### `list` — list all extension tags

```bash
extensionctl list
```

---

### `validate` — validate a manifest

```bash
extensionctl validate ./my-extension/
extensionctl validate ./my-extension/extension_manifest.json
```

---

### `registry` — low-level registry inspection

These commands bypass the extension abstraction and expose raw OCI objects. Useful for debugging.

```bash
extensionctl registry info     <tag>     # manifest digest, config digest, layer digests
extensionctl registry manifest <tag>     # raw OCI manifest JSON
extensionctl registry config   <tag>     # config blob with resolved file paths
extensionctl registry blob     <digest>  # raw blob content
extensionctl registry read     <tag>     # extension manifest + config side-by-side
extensionctl registry delete   <tag>     # delete a tag
```

---

## Python API

`ExtensionUtilityLibrary` exposes every operation the CLI uses. Registry credentials are only needed for operations that contact the registry.

```python
from pathlib import Path
from kaapana_extensions.extensions import ExtensionUtilityLibrary

# Build-only — no registry credentials needed
archive = ExtensionUtilityLibrary.build_extension(
    Path("my-extension"),
    output=Path("dist/"),
)

# Registry operations
lib = ExtensionUtilityLibrary(
    registry="registry.example.com",
    repo="kaapana/extensions",
    username="myuser",
    password="mytoken",
)

# Push
tag = lib.push(archive)
tag = lib.push(archive, bump="patch")          # auto-bump version
tag = lib.push(archive, tag="custom-tag", overwrite=True)

# Publish from a directory (build + push)
tag, old_v, new_v = lib.publish_dir(Path("my-extension"), bump="minor")

# Publish from git
tag, old_v, new_v = lib.publish_from_git(
    "https://git.example.com/repo.git",
    ref="main",
    bump="patch",
)

# Pull
lib.pull("my-extension-v1.0.0", Path("downloads/"))
lib.pull("my-extension-v1.0.0", Path("extracted/"), extract=True)

# Inspect
tags = lib.list_extensions()
info = lib.get_extension("my-extension-v1.0.0")
config = lib.read_extension_config("my-extension-v1.0.0")

# Delete
lib.delete_extension("my-extension-v1.0.0")

# Validate
ok, errors = ExtensionUtilityLibrary.validate(Path("my-extension/extension_manifest.json"))
ok, errors = lib.validate_extension(Path("my-extension/"))
```

### Resolving a source (local path or git URL)

`resolve_source` is a static context manager that transparently handles cloning remote repos into a temporary directory:

```python
with ExtensionUtilityLibrary.resolve_source(
    "https://git.example.com/repo.git",
    ref="main",
    subdir="extensions/my-extension",
) as (ext_dir, root_dir):
    archive = ExtensionUtilityLibrary.build_extension(ext_dir, output=Path("dist/"))
```

For local paths no cloning happens — `ext_dir` and `root_dir` point directly into the filesystem.

### Version bumping

```python
new_ver = ExtensionUtilityLibrary.bump_version("1.2.3", "patch")  # → "1.2.4"
new_ver = ExtensionUtilityLibrary.bump_version("1.2.3", "minor")  # → "1.3.0"
new_ver = ExtensionUtilityLibrary.bump_version("1.2.3", "major")  # → "2.0.0"
```

---

## Development

```bash
pip install -e "lib/kaapana_extensions[dev]"
pytest lib/kaapana_extensions/tests/
```
