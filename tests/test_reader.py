import pytest
from pathlib import Path

from _exceptions import CsvParseError
from reader import read_tasks


FIXTURES = Path(__file__).parent / "fixtures"


class TestReadTasks:
    def test_valid_csv(self) -> None:
        tasks = read_tasks(str(FIXTURES / "valid_tasks.csv"))
        assert len(tasks) == 3
        assert tasks[0].prompt == "A cat walking on beach at sunset"
        assert tasks[0].width == 1152
        assert tasks[0].height == 768
        assert tasks[0].num_frames == 121
        assert tasks[0].frame_rate == 24
        assert tasks[0].seed == 42
        assert tasks[0].image is None
        assert tasks[0].negative_prompt == "blurry"

    def test_empty_fields_become_none(self) -> None:
        tasks = read_tasks(str(FIXTURES / "valid_tasks.csv"))
        # Row 1: image is empty
        assert tasks[0].image is None
        # Row 3: num_frames is 241, seed is empty
        assert tasks[2].seed is None

    def test_single_image_parsing(self) -> None:
        tasks = read_tasks(str(FIXTURES / "single_image.csv"))
        assert len(tasks) == 1
        assert tasks[0].image == ["https://example.com/dog.jpg"]
        assert tasks[0].prompt == "A dog running on grass"

    def test_multi_image_parsing(self) -> None:
        tasks = read_tasks(str(FIXTURES / "multi_image.csv"))
        assert len(tasks) == 1
        assert tasks[0].image == ["a.jpg", "b.jpg", "c.jpg"]

    def test_image_prompt_parsing(self) -> None:
        tasks = read_tasks(str(FIXTURES / "image_prompt.csv"))
        assert len(tasks) == 1
        assert tasks[0].image_prompt == "Cyberpunk city rainy night neon lights"
        assert tasks[0].prompt == "Cinematic drone shot"

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            read_tasks("/nonexistent/file.csv")

    def test_empty_csv(self) -> None:
        with pytest.raises(CsvParseError) as exc:
            read_tasks(str(FIXTURES / "empty.csv"))
        assert "没有数据行" in str(exc.value)

    def test_type_conversion_error(self) -> None:
        import tempfile
        import os
        content = "prompt,width\nhello,abc\n"
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        try:
            read_tasks(f.name)
            assert False, "Should have raised CsvParseError"
        except CsvParseError as e:
            assert e.row_index == 2
        finally:
            os.unlink(f.name)