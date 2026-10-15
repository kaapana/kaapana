.. _projects:

Projects
^^^^^^^^^^

The Projects page shows a list of all projects a user with the keycloak role *user* has access to.
Each project has a *short id* shown next to its name, an 8 char identifier used for example when sending DICOM data (see :ref:`Data Upload<data_upload>`).
The short id also names the project's resources: its MinIO bucket (``project-<short_id>``) and its OpenSearch index (``project_<short_id>``), so a project's data is easy to locate directly in either system.
Project names have at most 13 characters. DICOM transfers can address a project by the AE title ``kp-<project-name>``, and an AE title has at most 16 characters.

Users with the keycloak role *project-manager* or *admin* see all existing projects.
They can add, edit, archive and delete projects, add users to existing projects or change the project role of a user.
Archived projects are read-only, their data is preserved and these projects can be unarchived if needed at any time.
Deleting a project tears down its MinIO bucket, OpenSearch index and roles.
Every series a project receives is also held by the admin project.
Deleting the project permanently removes each series that no other project holds, including the admin project's copy.
Series that other projects also hold stay with them.
Project managers and admins can also enable or disable workflows for a project.