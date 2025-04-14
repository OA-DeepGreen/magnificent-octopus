from octopus.core import app
from octopus.lib import plugin

import os, shutil, requests


class StoreException(Exception):
    pass


class StoreFactory(object):

    @classmethod
    def get(cls):
        """
        Returns an implementation of the base Store class
        """
        si = app.config.get("STORE_IMPL")
        sm = plugin.load_class(si)
        return sm()

    @classmethod
    def tmp(cls):
        """
        Returns an implementation of the base Store class which should be able
        to provide local temp storage to the app.  In addition to the methods supplied
        by Store, it must also provide a "path" function to give the path on-disk to
        the file
        """
        si = app.config.get("STORE_TMP_IMPL")
        sm = plugin.load_class(si)
        return sm()


class Store(object):

    def store(self, container_id, target_name, source_path=None, source_stream=None):
        pass

    def exists(self, container_id):
        return False

    def list(self, container_id):
        pass

    def get(self, container_id, target_name):
        return None

    def delete(self, container_id, target_name=None):
        pass


class StoreLocal(Store):
    """
    Primitive local storage system.  Use this for testing in place of remote store
    """
    def __init__(self):
        self.dir = app.config.get("STORE_LOCAL_DIR")
        if self.dir is None:
            raise StoreException("STORE_LOCAL_DIR is not defined in config")

    def store(self, container_id, target_name, source_path=None, source_stream=None):
        cpath = os.path.join(self.dir, container_id)
        if not os.path.exists(cpath):
            os.makedirs(cpath)
        tpath = os.path.join(cpath, target_name)

        if source_path:
            shutil.copyfile(source_path, tpath)
        elif source_stream:
            data = source_stream.read()
            mode = "wb" if isinstance(data, bytes) else "w"
            with open(tpath, mode) as f:
                while data:
                    f.write(data)
                    data = source_stream.read()

    def exists(self, container_id):
        cpath = os.path.join(self.dir, container_id)
        return os.path.exists(cpath) and os.path.isdir(cpath)

    def list(self, container_id):
        cpath = os.path.join(self.dir, container_id)
        return os.listdir(cpath)

    def get(self, container_id, target_name):
        cpath = os.path.join(self.dir, container_id, target_name)
        if os.path.exists(cpath) and os.path.isfile(cpath):
            f = open(cpath, "rb")
            return f

    def delete(self, container_id, target_name=None):
        cpath = os.path.join(self.dir, container_id)
        if target_name is not None:
            cpath = os.path.join(cpath, target_name)
        if os.path.exists(cpath):
            if os.path.isfile(cpath):
                os.remove(cpath)
            else:
                shutil.rmtree(cpath)


