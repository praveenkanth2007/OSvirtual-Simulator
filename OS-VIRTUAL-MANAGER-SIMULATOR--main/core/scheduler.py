# core/scheduler.py
import time
from collections import deque
from core.process import Process

# Helper to compute process metrics
def _set_completion_metrics(p: "Process", finish_time: int):
    p.completion_time = finish_time
    p.turnaround_time = p.completion_time - p.arrival_time
    p.waiting_time = p.turnaround_time - p.burst_time

# ------------------- FCFS -------------------
def fcfs_schedule(processes, time_unit=0):
    timeline = []
    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    time_cursor = 0
    for p in procs:
        if p.remaining <= 0:
            continue
        if time_cursor < p.arrival_time:
            time_cursor = p.arrival_time
        p.state = "RUNNING"
        while p.remaining > 0:
            p.remaining -= 1
            timeline.append((p.pid, p.name))
            if time_unit:
                time.sleep(time_unit)
            time_cursor += 1
        p.state = "TERMINATED"
        _set_completion_metrics(p, time_cursor)
    return timeline

# ------------------- SJF Non-preemptive -------------------
def sjf_schedule(processes, time_unit=0):
    timeline = []
    procs = [p for p in processes]
    time_cursor = 0
    finished = 0
    n = len(procs)
    while finished < n:
        available = [p for p in procs if p.remaining > 0 and p.arrival_time <= time_cursor]
        if not available:
            next_arrivals = [p.arrival_time for p in procs if p.remaining > 0]
            if not next_arrivals:
                break
            time_cursor = min(next_arrivals)
            continue
        current = min(available, key=lambda x: x.burst_time)
        current.state = "RUNNING"
        while current.remaining > 0:
            current.remaining -= 1
            timeline.append((current.pid, current.name))
            if time_unit:
                time.sleep(time_unit)
            time_cursor += 1
        current.state = "TERMINATED"
        _set_completion_metrics(current, time_cursor)
        finished += 1
    return timeline

# ------------------- SRTF (Preemptive SJF) -------------------
def srtf_schedule(processes, time_unit=0):
    timeline = []
    procs = [p for p in processes]
    time_cursor = 0
    n = len(procs)
    finished = 0
    while finished < n:
        available = [p for p in procs if p.remaining > 0 and p.arrival_time <= time_cursor]
        if not available:
            next_arrivals = [p.arrival_time for p in procs if p.remaining > 0]
            if not next_arrivals:
                break
            time_cursor = min(next_arrivals)
            continue
        current = min(available, key=lambda x: x.remaining)
        current.state = "RUNNING"
        current.remaining -= 1
        timeline.append((current.pid, current.name))
        if time_unit:
            time.sleep(time_unit)
        time_cursor += 1
        if current.remaining == 0:
            current.state = "TERMINATED"
            finished += 1
            _set_completion_metrics(current, time_cursor)
        else:
            current.state = "READY"
    return timeline

# ------------------- Round Robin -------------------
def rr_schedule(processes, quantum=2, time_unit=0):
    timeline = []
    procs = [p for p in processes]
    time_cursor = 0
    queue = deque()
    arrived = set()
    finished = 0
    n = len(procs)

    def add_arrivals(t):
        for p in procs:
            if p.arrival_time <= t and p.pid not in arrived and p.remaining > 0:
                queue.append(p)
                arrived.add(p.pid)

    add_arrivals(0)
    while finished < n:
        if not queue:
            next_arrivals = [p.arrival_time for p in procs if p.remaining > 0 and p.pid not in arrived]
            if not next_arrivals:
                break
            time_cursor = min(next_arrivals)
            add_arrivals(time_cursor)
            continue

        p = queue.popleft()
        p.state = "RUNNING"
        executed = 0
        while executed < quantum and p.remaining > 0:
            p.remaining -= 1
            timeline.append((p.pid, p.name))
            if time_unit:
                time.sleep(time_unit)
            time_cursor += 1
            executed += 1
            add_arrivals(time_cursor)
        if p.remaining == 0:
            p.state = "TERMINATED"
            finished += 1
            _set_completion_metrics(p, time_cursor)
        else:
            p.state = "READY"
            queue.append(p)

    return timeline

# ------------------- Priority (Non-preemptive) -------------------
def priority_non_preemptive(processes, time_unit=0):
    timeline = []
    procs = [p for p in processes]
    time_cursor = 0
    finished = 0
    n = len(procs)
    while finished < n:
        available = [p for p in procs if p.remaining > 0 and p.arrival_time <= time_cursor]
        if not available:
            next_arrivals = [p.arrival_time for p in procs if p.remaining > 0]
            if not next_arrivals:
                break
            time_cursor = min(next_arrivals)
            continue
        current = min(available, key=lambda x: (x.priority, x.arrival_time))
        current.state = "RUNNING"
        while current.remaining > 0:
            current.remaining -= 1
            timeline.append((current.pid, current.name))
            if time_unit:
                time.sleep(time_unit)
            time_cursor += 1
        current.state = "TERMINATED"
        finished += 1
        _set_completion_metrics(current, time_cursor)
    return timeline

# ------------------- Priority (Preemptive) -------------------
def priority_preemptive(processes, time_unit=0):
    timeline = []
    procs = [p for p in processes]
    time_cursor = 0
    n = len(procs)
    finished = 0
    while finished < n:
        available = [p for p in procs if p.remaining > 0 and p.arrival_time <= time_cursor]
        if not available:
            next_arrivals = [p.arrival_time for p in procs if p.remaining > 0]
            if not next_arrivals:
                break
            time_cursor = min(next_arrivals)
            continue
        current = min(available, key=lambda x: (x.priority, x.arrival_time))
        current.state = "RUNNING"
        current.remaining -= 1
        timeline.append((current.pid, current.name))
        if time_unit:
            time.sleep(time_unit)
        time_cursor += 1
        if current.remaining == 0:
            current.state = "TERMINATED"
            finished += 1
            _set_completion_metrics(current, time_cursor)
        else:
            current.state = "READY"
    return timeline
