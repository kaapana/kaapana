.. _concepts_monitoring_and_resources:

Monitoring and Resource Allocation
####################################

Kaapana schedules CPU, RAM and GPU for every task through Airflow, and exposes cluster and task health through Prometheus, Grafana and Loki.

Requesting resources
======================

A ``KaapanaBaseOperator`` requests memory and CPU explicitly (``ram_mem_mb``, ``cpu_millicores``, with matching ``_lmt`` limit parameters that default to the request plus a small headroom); these map directly onto the task pod's Kubernetes resource requests and limits.
GPU works differently and has its own memory-aware allocator; see :ref:`concepts_gpu_sharing`.

Admission via Airflow pools
==============================

Before Kubernetes ever sees a task, Airflow's own pool mechanism decides whether there is room to run it: ``NODE_RAM`` and ``NODE_CPU_CORES`` pools track available headroom, resized continuously by the same utilization service that also drives GPU allocation.
This is what stops Airflow from queuing more work onto a node than it has capacity for, ahead of -- and in addition to -- Kubernetes' own scheduling.

Per-project limits
=====================

Each project namespace ships with a Kubernetes ``LimitRange`` that sets a default memory request/limit for containers that don't specify one.
This is a **default, not a ceiling**: there is currently no ``ResourceQuota`` capping the total CPU or memory a project can consume.

Observing the platform
=========================

Prometheus scrapes cluster metrics as well as GPU metrics from the NVIDIA DCGM exporter; Grafana ships with dashboards for the Kubernetes cluster, node exporter, Airflow, individual operators, GPUs, and Traefik; Loki aggregates container logs across the platform.
See :ref:`monitoring` for how to reach Grafana and Loki from the web interface.
All shipped dashboards are cluster-wide -- there is no per-project resource-usage view today.
