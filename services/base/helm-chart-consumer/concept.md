# Concept for Helm Chart Consumer

## Extension Mechanism Overview
This image should help to understand how the Helm Chart Consumer is embedded in the system architecture and how it interacts with the Extension Manager.

![](https://s3.desy.de/hackmd/uploads/60929317-c85c-4cf7-a110-43dd963e88a3.png)

### System context diagram
![](https://s3.desy.de/hackmd/uploads/24431a6d-e807-4f63-9fc7-d8b146aa9871.png)


## Extension source code with content helm-chart
```bash
|- extension_manifest.json
|_ helm-chart-content/
   |- helm-chart-content.json ### corresponds to workflow.json; Kaapana facing information (e.g. multiinstallable, UI parameter)
   |_ chart/         ### contains only helm specific files
```


## Container diagram for helm-chart consumer

![](https://s3.desy.de/hackmd/uploads/265a2d89-5730-4c89-8373-4cbed649cd48.png)



## Api Requirements (to be extended) given by Extension-System
- install extension content of type helm-chart
- uninstall extension content of type helm-chart
- [optional]: update extension content of type helm-chart


## User Stories
- As an user I want to interact with an frontend deployed by an helm-extension (e.g. a JupiterLab Notebook that also contains an Web-UI)


## User groups
* user: vague user group. Role (of one of the below) is implied by context of the user story / epic.
* scientist: Can use applications in a project.
* principal-investigator: Can deploy and manage applications in a project.
* kaapana-system admin: Has admin access to all resources in Kaapana.
* platform-operator: Operators a Kaapana instance. Has access to all parts of the platform and deployment environment.
* extension-developer: Someone developing extensions and helm-chart content.

## Priorities
Priorities define in what stage of the development process the given user story / epic should be implemented
* MVP - Defines all user stories that a minimal viable product MUST support
* Release 2 - Defines user stories that will be supported by the second release
* Later - Defines user stories that will only be supported at a later stage or if the user story is requested by a customer.

## Epics

### Epic: Applications with a frontend per user

As a scientist I want to work with a coding environemnt (like JupyterLab) to analyze the data that I have access to in a project.

#### User Story: Installing the extension that contains the helm-chart content in Kaapana
As a kaapana-system-admin I want to install an extension that contains a helm-chart-content.

Acceptance criteria:
* The extension-manager dispatches content of helm-chart to the Helm-Chart Consumer.
* The helm-chart consumer registers the helm-chart content.

#### User Story: Enabling applications in a project
As a kaapana-system-admin I want to enable and disable applications for projects, such that some applications can only be used in some projects.

Acceptance criteria:
* Applications can be disabled for a project.
* Applications can only be deployed in projects, where they are enabled.

#### User Story: Deploying applications
As a principal-investigator (PI) of a project I want to deploy a JupyterLab Notebook for one of the scientists in my project.

Acceptance criteria:
* A principal investigator can browse all applications that he can deploy in his project.
* Before the helm release is created, helm executes a dry-run installation to check for errors or misconfigurations
* Deploy an application
* Undeploy an application

#### User Story: Opening an application
As a scientiest I want to open the web interface of an application to start working.

Acceptance criteria:
* Browse deployed applications
* Open deployed applications

#### User Story: Saving application data
As a scientist, I want to use the results I generated through my application in a workflow of my project.

Acceptance criteria:
* Applications support writing to persistent storage options in a kaapana platform like e.g. data-api, minio

#### User Story: Working on existing data
As a scientist, I want to access and work on data that is available in my project from within an application (e.g. loading segmentations into an segmentation viewer)

Acceptance criteria:
* Applications support loading from persistent storage options in a kaapana platform like e.g. data-api, minio

#### User Story: Continue previous work
As an scientist I want to continue working in my application where I left off last time. This could be e.g. contiue writing code in the JupiterLab web-application ui. 

Acceptance criteria:
* A deployed helm-chart-content can have persistent state.
* Deployed helm-chart content has a human readable identifier.

#### User Story: Configuring an application at deploy
As a principal-investigator I want to set parameters when I deploy an application (e.g. a display name, which folder of the project bucket to sync, whether it needs a GPU), so that the instance fits the task.

Acceptance criteria:
* A helm-chart-content declares deploy parameters (type, default, description) in helm-chart-content.json.
* Supported parameter types cover at least string, boolean and single choice from a list.
* The frontend renders a deploy form from these declarations.
* Deploy values are mapped onto chart values.
* Input parameters are validated (e.g. through regex, or helm lint)

### Epic: Deploy time management of applications
As a scientiest I want to monitor the state of a deployed application.

#### User Story: Seeing the status of a deployed application
As a scientist I want to see whether my deployed application is starting, ready or broken, so that I know whether I can open it or need help.

Acceptance criteria:
* Each deployed application shows a readiness state.
* Details show the underlying pods (status, restarts, age)
* A failed deploy shows an understandable reason and lists the bug details.

#### User Story: Seeing the configuratoin of a deployed application
As a scientist I want to see the deployment values / configuration the application is deployed with.

Acceptance criteria:
* A view shows the deployment values of the installed applications


### Epic: Helm-chart content development
As a extension-developer I want to package my application as a helm-chart content in a Kaapana extension, such that every Kaapana deployment can use it.

#### User Story:
As an extension-developer I want to know, how I can ensure that the kubernetes objects of my helm chart do not collide with existing resources in the k8s cluster, e.g. due to an uniqueness constraint of an object name.

Acceptance criteria:
* Maybe naming rules, using namespaces. TBD

#### User Story: Authentication against Kaapana APIs
As an extension-developer I want to give my application authenticated access to Kaapana APIs, such that I can e.g. trigger workflows, communicate with the Data API, read metrics from Prometheus.


### Epic: Permission and access control
As a product owner I want that any action performable via the helm chart consumer or the extension manager has to be authorized.


#### User Story
As a platform operator I want to create a custom access control model, that fits
the requirements of my project (e.g. Raccoon)

Acceptance criteria
* Custom roles can be created
* Roles can be mapped to actions
* Kaapana users can be assigned to a role.


#### User Story:
As kaapana-system admin I want to configure which deployment configuration parameters are accessable to which role in the access control model (e.g. scientist).

Acceptance criteria:
* On application deployment configuration values are only configurable if the user has permission.
* Unavailable application deployment configuration values stay at their default values.

Priority: later

Context: 
If different user groups are able to deploy an application, then it may not be save to let e.g. a scientist set deployment parameters like storage mounts, or network rules, it is however save to e.g. let him configure if the application requires a GPU.


#### User Story: Restricting who can open an application
As a principal-investigator I want only members of my project to open the applications deployed in it, so that project data stays inside the project.

Acceptance criteria:
* The web interface of a launched application is only reachable for members of its project.
* Browsing launched applications only shows those of the current project.
* Project scoped applications can only access project data



### Epic: Interactive steps in workflows
As a scientist I want a workflow to pause at a step where I work in an application (e.g. correcting segmentations in MITK) and continue with my results afterwards.

Priority: Release 2

#### User Story: Launching an application from a workflow
As a workflow developer I want a workflow task to launch an application with the data of the current workflow run.

Acceptance criteria:
* A workflow task can launch an application of a registered helm-chart-content through the consumer's API.
* Some run data is available in the application.
* The launched application is marked as started by a workflow run.

#### User Story: Finishing an interactive step
As a scientist I want to signal that I am done in the application, so that the workflow continues and the application is cleaned up.

Acceptance criteria:
* The user can mark a workflow-launched application as finished.
* Finishing removes the launched application.
* The waiting workflow task detects this and continues.
* The user sees how many applications in their project are waiting for input.

#### User Story: Cleaning up abandoned interactive steps
As a kaapana-system-admin I want applications launched by workflows to be removed when the workflow fails or times out, so that they do not consume resources forever.

Acceptance criteria:
* A workflow-launched application is removed when its task fails, is retried or times out.


### Epic: Multideployable applications in projects
As a principal-investigator I want to deploy multiple instances of an application (e.g. JupyerLab) in my project, such that each scientist can use one instance independently.

#### User Story: Deploy an application multiple times
As a PI I want to be able to launch the same multiinstallable application several times

Acceptance criteria
* Multiple applications can be deployed without conflicts (e.g. in the chartname, ...)
* Each accessible resource is accessible via a unique URL

#### User Story: Use case description for deployed applications
As a principal-investigator I want to write a use case description when I deploy an application, in order to not forget, why the application was deployed.

Acceptance criteria:
* When an application is deployed it can be given a usecase description.

#### User Story: Identifiying deployed applications
As a scientiest I want to know which applications I worked with in my last session, such that I can continue to work where I left.

Acceptance criteria:
* Deployed applications have a unique human readable identifier in the user interface.

#### User Story: Developing multiinstallable applications without conflicts
As a developer I want to know how I can make an helm-chart-content multideployable in a project.

Acceptance criteria:
* Documentation that describes the requirement for a helm-chart-content to be multideployable in a project.
* Concept for avoiding conflicts when installing multiple instances of an application (e.g. naming pre-fixes/post-fixes that are filled via values.yaml) so the developer can adhere.

### Epic: Globally deployed platform applications
As a kaapana-system-admin I want to deploy applications that are deployed only once (e.g. Collabora, OHIF, SLIM, ...) and are accessable from different projects and users. Users can access shared or project specific data through the applications.


#### User Story: Configure an application to be cluster wide.
As a kaapana-system-admin I want to deploy to configure an application to be deployed for the whole platform.

Acceptance criteria:
* All permitted users can view available platform wide applications
* All permitted users can access available platform wide applications

### Epic: Globally multideployable applications
As a kaapana-system-admin I want to deploy multiple instances of an application in the cluster, such that different deployment configurations of the same application can exist simultaniously.

Priority: later


### Epic: Updating applications
As a user I want to update a deployed application, because I want to change its configuration or upgrade to a new version of the helm-chart-content.

Context:
User role can be kaapana-system-admin or principle-investigator depending on if the application is globally installed or installed in a project.

#### User Story: Browse available versions
As a user I can see which versions of an application are available.

Acceptance criteria:
* List all available version of an application
* Helm-chart-content has a version

#### User Story: Updating a deployed application to a new version
As a user I want to update an application to a new version, such that I get the benefits of the new version of an application

Acceptance criteria:
* API supports application updates
* Data is persisted from one version to the other
* Not needed application-state and data is cleaned
* The state of the deployed application is UPDATING

#### User Story: Updating deployment parameters
As a user I want to update the deployment parameters of a deployed application, such that I can change volume size, resources and other available deployment parameters.

Acceptance criteria:
* API supports updating application parameters
* Data is persisted between updates
* Previous (before update) set configuration parameters are prefilled as default values.
* There is an option to reset parameters to the applications defaults.
* Deployment parameters are configurable also during update, not only during initial deploy. 
* It should be easy to keep the previous application deployment parameters from before the update.


#### User Story: Set deployment parameters when updating the application version
As a user I want to set the deployment parameters when I update an application, because a new version can introduce new parameters.

Acceptance criteria:
* I can update deployment parameters also when updating the version.

Context:
The new version of an application could introduce new parameters that should be configurable in update, or change behaviour for existing parameters.

### Epic: Uninstalling extension with helm-chart-content
As a kaapana-system-admin I want that when I uninstall an extension with an helm-chart-content the helm-chart-content cannot be installed anymore.

Acceptance critera
* Deployed applications are not effected

### Epic: Update extension with helm-chart-content
As a kaapana-system-admin I want that only helm-chart-content versions of installed extensions can be deployed.

Acceptance criteria
* When an extension with an helm-chart-content is updated, the helm-chart-content of the old version is removed
* Deployed applications that are on an old version are marked that a new version is available

Context:
An extension can contain a helm-chart-content. If an extension is installed the helm-chart-content is installed at the helm-chart-consumer. The version of the helm-chart-content is set in the extension. If the extension is uninstalled, the helm-chart-content with the corresponding version is also uninstalled from the helm-chart-consumer. A deployed application is an instance of a helm-chart-content that was deployed with the helm-chart-consumer. A helm-chart-content can be uninstalled from the helm-chart-consumer while deployed applications still persist.

_____




## Glossary

* helm-chart content: The content type of an extension that is managed by the Helm Chart Consumer
* application: See helm-chart content
* Helm Chart Consumer: The system component that manages helm-chart contents of an extension
* Deployed application: 


