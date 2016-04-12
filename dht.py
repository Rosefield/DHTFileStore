import hash_utils
import argparse
import asyncio
import json
import logging
import os
import base64
import functools


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

class Node:
    def __init__(self, n):
        self.node_id = n["node_id"]
        self.ip = n["ip"]
        self.port = n["port"]

    def __str__(self):
        return "Node(id {}, ip {}, port {})".format(self.node_id, self.ip, self.port)

class DHT:
    def __init__(self, eventLoop, config_file):
        self.loop = eventLoop
        self.config_file = config_file
        config = self.read_config(config_file)
        self.file_dir = config["file_dir"]
        self.node = Node(config)

        self.nodes = [Node(n) for n in config["nodes"]]
        self.server = None
        self.hash_id = None
        #The ids of the current in-flight requests
        self.request_magics = []
        #self.clients = []
        pass

    def start(self):
        if self.server is None:
            task = asyncio.streams.start_server(self.handle_client, self.node.ip, self.node.port, loop=self.loop)
            self.server = self.loop.run_until_complete(task)

        pass

    def stop(self):
        if self.server is not None:
            self.loop.stop()

    @asyncio.coroutine
    def join():
        '''
        Joins the DHT network
        '''
        pass


    @asyncio.coroutine
    def handle_client(self, reader, writer):

        peer = writer.get_extra_info("socket").getpeername()

        log.info("New Connection from %s", peer)

        #parse request
        request = None
        try:
            request = yield from self.parse_request(reader)
            if request.get("error") is not None:
                log.info("Error parsing request %s", request.get("error"))
                self.send_message(request, writer)
                writer.close()
                return
        except Exception as e:
            log.info("Exception thrown %s", e)
            writer.close()
            return
            
        #make whatever store/find/etc requests
        response = yield from self.handle_request(request)

        #send response
        self.send_message(response, writer)
        log.info("Connection end for %s", peer)

        writer.close()
        

    @asyncio.coroutine
    def parse_request(self, reader):
        request_s = yield from asyncio.wait_for(reader.readline(), 
            timeout=20, loop=self.loop)
        log.info("recieved request %s", request_s)

        if request_s is None:
            return
        request = json.loads(request_s.decode('utf8'))

        if not isinstance(request, dict):
            return {'error': 'Request incorrectly formed'}

        magic = request.get("magic")
        if magic is None or not isinstance(magic, int):
            return {'error': 'Request has no request magic'}

        request_type = request.get("type")
        if request_type is None or not isinstance(request_type, str):
            return {'error': 'Request has no request type'}

        return request

    @asyncio.coroutine
    def handle_request(self, request):
        '''
        Function that will handle any requests that are made 

        the request should have keys for
        magic:
        -Some value to associate the request

        type:
        -store_value request
            This will create a file in the local storage directory with name as the hash
            and the content as the data sent

        -find_value request
            If we hae the hash requested as the file we will return a note saying that (our ip/port) has 
            the requested file, otherwise will make requests to the our known nodes whose ids are closest
            to the requested hash to see if they have the hash. 

        -find_node request
            We will then return the n closest nodes from the response set of the nodes we asked.
            If we are the closest node of the nodes we asked, we will just return ourself
            
            
        -ping_node request
            just sends a response to the requestor saying we are alive

        params:
        -Most requests will have a "hash" param
        -The store_value will also have a "value" param that is the data
        '''

        request_params = request.get("params")
        if request_params is None or not isinstance(request_params, dict):
            return {'error': 'Request has no params (it can be an empty dict)'}

        response = {"magic":request["magic"], "resp":True}
        
        request_type = request.get("type")
        #Mostly for testing
        if(request_type == "ping_nodes"):
            yield from self.ping_nodes()

        if(request_type == "ping_node"):
            response["result"] = {"node_id":self.node_id, "ip":self.ip, "port":self.port}
        
        if(request_type == "store_value"):
            yield from self.store_value(requst_params["id"], request_params["data"])
            response["result"] = "saved"

        if(request_type == "find_node"):
            response["result"] = yield from self.find_node(request_params["id"])

        if(request_type == "find_value"):
            response["result"] = yield from self.find_value(request_params["id"])

        return response

    def nearest_nodes(self, nodes, hash_id, k = 7):
        '''
        Return the top k nodes who's ids are nearest to the provided hash
        '''
        return sorted(nodes, key=lambda x: hash_utils.dist(hash_id, x.id), cmp=hash_utils.compare)[:k]

    def send_message(self, response, writer):
        response_s = json.dumps(response).encode('utf8') + b'\r\n'
        log.info("Sending message %s", response_s)

        writer.write(response_s)
        

    @asyncio.coroutine
    def send_request(self, request, node, callback=None, error_callback=None):
        request['magic'] = int.from_bytes(os.urandom(4), byteorder='little')

        self.request_magics.append(request['magic'])
        host = node.ip
        port = node.port

        request_s = json.dumps(request).encode('utf8')
        log.info("Making request with %s", request_s)

        try:
            reader, writer = yield from asyncio.open_connection(host, port, loop=self.loop)
            log.info('Connected to %s:%s', host, port)
            self.send_message(request, writer)
            if callback is not None:
                yield from callback(reader, writer)
            return reader, writer
        except Exception as e:
            log.info('Error connecting to %s:%s', host, port)
            if error_callback is not None:
                yield from error_callback()
            return None
    
    @asyncio.coroutine
    def ping_nodes(self):
        '''
        Checks to see which of the nodes we have are still alive / in the network
        '''
        
        clients = {}
        log.info("Pinging %d nodes", len(self.nodes))

        for node in self.nodes:
            log.info("Pinging node %s", str(node))
            request = { "magic": os.urandom(4), "type":"ping_node", "params" : {} }
            task = self.send_request(request, node)
            clients[task] = node

        tasks = clients.keys()
        yield from asyncio.wait(tasks, loop=self.loop)

    @asyncio.coroutine
    def store_value(self, hash_id, data):
        '''
        Adds the data to the network with id of hash_id, and the data specified
        '''
        pass

    @asyncio.coroutine
    def find_node(self, hash_id):
        '''
        Makes a request to the n nodes with ids closest to hash_id asking them to find the nodes who's ids
        are closest to hash_id
        '''
        pass

    @asyncio.coroutine
    def find_value(self, hash_id):
        '''
        Makes a request to the n nodes with ids closest to hash_id to find who has the file hash_id
        '''
        pass

    def read_config(self, filename):
        with open(filename) as f:
            return json.loads(f.read())

def main():
    
    arg = argparse.ArgumentParser(description="DHT client/server")
    arg.add_argument("--config-file", dest="config_file", default="config.json", help="Config file location")

    args = arg.parse_args()

    loop = asyncio.get_event_loop()
    loop.set_debug(1)
    dht = DHT(loop, args.config_file)    
    dht.start()

    loop.run_until_complete(dht.ping_nodes())
    
    loop.run_forever()


if __name__ == '__main__':
    log.setLevel(logging.DEBUG)
    main()




