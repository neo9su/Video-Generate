"""GPU Scheduler Service — manages ComfyUI GPU queue and assignment."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class GPUInfo(BaseModel):
    id: int
    name: str
    memory_total: int
    memory_used: int
    memory_free: int
    utilization: float
    temperature: float
    status: str  # "idle", "busy", "error"


class GPUQueueItem(BaseModel):
    task_id: int
    user_id: int
    priority: int  # 0-100, higher = more priority
    gpu_required: int  # MB VRAM needed
    workflow_type: str  # "image", "video", "tts"
    created_at: datetime


class GPUScheduler:
    """Schedules GPU workloads across a pool of ComfyUI instances."""

    def __init__(self, comfyui_urls: list[str]):
        self.comfyui_urls = comfyui_urls
        self.queue: list[GPUQueueItem] = []
        self.gpu_status: dict[int, GPUInfo] = {}

    async def get_gpu_status(self) -> list[GPUInfo]:
        """Query nvidia-smi-like API or ComfyUI queue.
        Returns status of all GPUs.
        """
        # TODO: Implement actual GPU status polling from ComfyUI endpoints
        return list(self.gpu_status.values())

    async def enqueue(self, item: GPUQueueItem):
        """Add to priority queue and sort by priority (highest first)."""
        self.queue.append(item)
        self.queue.sort(key=lambda x: x.priority, reverse=True)

    async def dequeue(self) -> Optional[GPUQueueItem]:
        """Get highest priority task for available GPU."""
        if not self.queue:
            return None
        return self.queue.pop(0)

    async def assign_to_gpu(self, item: GPUQueueItem) -> bool:
        """Assign task to best available GPU. Update GPU status."""
        # TODO: Implement actual GPU assignment logic
        return True

    async def get_queue_status(self) -> dict:
        """Queue length, estimated wait time, GPU availability."""
        return {
            "queue_length": len(self.queue),
            "estimated_wait_seconds": len(self.queue) * 30,  # rough estimate
            "available_gpus": sum(
                1 for g in self.gpu_status.values() if g.status == "idle"
            ),
            "total_gpus": len(self.gpu_status),
        }

    def check_connectivity(self) -> bool:
        """Check ComfyUI connectivity."""
        # TODO: Implement actual connectivity check
        return bool(self.comfyui_urls)


# Singleton
gpu_scheduler = GPUScheduler(comfyui_urls=[])
