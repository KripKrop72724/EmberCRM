from django.core.files.storage import FileSystemStorage
from django.urls import reverse


class SecureFileSystemStorage(FileSystemStorage):
    def url(self, name):
        return reverse('AP01:secure_file_view', args=[name])
