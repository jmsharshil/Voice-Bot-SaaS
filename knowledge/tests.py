import os
import io
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from knowledge.services.text_extractor import extract_text


class TextExtractorTestCase(TestCase):
    def setUp(self):
        # Create a temp txt file
        self.txt_content = "Hello, this is a test knowledge base file content."
        self.txt_path = "test_temp_file.txt"
        with open(self.txt_path, "w", encoding="utf-8") as f:
            f.write(self.txt_content)

    def tearDown(self):
        if os.path.exists(self.txt_path):
            os.remove(self.txt_path)

    def test_extract_from_local_txt_path(self):
        # Test extraction from a local txt file path
        result = extract_text(self.txt_path)
        self.assertEqual(result, self.txt_content)

    def test_extract_from_txt_file_object(self):
        # Test extraction from a text stream (BytesIO)
        stream = io.BytesIO(self.txt_content.encode("utf-8"))
        stream.name = "test.txt"
        result = extract_text(stream)
        self.assertEqual(result, self.txt_content)

    def test_extract_from_django_uploaded_file(self):
        # Test extraction from Django's SimpleUploadedFile
        uploaded_file = SimpleUploadedFile(
            "test_upload.txt",
            self.txt_content.encode("utf-8"),
            content_type="text/plain"
        )
        result = extract_text(uploaded_file)
        self.assertEqual(result, self.txt_content)

    def test_unsupported_extension(self):
        # Test extraction with unsupported extension returns empty string
        stream = io.BytesIO(b"some content")
        stream.name = "test.xyz"
        result = extract_text(stream)
        self.assertEqual(result, "")

