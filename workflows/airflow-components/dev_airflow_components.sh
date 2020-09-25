#!/bin/bash

# Syncs your files between vscode and the specified remote server!
# sudo apt install inotify-tools and sudo apt install rsync must be installed!

SSHKEY=~/.ssh/kaapana.pem
USER=root
DEST=/home/kaapana/workflows/

while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -i|--sshkey)
            SSHKEY="$2"
            echo -e "${GREEN}SSHKEY $SSHKEY ${NC}";
            shift # past argument
            shift # past value
        ;;

        -u|--user)
            USER="$2"
            echo -e "${GREEN}USER $USER ${NC}";
            shift # past argument
            shift # past value
        ;;

        -h|--host)
            HOST="$2"
            echo -e "${GREEN}HOST ${HOST}";
            shift # past argument
            shift # past value
        ;;

        -d|--dest)
            DEST="$2"
            echo -e "${GREEN}DEST $DEST ${NC}";
            shift # past argument
            shift # past value
        ;;

        *)    # unknown option
            echo -e "${RED}unknow parameter: $key ${NC}"
            echo -e "Example usage ./dev_airflow_components.sh -i ~/.ssh/kaapana.pem -u ubuntu -h 10.128.129.28 -d /home/kaapana/workflows/"
            exit 1
        ;;
    esac
done

if [ -z ${HOST+x} ]; then
    echo "You need to specify a host!"
    echo "Example usage ./dev_airflow_components.sh -i ~/.ssh/kaapana.pem -u ubuntu -h 10.128.129.28 -d /home/kaapana/workflows/"
    exit 1
fi

echo Sychning with $SSHKEY to $USER@$HOST:$DEST

while inotifywait -r -e modify,create,delete $PWD
do
    rsync -avzh --include="*/" --include "*.py" --include "*.json" --exclude="*" --delete -e "ssh -i $SSHKEY" $PWD/* $USER@$HOST:$DEST
done

#rsync -avzh --include="*/" --include "*.py" --exclude="*" --delete -e "ssh -i ~/.ssh/kaapana.pem" $PWD/* ubuntu@10.128.129.6:/home/kaapana/workflows/