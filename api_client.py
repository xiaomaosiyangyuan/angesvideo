import logging
import time
from pathlib import Path
from typing import Any

import requests

from _constants import DOWNLOAD_RETRIES, DOWNLOAD_RETRY_DELAY, IMAGE_MODEL, DEFAULT_IMAGE_SIZE
from _exceptions import ApiError, NetworkError
from _types import AppConfig, TaskConfig, TaskStatus

AGNES_BASE = "https://apihub.agnes-ai.com"


class AgnesClient:
    def __init__(self, api_key: str, base_url: str = AGNES_BASE) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def submit_task(self, task: TaskConfig, defaults: AppConfig | None = None) -> str:
        body: dict[str, Any] = {
            "model": "agnes-video-v2.0",
        }

        candidates = {
            "prompt": task.prompt,
            "height": task.height,
            "width": task.width,
            "num_frames": task.num_frames,
            "frame_rate": task.frame_rate,
            "negative_prompt": task.negative_prompt,
            "seed": task.seed,
            "mode": task.mode,
        }
        for key, val in candidates.items():
            if val is not None:
                body[key] = val

        if defaults:
            if task.height is None:
                body["height"] = defaults.default_height
            if task.width is None:
                body["width"] = defaults.default_width
            if task.num_frames is None:
                body["num_frames"] = defaults.default_num_frames
            if task.frame_rate is None:
                body["frame_rate"] = defaults.default_frame_rate

        extra: dict[str, Any] = {}
        if task.extra_body_image is not None:
            extra["image"] = task.extra_body_image
        if task.extra_body_mode is not None:
            extra["mode"] = task.extra_body_mode

        if task.image is not None:
            body["image"] = task.image[0]
            if len(task.image) > 1:
                extra["image"] = task.image
                body["mode"] = "keyframes"
                extra["mode"] = "keyframes"

        if extra:
            body["extra_body"] = extra

        try:
            resp = self._session.post(
                f"{self.base_url}/v1/videos",
                json=body,
                timeout=(30, 300),
            )
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"提交任务超时: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"网络连接失败: {e}") from e

        if not resp.ok:
            raise ApiError(resp.status_code, resp.text)

        data = resp.json()
        video_id = data.get("video_id") or data.get("id") or data.get("task_id")
        if not video_id:
            raise ApiError(resp.status_code, resp.text, "响应中未找到 video_id")
        return str(video_id)

    def query_task(self, video_id: str) -> TaskStatus:
        errors: list[str] = []

        endpoints: list[tuple[str, dict[str, Any]]] = [
            (f"{self.base_url}/agnesapi", {"params": {"video_id": video_id}}),
        ]

        for url, extra_kwargs in endpoints:
            try:
                resp = self._session.get(url, timeout=(30, 120), **extra_kwargs)
            except requests.exceptions.RequestException as e:
                errors.append(f"{url}: {e}")
                continue

            if not resp.ok:
                errors.append(f"{url}: HTTP {resp.status_code} {resp.text[:200]}")
                continue

            data = resp.json()
            status_str = str(data.get("status", "unknown"))
            return TaskStatus(
                video_id=str(data.get("video_id", video_id)),
                status=status_str,
                progress=int(data.get("progress", 0)),
                    video_url=data.get("video_url") or data.get("url") or data.get("result") or data.get("remixed_from_video_id"),
                error=data.get("error"),
            )

        raise NetworkError(f"所有查询端点均失败: {'; '.join(errors)}")

    def generate_image(self, prompt: str, size: str = DEFAULT_IMAGE_SIZE) -> str:
        body = {
            "model": IMAGE_MODEL,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/images/generations",
                json=body,
                timeout=(30, 120),
            )
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"图片生成超时: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"网络连接失败: {e}") from e

        if not resp.ok:
            raise ApiError(resp.status_code, resp.text)

        data = resp.json()
        image_url: str | None = None
        if isinstance(data.get("data"), list) and len(data["data"]) > 0:
            image_url = data["data"][0].get("url")

        if not image_url:
            raise ApiError(resp.status_code, resp.text, "图片生成响应中未找到 URL")

        return image_url

    def download_video(self, video_url: str, output_path: str | Path) -> Path:
        output_path = Path(output_path)

        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            try:
                resp = requests.get(
                    video_url,
                    timeout=(30, 300),
                    stream=True,
                )
            except requests.exceptions.RequestException as e:
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(DOWNLOAD_RETRY_DELAY)
                    continue
                raise NetworkError(f"下载失败（已重试 {DOWNLOAD_RETRIES} 次）: {e}") from e

            if not resp.ok:
                raise ApiError(resp.status_code, resp.text)

            content_type = resp.headers.get("Content-Type", "")
            if not content_type.startswith("video/") and content_type:
                logging.getLogger(__name__).warning(
                    f"Content-Type 不是 video/*: {content_type}，继续保存",
                )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            return output_path

        raise NetworkError(f"下载失败（已重试 {DOWNLOAD_RETRIES} 次）")