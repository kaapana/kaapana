# Dev environment setup. 

1. Uncomment Dockerfile development part
2. Comment Dockerfile production part
3. Change dev_files value in values.yaml to your path: `/path/to/kaapana/services/base/workflow-ui/docker/files`
4. Install node, npm, yarn and run `yarn install` inside the afformentioned `files` directory
5. In `vite.config.ts` change value of allowed host to FQDN: `allowedHosts: ["<hostname>"],`
6. Enjoy HotModuleReload in-cluster.