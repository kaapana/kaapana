.. _workflow_execution:

Workflow Execution
^^^^^^^^^^^^^^^^^^

The Workflow Execution component of the WMS serves to configure and execute workflows on 
the Kaapana platform. This component is the only location on the platform to start 
executable instances which will run as DAG-runs in Kaapana`s workflow engine Airflow. 
The Workflow Execution component can either be directly accessed from Workflows -> Workflow Execution 
or from the Datasets component. 
Workflows are configured in the following way:

* specify runner instance(s), i.e. the instances on which jobs of the configured workflow should be executed.
* select the Airflow-DAG which should be run and further configured with DAG-specific specification
* select a dataset is selected with the data which should be processed within the workflow

Remote and Federated Workflow Execution
""""""""""""""""""""""""""""""""""""""""

Workflows can be executed in the following ways:

* Local execution: Workflow is orchestrated by the same instance that serves as runner instance.
* Remote execution: Workflow is orchestrated by another instance that serves as a runner instance.
* Federated execution: The workflows-orchestrating instance coordinates the execution of jobs on both local and remote instances. These jobs then report back data/information to the orchestrating instance. This mode is particularly useful for federated learning scenarios.
  
  - On the orchestrating instance a federated orchestration DAG has to be started which then automatically spawns up runner jobs on the workflow`s runner instances.

Both remote and federated executed workflows are triggered from the Workflow Execution component.
Concerning remote and federated execution of workflows, it is worth mentioning that Kaapana 
provides several security layers in order to avoid adversarial attacks:

* Each Kaapana platform has a username and password-protected login
* The registration of remote instances is handled by the instance name and a random 36-char token
* Each remote/federated communication can be SSL verified if configured
* Each remote/federated communication can be fernet encrypted with a 44-char fernet key if configured
* For each Kaapana platform, the user can configure whether the local instance should check automatically, regularly for updates from connected remote instances or only on demand
* For each Kaapana platform, the user can configure whether the local instance should automatically execute remote/federated workflow jobs which are orchestrated by a connected remote instance
  
  - If automatic execution is not allowed, remote/federated workflows will appear in the Workflow List with a confirmation button

* Remote/federated workflow jobs can always be aborted on the runner instance to give the user of the runner instance full control about her/his instance
