# core/paging.py
from collections import deque, defaultdict

class Frame:
    def __init__(self, idx):
        self.idx = idx
        self.pid = None
        self.page = None  # page number within pid

    def __repr__(self):
        return f"Frame(idx={self.idx}, pid={self.pid}, page={self.page})"


class PagingManager:
    """
    Simple paging manager:
    - single pool of frames
    - per-process page tables (mapping page -> frame index or None)
    - replacement algorithms: FIFO, LRU, OPT
    """

    def __init__(self, num_frames=4):
        self.num_frames = int(num_frames)
        self.frames = [Frame(i) for i in range(self.num_frames)]
        self.page_tables = defaultdict(dict)  # pid -> {page_num: frame_idx or None}
        # For replacement
        self.fifo_queue = deque()   # stores frame indexes in order filled
        self.lru_timestamps = {}    # frame_idx -> last_used_counter
        self.time_counter = 0
        # For OPT algorithm, GUI will provide future reference list; we don't store it here.

    def reset(self):
        self.frames = [Frame(i) for i in range(self.num_frames)]
        self.page_tables.clear()
        self.fifo_queue.clear()
        self.lru_timestamps.clear()
        self.time_counter = 0

    def ensure_pages(self, pid, num_pages):
        """Ensure page table has entries for 0..num_pages-1 set to None if unseen."""
        num_pages = int(num_pages)
        table = self.page_tables[pid]
        for p in range(num_pages):
            if p not in table:
                table[p] = None

    def frame_of_page(self, pid, page):
        return self.page_tables.get(pid, {}).get(page, None)

    def _find_free_frame_index(self):
        for f in self.frames:
            if f.pid is None:
                return f.idx
        return None

    def _assign_frame(self, frame_idx, pid, page):
        f = self.frames[frame_idx]
        f.pid = pid
        f.page = page
        self.page_tables[pid][page] = frame_idx
        # FIFO queue append if frame was free
        if frame_idx not in self.fifo_queue:
            self.fifo_queue.append(frame_idx)
        # update lru timestamp
        self.time_counter += 1
        self.lru_timestamps[frame_idx] = self.time_counter

    def _evict_frame(self, frame_idx):
        f = self.frames[frame_idx]
        if f.pid is not None:
            # clear page table entry for the owner
            if f.page is not None:
                if f.pid in self.page_tables and f.page in self.page_tables[f.pid]:
                    self.page_tables[f.pid][f.page] = None
            f.pid = None
            f.page = None
        # also remove from fifo queue and lru map
        try:
            self.fifo_queue.remove(frame_idx)
        except ValueError:
            pass
        self.lru_timestamps.pop(frame_idx, None)

    # ---------------- Page access API ----------------
    def access_page(self, pid, page, algorithm="FIFO", opt_future_refs=None, opt_index=0):
        """
        Simulate accessing page for pid.
        Returns dict:
          { 'hit': bool, 'evicted': (frame_idx or None), 'loaded_frame': frame_idx }
        - algorithm: "FIFO", "LRU", "OPT"
        - For OPT, pass opt_future_refs (list of ints) and opt_index (current position)
        """
        pid = int(pid)
        page = int(page)
        # if pid or page not known, return error-like behavior: ensure table slot
        if pid not in self.page_tables:
            self.page_tables[pid] = {}
        if page not in self.page_tables[pid]:
            self.page_tables[pid][page] = None

        current_frame = self.page_tables[pid][page]
        if current_frame is not None:
            # Hit
            self.time_counter += 1
            self.lru_timestamps[current_frame] = self.time_counter
            return {"hit": True, "evicted": None, "loaded_frame": current_frame}

        # Miss -> need to load
        free_idx = self._find_free_frame_index()
        evicted_idx = None

        if free_idx is not None:
            self._assign_frame(free_idx, pid, page)
            loaded = free_idx
        else:
            # need to select victim by algorithm
            if algorithm == "FIFO":
                # FIFO: evict the oldest frame in fifo_queue (leftmost)
                if not self.fifo_queue:
                    # shouldn't happen, but fallback
                    evicted_idx = 0
                else:
                    evicted_idx = self.fifo_queue.popleft()
            elif algorithm == "LRU":
                # find frame with minimum timestamp
                if not self.lru_timestamps:
                    evicted_idx = 0
                else:
                    evicted_idx = min(self.lru_timestamps.items(), key=lambda kv: kv[1])[0]
                    # remove from lru map
                    self.lru_timestamps.pop(evicted_idx, None)
                    # also remove from fifo queue if present
                    try:
                        self.fifo_queue.remove(evicted_idx)
                    except ValueError:
                        pass
            elif algorithm == "OPT":
                # OPT: choose frame whose next use is furthest in future (or never)
                # opt_future_refs should be a list of remaining page refs (tuples (pid,page) or just page if single pid)
                # Here, we assume opt_future_refs is a list of page numbers for the same pid.
                if not opt_future_refs:
                    # fallback to FIFO
                    evicted_idx = self.fifo_queue.popleft() if self.fifo_queue else 0
                else:
                    # for each frame, determine next index in opt_future_refs
                    furthest = -1
                    chosen = None
                    for f in self.frames:
                        # next use index
                        page_in_frame = f.page
                        try:
                            nxt = opt_future_refs.index(page_in_frame, opt_index)
                        except ValueError:
                            # not used again -> ideal candidate
                            chosen = f.idx
                            break
                        if nxt > furthest:
                            furthest = nxt
                            chosen = f.idx
                    evicted_idx = chosen if chosen is not None else 0
            else:
                # default FIFO
                evicted_idx = self.fifo_queue.popleft() if self.fifo_queue else 0

            # evict
            self._evict_frame(evicted_idx)
            # now assign evicted_idx
            self._assign_frame(evicted_idx, pid, page)
            loaded = evicted_idx

        return {"hit": False, "evicted": evicted_idx, "loaded_frame": loaded}

    # ---------------- Utility for GUI display ----------------
    def frames_snapshot(self):
        """Return a simple serializable snapshot of frames list for GUI."""
        return [(f.idx, f.pid, f.page) for f in self.frames]

    def page_table_snapshot(self, pid):
        """Return page->frame mapping for pid (dict)."""
        return dict(self.page_tables.get(pid, {}))
