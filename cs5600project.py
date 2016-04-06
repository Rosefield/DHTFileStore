
def store_value(data, nodes):
	hash = hash_data(data)

	to_contact = nearest_nodes(nodes, hash)

	for node in to_contact:
		dht.send_request("store", node, hash, extra=data)

	return hash	

def find_value(hash, nodes):

	to_contact = nearest_nodes(nodes, hash)

	futs = []
	for node in to_contact:
		futs.append(dht.send_request("findv", node, hash))

	#get data from futures?
	#get ip to contact from futures and then get data?

	return 

def find_node(hash, nodes):

	to_contact = nearest_nodes(nodes, hash)

	futs = []
	for node in to_contact:
		futs.append(dht.send_request("findn", node, hash))

	#get node ids from futures
	#update current list of nodes?

	return
