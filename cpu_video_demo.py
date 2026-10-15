#!/usr/bin/env python3
"""
CPU Workplace-Safety Sentinel (test tool, NOT PipeGen)
------------------------------------------------------
Runs on any laptop (no GPU). Reads a video file or webcam, detects people with
OpenCV's built-in HOG person detector, and raises a ZONE_ALERT when someone
stays inside a hazard zone longer than --dwell seconds.

Outputs (same shape the Blind-Spot Watchdog reads):
  feed.jsonl            one JSON line per processed frame (objects, zone status)
  hazard_incidents.jsonl ZONE_ALERT / ZONE_CLEARED events
  annotated.mp4         optional annotated video (--out)
Optional: MQTT alerts (--mqtt-host, needs paho-mqtt).

Honest scope: HOG is a classic, basic detector. It is far less accurate than a
PipeGen/TensorRT model. This tool exists so the watchdog and dashboard can be
demonstrated end to end on a laptop without an NVIDIA GPU.

Examples:
  python cpu_video_demo.py --source myvideo.mp4 --realtime
  python cpu_video_demo.py --source 0 --show          (webcam)
  python cpu_video_demo.py --source myvideo.mp4 --zone 0.5,0.2,1.0,1.0 --dwell 3 --out annotated.mp4
"""
import argparse
import datetime
import json
import sys
import time

import cv2


def now_iso():
    return datetime.datetime.now().isoformat(timespec="milliseconds")


def parse_zone(text):
    try:
        x1, y1, x2, y2 = [float(v) for v in text.split(",")]
    except ValueError:
        sys.exit("--zone must be 4 numbers: x1,y1,x2,y2 (fractions of width/height, e.g. 0.5,0.2,1.0,1.0)")
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        sys.exit("--zone values must satisfy 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1")
    return x1, y1, x2, y2


