import os
from logging import getLogger

log = getLogger(__name__)

class Storage:
    def __init__(self, file_dir):
        self.file_dir = file_dir
        
        #Ensure that the save directory exists
        os.makedirs(self.file_dir, exist_ok=True)

        self.set(
            "2ea970ff63aec5d7a014ca6447ec743d3ba37450b85ebdcbb582b089b0194fa2",
            b"\xdf")

    def path_for_key(self, key):
        return os.path.join(self.file_dir, key)

    def keys(self):
        return os.listdir(self.file_dir)

    def has(self, key):
        return os.path.exists(self.path_for_key(key))

    def get(self, key):
        try:
            with open(self.path_for_key(key), "rb") as file:
                return file.read()
        except:
            return None

    def set(self, key, value):
        try:
            with open(self.path_for_key(key), "wb") as file:
                file.write(value)
                return True
        except:
            return False

    def clear(self, key):
        os.unlink(self.path_for_key(key))

if __name__ == "__main__":
    storage = Storage("dht_store/")
    print(storage.has("fake_keys"))
    print(storage.get("byte_keys"))
    print(storage.set("testing", "value"))
    storage.clear("2ea970ff63aec5d7a014ca6447ec743d3ba37450b85ebdcbb582b089b0194fa2")
    print(storage.keys())
    storage.clear("testing")
