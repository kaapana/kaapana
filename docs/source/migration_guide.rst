###############
Migration Guide
###############

.. _migration_guide:


Upgrade from 0.3.x to 0.4.x
****************************

1. Login to keycloak and add the `system` user to the keycloak group `kaapana_admin`
2. Apply steps 1 to 5 to backup the meta information from opensearch
2. Undeploy 0.3.5 `./deploy_platform_0.3.5.sh --quiet --undeploy`
3. Uninstall server `sudo ./server_installation_0.3.5.sh --uninstall`
4. Run `sudo ./migration_0.3.x-0.4.x.sh`
5. Install server `sudo ./server_installation_0.4.0.sh`
6. Deploy platform 0.4.0 `./deploy_platform_0.4.0.sh --quiet --domain 10.128.130.164`
7. Apply steps 6 to 11 to restore the meta-information in the new opensearch cluster
8. Run the steps 1 to 4 to move thumbnails and static website results to the correct path in minio.

Data in postgres databases
---------------------------

Data in Minio buckets
----------------------

**Thumbnails & staticwebsiteresults**
1. Start a minio-sync application
2. Enter into the container of the minio-sync pod
3. Execute `mc find minio/thumbnails --name "*.png" -print {base} -exec "mc mv {} minio/project-admin/thumbnails/"`
4. Execute `mc mv -r minio/staticwebsiteresults minio/project-admin`

Meta information in Opensearch
-------------------------------


**Old instance**
1. Add `path.repo: ["/usr/share/opensearch/logs"]` to `opensearch.yml` in os-config
2. Restart opensearch pod
3. Create repository in `/usr/share/opensearch/logs/snapshots`
4. Create snapshot of `meta-index`
5. Backup all files in `/home/kaapana/os/logs/snapshots/` 

**New instance**
6. Create repository in `/usr/share/snapshots`
7. Copy all files from the backed up snapshot from into `/home/kaapana/os/snapshots`
8. Restore the `meta-index` index from the snapshot as  `restored_meta-index`
9. Reindex the `restored_meta-index` and the `project_admin` index into an index called `project_merged`
10. Check in the dashboard that `project_merged` contains data of both indices.
11. Reindex `project_merged` to `project_admin`