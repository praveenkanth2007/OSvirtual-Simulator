
# main.py
from core.process_manager import ProcessManager
from core.scheduler import fcfs_schedule
from core.memory_manager import MemoryManager

def main():
    pm = ProcessManager()
    mm = MemoryManager(total_memory=1024, partition_size=256)

    # Create processes with memory requests
    p1 = pm.create_process("A", burst_time=3)
    p2 = pm.create_process("B", burst_time=5)
    p3 = pm.create_process("C", burst_time=2)

    # Simulate memory allocation
    mm.allocate_memory(p1.pid, 200)
    mm.allocate_memory(p2.pid, 400)
    mm.allocate_memory(p3.pid, 100)

    print("\nMemory Status:")
    mm.show_memory_status()

    # Run scheduler
    print("\nRunning FCFS scheduler...")
    fcfs_schedule(pm.list_processes(), time_unit=0)

    print("\nFinal Process States:")
    for p in pm.list_processes():
        print(p)

    # Deallocate memory after termination
    print("\nDeallocating memory...")
    for p in pm.list_processes():
        mm.deallocate_memory(p.pid)

    print("\nMemory Status after deallocation:")
    mm.show_memory_status()

if __name__ == "__main__":
    main()
