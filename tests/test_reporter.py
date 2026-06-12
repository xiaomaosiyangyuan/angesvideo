import os
import tempfile
from pathlib import Path

from _types import TaskConfig, TaskResult
from reporter import write_results_csv, setup_logger


class TestWriteResultsCsv:
    def test_write_results(self) -> None:
        out_dir = tempfile.mkdtemp()
        result = TaskResult(
            task=TaskConfig(prompt="test vid", width=1152, height=768, num_frames=121),
            row_index=1, status="success", video_id="vid_123",
            output_path=str(Path(out_dir) / "0001_test.mp4"),
            duration_seconds=5.2,
        )
        csv_path = write_results_csv([result], out_dir)
        assert csv_path.exists()

        with open(csv_path, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert "row_index" in lines[0]
        assert "test vid" in lines[1]
        assert "5.2" in lines[1]

        import shutil
        shutil.rmtree(out_dir)

    def test_empty_results(self) -> None:
        out_dir = tempfile.mkdtemp()
        csv_path = write_results_csv([], out_dir)
        with open(csv_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
        import shutil
        shutil.rmtree(out_dir)


class TestSetupLogger:
    def test_logger_creation(self) -> None:
        log_path = tempfile.mktemp(suffix=".log")
        logger = setup_logger(log_path)
        assert logger.name == "agnes_video_batch"
        assert logger.level == 10  # DEBUG

        logger.info("info message")
        logger.debug("debug message")
        logger.warning("warning message")
        logger.handlers.clear()

        with open(log_path, "r") as f:
            content = f.read()

        assert "info message" in content
        assert "debug message" in content
        assert "warning message" in content
        os.unlink(log_path)

    def test_colored_formatter(self) -> None:
        from reporter import _ColoredFormatter
        import logging

        fmt = _ColoredFormatter("%(levelname)s: %(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        formatted = fmt.format(record)
        assert "\033[32m" in formatted  # Green for INFO
        assert "\033[0m" in formatted   # Reset