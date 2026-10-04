# gui/main_gui.py
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import random
from tkinter import BOTH
# add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.process import Process
from core.process_manager import ProcessManager
from core.memory_manager import MemoryManager
from core.scheduler import (
    fcfs_schedule, sjf_schedule, srtf_schedule, rr_schedule,
    priority_non_preemptive, priority_preemptive
)
from core.paging import PagingManager

# ---------------- Utility ----------------
import random

def get_random_color(seed=None):
    if seed is not None:
        random.seed(seed)
    # Generate light colors by limiting RGB values to the higher range (150–255)
    r = random.randint(180, 255)
    g = random.randint(180, 255)
    b = random.randint(180, 255)
    return f"#{r:02x}{g:02x}{b:02x}"



# ---------------- Main App ----------------
class OSVirtualManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OS Virtual Manager")
        self.root.geometry("1200x900")

        self.pm = ProcessManager()
        self.memory_manager = MemoryManager(total_memory=1024)
        self.process_colors = {}

        # paging manager (used in the paging tab)
        self.paging_manager = PagingManager(num_frames=10)
        # paging simulation state
        self.paging_sim_running = False
        self.paging_sim_index = 0
        self.paging_sim_refs = []  # list of page numbers (int) for the selected PID
        self.paging_sim_pid = None
        self.paging_sim_algo = "FIFO"
        self.paging_after_id = None
        self.gantt_anim_after_id = None

        self.setup_tabs()

    # ---------------- Tabs ----------------
    def setup_tabs(self):
        tab_control = ttk.Notebook(self.root)
        self.process_tab = ttk.Frame(tab_control)
        self.memory_tab = ttk.Frame(tab_control)
        self.paging_tab = ttk.Frame(tab_control)

        tab_control.add(self.process_tab, text="Process Management")
        tab_control.add(self.memory_tab, text="Memory Management")
        tab_control.add(self.paging_tab, text="Paging & Replacement")
        tab_control.pack(expand=1, fill="both")

        self.setup_process_tab()
        self.setup_memory_tab()
        self.setup_paging_tab()

    # ---------------- Process Tab ----------------
    def setup_process_tab(self):
        frame = ttk.Frame(self.process_tab)
        frame.place(relx=0.5, rely=0.02, anchor="n")

        # Left Inputs
        left_frame = ttk.Frame(frame)
        left_frame.grid(row=0, column=0, padx=20, pady=10, sticky="n")

        ttk.Label(left_frame, text="Process Name:").grid(row=0, column=0, sticky="e", pady=5)
        self.name_entry = ttk.Entry(left_frame, width=18)
        self.name_entry.grid(row=0, column=1, pady=5)

        ttk.Label(left_frame, text="Burst Time:").grid(row=1, column=0, sticky="e", pady=5)
        self.burst_entry = ttk.Entry(left_frame, width=18)
        self.burst_entry.grid(row=1, column=1, pady=5)

        ttk.Label(left_frame, text="Arrival Time:").grid(row=2, column=0, sticky="e", pady=5)
        self.arrival_entry = ttk.Entry(left_frame, width=18)
        self.arrival_entry.insert(0, "0")
        self.arrival_entry.grid(row=2, column=1, pady=5)

        ttk.Label(left_frame, text="Priority:").grid(row=3, column=0, sticky="e", pady=5)
        self.priority_entry = ttk.Entry(left_frame, width=18)
        self.priority_entry.grid(row=3, column=1, pady=5)

        # Right Inputs
        right_frame = ttk.Frame(frame)
        right_frame.grid(row=0, column=1, padx=40, pady=10, sticky="n")

        ttk.Label(right_frame, text="Scheduler:").grid(row=0, column=0, sticky="e", pady=5)
        self.scheduler_choice = ttk.Combobox(
            right_frame,
            values=["FCFS", "SJF", "SRTF (SJF Preemptive)", "Round Robin",
                    "Priority Non-Preemptive", "Priority Preemptive"],
            state="readonly",
            width=28
        )
        self.scheduler_choice.grid(row=0, column=1, pady=5)
        self.scheduler_choice.set("FCFS")
        self.scheduler_choice.bind("<<ComboboxSelected>>", self.on_scheduler_change)

        ttk.Label(right_frame, text="Quantum (for RR):").grid(row=1, column=0, sticky="e", pady=5)
        self.quantum_entry = ttk.Entry(right_frame, width=10)
        self.quantum_entry.insert(0, "2")
        self.quantum_entry.grid(row=1, column=1, pady=5)
        self.quantum_entry.config(state="disabled")

        ttk.Button(right_frame, text="Add Process", command=self.add_process).grid(row=2, column=1, pady=5, sticky="e")
        ttk.Button(right_frame, text="Run Scheduler", command=self.run_scheduler).grid(row=3, column=1, pady=5, sticky="e")

        # Animation controls for Gantt
        anim_frame = ttk.Frame(self.process_tab)
        anim_frame.place(relx=0.5, rely=0.36, anchor="n")
        ttk.Label(anim_frame, text="Gantt Animation: ").grid(row=0, column=0, padx=4)
        self.gantt_play_btn = ttk.Button(anim_frame, text="Play", command=self.gantt_play)
        self.gantt_play_btn.grid(row=0, column=1, padx=4)
        self.gantt_step_btn = ttk.Button(anim_frame, text="Step", command=self.gantt_step)
        self.gantt_step_btn.grid(row=0, column=2, padx=4)
        ttk.Label(anim_frame, text="Speed (ms):").grid(row=0, column=3, padx=4)
        self.gantt_speed = ttk.Entry(anim_frame, width=6)
        self.gantt_speed.insert(0, "400")
        self.gantt_speed.grid(row=0, column=4, padx=4)

        # Output Box & Gantt Chart
        self.output_box = tk.Text(self.process_tab, height=10, width=120)
        self.output_box.place(relx=0.5, rely=0.42, anchor="n")

        ttk.Label(self.process_tab, text="Gantt Chart:").place(relx=0.5, rely=0.72, anchor="n")
        self.gantt_canvas = tk.Canvas(self.process_tab, height=120, width=1000, bg="white")
        self.gantt_canvas.place(relx=0.5, rely=0.75, anchor="n")

        # internal animation state
        self._gantt_timeline = []
        self._gantt_anim_index = 0

    # Enable or disable Quantum field
    def on_scheduler_change(self, event=None):
        scheduler = self.scheduler_choice.get()
        if scheduler == "Round Robin":
            self.quantum_entry.config(state="normal")
        else:
            self.quantum_entry.config(state="disabled")

    # ---------------- Add & Run Processes ----------------
    def add_process(self):
        try:
            name = self.name_entry.get().strip()
            burst = int(self.burst_entry.get())
            arrival = int(self.arrival_entry.get() or 0)
            priority = int(self.priority_entry.get() or 0)
            if not name:
                messagebox.showerror("Error", "Process name cannot be empty.")
                return
            p = self.pm.create_process(name, burst, priority, arrival)
            self.process_colors[p.pid] = get_random_color(p.pid)
            self.output_box.insert(tk.END, f"✅ Added {name} (PID {p.pid}, Burst {burst})\n")
            self.name_entry.delete(0, tk.END)
            self.burst_entry.delete(0, tk.END)
            self.priority_entry.delete(0, tk.END)
            self.arrival_entry.delete(0, tk.END)
            self.arrival_entry.insert(0, "0")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values.")

    def run_scheduler(self):
        procs = self.pm.list_processes()
        if not procs:
            messagebox.showwarning("Warning", "No processes added.")
            return

        scheduler = self.scheduler_choice.get()
        for p in procs:
            p.reset_times()

        if scheduler == "FCFS":
            timeline = fcfs_schedule(procs)
        elif scheduler == "SJF":
            timeline = sjf_schedule(procs)
        elif scheduler == "SRTF (SJF Preemptive)":
            timeline = srtf_schedule(procs)
        elif scheduler == "Priority Non-Preemptive":
            timeline = priority_non_preemptive(procs)
        elif scheduler == "Priority Preemptive":
            timeline = priority_preemptive(procs)
        elif scheduler == "Round Robin":
            try:
                quantum = int(self.quantum_entry.get())
                if quantum <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid positive integer for quantum.")
                return
            timeline = rr_schedule(procs, quantum=quantum)
        else:
            messagebox.showerror("Error", "Invalid scheduler selected.")
            return

        # Output textual results
        self.output_box.insert(tk.END, f"\n▶ {scheduler} Results:\nTimeline: {timeline}\n")
        self.output_box.insert(tk.END, "\nPID | Name | AT | BT | PRI | CT | TAT | WT\n")
        total_tat = total_wt = 0
        for p in sorted(procs, key=lambda x: x.pid):
            self.output_box.insert(tk.END,
                f"{p.pid:^3} | {p.name:^6} | {p.arrival_time:^2} | {p.burst_time:^2} | {p.priority:^3} | "
                f"{p.completion_time:^3} | {p.turnaround_time:^3} | {p.waiting_time:^3}\n")
            total_tat += p.turnaround_time
            total_wt += p.waiting_time
        avg_tat = total_tat / len(procs)
        avg_wt = total_wt / len(procs)
        self.output_box.insert(tk.END, f"\nAvg TAT = {avg_tat:.2f}, Avg WT = {avg_wt:.2f}\n")

        # Prepare timeline for animation (list of (pid, name))
        self._gantt_timeline = timeline
        self._gantt_anim_index = 0
        self.draw_gantt_chart_with_timeline(timeline)

    def draw_gantt_chart_with_timeline(self, timeline, highlight_index=None):
        self.gantt_canvas.delete("all")
        if not timeline:
            return
        total_units = len(timeline)
        canvas_width = int(self.gantt_canvas["width"])
        unit_width = max(canvas_width / total_units, 6)
        x = 0
        for idx, (pid, name) in enumerate(timeline):
            color = self.process_colors.get(pid, "#AAA")
            x0, x1 = x, x + unit_width
            if highlight_index is not None and idx == highlight_index:
                # slightly bigger/outline
                self.gantt_canvas.create_rectangle(x0, 6, x1, 64, fill=color, outline="red", width=2)
            else:
                self.gantt_canvas.create_rectangle(x0, 10, x1, 60, fill=color, outline="black")
            self.gantt_canvas.create_text((x0 + x1) / 2, 35, text=name)
            self.gantt_canvas.create_text(x0 + 3, 75, text=str(idx), anchor="w", font=("Arial", 8))
            x += unit_width
        self.gantt_canvas.create_text(x, 75, text=str(total_units), anchor="w", font=("Arial", 8))

    # Animation controls for Gantt
    def gantt_play(self):
        if not self._gantt_timeline:
            messagebox.showinfo("Info", "Run a scheduler to produce a timeline first.")
            return
        # toggle behavior
        if self.gantt_anim_after_id:
            # currently running -> stop
            self.root.after_cancel(self.gantt_anim_after_id)
            self.gantt_anim_after_id = None
            self.gantt_play_btn.config(text="Play")
            return
        # start playing
        self.gantt_play_btn.config(text="Stop")
        speed = 400
        try:
            speed = max(10, int(self.gantt_speed.get()))
        except Exception:
            speed = 400
        self._gantt_anim_index = 0
        def step():
            if self._gantt_anim_index >= len(self._gantt_timeline):
                self.gantt_play_btn.config(text="Play")
                self.gantt_anim_after_id = None
                return
            self.draw_gantt_chart_with_timeline(self._gantt_timeline, highlight_index=self._gantt_anim_index)
            self._gantt_anim_index += 1
            self.gantt_anim_after_id = self.root.after(speed, step)
        step()

    def gantt_step(self):
        if not self._gantt_timeline:
            messagebox.showinfo("Info", "Run a scheduler to produce a timeline first.")
            return
        # single step
        if self._gantt_anim_index >= len(self._gantt_timeline):
            self._gantt_anim_index = 0
        self.draw_gantt_chart_with_timeline(self._gantt_timeline, highlight_index=self._gantt_anim_index)
        self._gantt_anim_index += 1

    # ---------------- Memory Tab (unchanged behavior, only layout kept) ----------------
    def setup_memory_tab(self):
        frame = ttk.Frame(self.memory_tab)
        frame.pack(pady=15)

        ttk.Label(frame, text="Select PID:").grid(row=0, column=0, padx=5, pady=5)
        self.pid_entry = ttk.Entry(frame, width=6)
        self.pid_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Memory Size:").grid(row=0, column=2, padx=5, pady=5)
        self.mem_size_entry = ttk.Entry(frame, width=10)
        self.mem_size_entry.insert(0, "256")
        self.mem_size_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(frame, text="Allocation Algorithm:").grid(row=0, column=4, padx=5, pady=5)
        self.alloc_algo_choice = ttk.Combobox(
            frame,
            values=["First Fit", "Best Fit", "Worst Fit", "Next Fit"],
            state="readonly",
            width=20
        )
        self.alloc_algo_choice.grid(row=0, column=5, padx=5, pady=5)
        self.alloc_algo_choice.set("First Fit")

        ttk.Button(frame, text="Allocate Memory", command=self.allocate_memory).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Deallocate Memory", command=self.deallocate_memory).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Defragment Memory", command=self.defragment_memory).grid(row=1, column=2, padx=5, pady=5)

        self.memory_box = tk.Text(self.memory_tab, height=10, width=120)
        self.memory_box.pack(pady=8)
        ttk.Label(self.memory_tab, text="Memory Map:").pack()
        self.memory_canvas = tk.Canvas(self.memory_tab, height=120, width=1000, bg="white")
        self.memory_canvas.pack(pady=8)

        self.update_memory_display()

    def allocate_memory(self):
        pid_text = self.pid_entry.get()
        size_text = self.mem_size_entry.get()
        algo = self.alloc_algo_choice.get()
        try:
            pid = int(pid_text)
            size = int(size_text)
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric PID and size.")
            return
        proc = next((p for p in self.pm.list_processes() if p.pid == pid), None)
        if not proc:
            messagebox.showerror("Error", f"No process with PID {pid}.")
            return

        success = self.memory_manager.allocate(pid, size, algorithm=algo)
        if not success:
            messagebox.showwarning("Warning", f"Not enough memory for PID {pid}.")
        self.update_memory_display()

    def deallocate_memory(self):
        pid_text = self.pid_entry.get()
        try:
            pid = int(pid_text)
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric PID.")
            return
        self.memory_manager.deallocate(pid)
        self.update_memory_display()

    def defragment_memory(self):
        self.memory_manager.defragment()
        self.update_memory_display()

    def update_memory_display(self):
        self.memory_box.delete("1.0", tk.END)
        self.memory_canvas.delete("all")

        total_used = sum(p.size for p in self.memory_manager.partitions if p.pid is not None)
        total_mem = self.memory_manager.total_memory
        usage_percent = (total_used / total_mem * 100) if total_mem else 0

        self.memory_box.insert(tk.END, f"Memory Usage: {total_used}/{total_mem} ({usage_percent:.2f}%)\n\n")

        parts = self.memory_manager.partitions
        width = int(self.memory_canvas["width"])
        if not parts:
            return
        # scale partition widths by actual size
        total = sum(p.size for p in parts)
        x = 0
        for i, part in enumerate(parts):
            w = max(2, (part.size / total) * width)
            x0, x1 = x, x + w
            color = "#90EE90" if getattr(part, "pid", None) is None else self.process_colors.get(getattr(part, "pid"), "#00BFFF")
            text = f"Free\nSize: {part.size}" if getattr(part, "pid", None) is None else f"PID {part.pid}\nSize: {part.size}"
            self.memory_canvas.create_rectangle(x0, 10, x1, 80, fill=color, outline="black")
            self.memory_canvas.create_text((x0 + x1) / 2, 45, text=text)
            self.memory_box.insert(tk.END, f"[{i}] {part}\n")
            x = x1
  

    # ---------------- Paging & Replacement Tab ----------------
    def setup_paging_tab(self):
        frame = ttk.Frame(self.paging_tab)
        frame.pack(pady=10, fill="x")

        # controls - single row
        ttk.Label(frame, text="PID:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.paging_pid_entry = ttk.Entry(frame, width=6)
        self.paging_pid_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Num Pages:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.paging_num_pages_entry = ttk.Entry(frame, width=6)
        self.paging_num_pages_entry.insert(0, "4")
        self.paging_num_pages_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(frame, text="Frames:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.paging_frames_entry = ttk.Entry(frame, width=6)
        self.paging_frames_entry.insert(0, str(self.paging_manager.num_frames))
        self.paging_frames_entry.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(frame, text="Algorithm:").grid(row=0, column=6, padx=5, pady=5, sticky="e")
        self.paging_algo_choice = ttk.Combobox(frame, values=["FIFO", "LRU", "OPT"], state="readonly", width=8)
        self.paging_algo_choice.grid(row=0, column=7, padx=5, pady=5)
        self.paging_algo_choice.set("FIFO")

        # reference string
        ttk.Label(frame, text="Reference String (comma sep):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.paging_refs_entry = ttk.Entry(frame, width=60)
        self.paging_refs_entry.grid(row=1, column=1, columnspan=6, padx=5, pady=5, sticky="w")

        # buttons
        ttk.Button(frame, text="Load Pages (create page table)", command=self.paging_load_pages).grid(row=0, column=8, padx=6)
        ttk.Button(frame, text="Reset Paging", command=self.paging_reset).grid(row=1, column=8, padx=6)
        ttk.Button(frame, text="Start Simulation", command=self.paging_start).grid(row=0, column=9, padx=6)
        ttk.Button(frame, text="Step", command=self.paging_step).grid(row=1, column=9, padx=6)
        ttk.Button(frame, text="Stop", command=self.paging_stop).grid(row=0, column=10, padx=6)

        # frame visualization & page table
        vis_frame = ttk.Frame(self.paging_tab)
        vis_frame.pack(pady=10, fill="both", expand=True)

        self.paging_canvas = tk.Canvas(vis_frame, height=160, width=800, bg="white")
        self.paging_canvas.pack(side="left", padx=8, pady=8, fill="both", expand=False)

        right_vis = ttk.Frame(vis_frame)
        right_vis.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        ttk.Label(right_vis, text="Page Table:").pack(anchor="nw")
        self.paging_table_box = tk.Text(right_vis, height=10, width=40)
        self.paging_table_box.pack(anchor="nw", fill="both", expand=True)

        ttk.Label(right_vis, text="Simulation Log:").pack(anchor="nw")
        self.paging_log_box = tk.Text(right_vis, height=8, width=40)
        self.paging_log_box.pack(anchor="nw", fill="both", expand=True)

        self.update_paging_visual()

    # ---------------- Paging controls ----------------
    def paging_load_pages(self):
        # create page table entries for PID with given num pages
        pid_text = self.paging_pid_entry.get()
        num_text = self.paging_num_pages_entry.get()
        frames_text = self.paging_frames_entry.get()
        try:
            pid = int(pid_text)
            num = int(num_text)
            frames = int(frames_text)
            if num <= 0 or frames <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric PID, pages and frames.")
            return
        # resize paging manager frames if frames changed
        if frames != self.paging_manager.num_frames:
            self.paging_manager = PagingManager(num_frames=frames)
            self.paging_frames_entry.delete(0, tk.END)
            self.paging_frames_entry.insert(0, str(frames))
        self.paging_manager.ensure_pages(pid, num)
        self.paging_table_box.insert(tk.END, f"Loaded page table for PID {pid} with {num} pages.\n")
        self.update_paging_visual()

    def paging_reset(self):
        self.paging_manager.reset()
        self.paging_sim_running = False
        self.paging_sim_index = 0
        self.paging_sim_refs = []
        self.paging_sim_pid = None
        self.paging_sim_algo = "FIFO"
        if self.paging_after_id:
            self.root.after_cancel(self.paging_after_id)
            self.paging_after_id = None
        self.paging_log_box.insert(tk.END, "Paging manager reset.\n")
        self.update_paging_visual()
        self.paging_table_box.delete("1.0", tk.END)

    def paging_parse_refs(self, text):
        # parse comma separated page numbers. allow spaces
        if not text.strip():
            return []
        parts = [p.strip() for p in text.split(",") if p.strip() != ""]
        refs = []
        for p in parts:
            try:
                refs.append(int(p))
            except ValueError:
                # ignore invalid tokens
                pass
        return refs

    def paging_start(self):
        # prepare simulation parameters and start autoplay
        pid_text = self.paging_pid_entry.get()
        refs_text = self.paging_refs_entry.get()
        algo = self.paging_algo_choice.get()
        try:
            pid = int(pid_text)
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric PID.")
            return
        refs = self.paging_parse_refs(refs_text)
        if not refs:
            messagebox.showerror("Error", "Enter a valid reference string (comma separated page numbers).")
            return
        self.paging_sim_pid = pid
        self.paging_sim_refs = refs
        self.paging_sim_index = 0
        self.paging_sim_algo = algo
        self.paging_sim_running = True
        self.paging_log_box.insert(tk.END, f"Starting simulation for PID {pid} with algo {algo}\n")
        self._paging_step_auto()

    def _paging_step_auto(self):
        if not self.paging_sim_running:
            return
        delay = 600
        # perform one step
        cont = self._paging_perform_step()
        if not cont:
            self.paging_sim_running = False
            self.paging_log_box.insert(tk.END, "Simulation finished.\n")
            return
        # schedule next
        self.paging_after_id = self.root.after(delay, self._paging_step_auto)

    def paging_step(self):
        # single step
        if self.paging_sim_pid is None:
            pid_text = self.paging_pid_entry.get()
            try:
                pid = int(pid_text)
            except ValueError:
                messagebox.showerror("Error", "Enter valid numeric PID.")
                return
            refs_text = self.paging_refs_entry.get()
            refs = self.paging_parse_refs(refs_text)
            if not refs:
                messagebox.showerror("Error", "Enter a valid reference string (comma separated page numbers).")
                return
            self.paging_sim_pid = pid
            self.paging_sim_refs = refs
            self.paging_sim_index = 0
            self.paging_sim_algo = self.paging_algo_choice.get()

        self._paging_perform_step()

    def paging_stop(self):
        self.paging_sim_running = False
        if self.paging_after_id:
            self.root.after_cancel(self.paging_after_id)
            self.paging_after_id = None
        self.paging_log_box.insert(tk.END, "Simulation stopped.\n")

    def _paging_perform_step(self):
        """
        Returns True if there are more steps to perform after this one.
        """
        if self.paging_sim_index >= len(self.paging_sim_refs):
            return False
        pid = self.paging_sim_pid
        page = self.paging_sim_refs[self.paging_sim_index]
        algo = self.paging_sim_algo
        # For OPT, pass future refs (list of pages) starting from next index
        opt_future = None
        if algo == "OPT":
            opt_future = self.paging_sim_refs  # our paging manager will use opt_index
        res = self.paging_manager.access_page(pid, page, algorithm=algo, opt_future_refs=self.paging_sim_refs, opt_index=self.paging_sim_index+1)
        # log
        if res["hit"]:
            self.paging_log_box.insert(tk.END, f"Access {self.paging_sim_index}: page {page} -> HIT (frame {res['loaded_frame']})\n")
        else:
            self.paging_log_box.insert(tk.END, f"Access {self.paging_sim_index}: page {page} -> MISS, loaded into frame {res['loaded_frame']}")
            if res["evicted"] is not None:
                self.paging_log_box.insert(tk.END, f", evicted frame {res['evicted']}\n")
            else:
                self.paging_log_box.insert(tk.END, "\n")
        self.paging_sim_index += 1
        self.update_paging_visual()
        return self.paging_sim_index < len(self.paging_sim_refs)

    def update_paging_visual(self):
        # draw frames
        self.paging_canvas.delete("all")
        fw = int(self.paging_canvas["width"])
        fh = int(self.paging_canvas["height"])
        frames = self.paging_manager.frames
        n = len(frames)
        if n == 0:
            return
        margin = 10
        box_w = (fw - 2 * margin) / n
        for i, f in enumerate(frames):
            x0 = margin + i * box_w
            x1 = x0 + box_w - 6
            y0 = 10
            y1 = fh - 30
            color = "#90EE90" if f.pid is None else self.process_colors.get(f.pid, "#00BFFF")
            self.paging_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black")
            text = f"Frame {f.idx}\n"
            if f.pid is None:
                text += "Free"
            else:
                text += f"PID {f.pid}\nPg {f.page}"
            self.paging_canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=text)

        # page table snapshot for the selected pid
        pid_text = self.paging_pid_entry.get()
        try:
            pid = int(pid_text)
        except ValueError:
            pid = None
        self.paging_table_box.delete("1.0", tk.END)
        if pid is not None and pid in self.paging_manager.page_tables:
            tbl = self.paging_manager.page_table_snapshot(pid)
            for pg, fr in sorted(tbl.items()):
                self.paging_table_box.insert(tk.END, f"Page {pg} -> Frame {fr}\n")
        else:
            self.paging_table_box.insert(tk.END, "No page table loaded for this PID.\n")

    # ---------------- Rest of process & memory functions re-used from your code ----------------
    def allocate_memory(self):
        pid_text = self.pid_entry.get()
        size_text = self.mem_size_entry.get()
        algo = self.alloc_algo_choice.get()
        try:
            pid = int(pid_text)
            size = int(size_text)
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric PID and size.")
            return
        proc = next((p for p in self.pm.list_processes() if p.pid == pid), None)
        if not proc:
            messagebox.showerror("Error", f"No process with PID {pid}.")
            return

        success = self.memory_manager.allocate(pid, size, algorithm=algo)
        if not success:
            messagebox.showwarning("Warning", f"Not enough memory for PID {pid}.")
        self.update_memory_display()

    def deallocate_memory(self):
        pid_text = self.pid_entry.get()
        try:
            pid = int(pid_text)
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric PID.")
            return
        self.memory_manager.deallocate(pid)
        self.update_memory_display()

    def defragment_memory(self):
        self.memory_manager.defragment()
        self.update_memory_display()

    def update_memory_display(self):
        self.memory_box.delete("1.0", tk.END)
        self.memory_canvas.delete("all")

        total_used = sum(p.size for p in self.memory_manager.partitions if getattr(p, "pid", None) is not None)
        total_mem = self.memory_manager.total_memory
        usage_percent = (total_used / total_mem * 100) if total_mem else 0

        self.memory_box.insert(tk.END, f"Memory Usage: {total_used}/{total_mem} ({usage_percent:.2f}%)\n\n")

        parts = self.memory_manager.partitions
        width = int(self.memory_canvas["width"])
        if not parts:
            return
        # scale partition widths by actual size
        total = sum(p.size for p in parts)
        x = 0
        for i, part in enumerate(parts):
            w = max(2, (part.size / total) * width)
            x0, x1 = x, x + w
            color = "#90EE90" if getattr(part, "pid", None) is None else self.process_colors.get(getattr(part, "pid"), "#00BFFF")
            text = f"Free\nSize: {part.size}" if getattr(part, "pid", None) is None else f"PID {part.pid}\nSize: {part.size}"
            self.memory_canvas.create_rectangle(x0, 10, x1, 80, fill=color, outline="black")
            self.memory_canvas.create_text((x0 + x1) / 2, 45, text=text)
            self.memory_box.insert(tk.END, f"[{i}] {part}\n")
            x = x1

# ---------------- Run App ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = OSVirtualManagerApp(root)
    root.mainloop()