class StoreJper(Store):
    def __init__(self):
        self.url = app.config.get("STORE_JPER_URL")
        if self.url is None:
            raise StoreException("STORE_JPER_URL is not defined in config")

    def store(self, container_id, target_name, source_path=None, source_stream=None):
        cpath = os.path.join(self.url, container_id)
        msg_path = f"Store - Container: {container_id} {cpath}"
        r = requests.get(cpath)
        if r.status_code != 200:
            requests.put(cpath)
            msg = f"{msg_path} container to be created {str(r.status_code)}"
            app.logger.debug(msg)
        else:
            msg = f"{msg_path} container already exists {str(r.status_code)}"
            app.logger.debug(msg)

        tpath = os.path.join(cpath, target_name)
        msg_path = f"Store - Container: {container_id} {tpath}"
        if source_path is not None:
            msg = f"{msg_path}. Attempting to save source path"
            app.logger.debug(msg)
            with open(source_path, 'rb') as payload:
                # headers = {'content-type': 'application/x-www-form-urlencoded'}
                # r = requests.post(tpath, data=payload, verify=False, headers=headers)
                r = requests.post(tpath, files={'file': payload})
        elif source_stream is not None:
            msg = f"{msg_path}. Attempting to save source stream to"
            app.logger.debug(msg)
            # headers = {'content-type': 'application/x-www-form-urlencoded'}
            # r = requests.post(tpath, data=source_stream, verify=False, headers=headers)
            r = requests.post(tpath, files={'file': source_stream})
        msg = f"{msg_path}. Request resulted in {r.status_code}"
        app.logger.debug(msg)

    def exists(self, container_id):
        cpath = os.path.join(self.url, container_id)
        r = requests.get(cpath)
        msg_path = f"Store - Container: {container_id}"
        app.logger.debug(f"{msg_path}. Checking existence {r.status_code}")
        if r.status_code == 200:
            try:
                listing = r.json()
                return isinstance(listing, list)
            except:
                return False
        else:
            return False

    def list(self, container_id):
        cpath = os.path.join(self.url, container_id)
        r = requests.get(cpath)
        msg_path = f"Store - Container: {container_id}"
        app.logger.debug(f"{msg_path}. Listing requested and returned")
        try:
            return r.json()
        except:
            return []

    def get(self, container_id, target_name):
        cpath = os.path.join(self.url, container_id, target_name)
        r = requests.get(cpath, stream=True)
        msg_path = f"Store - Container: {container_id} {cpath}"
        if r.status_code == 200:
            app.logger.debug(f"{msg_path}. Retrieved and returning raw")
            return r.raw
        else:
            app.logger.debug(f"{msg_path}. Could not be retrieved - {r.status_code}")
            return False

    def delete(self, container_id, target_name=None):
        cpath = os.path.join(self.url, container_id)
        if target_name is not None:
            cpath = os.path.join(cpath, target_name)
        msg_path = f"Store - Container: {container_id} {cpath}"
        r = requests.delete(cpath)
        if 200 <= r.status_code < 300:
            app.logger.debug(f"{msg_path}. Deleted {r.status_code}")
        else:
            app.logger.debug(f"{msg_path}. Could not delete - {r.status_code}")

    def list_backups(self, container_id, target_name):
        cpath = os.path.join(self.url, 'backup', container_id)
        if target_name is not None:
            cpath = os.path.join(cpath, target_name)
        msg_path = f"Store - Container: {container_id} {cpath}"
        app.logger.debug(f"{msg_path}. Get backup list")
        r = requests.get(cpath)
        try:
            return r.json()
        except:
            return []

    def backup(self, container_id, target_name):
        cpath = os.path.join(self.url, 'backup', container_id)
        if target_name is not None:
            cpath = os.path.join(cpath, target_name)
        msg_path = f"Store - Container: {container_id} {cpath}"
        r = requests.post(cpath)
        if 200 <= r.status_code < 300:
            app.logger.debug(f"{msg_path}. File backup done {r.status_code}")
        else:
            app.logger.debug(f"{msg_path}. File backup error {r.status_code}")
        try:
            return r.json()
        except:
            return ''

    def delete_backups(self, container_id, target_name):
        cpath = os.path.join(self.url, 'backup', container_id)
        if target_name is not None:
            cpath = os.path.join(cpath, target_name)
        msg_path = f"Store - Container: {container_id} {cpath}"
        r = requests.delete(cpath)
        if 200 <= r.status_code < 300:
            app.logger.debug(f"{msg_path}. Deleted backup {r.status_code}")
        else:
            app.logger.debug(f"{msg_path}. Could not delete backup - {r.status_code}")


class TempStore(StoreLocal):
    def __init__(self):
        self.dir = app.config.get("STORE_TMP_DIR")
        if self.dir is None:
            raise StoreException("STORE_TMP_DIR is not defined in config")

    def path(self, container_id, filename, must_exist=True):
        fpath = os.path.join(self.dir, container_id, filename)
        if not os.path.exists(fpath) and must_exist:
            msg = f"Unable to create path for container {container_id}, file {filename}"
            raise StoreException(msg)
        return fpath

    def list_container_ids(self):
        return [x for x in os.listdir(self.dir) if os.path.isdir(os.path.join(self.dir, x))]
