.. _concepts_interactive_workflows:

Interactive Workflows
#######################################

A workflow step is not limited to running a processing-container to completion on its own -- it can hand off to a human instead, and wait.

Spawning an Application and Waiting
=======================================

``KaapanaBaseOperator``'s ``launch_application_chart`` calls the :ref:`Kube-Helm API<concepts_architecture>`'s ``helm-install-chart`` endpoint to deploy an application (a long-running extension such as MITK Workbench or JupyterLab).
The step then polls the Kube-Helm API's chart status and only continues once that release is gone -- torn down when the application signals it is done.

This is the mechanism behind interactive workflows such as **MITK-Flow**: a workflow spawns a running application, a person interacts with it, and the workflow only resumes once that interaction is reported as finished.

What This Enables
=====================

Because a workflow step can wait on an arbitrary running application rather than only a processing-container, the same mechanism covers any human-in-the-loop step: a confirmation before a workflow proceeds, manual annotation or correction of an intermediate result, or a review step before results are finalized -- the workflow step itself does not need to know which of these it is waiting for, only that the application's Helm release still exists.
