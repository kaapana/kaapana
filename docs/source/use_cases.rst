.. _use_cases:

Use Cases
#########

Large-scale multi-centre studies need to handle distributed
data, heterogeneous infrastructure, and varying regulatory requirements
without becoming the bottleneck. Kaapana provides a consistent foundation
for developing, deploying, and governing medical image analysis workflows
across sites — from research to clinical routine.

Multi-Centre Federated Learning
--------------------------------
Train models across hospitals without moving patient data. Kaapana's
federated workflows run the same computation on each site's local data and share only model weights or aggregated results.

Clinical Workflow Automation
-----------------------------
Deploy segmentation, organ analysis, and classification pipelines into
clinical routine. Workflows like TotalSegmentator, BOA, and nnU-Net run
on incoming data automatically or on demand, writing results back as
DICOM objects that radiologists can review directly in OHIF or other
viewers.

Radiomics Feature Extraction at Scale
---------------------------------------
Run reproducible radiomics on large retrospective cohorts. The Radiomics
workflow extracts features from segmentation objects across an entire
dataset in a single run, with outputs in xlsx/csv for downstream
statistical analysis.
