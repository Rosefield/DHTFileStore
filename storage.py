
class Storage:

    def __init__(self, file_dir):
        self.store = {}
        
        self.store["2ea970ff63aec5d7a014ca6447ec743d3ba37450b85ebdcbb582b089b0194fa2"] = b"\xdf"

        self.file_dir = file_dir
        return

    
    def keys(self):
        return self.store.keys()

    def has(self, key):
        return key in self.store

    def get(self, key):
        if key in self.store:
            return self.store[key]
        
        return None

    def set(self, key, value):
        print("Storing key {}".format(key))
        self.store[key] = value
        
