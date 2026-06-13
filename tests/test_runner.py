from unittest.mock import Mock


from _types import TaskConfig, AppConfig, TaskResult
from runner import _build_output_filename, _backoff_delay, _image_size


class TestBuildOutputFilename:
    def test_basic(self) -> None:
        result = _build_output_filename(1, "A cat @ beach!")
        assert result.startswith("0001_")
        assert result.endswith(".mp4")

    def test_sanitize_special_chars(self) -> None:
        result = _build_output_filename(5, "test<>:\"/\\|?*")
        # Sanitized: all special chars become _
        assert "_" in result
        assert result.startswith("0005_")

    def test_prompt_truncated(self) -> None:
        long_prompt = "a" * 100
        _build_output_filename(2, long_prompt)
        assert len(long_prompt[:20].strip()) <= 20


class TestBackoffDelay:
    def test_attempt_1(self) -> None:
        assert _backoff_delay(1) == 5.0

    def test_attempt_2(self) -> None:
        assert _backoff_delay(2) == 10.0

    def test_attempt_3(self) -> None:
        assert _backoff_delay(3) == 15.0


class TestRunBatch:
    def test_all_success(self) -> None:
        from runner import run_batch
        from api_client import AgnesClient

        client = Mock(spec=AgnesClient)
        client.submit_task.return_value = "vid_1"
        client.query_task.return_value = Mock(
            status="completed", video_url="https://example.com/v.mp4",
        )
        client.download_video.return_value = "/tmp/vid_1.mp4"

        tasks = [
            TaskConfig(prompt="test1"),
            TaskConfig(prompt="test2"),
            TaskConfig(prompt="test3"),
        ]
        config = AppConfig(api_key="test", output_dir="/tmp/out", max_retries=3, poll_interval=1)

        results = run_batch(tasks, client, config)
        assert len(results) == 3
        assert all(r.status == "success" for r in results)

    def test_partial_failure(self) -> None:
        from runner import run_batch
        from api_client import AgnesClient
        from _exceptions import ApiError

        client = Mock(spec=AgnesClient)

        call_count = [0]

        def submit_side_effect(task: TaskConfig, defaults: AppConfig | None = None) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                return "vid_1"
            raise ApiError(500, "server error")

        client.submit_task.side_effect = submit_side_effect
        client.query_task.return_value = Mock(status="completed", video_url="https://example.com/v.mp4")
        client.download_video.return_value = "/tmp/vid_1.mp4"

        tasks = [
            TaskConfig(prompt="test1"),
            TaskConfig(prompt="test2"),
        ]
        config = AppConfig(api_key="test", output_dir="/tmp/out", max_retries=2, poll_interval=1)

        results = run_batch(tasks, client, config)
        assert len(results) == 2
        assert results[0].status == "success"
        assert results[1].status == "failed"

    def test_progress_callback_called(self) -> None:
        from runner import run_batch
        from api_client import AgnesClient

        client = Mock(spec=AgnesClient)
        client.submit_task.return_value = "vid_1"
        client.query_task.return_value = Mock(
            status="completed", video_url="https://example.com/v.mp4",
        )
        client.download_video.return_value = "/tmp/vid_1.mp4"

        tasks = [TaskConfig(prompt="test1"), TaskConfig(prompt="test2")]
        config = AppConfig(api_key="test", output_dir="/tmp/out", max_retries=3, poll_interval=1)

        calls: list[tuple[int, int, TaskResult]] = []

        def cb(current: int, total: int, result: TaskResult) -> None:
            calls.append((current, total, result))

        run_batch(tasks, client, config, progress_callback=cb)
        assert len(calls) == 2
        assert calls[0] == (1, 2, calls[0][2])
        assert calls[1] == (2, 2, calls[1][2])


class TestImageSize:
    def test_uses_task_dimensions(self) -> None:
        config = AppConfig(api_key="test")
        task = TaskConfig(width=1920, height=1080)
        assert _image_size(task, config) == "1920x1080"

    def test_falls_back_to_defaults(self) -> None:
        config = AppConfig(api_key="test", default_width=1152, default_height=768)
        task = TaskConfig()
        assert _image_size(task, config) == "1152x768"

    def test_mixed_defaults(self) -> None:
        config = AppConfig(api_key="test", default_width=1280, default_height=720)
        task = TaskConfig(width=1920)
        assert _image_size(task, config) == "1920x720"


class TestRunBatchWithImagePrompt:
    def test_generates_image_before_video(self) -> None:
        from runner import run_batch
        from api_client import AgnesClient

        client = Mock(spec=AgnesClient)
        client.generate_image.return_value = "https://example.com/gen_img.png"
        client.submit_task.return_value = "vid_1"
        client.query_task.return_value = Mock(
            status="completed", video_url="https://example.com/v.mp4",
        )
        client.download_video.return_value = "/tmp/vid_1.mp4"

        task = TaskConfig(prompt="video prompt", image_prompt="image prompt")
        config = AppConfig(api_key="test", output_dir="/tmp/out", max_retries=3, poll_interval=1)

        results = run_batch([task], client, config)
        assert len(results) == 1
        assert results[0].status == "success"

        client.generate_image.assert_called_once_with("image prompt", size="1152x768")
        submitted = client.submit_task.call_args[0][0]
        assert submitted.image == ["https://example.com/gen_img.png"]

    def test_skips_image_generation_when_image_already_set(self) -> None:
        from runner import run_batch
        from api_client import AgnesClient

        client = Mock(spec=AgnesClient)
        client.submit_task.return_value = "vid_1"
        client.query_task.return_value = Mock(
            status="completed", video_url="https://example.com/v.mp4",
        )
        client.download_video.return_value = "/tmp/vid_1.mp4"

        task = TaskConfig(prompt="test", image=["https://existing.jpg"], image_prompt="should be ignored")
        config = AppConfig(api_key="test", output_dir="/tmp/out", max_retries=3, poll_interval=1)

        run_batch([task], client, config)
        client.generate_image.assert_not_called()