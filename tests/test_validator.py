import pytest

from _types import TaskConfig
from validator import validate


class TestValidate:
    def test_valid_task(self) -> None:
        assert validate(TaskConfig(prompt="cat", num_frames=121, frame_rate=24)) == []

    def test_num_frames_not_8n_plus_1(self) -> None:
        errors = validate(TaskConfig(prompt="cat", num_frames=100))
        assert len(errors) == 1
        assert "8n+1" in errors[0]

    def test_num_frames_above_max(self) -> None:
        errors = validate(TaskConfig(prompt="cat", num_frames=500))
        assert len(errors) >= 1
        assert "441" in errors[0]

    def test_num_frames_below_min(self) -> None:
        errors = validate(TaskConfig(prompt="cat", num_frames=5))
        assert len(errors) >= 1
        assert "9" in errors[0]

    def test_num_frames_none_skips_validation(self) -> None:
        assert validate(TaskConfig(prompt="cat", num_frames=None)) == []

    def test_frame_rate_out_of_range(self) -> None:
        errors = validate(TaskConfig(prompt="cat", frame_rate=100))
        assert len(errors) == 1

    def test_frame_rate_none_skips_validation(self) -> None:
        assert validate(TaskConfig(prompt="cat", frame_rate=None)) == []

    def test_no_prompt_no_image(self) -> None:
        errors = validate(TaskConfig(prompt=None, image=None))
        assert len(errors) == 1
        assert "prompt" in errors[0] or "image" in errors[0]

    def test_width_zero(self) -> None:
        errors = validate(TaskConfig(prompt="cat", width=0))
        assert len(errors) == 1

    def test_height_zero(self) -> None:
        errors = validate(TaskConfig(prompt="cat", height=0))
        assert len(errors) == 1

    def test_invalid_mode(self) -> None:
        errors = validate(TaskConfig(prompt="cat", mode="invalid"))
        assert len(errors) == 1
        assert "ti2vid" in errors[0] or "keyframes" in errors[0]

    @pytest.mark.parametrize("frames", [9, 17, 25, 33, 41, 49, 57, 65, 73, 81, 121, 241, 441])
    def test_valid_num_frames_boundaries(self, frames: int) -> None:
        assert validate(TaskConfig(prompt="cat", num_frames=frames)) == []

    @pytest.mark.parametrize("frames", [8, 10, 16, 18, 440, 442])
    def test_invalid_num_frames_boundaries(self, frames: int) -> None:
        errors = validate(TaskConfig(prompt="cat", num_frames=frames))
        assert len(errors) >= 1