# The following commands can be used to test the Openmined helm charts
# Make sure you adapt the addresses according to your setting

# Openmined Duet
helm install --version 0.1.0-vdev --set network.id="42" --set global.registry_url="dktk-jip-registry.dkfz.de/kaapana" --set network.port=5000 --set network.container_port=5000 openmined-pysyft-nb kaapana-public/openmined-pysyft-nb

### Openmined release 0.2.9 (deprecated) ###
# Branch: https://github.com/OpenMined/PyGrid/tree/pygrid_0.2.x

# Openmined Grid
helm install --version 0.1.0-vdev --set global.id="dkfz" --set global.registry_url="registry.hzdr.de/<name.lastname>/<project>" --set port=7000 --set container_port=7000 openmined-grid-dkfz openmined-grid-chart-0.1.0-vdev.tgz

# Openmined Node
helm install --version 0.1.0-vdev --set global.id="dkfz" --set global.registry_url="registry.hzdr.de/<name.lastname>/<project>" --set port=5000 --set grid_network_url=http://<grid-ip-address>:7000 --set hostname="<own-ip-address>" openmined-node-dkfz openmined-node-chart-0.1.0-vdev.tgz

# PySyft Notebook (can also be installed as extension via GUI)
helm install --version 0.1.0-vdev --set global.registry_url="registry.hzdr.de/<name.lastname>/<project>" openmined-pysyft-nb openmined-pysyft-nb-chart-0.1.0-vdev.tgz
