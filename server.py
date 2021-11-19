"""
    Code for Multi-Threaded Server
    Python 3
    Usage: python3 TCPserver3.py localhost 12000
    coding: utf-8
    
    Author: Navid Bhuiyan
"""
from socket import *
from threading import Thread, Lock, enumerate
import time
import sys, select
import json
import pickle
import os.path
from random import randint

CLIENTSOCKETS = {}

"""
    Define multi-thread class for client
    This class would be used to define the instance for each connection from each client
    For example, client-1 makes a connection request to the server, the server will call
    class (ClientThread) to define a thread for client-1, and when client-2 make a connection
    request to the server, the server will call class (ClientThread) again and create a thread
    for client-2. Each client will be runing in a separate therad, which is the multi-threading
"""
class ClientThread(Thread):

    """
    Constructor
    """
    def __init__(self, clientAddress, clientSocket, serverMessageSocket, serverTimeout):
        Thread.__init__(self)
        self.serverMessageSocket = serverMessageSocket
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientMessageSocket = None
        self.clientMessageAddress = None
        self.timeout = serverTimeout
        self.clientMessagesAlive = False
        self.clientAlive = True
        self.username = None
        # Handle time class
        self.timeout_duration = serverTimeout
        self.timeout = time.time()

    """
    Run server
    """
    def run(self):
        
        # Create cache file
        self.create_cache()

        packet = ''
        while self.clientAlive:

            # Handling timeout
            difference = int(time.time() - self.timeout)
            if difference == self.timeout_duration and packet != '':
                packet = ''
            else:
                self.timeout = time.time()
            
            self.data = self.clientSocket.recv(1024)
            packet = self.data.decode()

            # if the packet from client is empty, the client would be off-line then set the client as offline (alive=Flase)
            if packet == '':
                self.clientAlive = False
                if self.username is not None:
                    info = self.load_info()
                    info[self.username]["isActive"] = False
                    self.write_info(info)
                print(f"===== the user at {self.username} disconnected =====")
                packet = "User Timeout, Logging Off"
                # Kill of other thread
                self.clientMessagesAlive = False
                self.clientSocket.sendall(packet.encode())
                break

            # TODO: Change later
            if packet == "user credentials request":
                self.process_login()
                # self.pull_messages()
            else:
                print("[recv] " + packet)
                print("[send] Cannot understand this packet")
                packet = 'Cannot understand this packet'
                self.clientSocket.send(packet.encode())

    """
    Convert json packets
    """
    def convert_json(self, json_str):
        return json.loads(json_str)

    """
    Create cache file
    """
    def create_cache(self):
        # Create file
        data_lock = Lock()
        if not os.path.isfile("cache.pickle"):
            f = open("cache.pickle", "wb")
            pickle.dump({}, f)
            f.close()
        # Opeh file
        f = open("cache.pickle", "rb")
        info = pickle.load(f)
        f.close()
        # Open users
        g = open("credentials.txt", "r")
        users = g.readlines()
        users = [k.split() for k in users]
        g.close()
        # Create users not created
        for user in users:
            if user[0] not in info:
                info[user[0]] = {
                    "isActive": False,
                    "messages": {},
                    "blocked": []
                }
        # Re-write info
        with data_lock:
            f = open("cache.pickle", "wb")
            pickle.dump(info, f)
            f.close()
    
    """
    Load cache
    """
    def load_info(self):
        data_lock = Lock()
        with data_lock:
            f = open("cache.pickle", "rb")
            info = pickle.load(f)
            f.close()
        return info

    """
    Update cache
    """
    def write_info(self, info):
        data_lock = Lock()
        with data_lock:
            g = open("cache.pickle", "wb")
            pickle.dump(info, g)
            g.close()

    """
    Cache user data to share amongst threads
    """
    def log_user(self, sub_packet, temp_username):
        # Read file and update
        info = self.load_info()
        if temp_username not in info:
            info[temp_username] = {
                "isActive": True,
                "packets": {},
                "blocked": []
            }
        else:
            info[temp_username]["isActive"] = True
        # Synchronise save
        self.write_info(info)
        self.username = temp_username
        # Activate thread for messaging
        packet = sub_packet + ' - ' + 'Login Successful'
        self.clientSocket.send(packet.encode())
        self.handle_messages_threads()
        print(f"==== {self.username} logged on ====")

    """
    Check if user is active
    """
    def check_active_user(self, username):
        info = self.load_info()
        if username in info:
            return info[username]["isActive"]
        else:
            return False
    
    """
    Create message thread on instance of login
    """
    def handle_messages_threads(self):
        self.serverMessageSocket.listen()
        self.clientMessageSocket, clientMessageAddress = self.serverMessageSocket.accept()
        # Save socket
        global CLIENTSOCKETS
        CLIENTSOCKETS[self.username] = self.clientMessageSocket
        self.clientMessagesAlive = True
        # Handle Thread to deal with sending messages
        t1 = Thread(target = self.handle_messages)
        t1.start()

    """
    Get messages uploaded and distributed
    """
    def handle_messages(self):
        self.serverMessageSocket.listen()
        clientMessageSocket, clientMessageAddress = self.serverMessageSocket.accept()
        clientMessagesAlive = True
        while clientMessagesAlive:
            # Recieve messages
            self.data = clientMessageSocket.recv(1024)
            packet = self.data.decode()
            packet = json.loads(packet)
            recipient = packet['recipient']
            message = packet['message']
            sender = packet['sender']
            info = self.load_info()
            if recipient not in info:
                clientMessageSocket.sendall(f"{recipient} does not exist")
            elif sender in info[recipient]['blocked']:
                clientMessageSocket.sendall(f"Message cannot be forwarded")
            elif not info[recipient]['isActive']:
                if sender not in info[recipient]['messages']:
                    info[recipient]['messages'][sender] = [message]
                else:
                    info[recipient]['messages'][sender].append(message)            
                self.write_info(info)
            # Send message via serverxw
            else:
                global CLIENTSOCKETS
                self.send_message(CLIENTSOCKETS[recipient], sender, message)
    """
    Send messages in between
    """
    def send_message(tempSocket, sender, message):
        tempSocket.sendall(f"{sender}: {message}".encode())

    """
    Recieve cached messages
    """
    def pull_messages(self):
        info = self.load_info()
        # Use name of thread to get username
        messages = info[self.username]['messages']
        for user in messages.keys():
            for message in messages[user]:
                self.clientMessageSocket.sendall(f"{user}: {message}".encode()) 
            # Empty buffered messages
            messages[user] = []
        # Remove buffered messages
        self.write_info(info)

    """
    Process the login.
    """
    def process_login(self):
        # Tell client to log in
        sub_packet = "user credentials request"
        self.clientSocket.send(sub_packet.encode())
        # Sort login
        i = 0
        data_lock = Lock()
        f = open("credentials.txt", 'r+')
        match_username = False
        match_password = False
        while (i < 3):
            # Convert json
            self.data = self.clientSocket.recv(1024)
            self.data = self.data.decode()
            self.data = self.convert_json(self.data)
            if self.check_active_user(self.data['username']):
                packet = sub_packet + ' - ' + "User already logged in."
                self.clientSocket.send(packet.encode())
                return
            for line in f.readlines():
                credentials = line.split()
                temp_username = credentials[0]
                temp_password = credentials[1]
                match_username = temp_username == self.data["username"]
                match_password = temp_password == self.data["password"]
                if match_username and match_password:
                    self.log_user(sub_packet, temp_username)
                    return
                if match_username:
                    packet = sub_packet + ' - ' + "Invalid Password. Please try again"
                    self.clientSocket.send(packet.encode())
                    break
            if not match_username:
                packet = sub_packet + ' - ' + "Welcome New User!"
                self.log_user(sub_packet, temp_username)
                with data_lock:
                    f.write(f"\n{temp_username},{temp_password}")
            # Reset variables
            i += 1
            f.seek(0)
        # Timeout
        self.timeout = time.time()
        self.timeout_enabled = True
        packet = "timeout - Your account is blocked due to multiple login failures. Please try again later"
        self.clientSocket.send(packet.encode())

if __name__ == "__main__":
    
    # acquire server host and port from command line parameter
    if len(sys.argv) != 3:
        print("\n===== Error usage, python3 TCPServer3.py SERVER_PORT ======\n")
        exit(0)
    serverHost = "127.0.0.1"
    serverPort = int(sys.argv[1])
    serverTimeout = int(sys.argv[2])
    serverAddress = (serverHost, serverPort)

    # define socket for the server side and bind address
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(serverAddress)
    serverMessageSocket = socket(AF_INET, SOCK_STREAM)
    serverMessageSocket.bind((serverAddress[0], serverAddress[1] + 100))

    print("\n===== Server is running =====")
    print("===== Waiting for connection request from clients...=====")

    while True:
        serverSocket.listen()
        clientSockt, clientAddress = serverSocket.accept()
        clientThread = ClientThread(clientAddress, clientSockt, serverMessageSocket, serverTimeout)
        clientThread.start()
    
