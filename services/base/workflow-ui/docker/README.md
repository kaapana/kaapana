# In-cluster development with hot module reload

1. In `Dockerfile`, uncomment the DEVELOPMENT part and comment out the PRODUCTION part.
2. Set `global.dev_files` in `workflow-ui-chart/values.yaml` to the absolute path of
   `services/base/workflow-ui/docker/files` on the node.
3. Build base-ui once (`npm ci && npm run build` in `services/base/base-ui/docker/files`), then run
   `npm ci` in `services/base/workflow-ui/docker/files`. The mounted sources bring their own
   `node_modules`.
4. Build and deploy the image. Changes to the sources reload in the browser.
