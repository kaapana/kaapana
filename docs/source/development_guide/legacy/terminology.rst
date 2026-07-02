Terminology
^^^^^^^^^^^
List of Kaapana specific terms used in this guide. Note that the reader is also expected to know about containers, images and registries, which are not explained here.

* **Extension**: A component that can be installed and run on the Kaapana platform. List of stable extensions can be found in the :ref:`extensions` section of the documentation.
* **Application Extension**: These extensions deploy standalone web applications, usually accessible via subpaths in the platform (e.g. JupyterLab, MITKWorkbench)
* **Workflow Extension**: These extensions deploy workflows, which are executed via Airflow. Every processing pipeline inside Kaapana is considered a workflow (e.g. nnunet-training, totalsegmentator, collect-metadata)
* **DAG**: Airflow Directed Acyclic Graph, defines a collection of operators that are executed in a specific order. Every workflow inside Kaapana defines a DAG that is managed by Airflow.
* **Operator**: A single task inside a DAG. Kaapana utilizes distributed operators, where each operator is linked to a specific container that is executed in a Kubernetes pod. The scheduler of Airflow is responsible for executing the operators in the correct order.
* **Chart**: A Kaapana extension is technically a Helm package which contains its configuration. It references the container images of the extension, and defines the necessary Kubernetes resources around them.
* **Microk8s**: Kubernetes distribution used in Kaapana. It contains the container runtime called :code:`containerd`, abbreviated as :code:`ctr`, which is used to run containers inside the platform.
* **EDK**: Extension Development Kit, available for versions >= 0.4.0. It provides a development environment inside Kaapana for building and deploying containers and charts. For more information :ref:`extensions_edk`
