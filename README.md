# CS5600FinalProject

# Overview
The goal is to implement a distributed, decentralized key-value store using a DHT to find the items/peers. 

##Networking architecture
    Ultimately the application is influenced by the BitTorrent protocol. Each node in the network implements two protocols, DHT to discover peers to connect to, and TCP to store/retrieve data. 

    Communication for the dht protocol uses JSON for message encoding with the data type of a request
```
{
    magic: int //A random id to associate the message
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



##File storage
    Within the network a chuck of data is stored as a simple key-value pair where the key is the sha256 hash of the data. A file as stored client side is a series of (key, size) tuples that corresponds to the data in the network and the size of the requested data. 


# TODO
- Change to use UDP instead of TCP for dht, listen for tcp on same port for large data tranfer
- Finish networking (bootstrapping, find_value/node, store_value)
- High level api for store/retrieve file
- CLI/Repl to interact as a user




