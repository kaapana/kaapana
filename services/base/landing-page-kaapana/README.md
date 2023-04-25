
# Landing-page development setup

1. Go to `services/base/landing-page-kaapana/docker/Dockerfile` and comment the `Production` part.
2. Build and push the Dockerfile with the tag of your current landing-page image:
and push it to the registry. Don't forget to tag it to the landing page image e.g.:
   `docker build -t <registry>/landing-page-kaapana:0.0.0-latest .`
   `docker push <registry>/landing-page-kaapana:0.0.0-latest`
3. Add the path to your src files in the dev_files variable in the values.yaml file of the landing-page-chart
```
  dev_files: /path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src 
```
4. Sanity check: Any changes in `/path/to/kaapana/services/utils/base-landing-page/files/kaapana_app/src` should (almost) instantly update in the browser.
