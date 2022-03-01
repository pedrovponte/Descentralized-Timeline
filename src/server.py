import logging
import asyncio
import json
import time, threading
import inspect
from utils import getNTPDateTime
import time

from kademlia.network import Server

from utils import ComplexEncoder, binaryTree

class KServer:
    def __init__(self, port):
        self.port = port
        self.bootstrapped_ports = [5000]


    def start(self):
        self.loop = asyncio.get_event_loop()

        self.server = Server()
        self.loop.run_until_complete(self.server.listen(self.port))

        self.loop.run_until_complete(self.server.bootstrap([('127.0.0.1', 5000), ('127.0.0.1', 5001), ('127.0.0.1', 5002)]))

        return self.loop
    
    def logout(self):
        self.server.stop()

    async def get(self, username):
        result = await self.server.get(username)
        
        if result is None:
            print("There is no User with that username.")
            time.sleep(2)
            return None
        return result

    async def updateStatus(self, username):
        user_info = await self.server.get(username)
        user_info = json.loads(user_info.decode("utf-8"))
        user_info = {
            "followers": user_info["followers"],
            "following": user_info["following"],
            "port": user_info["port"],
            "notifications": user_info["notifications"],
            "online": False
        }
        user_info = json.dumps(user_info).encode('utf-8')
        await self.server.set(username, user_info)

    def addNewBootstrap(self):
        t = threading.Timer(1.0, self.addNewBootstrap)
        t.daemon = True
        t.start()
        asyncio.run_coroutine_threadsafe(
                    self.server._refresh_table(),
                    self.loop)
                    
        neighbors = self.server.bootstrappable_neighbors()
        for x in range(0, len(neighbors)):
            asyncio.run_coroutine_threadsafe(
                self.server.bootstrap([('127.0.0.1', neighbors[x][1])]),
                self.loop)

    async def bootStrapNode(self):
        neighbors = self.server.bootstrappable_neighbors()
        if not neighbors:
            print("Unable to register at the moment.")
            time.sleep(2)
            return -1
        else:
            self.bootstrap_port = neighbors[0][1]
            self.bootstrapped_ports.append(self.bootstrap_port)       
            await self.server.bootstrap([('127.0.0.1', 8001)])
            return 0

    async def register(self, username):
        result = await self.server.get(username)

        if result is None:
            user_info = {
                "followers": [],
                "following": [],
                "port": self.port,
                "notifications": [],
                "online": False
            }
            user_info = json.dumps(user_info).encode('utf-8')
            await self.server.set(username, user_info)
        else:
            raise Exception("Username already exists.")
    
    async def login(self, username):
        result = await self.server.get(username)
        
        if result is None:
            raise Exception("Username doesn't exist.")

        result = json.loads(result)
        user_info = {
            "followers": result["followers"],
            "following": result["following"],
            "port": result["port"],
            "notifications": result["notifications"],
            "online": True
        }
        user_info = json.dumps(user_info).encode('utf-8')
        await self.server.set(username, user_info)
        return user_info

    async def getUserPort(self, user):
        port = await self.server.get(user)
        port = int(json.loads(port.decode("utf-8"))['port'])
        
        return port

    async def follow(self, user1, user2):
        new_following = [user2, getNTPDateTime()]
        if user1 == user2:
            print("You can't follow yourself.")
            time.sleep(2)
            return -1

        port = await self.getUserPort(user2)

        nr_tries = 1
        while nr_tries <= 3:
            try:
                (reader, writer) = await asyncio.open_connection(
                                '127.0.0.1', port)
                break
            except Exception:
                print("User might be offline! Retrying...")
                time.sleep(2)
                nr_tries = nr_tries + 1
                if nr_tries > 3:
                    await self.updateStatus(user2)
                    user1_info = await self.server.get(user1)
                    user2_info = await self.server.get(user2)

                    user1_info = json.loads(user1_info.decode())
                    user1_info['following'].append(new_following)
                    user1_info = json.dumps(user1_info).encode('utf-8')

                    user2_info = json.loads(user2_info.decode())
                    user2_info['followers'].append(user1)
                    if "notifications" in user2_info:
                        user2_info['notifications'].append(["follow", user1])
                    else:
                        user2_info['notifications'] = [["follow", user1]]
                    user2_info = json.dumps(user2_info).encode('utf-8')

                    await self.server.set(user1, user1_info)
                    await self.server.set(user2, user2_info)

                    return new_following
        
        req = {
            "follow": {
                "username": user1
            }
        }
        req = json.dumps(req) + '\n'
        req = req.encode('utf-8')
        writer.write(req)
        await writer.drain()

        rep = (await reader.readline()).strip()

        writer.close()

        rep = rep.decode().split(" ")

        if rep[0] == 'FOLLOW':
            if rep[1] == '200':
                user1_info = await self.server.get(user1)
                user2_info = await self.server.get(user2)

                user1_info = json.loads(user1_info.decode())
                user1_info['following'].append(new_following)
                user1_info = json.dumps(user1_info).encode('utf-8')

                user2_info = json.loads(user2_info.decode())
                user2_info['followers'].append(user1)
                user2_info = json.dumps(user2_info).encode('utf-8')

                await self.server.set(user1, user1_info)
                await self.server.set(user2, user2_info)
                
                return new_following
    
    async def unfollow(self, user1, user2):
        if user1 == user2:
            print("You can't unfollow yourself.")
            time.sleep(2)
            return -1

        port = await self.getUserPort(user2)

        nr_tries = 1
        while nr_tries <= 3:
            try:
                (reader, writer) = await asyncio.open_connection(
                                '127.0.0.1', port)
                break
            except Exception:
                print("User might be offline! Retrying...")
                time.sleep(2)
                nr_tries = nr_tries + 1
                if nr_tries > 3:
                    await self.updateStatus(user2)

                    user1_info = await self.server.get(user1)
                    user2_info = await self.server.get(user2)

                    user1_info = json.loads(user1_info.decode())
                    following = [i[0] for i in user1_info['following']]
                    index = following.index(user2)
                    old_following = following[index]
                    user1_info['following'].pop(index)
                    user1_info = json.dumps(user1_info).encode('utf-8')

                    user2_info = json.loads(user2_info.decode())

                    new_followers = []
                    for _user in user2_info['followers']:
                        if _user != user1:
                            new_followers.append(_user)

                    user2_info['followers'] = new_followers
                    if "notifications" in user2_info:
                        user2_info['notifications'].append(["unfollow", user1])
                    else:
                        user2_info['notifications'] = [["unfollow", user1]]
                    user2_info = json.dumps(user2_info).encode('utf-8')

                    await self.server.set(user1, user1_info)
                    await self.server.set(user2, user2_info)

                    return old_following

        req = {
            "unfollow": {
                "username": user1
            }
        }
        req = json.dumps(req) + '\n'
        req = req.encode('utf-8')
        writer.write(req)
        await writer.drain()

        rep = (await reader.readline()).strip()

        writer.close()

        rep = rep.decode().split(" ")

        if rep[0] == 'UNFOLLOW':
            if rep[1] == '200':
                user1_info = await self.server.get(user1)
                user2_info = await self.server.get(user2)

                user1_info = json.loads(user1_info.decode())
                following = [i[0] for i in user1_info['following']]
                index = following.index(user2)
                old_following = following[index]
                user1_info['following'].pop(index)
                user1_info = json.dumps(user1_info).encode('utf-8')

                user2_info = json.loads(user2_info.decode())

                new_followers = []
                for _user in user2_info['followers']:
                    if _user != user1:
                        new_followers.append(_user)

                user2_info['followers'] = new_followers
                user2_info = json.dumps(user2_info).encode('utf-8')

                await self.server.set(user1, user1_info)
                await self.server.set(user2, user2_info)

                user2_info = json.loads(user2_info.decode())

                return old_following

    async def get_messages(self, user_username, user_info, users):
        user_info = json.loads(user_info.decode("utf-8"))
        messages = []
        nodes = {}
        nodesaux = []
        port = int(user_info['port'])

        for user in users:
            node = await self.server.get(user[0])
            node = json.loads(node.decode("utf-8"))
            nodes[node['port']] = user[1]
            if node['online']:
                nodesaux.append(int(node['port']))

        nodesaux = [port] + nodesaux
        root = binaryTree(nodesaux)
        root = [root.left, root.right]

        for leaf in root:
            if leaf == {}:
                continue 
            nr_tries = 1
            connectionEstablished = False
            while nr_tries <= 3:
                try:
                    (reader, writer) = await asyncio.open_connection(
                                    '127.0.0.1', leaf.data)
                    connectionEstablished = True
                    break
                except Exception:
                    print("User might be offline! Retrying...")
                    time.sleep(2)
                    nr_tries = nr_tries + 1
                    if nr_tries > 3:
                        for user in users:
                            node = await self.server.get(user[0])
                            node = json.loads(node.decode("utf-8"))
                            if node['port'] == leaf.data:
                                await self.updateStatus(user[0])
                                print("It's not possible to contact that user right now!")
                                continue

            if connectionEstablished:
                left = leaf.left
                right = leaf.right

                if not isinstance(left, dict):
                    left = json.dumps(left.reprJSON(), cls=ComplexEncoder)
                if not isinstance(right, dict):
                    right = json.dumps(right.reprJSON(), cls=ComplexEncoder)
                
                req = {
                    "get": {
                        "nodes": [str(left), str(right)],
                        "time_dict": nodes
                    }
                }

                req = json.dumps(req) + '\n'
                req = req.encode('utf-8')
                writer.write(req)
                await writer.drain()

                rep = (await reader.readline()).strip()

                writer.close()

                rep = json.loads(rep.decode("utf-8"))['get']
                if rep['msgs']:
                    for msg in rep['msgs']:
                        if(msg[0] != user_username and msg[0] in str(user_info['following'])):
                            messages.append(msg)

        following = user_info['following'] 
        timestamp = getNTPDateTime()
        new_following = []
        for user in following:
            new_following.append([user[0], timestamp])

        user_info['following'] = new_following

        user_info = json.dumps(user_info).encode('utf-8')
        await self.server.set(user_username, user_info)

        return messages
                