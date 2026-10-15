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


if __name__ == "__main__":
    unittest.main()
