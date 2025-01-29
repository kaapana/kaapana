# How to enter development mode 

1. In `values.yaml` change `dev-files: /<your-path>/kaapana/services/data-separation/dicom-web-filter/docker/files` (use absolute path)
2. Comment production block and uncomment development block in `boot.sh`
3. Re-deploy -> The changes you make should be automatically applied as the application reloads on changes.

