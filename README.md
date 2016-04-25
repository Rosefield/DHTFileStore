# CS5600FinalProject

# Overview
The goal is to implement a distributed, decentralized key-value store using a DHT to find the items/peers. 

##Networking architecture
    Ultimately the application is influenced by the BitTorrent protocol. Each node in the network implements two protocols, DHT over UDP to discover peers to connect to, and TCP to store/retrieve data. 
    Communication for the dht protocol uses JSON for message encoding with the data type of a request
```
{
    magic: int //A random id to associate the message
    requestor: Node //The node in the network that initiated the request. Used primarily to assist in bootstrapping so that nodes can introduce themselves
    type: string //What kind of request is being made, one of store_value, find_node, find_value, ping_node
    params: Object // Any additional parameters for use the request, typically id and/or data
}
```    
    A response message will have be of the type resp | error
```
{
    magic: int //Reflect the magic in the original request
    resp: True //boolean always set to true
    result: any //Whatever data is given in response to the request

}
|
{
    error: string //Some message to explain an error
}
```
The basic networking flow looks like this:

On receive UDP packet (calls the Networking.datagram_received function), parse it, and then pass it off to either the DHT.handle_request or handle_response functions, and send back a response as necessary. 

On making a request, the Internal communication is done through using futures, and DHT has a request_magics dict that contains { “fut”:future, “node”:node } that corresponds to the node that we sent, and the future where we set whatever value is the result of the response (set in handle_response). Whenever make_request is called, it will generate a random magic, create a new future, and then add it to the request_magics dict.

For a TCP key request, the Networking.handle_client function is called, reads line to get the key, and then checks its storage for the key. If it has it, it will send back “size\ndata”. 

##Routing

Each node when joining the network is assigned an id that is composed of 32 random bytes, and keys for values are calculated as `key = sha256(value)`. Note that because of this, nodes and values share the same keyspace. This makes it convenient to decide what node to store a value on, since one can search the network for the closest nodes to `key` and then store the value there. 

Currently how routing works is the Routing class has an internal dictionary of id => node. The most important function right now is the nearest_nodes which takes a node_id (a hash like any other), and returns the top 7 nodes whose ids are closest to the provided node_id. There are optional parameters to change the number of returned nodes, as well as specify a set of nodes to search, if not using the internal dictionary. Additionally there are the add_nodes and add_or_update_nodes functions which adds a (list of) node(s) to the internal table, and then keeps the bucket_size nodes that are closest to our it.

The distance between two nodes (as used in calculating closest nodes in nearest_nodes) is simply an xor of the two node_ids. 


##File storage
    Within the network a chuck of data is stored as a simple key-value pair where the key is the sha256 hash of the data. A file as stored client side is a series of (key, size) tuples that corresponds to the data in the network and the size of the requested data. 


# TODO
- Update routing to handle multiple buckets each a different distance from our node
- Update the store/retrieve code to handle failure better in case a node sends us bad data, crashes, or otherwise doesn't respond
- Make the send/retrieve file code read/write the blocks as requested, instead of sequentially (don't want to be stuck on block 1 because one peer is slow when you can start sending blocks 2,3,etc)
- Quality of life improvements for the user interface (progress bars? transfer totals? ??)



