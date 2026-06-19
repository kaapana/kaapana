# kaapana_containers

Async OCI registry client used by **kaapana_extensions** to store and retrieve extension packages.

## Usage

> **`OCIRegistryDiscovery` must always be used as `async with` — it will not work otherwise.**

```python
from kaapana_containers.registries.registry import OCIRegistryDiscovery, OCIError

async with OCIRegistryDiscovery(
    registry_url="https://registry.example.com",
    repository="user/project",
    username="myuser",
    password="mytoken",
) as client:
    await client.check_login()
    tags   = await client.list_tags()
    meta   = await client.get("my-tag-v1.0.0")
    await client.create_or_update_tag("my-tag-v1.0.0", user_metadata={...}, files=["file.tar.gz"])
    await client.download_files("my-tag-v1.0.0", output_dir="/tmp/out")
    await client.delete_tag("my-tag-v1.0.0")
```

## Errors

All failures raise `OCIError(message, code=...)`. Error codes follow the [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec/blob/main/spec.md#error-codes).

```python
try:
    await client.list_tags()
except OCIError as e:
    print(e.code)   # e.g. "UNAUTHORIZED", "NAME_UNKNOWN", "MANIFEST_UNKNOWN"
    print(str(e))   # human-readable detail
```

## License

Apache-2.0
