import hashlib
import base64

def hash_data(data):
	h = hashlib.sha256()
	h.update(data)
	return h.digest()

def xor_string(s1, s2):
	return "".join([chr(ord(x) ^ ord(y)) for x,y in zip(s1, s2)])

def hash_dist(h1, h2):
	return xor_string(h1, h2)

def hash_compare(h1, h2):
	for x,y in zip(h1, h2):
		if(ord(x) < ord(y)):
			return -1
		if(ord(x) > ord(y)):
			return 1
	return 0

def nearest_nodes(nodes, hash, k = 7):
	'''
	Return the top k nodes who's ids are nearest to the provided hash
	'''
	return sorted(nodes, key=lambda x: hash_dist(hash, x.id), cmp=hash_compare)[:k]

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