import hash_utils
import argparse
import asyncio
import json
import logging
import os
import base64
from networking import Networking
from routing import Node, Routing
from storage import Storage

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

HEALTH_CHECK_INTERVAL = 10

class DHT:
    def __init__(self, eventLoop, config_file, log):
        self.loop = eventLoop
        self.config_file = config_file
        config = self.read_config(config_file)

        self.server = None
        #The ids of the current in-flight requests
        #maps id to {future, node}
        self.request_magics = {}

        self.max_timeout = 15.

        self.node = Node(config)
        self.routing = Routing(self.node, [Node(n) for n in config["nodes"]])
        self.storage = Storage(config["file_dir"])
        self.networking = Networking(self, self.storage)

    def start(self):
        if self.server is None:
            #DHT Protocol server
            task = asyncio.Task(self.loop.create_datagram_endpoint(
                lambda: self.networking,
                local_addr=(self.node.ip, self.node.port)))


            self.server, _ = self.loop.run_until_complete(task)

            #File Transfer protocol server
            task = asyncio.streams.start_server(self.networking.handle_client, self.node.ip, self.node.port, loop=self.loop)
            self.loop.run_until_complete(task)
            self.loop.run_until_complete(self.join())
            asyncio.ensure_future(self.health_check())

        return

    def stop(self):
        if self.server is not None:
            #self.save_state()
            self.loop.stop()

    @asyncio.coroutine
    def health_check(self):
        while True:
            log.info("Health check")
            log.info("Node %s: %d chunks" % (self.node.node_id, len(self.storage.store)))
            yield from self.ping_nodes()

            #Check every 10 minutes
            yield from asyncio.sleep(HEALTH_CHECK_INTERVAL)

    @asyncio.coroutine
    def join(self):
        '''
        Joins the DHT network
        '''
        if(len(self.routing.nodes) == 0):
            log.error("No nodes to bootstrap from")
            return

        nodes = yield from self.find_node(self.node.node_id)

        log.debug("Found nodes %s", nodes)

        if len(nodes) == 0:
            log.error("No nodes to bootstrap from")
            return

        self.routing.add_nodes(nodes)

        return

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
            If we have the hash requested as the file we will return a note saying that (our ip/port) has
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
        log.info("Handling request %s", request)
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

        request_hash = request_params.get("id")
        if(request_type == "store_value"):
            self.store_value(request_hash, request_params.get("value"))
            # yield from self.get_value(request_hash, node=Node(request_params["node"]))
            response["result"] = "saved"

        if(request_type == "find_node"):
            nodes = self.routing.nearest_nodes(request_hash)
            response["result"] = [n.__dict__ for n in nodes]

        if(request_type == "find_value"):
            if(self.storage.has(request_hash)):
                response["result"] = self.routing.node
            else:
                nodes = self.routing.nearest_nodes(request_hash)
                response["result"] = [n.__dict__ for n in nodes]

        return response

    def handle_response(self, response):
        log.info("Handling response %s", response)
        magic = response.get("magic")
        if magic is None or not isinstance(magic, int):
            log.debug("Response has no magic")
            return

        request_type = response.get("type")
        if request_type is None or not isinstance(request_type, str):
            log.debug("Response has no request type")
            return

        fut_node = self.request_magics.get(magic)
        if fut_node is None:
            log.info("Response with magic %s was unexpected. Duplicate response?", magic)
            return

        #Marking the request/response transaction as complete
        del self.request_magics[magic]

        result = response.get("result")

        node = fut_node["node"]
        fut = fut_node["fut"]
        #Future was cancelled / already handled but we didn't remove from our in-flight requests
        if(fut.done()):
            return

        if(request_type == "ping_node"):
            fut.set_result(Node(result))
            return

        #Just confirmation that the result was stored
        if(request_type == "store_value"):
            fut.set_result(result)
            return

        if(request_type == "find_node"):
            nodes = [Node(n) for n in result]
            fut.set_result(nodes)

            return

        if(request_type == "find_value"):
            #If a node is returned, instead of a list of nodes, they have the value
            if(isinstance(result, dict)):
                fut.set_result(Node(result))
            else:
                nodes = [Node(n) for n in result]
                fut.set_result(nodes)

            return


    def make_request(self, request, node):
        request['magic'] = int.from_bytes(os.urandom(4), byteorder='little')

        future = asyncio.Future()
        self.request_magics[request['magic']] = { "node": node, "fut": future }
        host = node.ip
        port = node.port

        request_s = json.dumps(request).encode('utf8')
        log.debug("Making request with %s to (%s:%s)", request_s, host, port)

        try:
            self.networking.send_message(request, (host, port))
        except Exception as e:
            log.info("Error %s connecting to %s:%s", e, host, port)
            future.set_exception(e)

        return future



    @asyncio.coroutine
    def ping_nodes(self):
        '''
        Sends a request to each of our nodes to see if they are still alive
        '''
        log.debug("Pinging %d nodes", len(self.routing.nodes))

        futs = []
        nodes = {}

        for node in self.routing:
            log.debug("Pinging node %s", str(node))
            request = { "type":"ping_node", "params" : {} }
            fut = self.make_request(request, node)
            futs.append(fut)
            nodes[fut] = node

        complete, pending = yield from asyncio.wait(futs, timeout=self.max_timeout)

        for f in complete:
            node = nodes[f]
            if f.exception() is not None:
                self.routing.remove_node(node)
            else:
                self.routing.add_or_update_node(node)

        for f in pending:
            node = nodes[f]
            f.cancel()
            self.routing.remove_node(node)

        return


    @asyncio.coroutine
    def store_value(self, hash_id, data):
        '''
        Adds the data to the network with id of hash_id, and the data specified
        '''

        # Add to our own storage so it is available on the network from us
        self.storage.set(hash_id, data)

        nodes = yield from self.find_node(hash_id)

        futs = []
        for node in nodes:
            request = {
                "request_type": "store_value",
                "params": {
                    "id": hash_id,
                    "node": self.routing.node.__dict__,
                    "value": data
                }
            }
            fut = self.make_request(request, node)
            futs.append(fut)

        complete, pending = yield from asyncio.wait(futs)

        return

    @asyncio.coroutine
    def find_node(self, hash_id):
        '''
        Makes a request to the n nodes with ids closest to hash_id asking them to find the nodes who's ids
        are closest to hash_id
        '''

        to_search = self.routing.nearest_nodes(hash_id)
        searched = set()

        while len(to_search) > 0:

            futs = []
            log.debug("next search set %s", to_search)
            for node in to_search:
                request = { "type":"find_node", "params":{ "id":hash_id } }
                fut = self.make_request(request, node)
                futs.append(fut)

            complete, pending = yield from asyncio.wait(futs, timeout=self.max_timeout)

            searched.update(to_search)

            nodes = set(searched)
            for fut in filter(lambda f: f.exception() is None, complete):
                res = fut.result()
                res = filter(lambda x: x.node_id != self.routing.node.node_id, res)
                nodes.update(res)

            log.debug("new nodes %s", nodes)

            to_search = set(self.routing.nearest_nodes(hash_id, nodes=nodes)) - searched

            #Update our own routing table in case any of the found nodes are useful to us
            self.routing.add_nodes(to_search)

        return self.routing.nearest_nodes(hash_id, nodes=searched)

    @asyncio.coroutine
    def find_value(self, hash_id):
        '''
        Makes a request to the n nodes with ids closest to hash_id to find who has the file hash_id
        '''
        if(self.storage.has(hash_id)):
            return self.routing.node

        to_search = self.routing.nearest_nodes(hash_id)
        searched = set()

        nodes_with_value = set()
        while len(nodes_with_value) == 0 and len(to_search) > 0:
            futs = []
            log.info("next search set %s", to_search)
            for node in to_search:
                request = { "type":"find_value", "params":{ "id":hash_id } }
                fut = self.make_request(request, node)
                futs.append(fut)

            complete, pending = yield from asyncio.wait(futs, timeout=self.max_timeout)

            searched.update(to_search)
            new_nodes = searched.copy()
            for fut in filter(lambda f: f.exception() is None, complete):
                res = fut.result()

                #Either get back one node that has the value, or a list of nodes to check next
                if isinstance(res, Node):
                    nodes_with_value.add(res)
                else:
                    res = filter(lambda x: x.node_id != self.routing.node.node_id, res)
                    new_nodes.update(res)


            log.info("new nodes %s", new_nodes)
            #Don't want to contact ourselves if that was returned
            new_nodes.discard(self.routing.node)

            #Get the next set of top nodes, excluding nodes we've already searched
            to_search = set(self.routing.nearest_nodes(hash_id, nodes=new_nodes)) - searched
            log.info("next search set %s", to_search)

        return list(nodes_with_value)

    @asyncio.coroutine
    def get_value(self, hash_id, node = None):
        '''
        Retrieves the value associated with hash_id from the network.
        Optionally pass in a node to request the data from the requested node
        '''
        data = None

        if(self.storage.hash(hash_id)):
            return self.storage.get(hash_id)

        while True:
            if node is None:
                nodes = yield from self.find_values(hash_id)

                if len(nodes) == 0:
                    raise Exception("No nodes have the requested value ({})".format(hash_id))

                #just get from the first node

                for node in nodes:
                    data = yield from self.networking.request_key(hash_id, node)
                    if data:
                        break
            else:
                data = yield from self.networking.request_key(hash_id, node)

            if hash_data(data) == hash_id:
                break

        if data is not None:
            self.storage.set(hash_id, data)

        log.INFO("Read chunk %s from node %d" % (hash_id, node.node_id))

        return data

    def read_config(self, filename):
        with open(filename) as f:
            return json.loads(f.read())

def startup(config_file):
    loop = asyncio.get_event_loop()
    # loop.set_debug(1)

    dht = DHT(loop, config_file, log)
    dht.start()

    return loop, dht

def main():
    arg = argparse.ArgumentParser(description="DHT client/server")
    arg.add_argument(
        "--config-file",
        dest="config_file",
        default="config.json",
        help="Config file location")

    args = arg.parse_args()
    loop = startup(args.config_file)[0]
    loop.run_forever()

if __name__ == '__main__':
    main()