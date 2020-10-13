

flask run

Running locally:

SCRIPT_NAME=/hello-world gunicorn -b :5000 -e SECRET_KEY='test' -e HELLO_WORLD_USER='klaus' -e APPLICATION_ROOT='/hello-world' run:ap

Running with docker locally
sudo docker run -p 5000:5000 -e SECRET_KEY='jip' -e HELLO_WORLD_USER='Klaus' -e APPLICATION_ROOT='/hello-world' $DOCKER_REGISTRY/$DOCKER_REPO/$IMAGE:$VERSION


Installing helm plugins
Add tutorial repo
helm repo add --username jip-ci-kaapana --password <password> tutorial https://dktk-jip-registry.dkfz.de/chartrepo/tutorial

Going to helm_chart folder
Pushing Chart: helm push hello-world tutorial
