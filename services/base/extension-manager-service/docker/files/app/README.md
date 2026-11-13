# Extension Manager Service

A FastAPI backend for discovering, installing, and managing extensions pulled from OCI-compatible container registries. Extensions package reusable content (e.g. workflows) that is dispatched to other platform services upon installation.

## Architecture

```mermaid
graph TD
    Client -->|HTTP| Router

    subgraph Routers
        Router --> RepositoryRouter["Repository Router\n/v1/repositories"]
        Router --> InstallationRouter["Installation Router\n/v1/extensions"]
    end

    subgraph Services
        RepositoryRouter -->|list/fetch manifests| OCI["OCI Service"]
        InstallationRouter -->|pull extension| OCI
        InstallationRouter -->|install/uninstall content| Dispatch["Dispatch Service"]
        RepositoryRouter -->|persist repositories| DB["Database Service"]
        InstallationRouter -->|track extension state| DB
    end

    subgraph External
        OCI -->|HTTPS| Registry["OCI Registry\n(e.g. GHCR, Harbor)"]
        Dispatch -->|HTTP| WorkflowAPI["Workflow API\n(workflow-api.services.svc)"]
        DB -->|SQL| SQLite[("SQLite / PostgreSQL")]
    end
```

The service is versioned under `/v1/` and follows a layered architecture: HTTP routers handle request validation and response shaping, service modules encapsulate external communication, and SQLAlchemy models track persistent state.

---

## Objects

### `ExtensionManifest`

The central descriptor of an extension, stored as JSON in the database and used throughout the install lifecycle.

| Field          | Type                  | Description                                              |
|----------------|-----------------------|----------------------------------------------------------|
| `id`           | UUID string           | Stable identifier for the extension                     |
| `name`         | string                | Human-readable extension name                           |
| `version`      | string                | Semantic version string                                  |
| `contents`     | `Content[]`           | List of content items bundled in this extension         |
| `dependencies` | string[]              | Tags of other extensions this one depends on            |

### `Content`

A single installable unit within an extension. Each content item has a dedicated installer registered in the dispatcher.

| Field         | Type       | Description                                                  |
|---------------|------------|--------------------------------------------------------------|
| `name`        | string     | Identifier for this content item                            |
| `contentType` | string     | Determines which installer handles it (e.g. `workflow-v1`)  |
| `files`       | string[]   | File paths within the extracted extension bundle            |

### `Repository` (database)

Represents an OCI registry endpoint that the service can query.

| Field         | Type   | Description                                          |
|---------------|--------|------------------------------------------------------|
| `id`          | UUID   | Primary key                                          |
| `name`        | string | Unique human-readable label                          |
| `description` | string | Optional free-text description                       |
| `url`         | string | Base URL of the OCI registry host                    |
| `credentials` | string | Base64-encoded JSON `{"username": ..., "password": ...}` |

### `Extension` (database)

Tracks an installed (or in-progress) extension.

| Field           | Type              | Description                                            |
|-----------------|-------------------|--------------------------------------------------------|
| `id`            | UUID              | Primary key                                            |
| `repository_id` | UUID (FK)         | Which registry this was pulled from                    |
| `tag`           | string            | OCI tag used to pull this extension                    |
| `manifest`      | JSON              | Full `ExtensionManifest` at install time               |
| `pending_update` | JSON (null)      | Target of a running or failed update: repository, tag and manifest; taken over into the fields above when the update succeeds |
| `status`        | `ExtensionStatus` | Current lifecycle state (see below)                    |
| `created_at`    | datetime          | First seen timestamp                                   |
| `updated_at`    | datetime          | Last status change timestamp                           |

