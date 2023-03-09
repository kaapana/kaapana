# Experimental

In principle kaapana can be build and pushed to a registry from within a docker container...

USAGE: docker run -t -i --privileged <registry>/kaapana:0.0.0 -gr https://github.com/kaapana/kaapana.git -b feature/podman-base-python-cpu -dr registry.<gitlab-url>/<group/user>/<project> -u <registry_username> -p <registry_password>
