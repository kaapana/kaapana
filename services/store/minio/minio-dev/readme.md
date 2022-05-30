# Needed Keycloak Adaptations in Kaapana

Adapted from https://github.com/minio/minio/blob/master/docs/sts/keycloak.md

### Configure Keycloak Realm

- Go to Clients
  - Click on `kaapana`
    - Settings
    - Change `Access Type` to `confidential`.
    - Save
  - Click on credentials tab
    - Copy the `Secret` to clipboard.
    - This value is needed for `MINIO_IDENTITY_OPENID_CLIENT_SECRET` for MinIO.

- Go to Users
  - Click on the user
  - Attribute, add a new attribute `Key` is `policy`, `Value` is name of the `policy` on MinIO (ex: `readwrite` or `consoleAdmin`)
  - Add and Save

- Go to Clients
  - Click on `kaapana`
  - Settings, set `Valid Redirect URIs` to `https://193.174.49.36:9443/minio-console/oauth_callback/`, expand `Advanced Settings` and set `Access Token Lifespan` to `1 Hours`
  - Save

- Go to Clients
  - Click on `kaapana`
  - Mappers
  - Create
    - `Name` with `KaapanaMinioAudience`
    - `Mapper Type` is `User Attribute`
    - `User Attribute` is `policy`
    - `Token Claim Name` is `policy`
    - `Claim JSON Type` is `string`
  - Save
