from os import path
from argparse import ArgumentParser
import logging
import sys
import asyncio

from dht import startup as start_dht
from hash_utils import hash_data

FAKE_HASHES = [
    ("1EB79602411EF02CF6FE117897015FFF89F80FACE4ECCD50425C45149B148408", 992358),
    ("FA51FD49ABF67705D6A35D18218C115FF5633AEC1F9EBFDC9D5D4956416F57F6", 903964),
    ("CA978112CA1BBDCAFAC231B39A23DC4DA786EFF8147C4E72B9807785AFEE48BB", 764787),
    ("6EE0EB490FF832101CF82A3D387C35F29E4230BE786978F7ACF9E811FEBF6723", 639385),
    ("28391D3BC64EC15CBB090426B04AA6B7649C3CC85F11230BB0105E02D15E3624", 578046),
    ("9F86D081884C7D659A2FEAA0C55AD015A3BF4F1B2B0B822CD15D6C15B0F00A08", 600106),
    ("3A4278F83ECEA3815F068FF7E014DD671BC7D790661F139315B2952888356A72", 907218),
]
DEFAULT_PATH = path.relpath("./dht_store/")
MAX_CHUNK_SIZE = 1 << 20

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

byte_suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
def humansize(nbytes):
    '''
    Given some number of bytes, produces a human-readable abbreviation

    Args:
        nbytes (int): number of bytes
    Return:
        (str) number of (kilo/mega/giga/tera)-bytes to two decimals

    >>> humansize(131)
    '131 B'
    >>> humansize(1049)
    '1.02 KB'
    >>> humansize(58812)
    '57.43 KB'
    >>> humansize(68819826)
    '65.63 MB'
    >>> humansize(39756861649)
    '37.03 GB'
    >>> humansize(18754875155724)
    '17.06 TB'
    '''
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(byte_suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, byte_suffixes[i])


class DistributedClient:
    def __init__(self, dht, loop):
        self.dht = dht
        self.loop = loop

    def __retrieve_from_hashes(self, hashes):
        '''
        Given a list of tuples containing hashes and chunk sizes, retrieves the
        data chunks and creates a local copy of the file
        '''
        for (hash, size) in hashes:
            log.debug("Retrieving chunk %s", hash)
            val = self.loop.run_until_complete(self.dht.get_value(hash))
            yield val

        yield None

    def hashes_from_file(self, hashfile_path):
        # read hashes from file
        # TODO: verify integrity of hash file (error check this)
        with open(hashfile_path, "r") as hashfile:
            return [(hash, int(size)) for (hash, size) in # cast size to int
                [pair.split("$") for pair in # split each pair string by $
                hashfile.read().split("|") # split up the file by pipes
                if pair]] # ignore empty string residues from end of file

            # alternate representation of above inline list generation
            # contents = hashfile.read()
            # pair_strings = filter(None, contents.split("|"))
            # pairs = map(lambda pair_str: pair_str.split("$"), pair_strings)
            # hashes = map(lambda pair: (pair[0], int(pair[1])), pairs)
            # return hashes

    def __retrieve_from_file(self, hashfile_path):
        '''
        Given a path to a file containing hashes and chunk sizes, retrieves the
        data chunks and creates a local copy of the file
        '''
        return self.__retrieve_from_hashes(self.hashes_from_file(hashfile_path))

    def retrieve_file(self, hash_data, file_path):
        '''
        Retrieves the data chunks of a remote file and creates a local copy

        Args:
            hash_data (str | [(str, int)...]): either a string containing a path
                to a hash file, or a list of hash-size tuples
            file_path (str): the local file path to create the local copy
        Return:
            (str) file path of retrieved file
        '''
        # determine retrieval function to use
        if isinstance(hash_data, str):
            retrieve_fn = self.__retrieve_from_file
        else:
            retrieve_fn = self.__retrieve_from_hashes

        # write to the file as chunks become available
        with open(file_path, "wb") as local_file:
            for chunk in retrieve_fn(hash_data):
                if chunk is not None:
                    # write to local file
                    local_file.write(chunk)

        if isinstance(hash_data, str):
            log.info(
                "Retrieved file from hashes in '%s' to '%s'" % \
                (hash_data, file_path))

        return file_path

    def __write_hashfile(self, hashfile_path, hashes):
        '''
        Writes hashes to a hash file in the expected format `hash$size`

        Args:
            hashfile_path: the local file to write the hashes to
            hashes: list of hash-size tuples to write
        '''
        with open(hashfile_path, "w") as hashfile:
            for chunk in hashes:
                hashfile.write("%s$%d|" % chunk)

        log.debug("Wrote hashes to '%s'" % hashfile_path)

    @asyncio.coroutine
    def __store_file(self, file_path): # TODO
        '''
        Stores file data on the network and returns a set of hashes stored

        Args:
            file_path (str): the local file to be stored
        Returns:
            [(str, int), ...] a list of hash-size tuples
        '''
        unread = path.getsize(file_path)
        hashes = []

        with open(file_path, "rb") as file:
            while unread > 0:
                chunk = file.read(MAX_CHUNK_SIZE)
                hash = hash_data(chunk)

                yield from self.dht.store_value(hash, chunk)
                hashes.append((hash, min(MAX_CHUNK_SIZE, unread)))

                unread -= MAX_CHUNK_SIZE

        print(hashes)
        return hashes

    def store_file(self, file_path, hashfile_path=None):
        '''
        Distributes all data to the network and creates a local file that
        contains the metadata required to retreive the data back on request

        Args:
            file_path (str): the local file to be stored
            hashfile_path (str | None): the local file to write the hashes to
        Returns:
            (str) file path of created hash file
        '''
        # get file hashes
        hashes = self.loop.run_until_complete(self.__store_file(file_path))

        # determine hash file path
        # TODO: better file name choice
        if hashfile_path is None:
            hashfile_path = path.join(DEFAULT_PATH, hashes[0][0])
        hashfile_path = path.abspath(hashfile_path)

        # write out hashes
        self.__write_hashfile(hashfile_path, hashes)

        log.info(
            "Stored file '%s' and wrote hashes to '%s'" % \
            (file_path, hashfile_path))

        return hashfile_path;

def main(store, retrieve, config_file):
    loop, dht = start_dht(config_file)
    client = DistributedClient(dht, loop)

    if store:
        client.store_file(*store)
    else:
        client.retrieve_file(*retrieve)

    loop.run_forever()

if __name__ == "__main__":
    arg = ArgumentParser(description="Client CLI")
    group = arg.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-s", "--store",
        nargs=2,
        help="Stores a file in the network",
        metavar=("source_loc", "hashfile_loc"))
    group.add_argument(
        "-r", "--retrieve",
        nargs=2,
        help="Retrieves a file; first argument specifies hash file; second " +
            "argument specifies destination of retrieved file",
        metavar=("source_loc", "dest_loc"))
    arg.add_argument(
        "-c", "--config",
        dest="config_file",
        default="config.json",
        help="Config file location",
        metavar="config_path")

    args = arg.parse_args()

    main(args.store, args.retrieve, args.config_file)
