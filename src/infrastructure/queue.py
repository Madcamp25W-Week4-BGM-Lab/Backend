import time
from typing import Optional, Dict, List
from src.infrastructure.schemas import LLMTask, TaskStatus

# Settings for Task Clean Up ==> different fix: use Redis for "Expiration" feature
TASK_TTL_SECONDS = 600 # keep completed task for 10 minutes, then delete

class MemoryQueue:
    def __init__(self):
        self.tasks: Dict[str, LLMTask] = {}

    async def add_task(self, task: LLMTask) -> LLMTask:
        # Run garbage collector
        self._cleanup_old_tasks()

        # Add new task
        self.tasks[task.id] = task
        print(f"[Queue] Added: {task.id}")
        return task
    
    async def get_task(self, task_id: str) -> Optional[LLMTask]:
        return self.tasks.get(task_id)

    async def pop_pending_task(self) -> Optional[LLMTask]:
        for _, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.PROCESSING
                return task
        return None
    
    async def complete_task(self, task_id: str, result: str) -> Optional[LLMTask]:
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].result = result
            # Update timestamp so TTL counts from *completion* time, not creation time
            self.tasks[task_id].created_at = time.time() 
            print(f"[Queue] Completed: {task_id}")
            return self.tasks[task_id]
        return None
    
    def _cleanup_old_tasks(self):
        """
        Garbage Collector: Deletes tasks that are COMPLETED 
        and older than TASK_TTL_SECONDS.
        """
        current_time = time.time()
        keys_to_delete: List[str] = []

        for task_id, task in self.tasks.items():
            # Only delete if it's DONE and OLD
            if task.status == TaskStatus.COMPLETED:
                age = current_time - task.created_at
                if age > TASK_TTL_SECONDS:
                    keys_to_delete.append(task_id)

        for key in keys_to_delete:
            del self.tasks[key]
            print(f"[Queue] Garbage Collected: {key}")

# Singleton
task_queue = MemoryQueue()