class Publisher:
    def __init__(self, host, port, topic):
        self.client, self.topic = None, topic
        if host:
            try:
                import paho.mqtt.client as mqtt
                try:
                    self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                except AttributeError:
                    self.client = mqtt.Client()
                self.client.connect(host, port, 60)
                self.client.loop_start()
            except Exception as exc:
                print(f"MQTT disabled: {exc}")
                self.client = None

    def send(self, record):
        if self.client:
            try:
                self.client.publish(self.topic, json.dumps(record))
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="CPU workplace-safety sentinel (test tool, not PipeGen)")
    ap.add_argument("--source", default="0", help="video file path or camera index (default 0)")
    ap.add_argument("--zone", default="0.5,0.2,1.0,1.0", help="hazard zone x1,y1,x2,y2 as fractions")
    ap.add_argument("--dwell", type=float, default=3.0, help="seconds in zone before ZONE_ALERT")
    ap.add_argument("--feed", default="feed.jsonl", help="per-frame JSON feed (watchdog input)")
    ap.add_argument("--incidents", default="hazard_incidents.jsonl")
    ap.add_argument("--out", help="write annotated video to this .mp4")
    ap.add_argument("--show", action="store_true", help="show a live window (press q to quit)")
    ap.add_argument("--realtime", action="store_true", help="pace a video file at its real speed")
    ap.add_argument("--stride", type=int, default=2, help="process every Nth frame (speed on slow CPUs)")
    ap.add_argument("--width", type=int, default=480, help="resize width used for detection")
    ap.add_argument("--max-seconds", type=float, default=0, help="stop after N seconds (0 = until end)")
    ap.add_argument("--mqtt-host")
    ap.add_argument("--mqtt-port", type=int, default=1883)
    ap.add_argument("--mqtt-topic", default="sentinel/alerts")
    args = ap.parse_args()

    zx1, zy1, zx2, zy2 = parse_zone(args.zone)
    is_cam = args.source.isdigit()
    if is_cam and sys.platform == "win32":
        cap = cv2.VideoCapture(int(args.source), cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(int(args.source) if is_cam else args.source)
    if not cap.isOpened():
        sys.exit(f"Could not open source: {args.source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if fps <= 1 or fps > 120:
        fps = 25.0

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    pub = Publisher(args.mqtt_host, args.mqtt_port, args.mqtt_topic)

    feed = open(args.feed, "w", encoding="utf-8")
    incidents = open(args.incidents, "a", encoding="utf-8")
    writer = None
    stride = max(1, args.stride)

    in_zone_since = None
    last_seen_zone = None
    alerted = False
    frame_idx = 0
    processed = 0
    t_start = time.time()
    n_alerts = 0
    print(f"Source: {args.source} | zone={args.zone} | dwell>{args.dwell}s | feed={args.feed}")

    def incident(event, **fields):
        rec = {"ts": now_iso(), "event": event, **fields}
        incidents.write(json.dumps(rec) + "\n")
        incidents.flush()
        pub.send(rec)
        return rec

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        # video time: deterministic for files, wall clock for cameras
        vt = (time.time() - t_start) if is_cam else frame_idx / fps
        if args.max_seconds and vt > args.max_seconds:
            break
        if args.realtime and not is_cam:
            lag = vt - (time.time() - t_start)
            if lag > 0:
                time.sleep(lag)
        if frame_idx % stride:
            continue

        h0, w0 = frame.shape[:2]
        scale = args.width / float(w0) if w0 > args.width else 1.0
        small = cv2.resize(frame, (int(w0 * scale), int(h0 * scale))) if scale != 1.0 else frame
        rects, weights = hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)

        zx_a, zy_a, zx_b, zy_b = int(zx1 * w0), int(zy1 * h0), int(zx2 * w0), int(zy2 * h0)
        objects, any_in_zone = [], False
        for (x, y, w, h), conf in zip(rects, [float(c) for c in (weights if len(weights) else [])]):
            if conf < 0.3:
                continue
            x, y, w, h = [int(v / scale) for v in (x, y, w, h)]
            foot = (x + w // 2, y + h)
            inside = zx_a <= foot[0] <= zx_b and zy_a <= foot[1] <= zy_b
            any_in_zone = any_in_zone or inside
            objects.append({"class": "person", "bbox": [x, y, w, h], "confidence": round(conf, 2), "in_zone": inside})

        if any_in_zone:
            last_seen_zone = vt
            if in_zone_since is None:
                in_zone_since = vt
            if not alerted and vt - in_zone_since >= args.dwell:
                alerted = True
                n_alerts += 1
                rec = incident("ZONE_ALERT", dwell_s=round(vt - in_zone_since, 1), video_t=round(vt, 1),
                                message="Person in hazard zone")
                print(f"[{rec['ts']}] ZONE_ALERT person in hazard zone for {vt - in_zone_since:.1f}s (video t={vt:.1f}s)")
        else:
            # Allow up to 0.4s detector flicker tolerance (HOG single-frame miss) before clearing zone
            if in_zone_since is not None and (last_seen_zone is None or vt - last_seen_zone >= 0.4):
                if alerted:
                    incident("ZONE_CLEARED", video_t=round(vt, 1))
                    print(f"[{now_iso()}] ZONE_CLEARED (video t={vt:.1f}s)")
                in_zone_since, alerted = None, False

        feed.write(json.dumps({"ts": now_iso(), "frame": frame_idx, "video_t": round(vt, 2),
                               "objects": objects, "zone_alert": alerted}) + "\n")
        feed.flush()
        processed += 1

        if args.out or args.show:
            vis = frame.copy()
            colour = (0, 0, 255) if alerted else (0, 200, 255)
            cv2.rectangle(vis, (zx_a, zy_a), (zx_b, zy_b), colour, 2)
            for o in objects:
                x, y, w, h = o["bbox"]
                cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 255) if o["in_zone"] else (0, 255, 0), 2)
            if alerted:
                cv2.putText(vis, "ZONE ALERT", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
            if args.out and writer is None:
                writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), fps / stride, (w0, h0))
            if writer:
                writer.write(vis)
            if args.show:
                cv2.imshow("Sentinel (q to quit)", vis)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    cap.release()
    if writer:
        writer.release()
    feed.close()
    incidents.close()
    cv2.destroyAllWindows()
    elapsed = time.time() - t_start
    print(f"Done. Processed {processed} frames in {elapsed:.1f}s ({processed / max(elapsed, 1e-6):.1f} fps on CPU), "
          f"{n_alerts} zone alert(s).")


if __name__ == "__main__":
    main()
