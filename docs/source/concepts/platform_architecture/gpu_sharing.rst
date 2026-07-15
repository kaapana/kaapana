.. _concepts_gpu_sharing:

GPU Sharing Strategy
#####################

GPU-accelerated :term:`processing-containers<processing-container>` (training, inference, registration, ...) usually only need a fraction of a modern GPU's memory, but Kubernetes' native way of requesting a GPU (a ``nvidia.com/gpu`` resource limit) only understands whole devices: a pod either gets an entire GPU or none at all.
On a cluster with a handful of GPUs shared by many workflows, that would leave most of a GPU's memory idle whenever a job doesn't need all of it.

Kaapana instead implements its own **memory-aware, space-based** GPU scheduler on top of Airflow, so that several tasks can share the same physical GPU as long as their combined memory requirement fits.

How a task gets a GPU
======================

.. mermaid::

    sequenceDiagram
        participant D as DAG (KaapanaBaseOperator)
        participant S as Airflow scheduler
        participant U as UtilService
        participant P as Prometheus and DCGM exporter
        participant Pod as Task pod

        D->>S: task requests gpu_mem_mb
        loop before every queue attempt
            S->>U: check_operator_scheduling(task_instance)
            U->>P: current free and reserved memory per GPU
            P-->>U: per GPU utilization
            U-->>S: chosen GPU (id, uuid) or "not yet"
        end
        S->>S: store gpu_device in executor_config
        S->>Pod: launch pod for queued task
        Pod->>Pod: pin NVIDIA_VISIBLE_DEVICES to the assigned GPU

A DAG author requests a GPU by setting ``gpu_mem_mb`` on a ``KaapanaBaseOperator``.
From there:

#. The operator stores this requirement in the Airflow task's ``executor_config`` and, unless scheduling is explicitly disabled, places the task in the ``NODE_GPU_COUNT`` Airflow pool rather than the plain RAM-based pool -- this is what limits how many GPU tasks Airflow allows to run at once, in addition to the check below.
#. Before queuing the task, a patched Airflow scheduler calls into ``UtilService.check_operator_scheduling()``. This function reads live GPU memory metrics (free/used/reserved) from Prometheus, sourced from the NVIDIA DCGM exporter, and combines them with the memory already reserved by other scheduled/queued/running tasks to compute how much headroom each GPU actually has.
#. It picks the least-loaded GPU with enough free headroom for the request, and writes the chosen GPU's id and UUID back into the task's ``executor_config``. If no GPU currently has enough room, the task is left unscheduled and retried on the next scheduling pass.
#. Once the pod for that task starts, the operator reads the assigned GPU back out of ``executor_config`` and sets ``NVIDIA_VISIBLE_DEVICES`` to that GPU's UUID and ``CUDA_VISIBLE_DEVICES=0``, so the container always sees its assigned GPU as device 0, regardless of which physical GPU it actually is.

The Kubernetes pod itself never requests a ``nvidia.com/gpu`` resource -- from Kubernetes' point of view it is an ordinary pod.
All admission control happens earlier, inside the Airflow scheduler.

Why not Kubernetes-native GPU sharing?
=======================================

Kubernetes does have native mechanisms for sharing GPUs (the NVIDIA device plugin's time-slicing, or Dynamic Resource Allocation).
Kaapana does not use either of them today.
The scheduler-level approach was chosen instead because it allocates by **memory headroom** rather than by device count or fixed time slices, and because the scheduler already has direct visibility into per-GPU memory state via Prometheus -- no additional cluster-level device plugin configuration is required to get fine-grained sharing.

The trade-off is that GPU admission control lives entirely in Kaapana/Airflow rather than in Kubernetes: at most one task instance is pinned to a given GPU at a time by this mechanism, and there is no time-slicing or oversubscription beyond the memory-based packing described above.

Requesting a GPU in a DAG
==========================

.. code-block:: python

   from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator

   my_task = KaapanaBaseOperator(
       dag=dag,
       name="my-gpu-task",
       image="my-gpu-image",
       gpu_mem_mb=4096,  # request 4 GiB of GPU memory
   )

Setting ``gpu_mem_mb=None`` (the default) means the task does not request a GPU and will run with GPU access disabled (``NVIDIA_VISIBLE_DEVICES=none``).
See :ref:`operators` for the full set of ``KaapanaBaseOperator`` parameters, and the :doc:`GPU usage FAQ </faq/gpu_usage>` for troubleshooting driver/CUDA version mismatches.

.. note::
   GPUs are identified by their stable hardware UUID (reported by DCGM) rather than their local device index, so allocation stays correct even if the local GPU ordering changes after a driver reload or a hot-swap.
