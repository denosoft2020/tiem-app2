import io
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from unittest.mock import patch

class UploadMediaViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('upload_media') if 'upload_media' in [url.name for url in self.client.handler._urls.urlpatterns] else '/upload_media/'

    def tearDown(self):
        # Clean up any uploaded files
        for file in default_storage.listdir('uploads')[1]:
            default_storage.delete(f'uploads/{file}')

    def test_upload_media_no_file(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertIn('No file provided', response.json()['message'])

    def test_upload_media_success(self):
        file_content = b'test file content'
        uploaded_file = SimpleUploadedFile('test.txt', file_content, content_type='text/plain')
        response = self.client.post(self.url, {'file': uploaded_file, 'file_type': 'text'}, format='multipart')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('File uploaded successfully', data['message'])
        self.assertTrue(data['path'].startswith('uploads/'))
        self.assertEqual(data['file_type'], 'text')
        # Check file actually saved
        self.assertTrue(default_storage.exists(data['path']))

    def test_upload_media_exception(self):
        # Patch default_storage.save to raise an exception
        file_content = b'test file content'
        uploaded_file = SimpleUploadedFile('test2.txt', file_content, content_type='text/plain')
        with patch('django.core.files.storage.default_storage.save', side_effect=Exception('Save failed')):
            response = self.client.post(self.url, {'file': uploaded_file}, format='multipart')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['status'], 'error')
            self.assertIn('Save failed', response.json()['message'])