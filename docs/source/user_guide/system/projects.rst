.. _projects:

Projects
^^^^^^^^^^

The Projects page shows a list of all projects a user with the keycloak role *user* has access to.
Each project has a *short id* shown next to its name, an 8 char identifier used for example when sending DICOM data (see :ref:`Data Upload<data_upload>`).
The short id also names the project's resources: its MinIO bucket (``project-<short_id>``) and its OpenSearch index (``project_<short_id>``), so a project's data is easy to locate directly in either system.
Project names follow DICOM AE-title rules -- up to 16 characters -- since a project name doubles as the AE title used for DICOM routing.

Users with the keycloak role *project-manager* or *admin* see all existing projects.
They can add, edit, archive and delete projects, add users to existing projects or change the project role of a user.
Archived projects are read-only, their data is preserved and these projects can be unarchived if needed at any time.
Deleting a project tears down its resources -- MinIO bucket, OpenSearch index, roles, its system user in Keycloak, and its Kubernetes namespace with its volumes (workflow data, models, TensorBoard logs and the storage of applications started in the project) -- along with any DICOM series held only by that project.
Workflows and applications still running in the project are stopped.
On Longhorn storage, application storage of the *slow* storage class stays on disk after the delete.
This cannot be undone; to keep a project's data, archive the project instead.
Additionally, they can enable or disable the execution of workflows for a project.