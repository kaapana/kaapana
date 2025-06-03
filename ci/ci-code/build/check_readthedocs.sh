#!/bin/bash
set -euf -o pipefail

TOKEN=$KAAPANA_READTHEDOCS_TOKEN
COMMIT=$CI_COMMIT_SHA

curl -s -H "Authorization: Token $TOKEN" https://readthedocs.org/api/v3/projects/kaapana/builds/ -o builds.json
NUM_BUILDS=$( cat builds.json | jq ".results | length" )

for (( c=0; c<=$NUM_BUILDS; c++ ))
do
    output=$( cat builds.json | jq ".results | .[$c] | .version, .success, .commit" )
    declare -a arr=( $output )
    
    if [[ ${arr[0]} == *"latest"* ]] && [[ ${arr[1]} == "true" ]] && [[ ${arr[2]} == *"$COMMIT"* ]] 
    then
        echo "Build for ${COMMIT} on https://readthedocs.org/projects/kaapana/ succeeded!"
        exit 0
    elif [[ ${arr[0]} == *"latest"* ]] && [[ ${arr[1]} == "false" ]] && [[ ${arr[2]} == *"$COMMIT"* ]] 
    then
        echo "Build for ${COMMIT} on https://readthedocs.org/projects/kaapana/ failed!"
        exit 1
    fi;
done

echo "No build found for ${COMMIT} on https://readthedocs.org/projects/kaapana/!"
exit 1