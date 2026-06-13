from unittest.mock import Mock, patch

import pytest

from _exceptions import ApiError, NetworkError
from _types import TaskConfig, AppConfig


class TestAgnesClient:
    @patch("api_client.requests.Session")
    def test_submit_task_success(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.ok = True
        mock_session.post.return_value.json.return_value = {"video_id": "vid_123", "status": "queued"}

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        task = TaskConfig(prompt="test video")

        video_id = client.submit_task(task)
        assert video_id == "vid_123"

    @patch("api_client.requests.Session")
    def test_submit_task_http_error(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.ok = False
        mock_session.post.return_value.status_code = 400
        mock_session.post.return_value.text = "bad request"

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")

        with pytest.raises(ApiError) as exc:
            client.submit_task(TaskConfig(prompt="test"))
        assert exc.value.status_code == 400

    @patch("api_client.requests.Session")
    def test_submit_task_timeout(self, mock_session_cls: Mock) -> None:
        from requests.exceptions import Timeout
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.side_effect = Timeout("timeout")

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")

        with pytest.raises(NetworkError):
            client.submit_task(TaskConfig(prompt="test"))

    @patch("api_client.requests.Session")
    def test_submit_single_image_sends_string(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.ok = True
        mock_session.post.return_value.json.return_value = {"video_id": "vid_1"}

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        task = TaskConfig(prompt="test", image=["https://example.com/img.jpg"])

        client.submit_task(task)
        body = mock_session.post.call_args[1]["json"]
        assert body["image"] == "https://example.com/img.jpg"
        assert isinstance(body["image"], str)

    @patch("api_client.requests.Session")
    def test_submit_multi_image_sends_array(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.ok = True
        mock_session.post.return_value.json.return_value = {"video_id": "vid_1"}

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        task = TaskConfig(prompt="test", image=["a.jpg", "b.jpg", "c.jpg"])

        client.submit_task(task)
        body = mock_session.post.call_args[1]["json"]
        assert body["image"] == "a.jpg"
        assert isinstance(body["image"], str)
        assert body["mode"] == "keyframes"
        assert body["extra_body"]["image"] == ["a.jpg", "b.jpg", "c.jpg"]
        assert body["extra_body"]["mode"] == "keyframes"

    @patch("api_client.requests.Session")
    def test_generate_image_success(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.ok = True
        mock_session.post.return_value.json.return_value = {
            "data": [{"url": "https://example.com/gen_img.png"}],
        }

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        url = client.generate_image("test prompt", size="1152x768")

        assert url == "https://example.com/gen_img.png"
        body = mock_session.post.call_args[1]["json"]
        assert body["model"] == "agnes-image-2.0-flash"
        assert body["prompt"] == "test prompt"
        assert body["size"] == "1152x768"

    @patch("api_client.requests.Session")
    def test_submit_fills_defaults(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.ok = True
        mock_session.post.return_value.json.return_value = {"video_id": "vid_1"}

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        defaults = AppConfig(api_key="k")
        task = TaskConfig(prompt="test")

        client.submit_task(task, defaults=defaults)
        body = mock_session.post.call_args[1]["json"]
        assert body["height"] == 768
        assert body["width"] == 1152
        assert body["num_frames"] == 121
        assert body["frame_rate"] == 24

    @patch("api_client.requests.Session")
    def test_query_task_completed(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.get.return_value.ok = True
        mock_session.get.return_value.json.return_value = {
            "video_id": "vid_1", "status": "completed",
            "video_url": "https://example.com/v.mp4", "progress": 100,
        }

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        status = client.query_task("vid_1")
        assert status.status == "completed"
        assert status.video_url == "https://example.com/v.mp4"
        assert status.progress == 100

    @patch("api_client.requests.Session")
    def test_query_task_failed(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.get.return_value.ok = True
        mock_session.get.return_value.json.return_value = {
            "video_id": "vid_1", "status": "failed", "error": "out of credits",
        }

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")
        status = client.query_task("vid_1")
        assert status.status == "failed"
        assert status.error == "out of credits"

    @patch("api_client.requests.Session")
    def test_query_task_http_error(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.get.return_value.ok = False
        mock_session.get.return_value.status_code = 401
        mock_session.get.return_value.text = "unauthorized"

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")

        with pytest.raises(NetworkError):
            client.query_task("vid_1")

    @patch("api_client.requests.Session")
    def test_download_video_success(self, mock_session_cls: Mock) -> None:
        import os
        import tempfile
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_resp = Mock()
        mock_resp.ok = True
        mock_resp.headers = {"Content-Type": "video/mp4"}
        mock_resp.iter_content.return_value = [b"fake video data"]
        mock_session.get.return_value = mock_resp

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")

        out_dir = tempfile.mkdtemp()
        out_path = os.path.join(out_dir, "test_video.mp4")
        result = client.download_video("https://example.com/v.mp4", out_path)
        assert str(result) == out_path.replace("\\", "/") or str(result) == out_path
        assert os.path.getsize(out_path) > 0

        import shutil
        shutil.rmtree(out_dir)

    @patch("api_client.requests.Session")
    def test_download_video_http_error(self, mock_session_cls: Mock) -> None:
        mock_session = Mock()
        mock_session_cls.return_value = mock_session
        mock_session.get.return_value.ok = False
        mock_session.get.return_value.status_code = 404
        mock_session.get.return_value.text = "not found"

        from api_client import AgnesClient
        client = AgnesClient(api_key="test-key")

        with pytest.raises(ApiError):
            client.download_video("https://example.com/v.mp4", "/tmp/nonexistent/v.mp4")