
from _types import TaskConfig, AppConfig, TaskStatus, TaskResult


class TestTaskConfig:
    def test_default_all_none(self) -> None:
        t = TaskConfig()
        assert t.prompt is None
        assert t.width is None
        assert t.height is None
        assert t.num_frames is None
        assert t.frame_rate is None
        assert t.seed is None
        assert t.image is None
        assert t.image_prompt is None
        assert t.negative_prompt is None
        assert t.mode is None
        assert t.extra_body_image is None
        assert t.extra_body_mode is None

    def test_with_prompt(self) -> None:
        t = TaskConfig(prompt="hello")
        assert t.prompt == "hello"

    def test_with_image_list(self) -> None:
        t = TaskConfig(image=["a.jpg", "b.jpg"])
        assert t.image == ["a.jpg", "b.jpg"]


class TestAppConfig:
    def test_default_values(self) -> None:
        c = AppConfig(api_key="key123")
        assert c.api_key == "key123"
        assert c.base_url == "https://apihub.agnes-ai.com"
        assert c.default_width == 1152
        assert c.default_height == 768
        assert c.default_num_frames == 121
        assert c.default_frame_rate == 24

    def test_custom_values(self) -> None:
        c = AppConfig(api_key="key", csv_path="t.csv", poll_interval=10, max_retries=5)
        assert c.csv_path == "t.csv"
        assert c.poll_interval == 10
        assert c.max_retries == 5


class TestTaskStatus:
    def test_video_id_only(self) -> None:
        s = TaskStatus(video_id="vid_1", status="queued")
        assert s.video_id == "vid_1"
        assert s.status == "queued"
        assert s.progress == 0

    def test_completed(self) -> None:
        s = TaskStatus(video_id="vid_1", status="completed", video_url="http://example.com/v.mp4")
        assert s.status == "completed"
        assert s.video_url == "http://example.com/v.mp4"


class TestTaskResult:
    def test_success(self) -> None:
        task = TaskConfig(prompt="test")
        r = TaskResult(task=task, row_index=1, status="success", output_path="/tmp/v.mp4")
        assert r.status == "success"
        assert r.output_path == "/tmp/v.mp4"

    def test_default_duration(self) -> None:
        task = TaskConfig(prompt="test")
        r = TaskResult(task=task, row_index=1, status="failed")
        assert r.duration_seconds == 0.0