The pair `(repository_id, tag)` is unique — the same tag cannot be installed twice from the same registry.
A tag that is installed from one repository cannot be installed from another one at the same time (409).
Extensions with the same manifest `id` are the same extension: a newer version from the same repository updates it (see [Update path](#update-path)), other requests get a 409.

### `InstalledContent` (database)

Tracks each content item within an installed extension.

| Field        | Type            | Description                                                     |
|--------------|-----------------|-----------------------------------------------------------------|
| `id`         | UUID            | Primary key                                                     |
| `extension_id` | UUID (FK)     | Parent extension                                               |
| `name`       | string          | Content item name from the manifest                            |
| `type`       | string          | Content type (mirrors `contentType` in the manifest)           |
| `status`     | `ContentStatus` | Current lifecycle state                                        |
| `location`   | string \| null  | Resource URL returned by the installer after successful install |
| `applied_version` | string \| null | Extension version this content last received; `null` until it is installed |

### Status Enums

#### `ExtensionStatus`

```mermaid
graph LR
    PENDING --> PULLING
    PENDING --> UNINSTALLING

    PULLING --> PULLING_FAILED
    PULLING --> INSTALLING
    PULLING --> UNINSTALLING

    INSTALLING --> INSTALLATION_FAILED
    INSTALLING --> INSTALLED
    INSTALLING --> UNINSTALLING

    INSTALLED --> UNINSTALLING
    INSTALLED --> UPDATING

    UPDATING --> INSTALLED
    UPDATING --> UPDATE_FAILED

    UPDATE_FAILED --> UPDATING
    UPDATE_FAILED --> UNINSTALLING

    PULLING_FAILED --> PENDING
    PULLING_FAILED --> UNINSTALLING

    INSTALLATION_FAILED --> PENDING
    INSTALLATION_FAILED --> UNINSTALLING

    UNINSTALLING --> UNINSTALLED
    UNINSTALLING --> UNINSTALLING_FAILED
    UNINSTALLING --> UNINSTALLING

    UNINSTALLING_FAILED --> UNINSTALLING
```

The `UNINSTALLING → UNINSTALLING` self-loop allows re-triggering an uninstall on an extension that is already transitioning (e.g. if a previous uninstall task was lost mid-flight). `PULLING_FAILED → PENDING` and `INSTALLATION_FAILED → PENDING` are the retry arcs triggered by calling `POST /extensions/install` again. `UPDATING` has no arc to `UNINSTALLING`, because the update job does not check for cancellation and its requests would race with the uninstall. An update that a restart interrupted is moved to `UPDATE_FAILED` by `boot.sh` before the workers start, together with its contents that were still in progress, so the same request retries it.

#### `ContentStatus`

```mermaid
graph LR
    PENDING --> INSTALLING
    PENDING --> UNINSTALLING

    INSTALLING --> INSTALLATION_FAILED
    INSTALLING --> INSTALLED
    INSTALLING --> UNINSTALLING

    INSTALLED --> UNINSTALLING
    INSTALLED --> UPDATING

    UPDATING --> INSTALLED
    UPDATING --> UPDATE_FAILED

    UPDATE_FAILED --> UPDATING
    UPDATE_FAILED --> UNINSTALLING

    INSTALLATION_FAILED --> INSTALLING
    INSTALLATION_FAILED --> UNINSTALLING

    UNINSTALLING --> UNINSTALLED
    UNINSTALLING --> UNINSTALLATION_FAILED

    UNINSTALLATION_FAILED --> UNINSTALLING
```

State transitions are validated in the CRUD layer — invalid transitions raise an exception rather than silently persisting bad state.

---

## Routers

### Repository Router — `/v1/repositories`

Manages the list of known OCI registries and exposes discovery endpoints.

| Method   | Path                                          | Description                                              |
|----------|-----------------------------------------------|----------------------------------------------------------|
| `POST`   | `/repositories`                               | Register a new OCI registry                             |
| `GET`    | `/repositories`                               | List registries (filter by `name` or `id`)              |
| `GET`    | `/repositories/{id}`                          | Get a single registry                                   |
| `PUT`    | `/repositories/{id}`                          | Update registry credentials or description (409 for the Upload repository) |
| `DELETE` | `/repositories/{id}`                          | Remove a registry (409 for the Upload repository)       |
| `GET`    | `/repositories/{id}/extensions`               | List available extension tags in the registry           |
| `GET`    | `/repositories/{id}/extensionManifests`       | Fetch manifests for tags (optionally filtered by tag)   |

### Installation Router — `/v1/extensions`

Manages the install/uninstall lifecycle.

| Method | Path                              | Description                                     |
|--------|-----------------------------------|-------------------------------------------------|
| `POST` | `/extensions/install`             | Install an extension by repository and tag, or update it to a newer version |
| `POST` | `/extensions/upload`              | Install an extension from a `.tar.gz` file, or update it to a newer version |
| `GET`  | `/extensions`                     | List installed extensions (filter by tag, repo) |
| `GET`  | `/extensions/{id}`                | Get details for one installed extension         |
| `POST` | `/extensions/{id}/uninstall`      | Uninstall an extension                          |

### Upload repository

Extensions installed from a file belong to the built-in repository `Upload` (`upload://local`, id `8f49216f-786c-42ba-9413-0722e781ea28`). The Alembic revision for 0.8.0 creates it. It cannot be changed or removed.

- `POST /extensions/upload` takes a `.tar.gz` built with `extensionctl build`, at most 100 MB. The archive is rejected with 400 when it has links, absolute paths or `..`, files the manifest does not list, an invalid manifest, a content type without an installer, or content its installer rejects.
- The extension gets the tag `<manifest id>-v<version>`, the same tag `extensionctl push` uses.
- The files are kept in `/extensions/uploads/<tag>` until the extension is uninstalled. The catalog of the Upload repository lists this folder, so a failed installation can be retried from the catalog or by uploading the same file again.
- Uploading the same tag with a different manifest is rejected while the old record exists (409).

---

## Services

### OCI Service

Wraps the `ExtensionUtilityLibrary` to communicate with OCI registries.

**Authentication** — Credentials are stored as a base64-encoded JSON blob (`{"username": ..., "password": ...}`). The service decodes them and validates login against the registry on construction.

**Fetching extension information** proceeds in two steps:

1. **Tag listing** — `get_extensions_for_repository()` calls the OCI catalog/tags API for the configured repository URL and returns the list of available tags. Each tag corresponds to one extension version.

2. **Manifest retrieval** — `get_extension_manifests(tags)` iterates the tag list and calls `get_extension_manifest(tag)` for each. The manifest is an OCI image config layer that encodes the `ExtensionManifest` JSON described above. The OCI library pulls the config blob, deserialises it, and returns typed `ExtensionManifest` objects.

**Pulling an extension** — `pull_extension(tag)` downloads and extracts the full OCI artifact to a local directory:

```
/extensions/{registry_hostname}/{tag}/
  extension_manifest.json
  <content-name>/
    <files listed in manifest>
```

The extracted path is passed to the dispatcher so each content installer can read its files.

After installation completes the background job removes the extracted directory.

### Dispatch Service

Routes each content item to the correct installer and abstracts the target platform service.

**`Dispatcher`** maintains a registry of `ContentInstaller` implementations. On `install_content()` / `uninstall_content()` it iterates registered installers, calls `can_install(content_type)`, and delegates to the first match. Raises `ContentTypeNotSupportedError` if no installer is found.

**`ContentInstaller`** (ABC) — all installers implement:
- `can_install(content_type: str) -> bool`
- `install(content: Content) -> InstallationResult`
- `update(content: Content) -> InstallationResult`
- `uninstall(content: Content) -> None`

`InstallationResult` carries a `location` string — typically a URL returned by the target service — that is persisted in `InstalledContent.location` and used later for uninstallation.

**Adding a new content type** requires:
1. Subclass `ContentInstaller` and implement its methods.
2. Register the instance with the `Dispatcher` at application startup.

**`WorkflowConsumer`** — the built-in installer for `workflow-v1` content:
- Reads `workflow.json` and `workflow_definition.py` from the extracted content directory.
- `POST`s the workflow payload to `http://workflow-api.services.svc:80/v1/workflows`.
- Stores the `Location` response header as `InstallationResult.location`.
- On update, issues a `PATCH` to that stored URL; the workflow keeps its ID and gets a new revision.
- On uninstall, issues a `DELETE` to that stored URL.

### Database Service

Provides async SQLAlchemy CRUD operations over the `registries`, `extensions`, and `contents` tables.

Key behaviours:
- **Row-level locking** — `SELECT ... FOR UPDATE NOWAIT` prevents two concurrent requests from mutating the same extension or content row simultaneously. The lock fails immediately rather than waiting; concurrent attempts raise a `LockedExtensionException` which the caller surfaces as an HTTP 409.
- **Transition validation** — `update_extension_status` and `update_content_status` check the requested transition against an allow-list before committing. This enforces the state machines described above.
- **Cascade deletes** — deleting an extension removes all its `InstalledContent` rows automatically.

---

## Extension Lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant IR as Installation Router
    participant BG as Background Job
    participant OCI as OCI Service
    participant DB as Database Service
    participant D as Dispatch Service
    participant P as Platform Service

    C->>IR: POST /extensions/install {repository_id, tag}
    IR->>OCI: get_extension_manifest(tag)
    OCI-->>IR: ExtensionManifest
    IR->>IR: Validate all content types have installers
    IR->>DB: create_extension(PENDING) + create_contents(PENDING)
    IR-->>C: 201 Created {extension_id}

    IR->>BG: schedule background install task

    BG->>DB: update_extension_status(PULLING)
    BG->>OCI: pull_extension(tag)
    OCI-->>BG: local extraction path

    BG->>DB: update_extension_status(INSTALLING)
    loop For each content item
        BG->>DB: update_content_status(INSTALLING)
        BG->>D: install_content(content)
        D->>P: POST /v1/<resource>
        P-->>D: 201 {Location}
        D-->>BG: InstallationResult {location}
        BG->>DB: update_content_status(INSTALLED, location)
    end
    BG->>DB: update_extension_status(INSTALLED)
    BG->>BG: cleanup extracted files

    Note over C,P: Update flow
    C->>IR: POST /extensions/install {repository_id, tag of a newer version}
    IR->>IR: resolve_install_target(active extension, version)
    IR->>DB: update_extension_status(UPDATING, pending_update)
    IR-->>C: 202 Accepted {extension_id}
    IR->>BG: schedule background update task
    BG->>OCI: pull_extension(pending tag)
    loop For each content to install, update or uninstall
        BG->>D: install_content / update_content / uninstall_content
        D->>P: POST / PATCH / DELETE
        BG->>DB: update_content_status(applied_version)
    end
    BG->>DB: complete_extension_update (INSTALLED, pending_update taken over)
    BG->>BG: cleanup extracted files

    Note over C,P: Uninstall flow
    C->>IR: POST /extensions/{id}/uninstall
    IR->>DB: update_extension_status(UNINSTALLING)
    IR-->>C: 202 Accepted
    IR->>BG: schedule background uninstall task
    loop For each non-uninstalled content
        BG->>DB: update_content_status(UNINSTALLING)
        BG->>D: uninstall_content(content)
        D->>P: DELETE {location}
        BG->>DB: update_content_status(UNINSTALLED)
    end
    BG->>DB: delete_extension (after 30s grace period)
```

### Install path

1. **Validate** — The router fetches the manifest from the OCI registry and checks that every `contentType` listed in the manifest has a registered installer in the dispatcher. If any type is unsupported the request is rejected immediately (no DB writes).
2. **Record** — An `Extension` row is created with status `PENDING`; one `InstalledContent` row is created per content item, also `PENDING`. If two concurrent requests race to install the same `(repository_id, tag)`, the database unique constraint resolves the conflict: the losing request detects the `IntegrityError`, loads the existing record, and retries the installation from there.
3. **Pull** — The background job transitions the extension to `PULLING` and calls `OCI.pull_extension()`, which downloads and extracts the OCI artifact locally.
4. **Install contents** — Status moves to `INSTALLING`. Content Items are installed consecutively; failures are collected and re-raised together as an `ExceptionGroup` so all results are captured.
5. **Finalise** — On full success the extension moves to `INSTALLED`. If any content item fails, the extension moves to `INSTALLATION_FAILED`; successfully installed items keep their `INSTALLED` status.
6. **Cleanup** — The extracted directory is removed regardless of outcome.

### Uninstall path

1. **Trigger** — The router synchronously transitions the extension to `UNINSTALLING` (enforced by the state machine, returns 409 if the extension is not in an uninstallable state), then schedules a background uninstall task.
2. **Uninstall contents** — Each `InstalledContent` that is not already `UNINSTALLED` is moved to `UNINSTALLING`, then the dispatcher calls the appropriate consumer which issues a `DELETE` to the stored `location` URL. Content still in `PENDING` state is driven through `UNINSTALLING → UNINSTALLED` as well (its `location` is `null`, the dispatcher throws a warning but succeeds).
3. **Remove record** — After a 30-second grace period the extension row (and cascaded content rows) is deleted from the database.

### Update path

An update replaces an installed extension in place: it keeps its row, and its workflows keep their IDs and get a new revision. Runs that are active during an update finish on their revision, because the workflow API renders each revision as its own DAG. Versions are compared with `semver` from the `version` field of the manifest; the tag is only the address to pull from.

`resolve_install_target` (`v1/services/install_target.py`) decides what `POST /extensions/install` and `POST /extensions/upload` do when an extension with the same manifest `id` is not uninstalled:

| Requested version | Active extension | Result |
|-------------------|------------------|--------|
| Any | none | Install, 201 |
| Same repository and tag | any status | Install path above (retry, or 409 by the state machine) |
| Any, from another repository | `INSTALLED` or `UPDATE_FAILED` | 409 |
| Higher | `INSTALLED` | Update, 202 |
| The failed target or higher | `UPDATE_FAILED` | Update (retry or new target), 202 |
| Higher, but below the failed target | `UPDATE_FAILED` | 409, contents already on the failed target would go back |
| Same or lower | `INSTALLED` or `UPDATE_FAILED` | 409, downgrades are not supported |
| Any | other status | 409 |
| Not semver | any | 400 |

Extensions installed from a file belong to the Upload repository, so a newer upload updates them.

1. **Trigger**: The router moves the extension to `UPDATING` and stores the target (repository, tag, manifest) in `pending_update`. A content whose type changes is rejected with 400 before that.
2. **Pull**: The background job pulls the target from its repository and checks that the pulled manifest matches `pending_update`.
3. **Apply contents**: see below.
4. **Finalise**: On success the target replaces `repository_id`, `tag` and `manifest`, `pending_update` is cleared and the extension moves to `INSTALLED`; the files of a replaced upload are removed. On failure it moves to `UPDATE_FAILED` and keeps `pending_update`, which the API shows; sending the request again retries.

`apply_content_changes` (`v1/services/content_update.py`) brings the contents to the target manifest. Contents are matched by name:
- **New in the manifest**: installed.
- **In both, with an older `applied_version`**: updated through the installer's `update`.
- **Already on the target version**: skipped, which is what makes a retry cheap.
- **Gone from the manifest**: uninstalled; the row is deleted afterwards.
- **Same name, different `contentType`**: rejected, no installer can update across types.

A renamed content is therefore uninstalled and installed again, and a renamed workflow gets a new ID. A content that fails keeps its old `applied_version` and moves to `UPDATE_FAILED` (or `INSTALLATION_FAILED` if it was new); the failures are raised together as an `ExceptionGroup` after all other contents were handled.

Limits:
- There is no downgrade and no rollback. A broken update is fixed with a newer version, or by uninstalling and installing again, which gives the workflows new IDs.
- A version pushed again with `extensionctl push --overwrite` does not reach a platform that has this version installed.
- A workflow keeps the engine it was created with. The workflow API does not accept a new engine on update, so a changed `workflow_engine` is dropped without notice.
- The workflow API stores a new revision before it submits it to the workflow engine. If the submission fails, the content stays on its old `applied_version`, but the workflow's latest revision is already the new one, and each retry adds another revision.
- A workflow that was deleted outside the Extension Manager fails every update that changes or removes it. A retry does not help, and uninstalling fails the same way as long as the uninstall does not treat a missing workflow as removed.
- A restart while a workflow is created can leave a workflow that the Extension Manager did not record; the retry then fails on its title.
