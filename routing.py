import hash_utils

class Node:
    def __init__(self, n):
        self.node_id = n["node_id"]
        self.ip = n["ip"]
        self.port = n["port"]

    def __str__(self):
        return "Node(id {}, ip {}, port {})".format(self.node_id, self.ip, self.port)

    def __hash__(self):
        return hash(self.node_id)


class Routing:
    def __init__(self, node, nodes, bucket_size = 20):
        self.nodes = {}
        self.node = node
        self.bucket_size = bucket_size
        for node in nodes:
            self.nodes[node.node_id] = node

    def __iter__(self):
        for k,v in self.nodes.items():
            yield v

    def add_nodes(self, nodes):
        if len(nodes) > self.bucket_size:
            nodes = self.nearest_nodes(self.node.node_id, nodes, self.bucket_size)

        for node in nodes:
            self.nodes[node.node_id] = node

        self.nodes = self.nearest_nodes(self.node.node_id, k=self.bucket_size)

    def add_or_update_node(self, node):
        id = node.node_id
        if id in self.nodes:
            self.nodes[id] = node
        else:
            self.nodes[id] = node
            self.nodes = self.nearest_nodes(self.node.node_id, k=self.bucket_size)

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
