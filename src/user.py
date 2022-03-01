import asyncio
import json
from threading import Thread
import time
from utils import getNTPDateTime
import itertools
import threading
import datetime
import pickle
import os

global MESSAGES
global OTHER_PEERS_MESSAGES
global USERNAME
global NOTIFICATIONS


class Listener(Thread):

    def __init__(self, address, port, username):
        super(Listener, self).__init__()
        self.address = address
        self.port = port
        self.server = None
        self.username = username

    def logout(self):
        self.server.close()

    async def handleConnection(self, reader, writer):
        global NOTIFICATIONS
        req = await reader.readline()
        req = json.loads(req.decode())

        if 'follow' in req:
            user = req['follow']['username']
            NOTIFICATIONS.append(("User " + str(user) + " followed!", getNTPDateTime()))
            rep = "FOLLOW 200"
        elif 'unfollow' in req:
            user = req['unfollow']['username']
            NOTIFICATIONS.append(("User " + str(user) + " unfollowed!", getNTPDateTime()))
            rep = "UNFOLLOW 200"
        elif 'get' in req:
            global MESSAGES
            global OTHER_PEERS_MESSAGES
            global USERNAME
            nodes = req['get']['nodes']
            time_dict = dict(req['get']['time_dict'])
            messages = []

            for leaf in nodes:
                if str(leaf) == '{}':
                    continue
                s = str(leaf)
                s = s.replace("\'", "\"")
                leaf = json.loads(s)
                connectionEstablished = False
                nr_tries = 1
                while nr_tries <= 3:
                    try:
                        (reader2, writer2) = await asyncio.open_connection(
                                        '127.0.0.1', int(leaf["data"]))
                        connectionEstablished = True
                        break
                    except ConnectionRefusedError:
                        nr_tries = nr_tries + 1
                        print("It's not possible to contact that user right now!")
                        break
                    except Exception:
                        print("User might be offline! Retrying...")
                        time.sleep(2)
                        nr_tries = nr_tries + 1
                        if nr_tries > 3:
                            print("It's not possible to contact that user right now!")
                            break

                if connectionEstablished:
                    left = leaf["left"]
                    right = leaf["right"]

                    req = {
                        "get": {
                            "nodes": [left, right],
                            "time_dict": time_dict
                        }
                    }

                    req = json.dumps(req) + '\n'
                    req = req.encode('utf-8')
                    writer2.write(req)
                    await writer2.drain()

                    rep = (await reader2.readline()).strip()

                    writer2.close()

                    rep = json.loads(rep.decode("utf-8"))['get']
                    if rep['msgs']: 
                        for msg in rep['msgs']:
                            messages.append(msg)
                            OTHER_PEERS_MESSAGES.append(msg)

            # print("Receiver messages stored: " + str(MESSAGES))
            for message in MESSAGES:
                messages.append([USERNAME, message[0], message[1]])
            
            messages = messages + OTHER_PEERS_MESSAGES
            # print("Receiver messages all: " + str(messages))
            messages.sort()
            list(messages for messages,_ in itertools.groupby(messages))    
            rep = {
                "get": {
                    "msgs": messages
                }
            }
            rep = json.dumps(rep) + '\n'

        writer.write(rep.encode('utf-8'))
        await writer.drain()

        writer.close()

    async def start_listener(self):
        self.server = await asyncio.start_server(self.handleConnection,
                                                 self.address,
                                                 self.port)
        
        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.exceptions.CancelledError:
                pass
            finally:
                self.server.close()


    def run(self):
        LIST_LOOP = asyncio.new_event_loop()
        LIST_LOOP.run_until_complete(self.start_listener())

