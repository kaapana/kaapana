# The following commands can be used to test the helm templates
# Make sure you adapt the addresses of the grid-network and grid-node according to your setting

# Openmined Gateway/Grid-Network
helm install --version 0.1.0-vdev --set global.id="my-gateway" --set global.registry_url="dktk-jip-registry.dkfz.de"  --set global.registry_project="/kaapana" --set port=7000 --set container_port=7000 openmined-grid-network kaapana-public/openmined-grid-network

#Openmined Node
helm install --version 0.1.0-vdev --set global.id="heidelberg" --set global.registry_url="dktk-jip-registry.dkfz.de" --set global.registry_project="/kaapana" --set port=5000 --set grid_network_url=http://10.128.130.139:7000 --set hostname="10.128.130.139" openmined-grid-node kaapana-public/openmined-grid-node

#PySyft Notebook
helm install --version 0.1.0-vdev --set global.registry_url="dktk-jip-registry.dkfz.de"  --set global.registry_project="/kaapana" pysyft-nb kaapana-public/pysyft-nb
