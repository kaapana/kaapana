# Extension Manager UI

The web frontend for the **extension-manager-service**. Vue 3 + TypeScript + Vuetify, app that lets users:

- browse the **catalog** of extensions available in the registered OCI repositories
- manage those **repositories** (add / edit / remove oci registry entries)
- **install / uninstall** extensions and view their platform state

## Folder layout

All application code lives under `docker/files/`:

| Path | Purpose |
| --- | --- |
| `src/main.ts` | App entry point — creates the Vue app, registers the router and Vuetify. |
| `src/App.vue` | Root component / app shell. |
| `src/router/router.ts` | Routes for the three views (`/catalog`, `/extensions`, `/repositories`). |
| `src/views/` | Top-level pages: `Catalog.vue`, `Extensions.vue`, `Repositories.vue`. |
| `src/features/` | Feature modules, each self-contained with its own `components/`, `api.ts`, `types.ts`, `utils.ts`: `catalog/`, `extensions/`, `repositories/`. |
| `src/shared/` | Cross-feature code: `api/client.ts` (the axios instance), `components/` (reusable UI), `types/apiSchemas.ts` (TypeScript types mirroring the service responses), `utils/`. |
| `src/plugins/vuetify.ts` | Vuetify instance, theme and icon setup. |
| `nginx.conf` | Production static-file serving (non-root, listens on `5000`). |

## In-cluster dev environment

1. Uncomment the development part of the `Dockerfile` and comment out the production part.
2. Set `dev_files` in `values.yaml` to your local path, e.g.
   `/home/<username>/kaapana/services/base/extension-manager-ui/docker/files`.
3. In `vite.config.ts`, add your machine's FQDN to the allowed hosts, e.g.
   `allowedHosts: ["<your-host-fqdn>"]`.
4. Deploy — you now get Hot Module Reload in-cluster.
