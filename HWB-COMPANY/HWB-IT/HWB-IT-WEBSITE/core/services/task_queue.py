"""
SigmaFidelity™ Enterprise Managed Task Queue & Background Worker
Standard: HWB-QMS-7.6 Enterprise Architecture Standards (SOC 2 / ISO 27001)
Custodians: George (Systems Architect) & Peter (Recovery Specialist)
"""

import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Dict, Optional

class TaskJob:
    def __init__(self, task_id: str, name: str, fn: Callable, args: tuple, kwargs: dict, max_retries: int = 2):
        self.task_id = task_id
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.max_retries = max_retries
        self.retry_count = 0
        self.status = "QUEUED"  # QUEUED, RUNNING, SUCCESS, FAILED
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "retries": self.retry_count,
            "max_retries": self.max_retries,
            "error": self.error,
            "duration_seconds": round((self.completed_at or time.time()) - self.started_at, 2) if self.started_at else 0,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at)),
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.completed_at)) if self.completed_at else None
        }


class EnterpriseTaskQueue:
    """
    Managed background task queue with automated worker thread pool,
    retry policies, and live execution telemetry.
    """
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SigmaWorker")
        self._tasks: Dict[str, TaskJob] = {}
        self._lock = threading.Lock()

    def enqueue(self, fn: Callable, *args, name: Optional[str] = None, max_retries: int = 2, **kwargs) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task_name = name or fn.__name__
        job = TaskJob(task_id, task_name, fn, args, kwargs, max_retries=max_retries)
        
        with self._lock:
            self._tasks[task_id] = job
            
        self.executor.submit(self._execute_job, job)
        print(f"[TASK_QUEUE] Enqueued background job: {task_name} (ID: {task_id})", flush=True)
        return task_id

    def _execute_job(self, job: TaskJob):
        job.started_at = time.time()
        job.status = "RUNNING"
        
        while job.retry_count <= job.max_retries:
            try:
                job.result = job.fn(*job.args, **job.kwargs)
                job.status = "SUCCESS"
                job.completed_at = time.time()
                print(f"[TASK_QUEUE] Task completed successfully: {job.name} ({job.task_id}) in {job.completed_at - job.started_at:.2f}s", flush=True)
                return
            except Exception as e:
                job.retry_count += 1
                job.error = str(e)
                print(f"[TASK_QUEUE_WARN] Task {job.name} ({job.task_id}) failed attempt {job.retry_count}/{job.max_retries}: {e}", flush=True)
                if job.retry_count <= job.max_retries:
                    time.sleep(1 * job.retry_count)  # Linear backoff
                    
        job.status = "FAILED"
        job.completed_at = time.time()
        print(f"[TASK_QUEUE_FATAL] Task permanently failed: {job.name} ({job.task_id}) - {job.error}", flush=True)

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._tasks.get(task_id)
            return job.to_dict() if job else None

    def list_recent(self, limit: int = 20) -> list:
        with self._lock:
            sorted_jobs = sorted(self._tasks.values(), key=lambda j: j.created_at, reverse=True)
            return [j.to_dict() for j in sorted_jobs[:limit]]


task_queue = EnterpriseTaskQueue(max_workers=4)
