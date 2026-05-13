# Kaapana OCI
<!-- TODO change name from kaapana_containers to kaapana_oci -->

A lightweight library for interacting with OCI-compatible registries.

## Purpose

`kaapana_containers` is the OCI registry management component used by **kaapana_extensions** to store and retrieve extension packages as OCI artifacts.

## Core Concepts

### OCI Registry Operations
- Authentication: HTTP Basic and Bearer token authentication
- Blob Management: Upload/download arbitrary binary blobs
- Manifest Operations: Create and retrieve OCI image manifests
- Tag Management: Create/update tags and list available tags

## API Reference

### OCIRepositoryManager

```python
class OCIRepositoryManager:
    def __init__(self, registry_url: str, repository: str, username: Optional[str] = None, password: Optional[str] = None)
    
    def list_tags(self) -> List[str]
    
    def get(self, tag: str) -> Dict[str, Any]
    
    def get_all_metadata(self, specific_tag: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]
    
    def create_or_update_tag(self, tag: str, user_metadata: Dict[str, Any], files: Optional[List[str]] = None) -> bool
    
    def delete_tag(self, tag: str) -> bool
    
    def download_files(self, tag: str, output_dir: str = ".") -> bool
```

## License

Apache-2.0

