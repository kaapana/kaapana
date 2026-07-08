.. _concepts_federated_learning:

Federated Learning
####################

Federated execution lets several independent Kaapana instances collaborate on a computation (training a model, aggregating radiomics features, collecting metadata) **without moving raw patient data** between them.
Only intermediate artifacts -- model weights, aggregated statistics, extracted features -- ever cross an instance boundary.

Coordinator and Remote Instance Roles
==========================================

A federation consists of one **coordinator** instance and one or more **remote** instances, registered with each other through the :ref:`Instance Overview<instance_overview>` component (shared instance tokens and, optionally, Fernet encryption for the data exchanged between them).
The web interface calls these the same roles by different names: the coordinator is the job's **Owner Instance**, and the remote instances it distributes work to are the **Runner instances**.
Each remote instance independently decides which of its own DAGs and datasets it makes available to the federation -- the coordinator cannot execute or read anything the remote instance hasn't explicitly allowed.

The orchestration flow
========================

.. mermaid::

    sequenceDiagram
        participant C as Coordinator DAG
        participant R1 as Remote instance 1
        participant R2 as Remote instance 2
        participant M as MinIO (presigned URLs)

        loop each federated round
            C->>R1: distribute job (local counterpart DAG)
            C->>R2: distribute job (local counterpart DAG)
            R1->>R1: run workflow on local data
            R2->>R2: run workflow on local data
            R1->>M: upload round result
            R2->>M: upload round result
            C->>M: download round results
            C->>C: aggregate (e.g. federated averaging)
        end
        C->>R1: distribute final/next round job

A federated workflow on the coordinator side is built around a **round**: it distributes a job to every registered remote instance (each remote instance runs the ordinary, non-federated counterpart workflow locally), waits for all of them to finish, downloads their results from MinIO via time-limited presigned URLs, aggregates them, and either starts another round or finalizes.
This distribute-wait-aggregate loop is implemented once, in a shared base class, and reused by every federated workflow -- individual workflows only implement what "aggregate" means for their use case.

Kaapana ships a handful of federated example workflows built on this base: federated nnU-Net training (which aggregates model weights and, in one mode, dataset intensity statistics across sites), federated radiomics feature extraction, federated metadata collection, and a minimal test pair used to validate that a newly connected federation is wired up correctly.

.. note::
   This orchestration logic currently lives in :term:`kaapana-backend`, not in the newer ``workflow-api`` / ``data-api`` services described in :ref:`concepts_architecture`.
   If you are extending federated execution today, you are extending the legacy backend's federation endpoints, not the new workflow model.

Security model
================

Federation relies on the same building blocks as everything else in Kaapana: mutual instance registration with shared secrets and encrypted transport for sensitive payloads (see :ref:`Access Control<access_control_root>`).
However, federated capabilities are currently only supported in the ``admin`` project and only enabled for system admin users.
A remote instance is never given direct access to the coordinator's data or vice versa -- all it receives is a job to run against its own data, and all it returns is the artifact its local workflow produced.

Building a new federated workflow
====================================

If you need a new federated workflow, look at one of the existing ones as a template rather than starting from scratch: subclass the shared federated-training base class, implement the aggregation step for your use case, and provide the non-federated counterpart DAG that each remote instance runs locally.
See :ref:`workflow_dev_guide` for how workflow extensions are structured in general.

Future Direction
================

Federation is currently Kaapana's own round-based orchestration, implemented once in a shared base class and reused by every federated workflow -- it is not built on top of an external FL framework. Making federation agnostic to the FL engine is planned: a coordinator will be able to drive a round through a different, external FL framework instead.
