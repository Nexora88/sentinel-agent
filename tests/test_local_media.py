import tempfile
import unittest
from unittest.mock import patch
from tools.image_gen import ImageGenerator, MediaToolError


class LocalMediaTests(unittest.TestCase):
    def test_no_public_fallback_when_backend_missing(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"SD_API_URL": ""}):
            generator = ImageGenerator(directory)
            with self.assertRaisesRegex(MediaToolError, "Dış görsel servisine veri gönderilmedi"):
                generator.generate("bir dağ manzarası")

    def test_rejects_public_backend_host(self):
        with patch.dict("os.environ", {"SD_API_URL": "http://public.example.com:7860"}):
            with self.assertRaises(MediaToolError):
                ImageGenerator()

    def test_rejects_https_endpoint_instead_of_local_http(self):
        with patch.dict("os.environ", {"SD_API_URL": "https://images.example.com"}):
            with self.assertRaises(MediaToolError):
                ImageGenerator()

    def test_video_filename_cannot_escape_output_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"SD_API_URL": ""}):
            generator = ImageGenerator(directory)
            with self.assertRaises(MediaToolError):
                generator.create_video("../secret.png")


    def test_story_video_requires_two_to_six_scenes(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ImageGenerator(directory)
            with self.assertRaisesRegex(MediaToolError, "2-6"):
                generator.create_story_video(["only one scene"])

    def test_story_video_generates_local_storyboard_and_reports_mode_honestly(self):
        from pathlib import Path
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            generator = ImageGenerator(directory)
            for name in ("frame_a.png", "frame_b.png"):
                (Path(directory) / name).write_bytes(b"test-frame")
            with patch.object(generator, "generate", side_effect=[
                {"filename": "frame_a.png"}, {"filename": "frame_b.png"}
            ]), patch("tools.image_gen.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
                "tools.image_gen.subprocess.run"
            ) as run:
                def create_output(command, **kwargs):
                    Path(command[-1]).write_bytes(b"mp4-test")
                    return Mock(returncode=0, stdout=b"", stderr=b"")
                run.side_effect = create_output
                result = generator.create_story_video(["A sunrise over mountains", "A city at night"], 6)
            self.assertTrue(result["success"])
            self.assertEqual(result["scene_count"], 2)
            self.assertIn("not neural text-to-video", result["mode"])
            self.assertTrue((Path(directory) / result["filename"]).is_file())

    def test_generated_image_is_normalized_to_real_png(self):
        import base64
        import io
        from pathlib import Path
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            generator = ImageGenerator(directory)
            source = io.BytesIO()
            Image.new("RGB", (32, 24), (20, 40, 60)).save(source, format="JPEG")
            result = generator._save_b64_image(base64.b64encode(source.getvalue()).decode("ascii"), "test")
            target = Path(directory) / result["filename"]
            with Image.open(target) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (32, 24))
            self.assertEqual(list(Path(directory).glob(".image-*.tmp")), [])

    def test_generated_image_rejects_invalid_base64_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ImageGenerator(directory)
            with self.assertRaises(MediaToolError):
                generator._save_b64_image("not-valid-base64!", "test")

if __name__ == "__main__":
    unittest.main()
