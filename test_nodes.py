import asyncio
import argparse
from dht import DHT
import hash_utils
import json
import os
from routing import Node
import random
import socket

def get_ip():
    return socket.gethostbyname(socket.gethostname())

TEST_DIR = "test_files"
IP = get_ip()
BASE_PORT = 55000

def create_nodes(num=1000):
    nodes = []
    for i in range(num):
        d = dict()
        d["ip"] = IP
        d["port"] = BASE_PORT + i
        d["node_id"] = hash_utils.hash_data(i.to_bytes(2, byteorder="little"))
        nodes.append(Node(d))

    return nodes
    
def create_config(i, nodes):

    node = nodes[i]
    
    config = node.__dict__.copy()
    config["file_dir"] = os.path.join(TEST_DIR, "store" + str(i))
    node_sample = random.sample(nodes, 7)
    #make sure we aren't in our own list
    node_sample = filter(lambda x: x.node_id != node.node_id, node_sample)    

    config["nodes"] = [n.__dict__ for n in node_sample]


    filename = os.path.join(TEST_DIR, "config{}.json".format(i))
    with open(filename, 'w') as f:
        f.write(json.dumps(config))
    return filename


@asyncio.coroutine
def run_nodes(files):
    loop = asyncio.get_event_loop()

    futs = []
    for filename in files:
        dht = DHT(loop, filename)
        futs.append(dht.start_async())
        
    #let all of the dhts start
    yield from asyncio.wait(futs)



def main():

    arg = argparse.ArgumentParser()

    arg.add_argument(
        "-n", "--num-nodes",
        dest="num_nodes",
        default=100, type=int,
        help="Number of nodes to run",
        metavar="num_nodes")
    args = arg.parse_args()

    num_nodes = args.num_nodes

    os.makedirs(TEST_DIR, exist_ok=True)

    nodes = create_nodes(num_nodes)
    files = []
    for i in range(num_nodes):
        filename = create_config(i, nodes)
        files.append(filename)

    
    loop = asyncio.get_event_loop()
    
    loop.run_until_complete(run_nodes(files))

    try:
        loop.run_forever()
    except:
        loop.close()
    
    








if __name__ == "__main__":
    main()


