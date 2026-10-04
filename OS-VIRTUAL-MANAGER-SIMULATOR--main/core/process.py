# core/process.py
from dataclasses import dataclass, field
import itertools

_id_counter = itertools.count(1)

@dataclass
class Process:
    name: str
    burst_time: int            # CPU burst time (units)
    priority: int = 0
    arrival_time: int = 0
    pid: int = field(default_factory=lambda: next(_id_counter))
    state: str = field(default="NEW")   # NEW, READY, RUNNING, WAITING, TERMINATED
    remaining: int = field(init=False)
    completion_time: int = field(default=0)
    turnaround_time: int = field(default=0)
    waiting_time: int = field(default=0)

    def __post_init__(self):
        # Ensure numeric types
        self.burst_time = int(self.burst_time)
        self.priority = int(self.priority)
        self.arrival_time = int(self.arrival_time)
        self.remaining = self.burst_time

    def reset_times(self):
        self.remaining = self.burst_time
        self.state = "READY"
        self.completion_time = 0
        self.turnaround_time = 0
        self.waiting_time = 0

    def __repr__(self):
        return (f"Process(pid={self.pid}, name={self.name}, burst={self.burst_time}, "
                f"remaining={self.remaining}, priority={self.priority}, arrival={self.arrival_time}, state={self.state})")
