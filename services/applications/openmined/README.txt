# The following commands can be used to test the Openmined helm charts
# Make sure you adapt the addresses according to your setting

# Openmined Duet
helm install --version 0.1.0 --set network.id="42" --set global.registry_url="dktk-jip-registry.dkfz.de/kaapana" --set network.port=5000 --set network.container_port=5000 openmined-pysyft-nb kaapana-public/openmined-pysyft-nb

# Openmined release 0.2.9 (deprecated)
# Openmined Gateway/Grid-Network
helm install --version 0.1.0 --set global.id="my-gateway" --set global.registry_url="dktk-jip-registry.dkfz.de/kaapana" --set port=7000 --set container_port=7000 openmined-grid-network kaapana-public/openmined-grid-network

#Openmined Node
helm install --version 0.1.0 --set global.id="heidelberg" --set global.registry_url="dktk-jip-registry.dkfz.de/kaapana" --set port=5000 --set grid_network_url=http://10.128.130.139:7000 --set hostname="10.128.130.139" openmined-grid-node kaapana-public/openmined-grid-node

#PySyft Notebook
helm install --version 0.1.0 --set global.registry_url="dktk-jip-registry.dkfz.de/kaapana"  pysyft-nb kaapana-public/pysyft-nb
