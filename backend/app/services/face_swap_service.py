"""Face swap service using FaceFusion on GPU server (10.190.0.222).

Pipeline:
  1. Upload source face + target video to GPU server
  2. Run FaceFusion headless-run (face_swapper + face_enhancer)
  3. Download result

Requires:
  - SSH access to neo@10.190.0.222 (keyless)
  - FaceFusion conda env 'facefusion' on server
  - Model: inswapper_128_fp16 + gfpgan_1.4
"""
import asyncio
import os
import tempfile
import uuid
from typing import Optional

from ..config import settings


class FaceSwapService:
    """Swap faces in video using FaceFusion on remote GPU server."""

    GPU_HOST = "neo@10.190.0.222"
    REMOTE_DIR = "/mnt/disk3/facefusion"
    CONDA_ACTIVATE = (
        'export PATH="$HOME/miniconda3/bin:$PATH" && '
        'eval "$(conda shell.bash hook)" && '
        "conda activate facefusion"
    )

    def __init__(self):
        self.face_swapper_model = "inswapper_128_fp16"
        self.face_enhancer_model = "gfpgan_1.4"
        self.face_enhancer_blend = 80

    async def swap_face(
        self,
        source_face_path: str,
        target_video_path: str,
        output_path: str,
        enhancer: bool = True,
        enhancer_blend: int = 80,
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        remote_job_dir = f"{self.REMOTE_DIR}/jobs/{job_id}"

        try:
            await self._ssh(f"mkdir -p {remote_job_dir}")
            await self._upload(source_face_path, f"{remote_job_dir}/source.png")
            await self._upload(target_video_path, f"{remote_job_dir}/target.mp4")

            processors = "face_swapper"
            extra_args = ""
            if enhancer:
                processors += " face_enhancer"
                extra_args += f" --face-enhancer-model {self.face_enhancer_model}"
                extra_args += f" --face-enhancer-blend {enhancer_blend}"

            cmd = (
                f"cd {self.REMOTE_DIR} && "
                f"python facefusion.py headless-run "
                f"-s {remote_job_dir}/source.png "
                f"-t {remote_job_dir}/target.mp4 "
                f"-o {remote_job_dir}/output.mp4 "
                f"--processors {processors} "
                f"--face-swapper-model {self.face_swapper_model} "
                f"--face-detector-model yolo_face "
                f"--face-selector-mode many "
                f"--output-video-encoder libx264 "
                f"--output-video-quality 85 "
                f"--execution-providers cuda "
                f"--execution-device-ids 0 "
                f"--execution-thread-count 2 "
                f"{extra_args}"
            )

            print(f"[FaceSwap] Running job {job_id}...")
            result = await self._ssh_conda(cmd)

            check = await self._ssh(f"ls -la {remote_job_dir}/output.mp4 2>/dev/null")
            if "output.mp4" not in check:
                raise RuntimeError(f"FaceFusion output not found. Log: {result[-500:]}")

            await self._download(f"{remote_job_dir}/output.mp4", output_path)
            print(f"[FaceSwap] Done! Output: {output_path}")
            await self._ssh(f"rm -rf {remote_job_dir}")
            return output_path

        except Exception as e:
            await self._ssh(f"rm -rf {remote_job_dir}")
            raise RuntimeError(f"Face swap failed: {e}")

    async def generate_synthetic_face(
        self,
        reference_image_path: Optional[str] = None,
        prompt: str = "",
        output_path: str = "",
    ) -> str:
        from .image_generation_service import image_gen_service

        if not prompt:
            prompt = (
                "professional headshot portrait of a young Chinese woman, "
                "age 25-30, fair skin, natural makeup, warm smile, "
                "soft studio lighting, white background, photorealistic, "
                "face clearly visible front-facing, high quality"
            )
        if not output_path:
            output_path = os.path.join(
                settings.output_dir, "faces", f"gen_face_{uuid.uuid4().hex[:8]}.png"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        face_negative = (
            "nsfw, ugly, deformed, text, watermark, signature, logo, "
            "low quality, blurry, distorted, bad anatomy, extra limbs, "
            "disfigured, glasses, hat, mask, obscured face, multiple faces, "
            "looking away, eyes closed, extreme makeup, cartoon, painting"
        )
        await image_gen_service.generate_scene_image(
            prompt=prompt,
            output_path=output_path,
            negative_prompt=face_negative,
            width=512,
            height=768,
            steps=30,
            cfg_scale=6.0,
        )
        return output_path

    async def _ssh(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "ssh", self.GPU_HOST, cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode() + stderr.decode()

    async def _ssh_conda(self, cmd: str) -> str:
        """Execute SSH command with conda env activated (uses GPU 1 for CUDA)."""
        full_cmd = f"export CUDA_VISIBLE_DEVICES=1 && {self.CONDA_ACTIVATE} && {cmd}"
        proc = await asyncio.create_subprocess_exec(
            "ssh", self.GPU_HOST, full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode() + stderr.decode()

    async def _upload(self, local_path: str, remote_path: str):
        proc = await asyncio.create_subprocess_shell(
            f'cat "{local_path}" | ssh {self.GPU_HOST} "cat > {remote_path}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Upload failed: {local_path} -> {remote_path}")

    async def _download(self, remote_path: str, local_path: str):
        proc = await asyncio.create_subprocess_shell(
            f'ssh {self.GPU_HOST} "cat {remote_path}" > "{local_path}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Download failed: {remote_path} -> {local_path}")

    async def check_connectivity(self) -> bool:
        try:
            result = await self._ssh_conda(
                f"cd {self.REMOTE_DIR} && python -c "
                "'from facefusion import metadata; print(metadata.get(\"version\"))'"
            )
            return "3." in result
        except Exception:
            return False


face_swap_service = FaceSwapService()
