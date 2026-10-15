# PipeGen Configuration Blueprint

This folder contains the architectural design blueprint for PipeGen by CraftifAI:
- `pipeline_ir.json`: PipeGen Node Graph Intermediate Representation for Track 2 (Worker Safety / Danger Zone Sentinel).
- Target model: PeopleNet (TensorRT FP16 / INT8).
- Downstream safety supervisor: `watchdog.py`.
