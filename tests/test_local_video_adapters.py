import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock

from core.media.generation_bridge import TextToVideoAdapter, LocalVideoFrameAnalysisAdapter


class VideoAdapterTests(unittest.TestCase):
    def test_frame_analysis_is_disabled_without_local_vision_and_tools(self):
        vision = Mock()
        vision.capabilities.return_value = {"enabled": False}
        adapter = LocalVideoFrameAnalysisAdapter(vision, ffmpeg=None, ffprobe=None)
        self.assertFalse(adapter.capabilities()["enabled"])
        self.assertEqual(adapter.capabilities()["operations"], [])

    def test_text_to_video_is_separate_and_requires_local_backend(self):
        adapter = TextToVideoAdapter()
        self.assertFalse(adapter.capabilities()["enabled"])
        backend = Mock()
        backend.local_only = True
        backend.generate_video.return_value = {"filename": "clip.mp4"}
        adapter = TextToVideoAdapter(backend)
        self.assertEqual(adapter.capabilities()["operations"], ["text_to_video"])
        self.assertEqual(adapter.execute("text_to_video", {"prompt": "Bir gün doğumu"}),
                         {"filename": "clip.mp4"})
        backend.generate_video.assert_called_once_with(prompt="Bir gün doğumu", duration_seconds=4.0)

    def test_text_to_video_rejects_empty_or_oversized_prompt(self):
        backend = Mock()
        backend.local_only = True
        backend.generate_video = Mock()
        adapter = TextToVideoAdapter(backend)
        with self.assertRaisesRegex(RuntimeError, "istemi"):
            adapter.execute("text_to_video", {"prompt": " "})
        with self.assertRaisesRegex(RuntimeError, "istemi"):
            adapter.execute("text_to_video", {"prompt": "x" * 2001})
        backend.generate_video.assert_not_called()

    def test_video_sampling_is_evenly_spaced_and_uses_local_vision(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                video = Path("memory/videos/sample.mp4")
                video.parent.mkdir(parents=True)
                video.write_bytes(b"local-video")
                vision = Mock()
                vision.capabilities.return_value = {"enabled": True}
                vision.model = "local-vision"
                vision.execute.return_value = {"text": "Kare açıklandı."}
                adapter = LocalVideoFrameAnalysisAdapter(vision, ffmpeg="ffmpeg", ffprobe="ffprobe")
                def run(command, **kwargs):
                    if command[0] == "ffprobe":
                        return Mock(stdout="10", stderr="")
                    return Mock(stdout=b"png-frame", stderr=b"")
                with patch("subprocess.run", side_effect=run):
                    result = adapter.execute("analyze_video_frames", {"video_path": str(video), "frame_count": 4})
                timestamps = [frame["timestamp_seconds"] for frame in result["frames"]]
                self.assertEqual(timestamps, [1.25, 3.75, 6.25, 8.75])
                self.assertEqual(vision.execute.call_count, 4)
                self.assertIn("not_full_temporal_understanding", result["mode"])
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
