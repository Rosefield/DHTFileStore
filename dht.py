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
    class Networking:
        def __init__(self, dht_protocol):
            self.dht = dht_protocol

        def connection_made(self, transport):
            log.info("Connection made")
            self.transport = transport

        def datagram_received(self, data, addr):
            log.info("Received %s from %s", data, addr)

            message = None
            try:
                message = self.parse_message(data)
                if message.get("error") is not None:
                    log.info("Error parsing message %s", message.get("error"))
                    self.transport.close()
                    return
            except Exception as e:
                log.warning("Exception %s thrown parsing message %s", e, data)
                self.transport.close()
                return
                
            is_resp = message.get("resp")
            if is_resp is not None and is_resp == True:
                self.dht.handle_response(message)   
            else:
                #make whatever store/find/etc requests
                #Can't use yield from directly since this function is never itself scheduled
                task = asyncio.async(self.dht.handle_request(message))

                #schedule response
                task.add_done_callback(lambda task: self.send_message(task.result(), addr))
            log.info("Connection end for %s", addr)

#            self.transport.close()

        def parse_message(self, data):
            if data is None:
                return {"error": "empty message"}
            message = json.loads(data.decode('utf8'))

            if not isinstance(message, dict):
                return {"error": "message incorrectly formed"}

            return message

        def send_message(self, message, addr):
            message_s = json.dumps(message).encode('utf8')
            log.info("Sending message %s to %s", message_s, addr)

            self.transport.sendto(message_s, addr)
            

        def error_received(self, exc):
            print('Error received:', exc)

        def connection_lost(self, exc):
            log.info("connection closed %s", exc)

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
        self.request_magics = {}

        self.networking = self.Networking(self)

        pass

    def start(self):
        if self.server is None:
            task = asyncio.Task(self.loop.create_datagram_endpoint(lambda: self.networking, 
                        local_addr=(self.node.ip, self.node.port)))
            self.server, _ = self.loop.run_until_complete(task)

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
        magic = request.get("magic")
        if magic is None or not isinstance(magic, int):
            return {"error": 'Request has no request magic'}

        request_type = request.get("type")
        if request_type is None or not isinstance(request_type, str):
            return {"error": 'Request has no request type'}

        request_params = request.get("params")
        if request_params is None or not isinstance(request_params, dict):
            return {"error": 'Request has no params (it can be an empty dict)'}

        response = {"magic":request["magic"], "type":request["type"], "resp":True}
        
        #Mostly for testing
        if(request_type == "ping_nodes"):
            yield from self.ping_nodes()

        if(request_type == "ping_node"):
            response["result"] = self.node.__dict__
        
        if(request_type == "store_value"):
            yield from self.store_value(requst_params["id"], request_params["data"])
            response["result"] = "saved"

        if(request_type == "find_node"):
            response["result"] = yield from self.find_node(request_params["id"])

        if(request_type == "find_value"):
            response["result"] = yield from self.find_value(request_params["id"])

        return response

    def handle_response(self, response):
        log.info("Handling response %s", response)
        magic = response.get("magic")
        if magic is None or not isinstance(magic, int):
            log.info("Response has no magic")
            return

        request_type = response.get("type")
        if request_type is None or not isinstance(request_type, str):
            log.info("Response has no request type")
            return

        request_node = self.request_magics.get(magic)
        if request_node is None:
            log.info("Response was unexpected. Duplicate response?")
            return

        #Marking the request/response transaction as complete
        del self.request_magics[magic]


        result = response.get("result")

        if(request_type == "ping_node"):
            node = Node(result)
            log.info("Ping response from %s", node)
            #update_node(request_node, node)
            
                
        
        if(request_type == "store_value"):
            pass

        if(request_type == "find_node"):
            pass

        if(request_type == "find_value"):
            pass
        



    def nearest_nodes(self, nodes, hash_id, k = 7):
        '''
        Return the top k nodes who's ids are nearest to the provided hash
        '''
        return sorted(nodes, key=lambda x: hash_utils.dist(hash_id, x.id), cmp=hash_utils.compare)[:k]

    def make_request(self, request, node):
        request['magic'] = int.from_bytes(os.urandom(4), byteorder='little')

        self.request_magics[request['magic']] = node
        host = node.ip
        port = node.port

        request_s = json.dumps(request).encode('utf8')
        log.info("Making request with %s to (%s:%s)", request_s, host, port)

        try:
            self.networking.send_message(request, (host, port))
        except Exception as e:
            log.info("Error %s connecting to %s:%s", e, host, port)
    
    @asyncio.coroutine
    def ping_nodes(self):
        '''
        Sends a request to each of our nodes to see if they are still alive
        '''
        log.info("Pinging %d nodes", len(self.nodes))

        for node in self.nodes:
            log.info("Pinging node %s", str(node))
            request = { "type":"ping_node", "params" : {} }
            task = self.make_request(request, node)

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




