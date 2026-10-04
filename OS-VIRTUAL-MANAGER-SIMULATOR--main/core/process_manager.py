# core/process_manager.py
from core.process import Process

class ProcessManager:
    def __init__(self):
        self.process_table = []  # list of Process objects

    def create_process(self, name: str, burst_time: int, priority: int = 0, arrival_time: int = 0):
        p = Process(name=name, burst_time=burst_time, priority=priority, arrival_time=arrival_time)
        p.state = "READY"
        self.process_table.append(p)
        return p

    def terminate_process(self, pid: int):
        for p in self.process_table:
            if p.pid == pid:
                p.state = "TERMINATED"
                return p
        return None

    def get_ready_processes(self):
        return [p for p in self.process_table if p.state == "READY"]

    def list_processes(self):
        return list(self.process_table)
