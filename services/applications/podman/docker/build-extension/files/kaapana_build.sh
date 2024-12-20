#!/bin/bash
set -euf -o pipefail

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -h|--help)
            echo -e "build extension in container";
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

    esac
done

echo Cloning from $GIT_REPOSITORY
echo Building branch $BRANCH

git clone -b $BRANCH --single-branch $GIT_REPOSITORY

echo successfully cloned repository

echo Downloading extensionctl
# TODO
