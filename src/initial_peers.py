import logging
import asyncio
import os

from kademlia.network import Server
from threading import Thread

class InitialNode(Thread):
    def __init__(self, port, bootstrap_address, bootstrap_port):
        Thread.__init__(self)
        self.port = port
        self.bootstrap_port = bootstrap_port
        self.bootstrap_address = bootstrap_address

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_debug(True)

        server = Server()
        loop.run_until_complete(server.listen(self.port))

        if self.bootstrap_port is not None:
            bootstrap_node = (self.bootstrap_address, self.bootstrap_port)
            loop.run_until_complete(server.bootstrap([bootstrap_node]))

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.stop()
        loop.close()

ports = [5000, 5001, 5002]

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s'
                              ' - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)

threads = []

thread = InitialNode(ports[0], None, None)
threads.append(thread)
thread.start()

for port in range(1, len(ports)):
    thread = InitialNode(ports[port], "localhost", ports[0])
    threads.append(thread)
    thread.start()

for thread in threads:
    try:
        thread.join()
    except:
        os._exit(1)