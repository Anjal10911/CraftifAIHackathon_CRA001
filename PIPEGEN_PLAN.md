# PipeGen Plan: Guardian Vision (with Blind-Spot Watchdog)

**HackwithBangalore 4.0** | [Event Link](https://luma.com/5z8w42mq) | **Track 2:** PipeGen (Computer Vision & Edge AI)

---

## 1. Requirement Sentence
> *Copy & paste into PipeGen's Requirement Stage:*
>
> "Detect people in a video or USB camera stream. Raise an alert when a person stays inside a defined danger zone for more than 3 seconds. Output a JSON metadata feed and MQTT alerts with person count, zone status and timestamp. Show the video live with boxes and the zone drawn."

*Note: Adapt zone dwell time and metadata labels if PipeGen's prebuilt cards suggest slight variations, keeping person detection, danger zone analytics, and JSON/MQTT output intact.*

---

## 2. Pipeline Design Matrix

| Component | Target Specification | Purpose |
|---|---|---|
| **Input Source** | Video file under `/home` first; USB / RTSP camera next | Testable offline & live demo |
| **Vision Task** | Person detection, tracking, zone dwell-time analytics | Identify safety hazard events |
| **Model** | Closest catalog person-detection repository (or Deep Search) | Optimized edge inference |
| **Precision** | FP16 primary; INT8 secondary for Edge Optimization comparison | Benchmark edge performance |
| **Outputs** | Live display overlay, JSON metadata feed, MQTT alerts | Immediate & downstream integration |
| **Watchdog Add-on** | `watchdog.py` monitors JSON feed activity | Fail-safe: triggers SYSTEM BLIND on freeze/crash |

---

## 3. Why This System Stands Out: Fail Loudly
Most computer vision pipelines only show positive detections. When an edge camera gets unplugged, a cable is severed, or a GPU pipeline hangs, conventional systems fail silently—leaving operators with a false sense of security.

The **Blind-Spot Watchdog** ensures the safety system **fails loudly**:
1. Monitors the heartbeat of the vision feed.
2. Raises immediate alerts (`SYSTEM_BLIND`) when pipeline output stalls.
3. Logs recovery timestamps (`RECOVERED`) with exact downtime duration.
4. Exposes an incident review dashboard (`dashboard.html`) for post-incident audits.

---

## 4. GPU-Day Execution Runbook (NVIDIA GPU, Linux, X11)

1. **Verify Environment:**
   ```bash
   pipegen --version    # Expected: 0.5.1
   ```
   *Keep input video files accessible under `/home`.*
2. **Execute PipeGen Stages:**
   - Step through all 5 stages: *Requirement* -> *Pipeline IR* -> *Model* -> *Compiler* -> *Run*.
   - Capture a screenshot of the generated *Pipeline IR* node graph.
3. **Model Compilation & Benchmark:**
   - Compile model to TensorRT with **FP16** precision.
   - Save the TensorRT speed / latency benchmark report.
   - (Bonus) Compile with **INT8** precision and document FPS vs precision trade-offs.
4. **Enable Outputs & Live Run:**
   - Enable JSON metadata and MQTT publishing in PipeGen.
   - Launch live execution on sample video, then switch to USB camera.
5. **Attach Blind-Spot Watchdog:**
   ```bash
   python3 watchdog.py --path /path/to/pipegen/json_output --timeout 3 --target person
   ```
6. **Trigger Failure Demo:**
   - Simulate camera disconnect or pipeline freeze.
   - Verify terminal logs `SYSTEM BLIND`, followed by `RECOVERED` when restored.
   - Open `dashboard.html` and inspect `incident_log.jsonl`.
7. **Generate Evaluation Metrics:**
   - Run pipeline across 10–20 test clips.
   - Record outputs in `predictions.csv` vs `ground_truth.csv`.
   - Run `python3 evaluate.py ground_truth.csv predictions.csv` to generate the Markdown table.
8. **Export Project:**
   - Use PipeGen's "Export Project" feature and push the export bundle to the repository.

---

## 5. Submission Evidence Checklist

- [ ] Pipeline IR graph screenshot
- [ ] TensorRT speed benchmark report (FP16, and INT8 comparison)
- [ ] Live inference run screenshot or screen recording
- [ ] Sample JSON / MQTT output snippet
- [ ] Watchdog incident log (`incident_log.jsonl`) + dashboard screenshot
- [ ] Accuracy evaluation table (`evaluate.py`)
- [ ] Complete repository link including PipeGen exported project folder

---

## 6. Official Project Description

- **Problem:** Vision-based safety systems fail silently: when the camera or pipeline stops working, nobody knows the system is blind.
- **Solution:** A PipeGen person-detection pipeline with zone dwell-time alerts, JSON/MQTT output, and an independent Blind-Spot Watchdog that detects silence, raises `SYSTEM BLIND`, and logs incident metrics for dashboard visualization.
- **PipeGen Scope:** Full 5-stage pipeline, TensorRT acceleration, edge metadata export.
- **Edge Optimization Bonus:** FP16 vs INT8 latency/FPS comparison.
- **Current Project Status (Truthful):** Architecture, Blind-Spot Watchdog, web dashboard, and evaluation harness are fully implemented and verified locally without a GPU. Physical PipeGen live pipeline and TensorRT compiler runs (FP16/INT8) require an NVIDIA GPU environment and will be executed during live testing on GPU hardware.
