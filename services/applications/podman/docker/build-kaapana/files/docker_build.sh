#!/bin/bash
set -euf -o pipefail

### Parsing command line arguments:
usage="$(basename "$0")
USAGE: docker run -t -i --privileged <registry>/kaapana:0.0.0 -gr https://github.com/kaapana/kaapana.git -b feature/podman-base-python-cpu -dr registry.<gitlab-url>/<group/user>/<project> -u <registry_username> -p <registry_password>

_Argument: -gr|--git-repository [Kaapana Git repository, the default is 'https://github.com/kaapana/kaapana.git']
_Argument: -b|--branch [Branch of repository that should be built, the default is 'develop']
_Argument: Further arguments are parsed to the start_build.py script"

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -h|--help)
            echo -e "$usage";
            exit 0
        ;;

        -gr|--git-repository)
            GIT_REPOSITORY="$2"
            echo -e "GIT_REPOSITORY set to: $GIT_REPOSITORY";
            shift # past argument
            shift # past value
        ;;

        -b|--branch)
            BRANCH="$2"
            echo -e "BRANCH set to: $BRANCH";
            shift # past argument
            shift # past value
        ;;
        *)    # unknown option
            # break
            START_BUILD_KWARGS="${START_BUILD_KWARGS-""} $key $2"
            shift # past argument
            shift # past value
        ;;
    esac
done


if [ -z ${GIT_REPOSITORY-""} ]; then
    GIT_REPOSITORY=https://github.com/kaapana/kaapana.git 
    echo "GIT_REPOSITORY not set, setting it to $GIT_REPOSITORY"
fi

if [ -z ${BRANCH-""} ]; then
    BRANCH=develop
    echo "GIT_REPOSITORY not set, setting it to $BRANCH"
fi

echo kwargs for start_build.py for $START_BUILD_KWARGS
echo Cloning from $GIT_REPOSITORY
echo Building branch $BRANCH
git clone -b $BRANCH --single-branch $GIT_REPOSITORY
pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt -r /kaapana/app/kaapana/build-scripts/requirements.txt
cp /kaapana/app/kaapana/build-scripts/build-config-template.yaml /kaapana/app/kaapana/build-scripts/build-config.yaml
sed -i 's/container_engine: "docker"/container_engine: "podman"/g' /kaapana/app/kaapana/build-scripts/build-config.yaml
python3 /kaapana/app/kaapana/build-scripts/start_build.py $START_BUILD_KWARGS