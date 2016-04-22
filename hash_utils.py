import hashlib

def hash_data(data):
	h = hashlib.sha256()
	h.update(data)
	return h.digest()

def xor_string(s1, s2):
	return b"".join([chr(ord(x) ^ ord(y)) for x,y in zip(s1, s2)])

def dist(h1, h2):
	return xor_string(h1, h2)

def compare(h1, h2):
	for x,y in zip(h1, h2):
		if(ord(x) < ord(y)):
			return -1
		if(ord(x) > ord(y)):
			return 1
	return 0
