import hash_utils

class DHT:
    def __init__():
        pass

    
    def nearest_nodes(hash_id, k = 7):
        '''
        Return the top k nodes who's ids are nearest to the provided hash
        '''
        pass
        #return sorted(nodes, key=lambda x: hash_utils.dist(hash_id, x.id), cmp=hash_utils.compare)[:k]


    def join():
        '''
        Joins the DHT network
        '''
        pass

    def ping_nodes():
        '''
        Checks to see which of the nodes we have are still alive / in the network
        '''
        pass

    def store_value(hash_id, data):
        '''
        Adds the data to the network with id of hash_id, and the data specified
        '''
        pass

    def find_node(hash_id):
        '''
        Makes a request to the n nodes with ids closest to hash_id asking them to find the nodes who's ids
        are closest to hash_id
        '''
        pass

    def find_value(hash_id):
        '''
        Makes a request to the n nodes with ids closest to hash_id to find who has the file hash_id
        '''
        pass

    def handle_request(request):
        '''
        Function that will handle any requests that are made 

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

        '''
        pass
