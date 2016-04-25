from argparse import ArgumentParser
from multiprocessing import Pool
import logging
import sys
import shlex
import asyncio
from concurrent.futures import ThreadPoolExecutor

from client import DistributedClient
from dht import startup as start_dht
from hash_utils import hash_data

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
        client_log.setLevel(logging.DEBUG)

        # start up the magic
        self.loop, dht = start_dht(config_file)
        self.client = DistributedClient(dht, self.loop)

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
        self.print("\ts[tore] <file_loc> <hashfile_loc>")
        self.print()
        self.print("Retrieve a file from the network")
        self.print("\tr[etrieve] <hashfile_loc> <dest_loc>")
        self.print()
        self.print()
        self.print("Test storing and retrieving files from the network")
        self.print("\tt[est] <hashfile_loc>...")
        self.print()
        self.print()
        self.print("Clear files from local storage")
        self.print("\tc[lear] <hashfile_loc>...")
        self.print()
        self.print()
        self.print("List the hashes stored locally")
        self.print("\tl[ist]")
        self.print()
        self.print()
        self.print("Exit the CLI")
        self.print("\tq[uit]")
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
            op, args = (args[0].lower(), args[1:])

            if op in ("s", "store") and len(args) == 2:
                # store a file
                self.client.store_file(*args)
                self.print()
            elif op in ("r", "retrieve") and len(args) == 2:
                # retrieve a file
                self.client.retrieve_file(*args)
                self.print()
            elif op in ("t", "test") and len(args):
                # test storing and retrieving a file
                for file in args:
                    self.test_store_retrieve(file)
                self.print()
            elif op in ("c", "clear") and len(args):
                # clear a file from local storage
                for path in args:
                    self.print(path)
                    for hash, size in self.client.hashes_from_file(path):
                        self.client.dht.storage.clear(hash)
            elif op in ("l", "list"):
                # list hashes of locally-stored chunks
                for hash in self.client.dht.storage.keys():
                    self.print(hash)
                self.print()
            elif op in ("q", "quit"):
                # exit the REPL
                self.loop.stop()
                quit()
            else:
                self.show_usage()
        else:
            self.show_usage()

    def test_store_retrieve(self, file_path):
        self.handle_input("s %s dht_store/tmp_keys" % file_path)
        self.handle_input("r dht_store/tmp_keys dht_store/tmp_data")

        with open(file_path, "rb") as file:
            hash_before = hash_data(file.read())

        with open("dht_store/tmp_data", "rb") as file:
            hash_after = hash_data(file.read())

        self.print(
            "Before: %s\nAfter: %s" % (hash_before, hash_after))


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
