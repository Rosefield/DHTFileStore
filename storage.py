
class Storage:

    def __init__(self, file_dir):
        self.store = {}
        self.file_dir = file_dir
        return

    def has(self, key):
        return key in self.store

    def get(self, key):
        if key in self.store:
            return self.store[key]
        
        return None

    def set(self, key, value):
        self.store[key] = value
        
