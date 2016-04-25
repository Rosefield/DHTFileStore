import json

class Config(object):
    class __Config(object):
        __CONFIG_PATH = "config.json"

        def __init__(self):
            with open(self.__CONFIG_PATH, "r") as config_file:
                self.__dict__.update(json.loads(config_file.read()))

    __instance = None

    def __init__(self):
        if not self.__instance:
            self.__instance = Config.__Config()

    def __getattr__(self, name):
        return getattr(self.__instance, name)

    def __setattr__(self, name, value):
        if not self.__instance:
            super(Config, self).__setattr__(name, value)
        else:
            raise AttributeError


if __name__ == "__main__":
    config = Config()
    print(config.file_dir)
    config2 = Config()
    try:
        config2.port = 88888
    except AttributeError:
        pass
    print(config.port)
    print(config2.port)