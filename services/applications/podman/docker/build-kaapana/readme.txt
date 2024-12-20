# Experimental

In principle kaapana can be build and pushed to a registry from within a docker container...

USAGE: docker run -t -i --privileged --cgroupns=host <registry>/build-kaapana:0.0.0 -dr registry.<gitlab-url>/<group/user>/<project> -gr https://github.com/kaapana/kaapana.git -b develop -u <registry_username> -p <registry_password>
