import asyncio
import json
import logging

log = logging.getLogger(__name__)

class Networking:
    def __init__(self, dht_protocol, storage):
        self.dht = dht_protocol
        self.storage = storage

    #UDP
    def connection_made(self, transport):
        log.info("Connection made")
        self.transport = transport

    def datagram_received(self, data, addr):
        log.debug("Received %s from %s", data, addr)

        message = None
        try:
            message = self.parse_message(data)
            if message.get("error") is not None:
                log.info("Error parsing message %s", message.get("error"))
                self.transport.close()
                return
        except Exception as e:
            log.warning("Exception %s thrown parsing message %s", e, data)
            self.transport.close()
            return

        is_resp = message.get("resp")
        if is_resp is not None and is_resp == True:
            self.dht.handle_response(message)
        else:
            #make whatever store/find/etc requests
            #Can't use yield from directly since this function is never itself scheduled
            task = asyncio.async(self.dht.handle_request(message))

            #schedule response
            task.add_done_callback(lambda task: self.send_message(task.result(), addr))
        log.debug("Connection end for %s", addr)


    def parse_message(self, data):
        if data is None:
            return {"error": "empty message"}
        message = json.loads(data.decode('utf8'))

        if not isinstance(message, dict):
            return {"error": "message incorrectly formed"}

        return message

    def send_message(self, message, addr):
        message_s = json.dumps(message).encode('utf8')
        log.debug("Sending message %s to %s", message_s, addr)

        self.transport.sendto(message_s, addr)


    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        log.info("connection closed %s", exc)

    #TCP
    @asyncio.coroutine
    def handle_client(self, reader, writer):
        peer = writer.get_extra_info("socket").getpeername()

        log.info("New TCP connection from %s", peer)

        request = yield from asyncio.wait_for(reader.readline(), timeout=15)
        #strip the newline
        request = request[:-1].decode()

        log.info("Peer %s requested %s and we have it? %s", peer, request, self.storage.has(request))


        if self.storage.has(request):
            log.info("Serving %s", request)
            data = self.storage.get(request)
            data_len = len(data)
            writer.write(data_len.to_bytes(4, byteorder="little") + b"\n")
            yield from writer.drain()
            log.debug("Sent size header (%d) for %s", data_len, request)
            if isinstance(data, str):
                data = data.encode()
            writer.write(data)
            yield from writer.drain()
            log.debug("Sent data for %s", request)

        writer.close()

    @asyncio.coroutine
    def request_key(self, hash_id, node):
        data = None
        try:
            reader, writer = yield from asyncio.open_connection(node.ip, node.port)

            #Request the key
            writer.write(hash_id.encode() + b"\n")
            yield from writer.drain()
            #Wait until the request has been sent before continuing

            size = yield from asyncio.wait_for(reader.readline(), timeout=10)
            size = int.from_bytes(size[:-1], byteorder="little")

            log.debug("Request %s of size %d", hash_id, size)
            data = yield from reader.read(size)
            log.debug("Finished receiving data for %s, received %d bytes", hash_id, len(data))
            data = data

        except Exception as e:
            log.warning("Error connecting to %s:%s (%s)", node.ip, node.port, e)

        return data


    #General
