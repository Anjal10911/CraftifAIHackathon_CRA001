#!/usr/bin/env python3
"""
Blind-Spot Watchdog
-------------------
Watches the output of a safety vision pipeline (such as PipeGen by CraftifAI or DeepStream)
via a JSON/JSONL file or folder, and raises a SYSTEM BLIND alert if the pipeline
stops producing output (camera unplugged, pipeline crashed, stream frozen).

It also tracks detection changes (e.g. 'person' counts) by inspecting standard
dictionary keys ('class', 'label', 'name') in a schema-agnostic manner, and writes
every event to an incident log (JSONL). Optional MQTT publishing.

Runs on any laptop, no GPU needed. Standard library only (paho-mqtt optional).

Usage:
  python3 watchdog.py --path /path/to/pipeline/output --timeout 3
  python3 watchdog.py --path feed.jsonl --target person --mqtt-host localhost
  python3 watchdog.py --demo        # self-test with a SIMULATED feed (not PipeGen data)
"""
import argparse
import datetime
import json
import os
import sys
import tempfile
import threading
import time

RED, GREEN, YELLOW, RESET = "\033[91m", "\033[92m", "\033[93m", "\033[0m"
LABEL_KEYS = ("class", "label", "name", "class_name", "category", "obj_label")


def now_iso():
    return datetime.datetime.now().isoformat(timespec="milliseconds")


def last_activity(path):
    """Newest modification time under path (file or directory); 0.0 if missing."""
    try:
        if os.path.isdir(path):
            newest = 0.0
            for root, _, files in os.walk(path):
                for name in files:
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, name)))
                    except OSError:
                        pass
            return newest
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def newest_file(path):
    if not os.path.isdir(path):
        return path
    best, best_t = None, 0.0
    for root, _, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)
            try:
                t = os.path.getmtime(full)
            except OSError:
                continue
            if t >= best_t:
                best, best_t = full, t
    return best


def read_last_json(path):
    """Best-effort: parse the last JSON record from a file (JSONL or single JSON)."""
    target = newest_file(path)
    if not target:
        return None
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return None
    text = text.strip()
    if not text:
        return None
    for chunk in (text.splitlines()[-1], text):
        try:
            return json.loads(chunk)
        except (ValueError, IndexError):
            continue
    return None


def count_label(node, label):
    """Recursively count dicts whose label-like field equals `label`."""
    label = label.lower()
    total = 0
    if isinstance(node, dict):
        for key in LABEL_KEYS:
            if key in node and isinstance(node[key], str) and node[key].lower() == label:
                total += 1
                break
        for value in node.values():
            total += count_label(value, label)
    elif isinstance(node, list):
        for item in node:
            total += count_label(item, label)
    return total


class Reporter:
    def __init__(self, log_path, mqtt_host=None, mqtt_port=1883, mqtt_topic="watchdog/alerts"):
        self.log_path = log_path
        self.client = None
        self.topic = mqtt_topic
        if mqtt_host:
            try:
                import paho.mqtt.client as mqtt  # optional dependency
                try:
                    self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                except AttributeError:
                    self.client = mqtt.Client()
                self.client.connect(mqtt_host, mqtt_port, 60)
                self.client.loop_start()
            except Exception as exc:  # keep running without MQTT
                print(f"{YELLOW}MQTT disabled: {exc}{RESET}")
                self.client = None

    def emit(self, event, **fields):
        record = {"ts": now_iso(), "event": event, **fields}
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        if self.client:
            try:
                self.client.publish(self.topic, json.dumps(record))
            except Exception:
                pass
        return record


def watch(path, timeout, target, log_path, poll, duration, reporter):
    start = time.time()
    state = "STARTING"
    blind_since = None
    last_count = None
    print(f"Watching: {path} | blind if silent > {timeout}s | log: {log_path}")
    while True:
        now = time.time()
        if duration and now - start > duration:
            break
        activity = last_activity(path)
        age = (now - activity) if activity else (now - start)

        if age > timeout:
            if state != "BLIND":
                blind_since = now
                state = "BLIND"
                reporter.emit("SYSTEM_BLIND", silent_for_s=round(min(age, 1e6), 1),
                              message="No pipeline output; system cannot see")
                print(f"{RED}[{now_iso()}] SYSTEM BLIND - no pipeline output for >{timeout}s{RESET}")
        else:
            if state == "BLIND":
                reporter.emit("RECOVERED", blind_duration_s=round(now - blind_since, 1))
                print(f"{GREEN}[{now_iso()}] RECOVERED after {now - blind_since:.1f}s blind{RESET}")
                state = "OK"
            elif state == "STARTING":
                if activity > 0:
                    print(f"{GREEN}[{now_iso()}] Pipeline output detected, monitoring{RESET}")
                    state = "OK"
            else:
                state = "OK"

            if target and state == "OK":
                record = read_last_json(path)
                if record is not None:
                    count = count_label(record, target)
                    if count != last_count:
                        reporter.emit("DETECTION_CHANGE", target=target, count=count)
                        print(f"[{now_iso()}] {target} count: {count}")
                        last_count = count
        time.sleep(poll)
    print("Watchdog stopped.")


def simulated_feed(feed_path):
    """SIMULATED pipeline output, only to self-test the watchdog. NOT PipeGen data."""
    def run():
        t0 = time.time()
        while time.time() - t0 < 30:
            elapsed = time.time() - t0
            if 8 < elapsed < 15:  # simulate camera unplugged / pipeline dead
                time.sleep(0.2)
                continue
            people = 1 if int(elapsed) % 6 < 3 else 0
            objs = [{"class": "person", "bbox": [10, 10, 50, 90]}] * people
            with open(feed_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"frame": int(elapsed * 10), "objects": objs}) + "\n")
            time.sleep(0.3)
    threading.Thread(target=run, daemon=True).start()


def main():
    if sys.platform == "win32":
        os.system("")  # Enable ANSI color escape codes in Windows Command Prompt

    ap = argparse.ArgumentParser(description="Blind-Spot Watchdog for PipeGen output")
    ap.add_argument("--path", help="JSON/JSONL file or folder written by the pipeline")
    ap.add_argument("--timeout", type=float, default=3.0, help="seconds of silence before SYSTEM BLIND")
    ap.add_argument("--target", default="person", help="label to count (empty to disable)")
    ap.add_argument("--log", default="incident_log.jsonl", help="incident log file (JSONL)")
    ap.add_argument("--poll", type=float, default=0.5)
    ap.add_argument("--duration", type=float, default=0, help="stop after N seconds (0 = run forever)")
    ap.add_argument("--mqtt-host")
    ap.add_argument("--mqtt-port", type=int, default=1883)
    ap.add_argument("--mqtt-topic", default="watchdog/alerts")
    ap.add_argument("--demo", action="store_true", help="self-test with a SIMULATED feed")
    args = ap.parse_args()

    path, duration = args.path, args.duration
    if args.demo:
        path = os.path.join(tempfile.gettempdir(), "watchdog_demo_feed.jsonl")
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        if os.path.exists(args.log):
            try:
                os.remove(args.log)
            except OSError:
                pass
        simulated_feed(path)
        duration = duration or 22
        print(f"{YELLOW}DEMO MODE: simulated feed, not real PipeGen output{RESET}")
    if not path:
        ap.error("--path is required (or use --demo)")

    reporter = Reporter(args.log, args.mqtt_host, args.mqtt_port, args.mqtt_topic)
    try:
        watch(path, args.timeout, args.target, args.log, args.poll, duration, reporter)
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
