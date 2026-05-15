.. _projects:

Projects
^^^^^^^^^^

The Projects page shows a list of all projects a user with the keycloak role *user* has access to.
Each project has a *short id* shown next to its name, an 8 char identifier used for example when sending DICOM data (see :ref:`Data Upload<data_upload>`).

Users with the keycloak role *project-manager* or *admin* see all existing projects.
They can add, edit, archive and delete projects, add users to existing projects or change the project role of a user.
Archived projects are read-only, their data is preserved and these projects can be unarchived if needed.
Additionally, they can enable or disable the execution of workflows for a project.