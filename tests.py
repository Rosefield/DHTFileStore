from argparse import ArgumentParser
from multiprocessing import Pool
import logging
import sys
import shlex
import asyncio
from client import DistributedClient
from concurrent.futures import ThreadPoolExecutor

from dht import startup as start_dht

# discards everything written to it
class Discarder(object):
    def flush(self):
        pass

    def write(self, text):
        pass
sys.stdout = Discarder()

class REPL(object):
    PROMPT = ">>> "

    def __init__(self, config_file):
        # silence logging
        logging.basicConfig(level=logging.CRITICAL)
        logging.getLogger("networking").disabled = True
        logging.getLogger("dht").disabled = True
        logging.getLogger("routing").disabled = True

        # still show simple updates from the client
        client_log = logging.getLogger("client")
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        client_log.addHandler(handler)
        client_log.propagate = False
        client_log.setLevel(logging.INFO)

        # start up the magic
        self.loop, dht = start_dht(config_file)
        self.client = DistributedClient(dht)

        # keep the CLI running
        asyncio.ensure_future(self.cli())

        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=sys.__stdout__)

    def show_usage(self):
        self.print("Usage:")
        self.print()
        self.print("Store a file on the network")
        self.print("\tstore <file_loc> <hashfile_loc>:")
        self.print()
        self.print("Retrieve a file from the network")
        self.print("\tretrieve <hashfile_loc> <dest_loc>:")
        self.print()
        self.print("(paths containing spaces should be wrapped in quotes)")
        self.print()

    # @asyncio.coroutine
    def cli(self):
        self.print("Distributed File Storage CLI")
        self.print("Written by Schuyler Rosefield and Ryan Cebulko")
        self.print()
        self.show_usage()

        while True:
            self.print(">>> ", end="", flush=True)
            self.handle_input(input())

    def handle_input(self, input):
        args = shlex.split(input)

        if args:
            op, = args[0].lower();

            if op in ("s", "store") and len(args) == 3:
                self.client.store_file(*args[1:])
                self.print()
            elif op in ("r", "retrieve") and len(args) == 3:
                self.client.retrieve_file(*args[1:])
                self.print()
            elif op in ("q", "quit"):
                self.loop.stop()
                quit()
            else:
                self.show_usage()
        else:
            self.show_usage()


if __name__ == "__main__":
    arg = ArgumentParser(description="Distributed File Storage REPL")

    arg.add_argument(
        "-c", "--config",
        dest="config_file",
        default="config.json",
        help="Config file location",
        metavar="config_path")

    args = arg.parse_args()

    REPL(args.config_file)