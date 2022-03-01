import logging
import asyncio
import sys
import json
import inspect

from kademlia.network import Server
from server import KServer
from threading import Thread
from user import User
from menu import Menu
from menu_item import MenuItem
import os

from utils import showMessages

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

SERVER = None
BOOTSTRAP = None
MAIN_THREAD = None
USER = None
SEARCHED_USER = None
RUNNING = True
LOOP = None

async def login():
    global SERVER
    global USER
    username = input("Username: ")
    
    try:
        user_info = await SERVER.login(username)
        USER = User(username, user_info, SERVER)
        print("Logged In Successfully.")

        return 1
    except Exception as e:
        print(e)
        return 0

async def logout():
    global USER
    global SEARCHED_USER
    global SERVER
    global RUNNING
    await SERVER.updateStatus(USER.username)
    SERVER.logout()
    USER.logout()

    USER = None
    SEARCHED_USER = None

    SERVER = None
    RUNNING = False

async def register():
    global SERVER
    global BOOTSTRAP

    username = input("Username: ")

    try:
        await SERVER.register(username)
        print("Successfully Registered.")

        return 1
    except Exception as e:
        print(e)
        return 0

async def close():
    global SERVER
    global RUNNING
    SERVER = None
    RUNNING = False

async def search():
    global SERVER
    global USER
    global SEARCHED_USER

    username = input("Username: ")
    try:
        user_info = await SERVER.get(username)
        if user_info is not None:
            print("User found!")
            SEARCHED_USER = [username, json.loads(user_info.decode("utf-8"))]
            return 1
        else:
            print("Username doesn't exist.")
    except Exception as e:
        print(e)
        return 0

async def follow():
    global SEARCHED_USER
    global USER
    new_following = await SERVER.follow(USER.username, SEARCHED_USER[0])
    USER.addFollowing(new_following)

async def unfollow():
    global SEARCHED_USER
    old_following = await SERVER.unfollow(USER.username, SEARCHED_USER[0])
    USER.removeFollowing(old_following)

async def post():
    USER.post()

async def show():
    user_info = await SERVER.get(USER.username)
    following = json.loads(user_info.decode("utf-8"))
    following = following['following']
    messages = await SERVER.get_messages(USER.username, user_info, following)
    messages = USER.removeDups(messages)

    showMessages(messages)
    input("Press any key to continue...")

async def back():
    global SEARCHED_USER
    SEARCHED_USER = None

def build_auth_menu():
    menu = Menu("Authentication", [])
    menu.append_item(MenuItem("Login", login))
    menu.append_item(MenuItem("Register", register))
    menu.append_item(MenuItem("Close the Application", close))

    return menu

async def getUpdatedSearchedUser():
    global SEARCHED_USER
    user_info = await SERVER.get(SEARCHED_USER[0])
    SEARCHED_USER = [SEARCHED_USER[0], json.loads(user_info.decode("utf-8"))]
    return SEARCHED_USER

async def getUpdatedUser():
    user_info = await SERVER.get(USER.username)
    followers = json.loads(user_info.decode("utf-8"))
    followers = followers['followers']
    return followers

def checkIfFollowed():
    global SEARCHED_USER
    global USER

    users = USER.getFollowing()

    if SEARCHED_USER[0] in users:
        return 1
    return 0

def followers():
    print (f"{USER.username} is followed by: ")

    loop = asyncio.get_event_loop()
    loop = asyncio.get_event_loop()
    if inspect.iscoroutinefunction(getUpdatedUser):
        future = asyncio.run_coroutine_threadsafe(
            getUpdatedUser(),
            loop)
        followers = future.result()
    elif inspect.iscoroutinefunction(getUpdatedUser):
        future = asyncio.run_coroutine_threadsafe(getUpdatedUser, loop)
        followers = future.result()

    USER.followers = followers

    for follower in USER.followers:
        print('\t- ' + str(follower))

def following():
    print (f"{USER.username} follows: ")
    for follow in USER.following:
        print('\t- ' + str(follow[0]))

def build_user_menu():
    global SEARCHED_USER
    global LOOP
    global SERVER
    menu = Menu("Welcome " + str(USER.username), USER.checkForNotifications())
    USER.deleteNotifications()
    if SEARCHED_USER is not None:
        loop = asyncio.get_event_loop()
        if inspect.iscoroutinefunction(getUpdatedSearchedUser):
            future = asyncio.run_coroutine_threadsafe(
                getUpdatedSearchedUser(),
                loop)
            SEARCHED_USER = future.result()
        elif inspect.iscoroutinefunction(getUpdatedSearchedUser):
            future = asyncio.run_coroutine_threadsafe(getUpdatedSearchedUser, loop)
            SEARCHED_USER = future.result()
        menu.addConstLine(SEARCHED_USER)

        if checkIfFollowed():
            menu.append_item(MenuItem("Unfollow User", unfollow))
        else:
            menu.append_item(MenuItem("Follow User", follow))
        menu.append_item(MenuItem("Back", back))
    else:
        menu.append_item(MenuItem("Search for an User", search))
        menu.append_item(MenuItem("Show Timeline", show))
        menu.append_item(MenuItem("Post a Message", post))
        menu.append_item(MenuItem("Check My Followers", followers))
        menu.append_item(MenuItem("Check Who I'm Following", following))
    
    menu.append_item(MenuItem("Logout", logout))

    return menu
    
def run_auth_menu():
    global AUTH_MENU
    global SERVER
    global USER
    while RUNNING:
        if USER is None:
            AUTH_MENU = build_auth_menu()
            AUTH_MENU.execute()
        else:
            USER_MENU = build_user_menu()
            USER_MENU.execute()

def main(port):
    global SERVER
    global MAIN_THREAD
    global LOOP
    SERVER = KServer(port)
    LOOP = SERVER.start();

    MAIN_THREAD =Thread(target=LOOP.run_forever, daemon=True).start()

    run_auth_menu()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python peer.py <peer_port>")
        sys.exit(1)
    
    port = int(sys.argv[1])

    if port >= 5000 and port <= 5002:
        print("Ports 5000, 5001 and 5002 are reserved for the system.")
        sys.exit(1)

    BOOTSTRAP = False
    main(port)