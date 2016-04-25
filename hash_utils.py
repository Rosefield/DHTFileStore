import hashlib

def hash_data(data):
	h = hashlib.sha256()
	h.update(data)
	return h.digest().hex()

def xor_string(s1, s2):
	return bytes([x ^ y for x,y in zip(s1, s2)])

def dist(h1, h2):
    h1 = bytes.fromhex(h1)
    h2 = bytes.fromhex(h2)
    return xor_string(h1, h2)
