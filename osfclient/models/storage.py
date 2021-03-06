import os

from .core import OSFCore
from .file import ContainerMixin
from .file import File
from ..utils import norm_remote_path


class Storage(OSFCore, ContainerMixin):
    _files_key = ('relationships', 'files', 'links', 'related', 'href')

    def _update_attributes(self, storage):
        if not storage:
            return

        self.id = self._get_attribute(storage, 'id')

        self.path = self._get_attribute(storage, 'attributes', 'path')
        self.name = self._get_attribute(storage, 'attributes', 'name')
        self.node = self._get_attribute(storage, 'attributes', 'node')
        self.provider = self._get_attribute(storage, 'attributes', 'provider')

        self._files_url = self._get_attribute(storage, *self._files_key)

        self._new_folder_url = self._get_attribute(storage,
                                                   'links', 'new_folder')
        self._new_file_url = self._get_attribute(storage, 'links', 'upload')

    def __str__(self):
        return '<Storage [{0}]>'.format(self.id)

    XXX = """
    def remove(self, path):
        # Remove `path` from this storage
        path = os.path.normpath(path)
        directory, fname = os.path.split(path)

        stack = []
        children = self._follow_next(self._files_url)
        while children:
            child = children.pop()
            kind = self._get_attribute(child, 'attributes', 'kind')
            if kind == 'file':
                child = File(child, self.session)
            elif kind == 'folder':
                child = Folder(child, self.session)
                # only check folders that match the path
                if path.startswith(child.path):
                    url = self._get_attribute(file, *self._files_key)
                    children.extend(self._follow_next(url))

            # if it forms part of the path to our target, queue it up for
            # deletion
            print(child.path, child)
            if path.startswith(child.path):
                stack.append(child)

        print(stack)
        """

    @property
    def files(self):
        """Iterate over all files in this storage.

        Recursively lists all files in all subfolders.
        """
        return self._iter_children(self._files_url, 'file', File,
                                   self._files_key)

    def create_file(self, path, fp):
        """Store a new file at `path` in this storage.

        The contents of the file descriptor `fp` (opened in 'rb' mode)
        will be uploaded to `path` which is the full path at
        which to store the file.
        """
        # all paths are assumed to be absolute
        path = norm_remote_path(path)

        directory, fname = os.path.split(path)
        directories = directory.split('/')
        # navigate to the right parent object for our file
        parent = self
        for directory in directories:
            # skip empty directory names
            if directory:
                parent = parent.create_folder(directory, exist_ok=True)

        url = parent._new_file_url
        # peek at the file to check if it is an ampty file which needs special
        # handling in requests. If we pass a file like object to data that
        # turns out to be of length zero then no file is created on the OSF
        if fp.peek(1):
            response = self._put(url, params={'name': fname}, data=fp)
        else:
            response = self._put(url, params={'name': fname}, data=b'')

        if response.status_code == 409:
            raise FileExistsError(path)
