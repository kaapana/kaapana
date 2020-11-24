# The following commands can be used to test the helm templates
# Make sure you adapt the addresses of the gateway and node according to your setting

# Openmined Gateway
helm install --version 0.1.0-vdev --set port=7000 --set container_port=7000 openmined-gateway-node04 kaapana-public/openmined-gateway 

#Openmined Node
helm install --version 0.1.0-vdev --set id=heidelberg-node --set port=5000 --set grid_network_url=http://10.128.130.139:7000 --set hostname="10.128.130.139" openmined-node kaapana-public/openmined-node

#PySyft Notebook
helm install --version 0.1.0-vdev --set global.registry_url="dktk-jip-registry.dkfz.de"  --set global.registry_project="/kaapana" pysyft-nb kaapana-public/pysyft-nb
