from unittest.mock import Mock


from _types import TaskConfig, AppConfig, TaskResult
from runner import _build_output_filename, _backoff_delay


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