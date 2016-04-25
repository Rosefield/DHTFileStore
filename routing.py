import hash_utils
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

class Node:
    def __init__(self, n):
        self.node_id = n["node_id"]
        self.ip = n["ip"]
        self.port = n["port"]

    def __repr__(self):
        return "Node(id {}, ip {}, port {})".format(self.node_id, self.ip, self.port)

    def __str__(self):
        return "Node(id {}, ip {}, port {})".format(self.node_id, self.ip, self.port)

    def __eq__(self, other):
        return self.node_id == other.node_id

    def __hash__(self):
        return hash(self.node_id)


class Routing:
    def __init__(self, node, nodes, bucket_size = 20):
        self.nodes = {}
        self.node = node
        self.bucket_size = bucket_size
        self.set_nodes(nodes)

    def __iter__(self):
        for k,v in self.nodes.items():
            yield v

    def set_nodes(self, nodes):
        self.nodes = {}
        for node in nodes:
            self.nodes[node.node_id] = node

    def add_nodes(self, nodes):
        if len(nodes) == 0:
            return
        if len(nodes) > self.bucket_size:
            nodes = self.nearest_nodes(self.node.node_id, nodes, self.bucket_size)

        log.debug("Adding nodes %s", nodes)

        for node in nodes:
            if node.node_id == self.node.node_id:
                continue
            self.nodes[node.node_id] = node

        self.set_nodes(self.nearest_nodes(self.node.node_id, k=self.bucket_size))
        log.debug("Bucket size now %d", len(self.nodes))
        

    def add_or_update_node(self, node):
        if(node.node_id == self.node.node_id):
            return
        id = node.node_id
        if id in self.nodes:
            log.debug("Updating node %s", id)
            self.nodes[id] = node
        else:
            log.debug("Adding node %s", node)
            self.nodes[id] = node
            self.set_nodes(self.nearest_nodes(self.node.node_id, k=self.bucket_size))

        return

    def remove_node(self, node):
        id = node.node_id
        if id in self.nodes:
            del self.nodes[id]

    def nearest_nodes(self, node_id, nodes= None, k=7):
        '''
        Return the top k nodes who's ids are nearest to the provided hash
        '''

        if nodes is None:
            nodes = self.nodes
            top =  sorted(nodes, key=lambda x: hash_utils.dist(node_id, x))[:k]
            return [nodes[x] for x in top]
        else:
            top = sorted(nodes, key=lambda x: hash_utils.dist(node_id, x.node_id))[:k]
            return top
