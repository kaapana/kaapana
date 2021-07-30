# Integrated Components of PySyft by Openmined
The following commands can be used to start and test the Helm charts of the integrated PySyft components. Make sure you adapt the addresses according to your setting


## Openmined (release version 0.2.9)

The following three PySyft components can be run in Kaapana. Together the serve as Federated Learning Solution developed by Openmined. 

Source branch: https://github.com/OpenMined/PyGrid/tree/pygrid_0.2.x

Please note that the community is working newer and different architectures  the solution integrated in Kaapana is more or less deprecated by the community. Unfortunately. The newer version is not yet deployable in the Kaapana instrastructure. 

### Openmined PySyft-Grid

Run the following to host a PySyft-Grid on your central Kaapana instance.

```
helm install --version 0.1.0-vdev --set global.id="dkfz" --set global.registry_url="registry.hzdr.de/<name.lastname>/<project>" --set port=7000 --set container_port=7000 openmined-grid-dkfz openmined-grid-chart-0.1.0-vdev.tgz
```
Should be also installable as Kaapana extension via GUI. Lave 

### Openmined PySyft-Node

Run the following to host a PySyft-Node on a participating Kaapana instance.

```
helm install --version 0.1.0-vdev --set global.id="dkfz" --set global.registry_url="registry.hzdr.de/<name.lastname>/<project>" --set port=5000 --set grid_network_url=http://<grid-ip-address>:7000 --set hostname="<own-ip-address>" openmined-node-dkfz openmined-node-chart-0.1.0-vdev.tgz
```
Should be also installable as Kaapana extension via GUI.


### Openmined PySyft Notebook

Run the following to host a PySyft-Notebook on your central Kaapana instance.

```
helm install --version 0.1.0-vdev --set global.registry_url="registry.hzdr.de/<name.lastname>/<project>" openmined-pysyft-nb openmined-pysyft-nb-chart-0.1.0-vdev.tgz
```
Should be also installable as Kaapana extension via GUI.

## Openmined Duet

Duet is only a temporary solution by Openmined. Further, the Kaapana structure changed so the following is deprecated and might not work.

```
helm install --version 0.1.0-vdev --set network.id="42" --set global.registry_url="dktk-jip-registry.dkfz.de/kaapana" --set network.port=5000 --set network.container_port=5000 openmined-pysyft-nb kaapana-public/openmined-pysyft-nb

```
**kaapana-public** it the old Harbor repository. Duet was never migrated to the new project structure.
