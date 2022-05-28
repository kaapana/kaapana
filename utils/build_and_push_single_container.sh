#!/bin/bash
input="Dockerfile"
if test -f "$input"; then
    echo "$input exist"
else
    echo "$input not found..."
    exit 1
fi
bsdocker_registry=""
image=""
version=""
project=""
default_registry="" # eg 'registry.hzdr.de/kaapana'
default_project="" # eg '/kaapana'
while IFS= read -r line;
do
    if [[ $line == *"LABEL IMAGE="* ]]; then
        image=${line#*=}
        image=$(sed -e "s/\"//g" -e "s/\'//g" <<<"$image")
    fi
    if [[ $line == *"LABEL PROJECT="* ]]; then
        project=${line#*=}
        project=$(sed -e "s/\"//g" -e "s/\'//g" <<<"$project")
    fi
    if [[ $line == *"LABEL REGISTRY="* ]]; then
        docker_registry=${line#*=}
        docker_registry=$(sed -e "s/\"//g" -e "s/\'//g" <<<"$docker_registry")
    fi
    if [[ $line == *"LABEL VERSION"* ]]; then
        version=${line#*=}
        version=$(sed -e "s/\"//g" -e "s/\'//g" <<<"$version")
    fi
    if [[ $line == *"LABEL CI_IGNORE"* ]]; then
        ci_ignore=${line#*=}
        ci_ignore=$(sed -e "s/\"//g" -e "s/\'//g" <<<"$ci_ignore")
    fi
done < "$input"
if [ -z "$docker_registry" ]
then
      echo "Setting default docker_registry: $default_registry"
      docker_registry=$default_registry
fi
if [ -z "$project" ] && [ "$docker_registry" != "local-only" ] 
then
      echo "Setting default project: $default_project"
      project=$default_project
fi
if [ -z "$image" ]
then
      echo "INFO MISSING: image"
      exit 1
fi
if [ -z "$version" ]
then
      echo "INFO MISSING: version"
      exit 1
fi
docker_tag="$docker_registry$project/$image:$version"
echo "docker_registry: $docker_registry"
echo "project:         $project"
echo "image:           $image"
echo "version:         $version"
echo "DOCKER_TAG: $docker_tag"
DOCKER_BUILDKIT=1 docker build -t  $docker_tag . && echo "Docker Build -> OK " || { echo "Docker Build -> FAILED!" ; exit 1; }
if [[ ! $docker_tag == *"local-only"* ]]; then
    echo "STARTED PUSHING..."
    docker push $docker_tag && echo "Docker Push -> OK "  || { echo "Docker Push -> FAILED!" ; exit 1; }
else
    echo "SKIPPED PUSHING -> local-only"
fi
    echo "DONE"
    