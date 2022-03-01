import datetime
from collections import deque
import json
import ntplib
import datetime
import time

def showMessages(messages):
    if not messages:
        print("No new messages!")
        return
    print("=" * 34 + " Timeline " + "=" * 35)

    messages = sorted(messages, key=lambda tup: tup[2])
    
    for message in messages:
        time = datetime.datetime.fromtimestamp(message[2])
        
        diff = datetime.datetime.utcfromtimestamp(getNTPDateTime()) - time

        days = diff.days
        hours = diff.seconds // 3600
        minutes = diff.seconds // 60
        seconds = diff.seconds - (hours*3600) - (minutes*60)

        header_front = "| Posted by: " + message[0]

        if days > 0:
            header_back = str(days) + " days ago"
        elif hours > 0:
            header_back = str(hours) + " hours ago"
        elif minutes > 0:
            header_back = str(minutes) + " minutes ago"
        else:
            header_back = str(seconds) + " seconds ago"

        header = header_front + (77-len(header_front)-len(header_back)) * " " + header_back

        print(header + (78-len(header)) * " " + "|")
        chunk = message[1][0: 75]
        if len(message[1]) < 76:
            print("| " + chunk + (76-len(chunk)) * " " + "|")
            print("|" + 77 * " " + "|")
        else:
            print("| " + chunk + " |")
            multiplier = 1
            while multiplier * 77 < len(message[1]):
                chunk = message[1][75*multiplier: 75*(multiplier+1)]
                print("| " + chunk + (76-len(chunk)) * " " + "|")
                multiplier = multiplier + 1
            print("|" + 77 * " " + "|")

class Node(object):
    def __init__(self, data):
        self.data = data
        self.left = {}
        self.right = {}

    def __str__(self):
        return f'[{self.data}, {self.left}, {self.right}]'

    def reprJSON(self):
        return dict(data=self.data, left=self.left, right=self.right) 

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)

def binaryTree(data):
    n = iter(data)
    tree = Node(next(n))
    fringe = deque([tree])
    while True:
        head = fringe.popleft()
        try:
            head.left = Node(next(n))
            fringe.append(head.left)
            head.right = Node(next(n))
            fringe.append(head.right)
        except StopIteration:
            break

    return tree         

def getNTPDateTime():
    #return time.time()
    addr = '1.pool.ntp.org'
    try:
        ntpDate = None
        client = ntplib.NTPClient()
        response = client.request(addr, version=3)
        return response.tx_time
        # ntpDate = time.ctime(response.tx_time)
        # print(response.tx_time)
    except Exception as e:
        # print(e)
        return time.time()
    # return datetime.datetime.strptime(ntpDate, "%a %b %d %H:%M:%S %Y") # "%Y-%m-%d %H:%M:%S.%f"

