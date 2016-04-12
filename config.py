import json

class Config(object):
    __instance = None

    def __init__(self, config_path):
        if not self.__instance:
            self.__instance = Config.__Config(config_path)

    def __getattr__(self, name):
        return getattr(self.__instance, name)

    def __setattr__(self, name, value):
        if not self.__instance:
            super(Config, self).__setattr__(name, value)
        else:
            raise AttributeError

    class __Config(object):
        def __init__(self, config_path):
            with open(config_path, "r") as config_file:
                self.__dict__.update(json.loads(config_file.read()))

if __name__ == "__main__":
    config = Config("config.json")
    print(config.file_dir)
    config2 = Config("config.json")
    try:
        config2.port = 88888
    except AttributeError:
        pass
    print(config.port)
    print(config2.port)