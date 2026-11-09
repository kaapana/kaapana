## Q1 Ownership
Is a deployed application assigned to one scientist or shared by the whole project? Story 2.1 deploys "for one of the scientists" and Epic 8 aims at one instance per scientist, but Story 5.3 lets every project member open every application of the project.

### Answer
Every project member can open every application of the project. Applications can be deployed for the whole project or a single scientist. However, each scientist can access them.


## Q2 Who deploys
Only PIs (Stories 2.1, 5.1), or scientists as well? Story 5.5 assumes that other user groups may deploy.

### Answer
Only PIs can deploy applications


## Q3 Parallel versions
Can several versions of the same helm-chart content be registered at the same time? The Extension Manager allows installing several tags of an extension, Story 1.3 deregisters the old version on update, Story 11.1 lists all available versions.

### Answer
Yes, several version for the same helm-chart-content can be registered at the same time. Since otherwise e.g. two different extensions that use different versions would not be supported.


## Q4 Deregistered content
Can a deployed application whose helm-chart content was deregistered (Story 1.2) still change its deploy parameters? Helm keeps the chart of every release, so it would be technically possible.

### Answer
Yes.


## Q5 Persistent volumes on undeploy
Are they deleted, kept, or does the PI decide (Story 2.3)? Kept volumes need a way to be reattached or cleaned up.

### Answer
If an application is undeployed because it is no longer needed (Story 2.3) persistent volumes are deleted and the data should be cleaned.


## Q6 Namespaces
Do deployed applications run in one namespace per project, one per deployed application, or a shared namespace? This affects Stories 4.3, 5.3 and 6.1.

### Answer
TBD: The answer is required at a later stage.


## Q7 Identity of API credentials
Does an application act on behalf of the PI who deployed it, of the scientist who opens it, or of the project (Story 4.5)?

Raised in 4.5

### Answer
An application acts on behalf of the project with the same permissions as a scientist in this project.
Possible via project user or a dedicated client.


## Q8 Default enablement
Is a newly registered application enabled or disabled in all projects (Story 5.2)?

### Answer
Disabled by default.


## Q9 Project deletion
Are the deployed applications of a deleted project undeployed automatically, or is the deletion refused (Story 12.2)?

### Answer
Deletion is refused


## Q10 Offline installations
How are the container images referenced by a chart made available in air-gapped Kaapana installations?

### Answer
The helm-content-consumer does not have to care about that.


## Q11 Scope
Can a helm-chart content support both scopes (project and platform-wide), and does the kaapana-system-admin choose the scope at deploy (Stories 4.2, 9.1)?

### Answer
Yes it can support both. But does not have to. If both are supported, then only the kaapana-system-admin can chose the scope on deploy. The principle-investigator can not install platform-wide.