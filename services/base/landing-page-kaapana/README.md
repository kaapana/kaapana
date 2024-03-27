
# Landing-page development setup

1. Go to `services/base/landing-page-kaapana/docker/Dockerfile` and comment the `Production` part and add the `Development` part.
2. Add the path to your src files as dev_files variable in the `services/base/landing-page-kaapana/landing-page-kaapana-chart/values.yaml`
```
  dev_files: /path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src 
```
3. Build the platform.
4. Deploy the platform.
5. Sanity check: Any changes in `/path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src` should (almost) instantly update in the browser.
