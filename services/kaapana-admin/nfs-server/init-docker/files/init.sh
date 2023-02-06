#!/bin/sh

cat /tmp/dirs.txt | while read line 
do
    echo "Init dir $line"
    dir=/exports/$(echo $line | cut -d' ' -f1)
    user=$(echo $line | cut -d' ' -f2)
    group=$(echo $line | cut -d' ' -f3)

    echo dir:   $dir
    echo user:  $user
    echo group: $group

    if [ ! -d "$dir" ]; then
        echo "$dir does not exist -> creating ..."
        mkdir -p $dir
        chown -R $user:$group $dir
    else
        echo "$dir does already exist -> skipping ..."
    fi
    echo ""
    echo "------------------------------------------------------------------------"
    echo ""
done

echo "Done"
