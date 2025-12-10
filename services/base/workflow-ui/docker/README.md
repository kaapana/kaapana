# Dev environment setup. 

1. Uncomment Dockerfile development part
2. Comment Dockerfile production part
3. Change dev_files value in values.yaml to your path: `/home/<username>/kaapana/services/base/workflow-ui/docker/files`
4. In `vite.config.ts` change value of allowed host to FQDN: `allowedHosts: ["e230-pc25.inet.dkfz-heidelberg.de"],`
5. Enjoy HotModuleReload in-cluster.