class User:
    def __init__(self, username, user_info, server):
        global MESSAGES
        global OTHER_PEERS_MESSAGES
        global USERNAME
        global NOTIFICATIONS
        MESSAGES = []
        OTHER_PEERS_MESSAGES = []
        USERNAME = username
        user_info = json.loads(user_info.decode("utf-8"))
        NOTIFICATIONS = []
        if "notifications" in user_info:
            for n in user_info["notifications"]:
                if n[0] == "follow": 
                    NOTIFICATIONS.append(("User " + str(n[1]) + " followed!", getNTPDateTime()))
                else:
                    NOTIFICATIONS.append(("User " + str(n[1]) + " unfollowed!", getNTPDateTime()))
        self.username = username
        self.followers = user_info['followers']
        self.following = user_info['following']
        self.port = user_info['port']
        self.online = True
        self.listener = Listener('127.0.0.1', self.port, self.username)
        self.listener.daemon = True
        self.listener.start()
        self.server = server
        self.deserialize()
        self._garbageCollector()
        self._serialize()
    
    def deserialize(self):
        global MESSAGES
        path = 'messages/' + self.username + '.dat'
        if os.path.isfile(path):
            inputFile = open(path, 'rb')
            endOfFile = False
            while not endOfFile:
                try:
                    messages = pickle.load(inputFile)
                    break
                except EOFError:
                    endOfFile = True
                
                inputFile.close()
            MESSAGES = messages

    def _serialize(self):
        global MESSAGES
        threading.Timer(5, self._serialize).start()
        if not MESSAGES:
            return
        path = 'messages/'
        check_folder = os.path.isdir(path)

        # If folder doesn't exist, then create it.
        if not check_folder:
            os.makedirs(path)
        
        path = 'messages/' + self.username + '.dat'
        outputFile = open(path, 'wb')
        pickle.dump(MESSAGES, outputFile)
        outputFile.close()

    def _garbageCollector(self):
        threading.Timer(1, self._garbageCollector).start()
        global MESSAGES
        global OTHER_PEERS_MESSAGES

        new_messages = []
        new_other_peers_messages = []
        curr_time = datetime.datetime.utcfromtimestamp(getNTPDateTime())

        for msg in MESSAGES:
            diff = curr_time - datetime.datetime.utcfromtimestamp(msg[1])
            if (diff.seconds) < 300:
                new_messages.append(msg)
        
        for msg in OTHER_PEERS_MESSAGES:
            diff = curr_time - datetime.datetime.utcfromtimestamp(msg[2])
            if (diff.seconds) < 300:
                new_other_peers_messages.append(msg)

        MESSAGES = new_messages
        OTHER_PEERS_MESSAGES = new_other_peers_messages

    def getFollowing(self):
        users = []
        for f in self.following:
            users.append(f[0])
        return users

    def addFollowing(self, user):
        self.following.append(user)

    def removeFollowing(self, user):
        users = []

        for following in self.following:
            if following[0] != user:
                users.append(following[0])
        
        self.following = users

    def logout(self):
        self.listener.logout()

    def post(self):
        global MESSAGES
        msg = input("Write your message:\n")
        size_init = len(MESSAGES)
        MESSAGES.append([msg, getNTPDateTime()])
        size_fin = len(MESSAGES)
        # print("Posted messages: " + str(MESSAGES))
        if(size_fin > size_init):
            print("Message added succesfully.")
        else:
            print("An error occurred while posting the message.")

    def checkForNotifications(self):
        global NOTIFICATIONS
        return NOTIFICATIONS

    def deleteNotifications(self):
        global NOTIFICATIONS
        NOTIFICATIONS = []
    
    def removeDups(self, messages):
        global OTHER_PEERS_MESSAGES
        OTHER_PEERS_MESSAGES = OTHER_PEERS_MESSAGES + messages
        
        new_other_peers_messages = []

        # print("MESSAGES: " + str(OTHER_PEERS_MESSAGES))

        for x in OTHER_PEERS_MESSAGES:
            if x not in new_other_peers_messages and x[0] in str(self.following):
                new_other_peers_messages.append(x)

        OTHER_PEERS_MESSAGES = new_other_peers_messages

        return OTHER_PEERS_MESSAGES

