.. _extension_stuck:

Extensions Page Stuck in Loading
********************************

This issue is most likely due to having too many `.tgz` files in the extensions folder `<FAST_DATA_DIR>/extensions`. This can occur if the platform is redeployed with multiple versions consecutively. If different versions exist for many extensions, it may take a long time to gather all the information. 
To resolve this issue, manually delete some of the unused older versions of chart files.

Note that there is no hard limit for the number of extensions or versions that will cause this issue. It will vary based on the state of resources for every instance.
