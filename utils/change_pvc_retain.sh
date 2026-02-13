#!/bin/bash


microk8s.kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.storageClassName}{"\n"}{end}' | while read -r pv_name sc_name; do

    echo "Checking PV: $pv_name (StorageClass: $sc_name)"

    # Check if the StorageClass matches the exclusion rule
    if [ "$sc_name" == "kaapana-hostpath" ]; then
        echo ">> Skipping: $pv_name uses kaapana-hostpath."
        continue
    fi

    # Check current policy
    policy=$(microk8s.kubectl get pv "$pv_name" -o jsonpath='{.spec.persistentVolumeReclaimPolicy}')

    if [ "$policy" == "Delete" ]; then
        echo ">> Patching $pv_name to Retain..."
        microk8s.kubectl patch pv "$pv_name" -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
    else
        echo ">> No action: $pv_name is already set to $policy."
    fi
    
    echo "-----------------------------------"
done

echo "Process complete."