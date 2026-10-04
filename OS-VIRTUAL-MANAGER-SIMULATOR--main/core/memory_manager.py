# core/memory_manager.py

class Partition:
    def __init__(self, start, size, pid=None):
        self.start = start
        self.size = size
        self.pid = pid  # None means free

    def __repr__(self):
        status = f"Used by PID {self.pid}" if self.pid is not None else "Free"
        return f"Partition(start={self.start}, size={self.size}, {status})"


class MemoryManager:
    def __init__(self, total_memory):
        self.total_memory = total_memory
        self.partitions = [Partition(0, total_memory)]  # Initially, one big free block
        self.next_fit_index = 0  # for next fit

    def allocate(self, pid, size, algorithm="First Fit"):
        if algorithm == "First Fit":
            return self._first_fit(pid, size)
        elif algorithm == "Best Fit":
            return self._best_fit(pid, size)
        elif algorithm == "Worst Fit":
            return self._worst_fit(pid, size)
        elif algorithm == "Next Fit":
            return self._next_fit(pid, size)
        return False

    # ---------------- Allocation Algorithms ----------------
    def _first_fit(self, pid, size):
        for i, part in enumerate(self.partitions):
            if part.pid is None and part.size >= size:
                self._split_partition(i, pid, size)
                return True
        return False

    def _best_fit(self, pid, size):
        best_index = -1
        min_size = float('inf')
        for i, part in enumerate(self.partitions):
            if part.pid is None and part.size >= size and part.size < min_size:
                best_index = i
                min_size = part.size
        if best_index != -1:
            self._split_partition(best_index, pid, size)
            return True
        return False

    def _worst_fit(self, pid, size):
        worst_index = -1
        max_size = -1
        for i, part in enumerate(self.partitions):
            if part.pid is None and part.size >= size and part.size > max_size:
                worst_index = i
                max_size = part.size
        if worst_index != -1:
            self._split_partition(worst_index, pid, size)
            return True
        return False

    def _next_fit(self, pid, size):
        n = len(self.partitions)
        count = 0
        i = self.next_fit_index
        while count < n:
            part = self.partitions[i]
            if part.pid is None and part.size >= size:
                self._split_partition(i, pid, size)
                self.next_fit_index = i  # next allocation starts from here
                return True
            i = (i + 1) % n
            count += 1
        return False

    # ---------------- Helper to split partition ----------------
    def _split_partition(self, index, pid, size):
        part = self.partitions[index]
        if part.size == size:
            part.pid = pid
        else:
            new_part = Partition(part.start + size, part.size - size)
            part.size = size
            part.pid = pid
            self.partitions.insert(index + 1, new_part)

    # ---------------- Deallocate & Defragment ----------------
    def deallocate(self, pid):
        deallocated = False
        for part in self.partitions:
            if part.pid == pid:
                part.pid = None
                deallocated = True
        if deallocated:
            self.merge_free_partitions()
        return deallocated

    def merge_free_partitions(self):
        """Merge adjacent free partitions to reduce fragmentation."""
        merged = []
        for part in self.partitions:
            if merged and merged[-1].pid is None and part.pid is None:
                merged[-1].size += part.size
            else:
                merged.append(part)
        self.partitions = merged

    def defragment(self):
        """Move all used partitions to the start and merge free memory at the end."""
        used = [p for p in self.partitions if p.pid is not None]
        free_memory = sum(p.size for p in self.partitions if p.pid is None)
        start = 0
        for p in used:
            p.start = start
            start += p.size
        self.partitions = used
        if free_memory > 0:
            self.partitions.append(Partition(start, free_memory))

    def __repr__(self):
        return "\n".join(f"[{i}] {p}" for i, p in enumerate(self.partitions))
