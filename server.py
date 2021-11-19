"""
    Code for Multi-Threaded Server
    Python 3
    Usage: python3 TCPserver3.py localhost 12000
    coding: utf-8
    
    Author: Navid Bhuiyan
"""
from socket import *
from threading import Thread, Lock
import time
import sys, select
import json
import pickle
import os.path

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
    def __init__(self, clientAddress, clientSocket, serverTimeout):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientMessageSocket = None
        self.clientMessageAddress = (clientAddress[0], clientAddress[1] + 100)
        self.timeout = serverTimeout
        self.clientMessagesAlive = False
        self.clientAlive = True
        self.username = None
        # Handle time class
        self.timeout_duration = timeout
        self.timeout = time.time()
    
    def get_username(self):
        return self.username

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
        self.create_messages_thread()
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
    def create_messages_thread(self):
        t1 = Thread(target = self.handle_messages)
        t1.start()

    """
    Get messages uploaded and distributed
    """
    def handle_messages(self):
        self.clientMessageSocket = socket(AF_INET, SOCK_STREAM)
        self.clientMessageSocket.bind(self.clientMessageAddress)
        self.clientMessageSocket.listen()
        self.clientMessageSocket.accept()
        self.clientMessagesAlive = True
        while self.clientMessagesAlive:
            # Send messages
            self.send_message()
            # Recieve messages
            self.data = self.clientMessageSocket.recv(1024)
            packet = self.data.decode()
            packet = json.loads(packet)
            recipient = packet['recipient']
            message = packet['message']
            sender = packet['sender']
            info = self.load_info()
            if recipient not in info:
                self.clientMessageSocket.sendall(f"{recipient} does not exist")
            elif sender in info[recipient]['blocked']:
                self.clientMessageSocket.sendall(f"Message cannot be forwarded")
            else:
                if sender not in info[recipient]['messages']:
                    info[recipient]['messages'][sender] = [message]
                else:
                    info[recipient]['messages'][sender].append(message)
            self.write_info(info)

    """
    Recieve messages
    """
    def send_message(self):
        info = self.load_info()
        # Use name of thread to get username
        messages = info[self.getName()]['messages']
        for user in messages.keys():
            for message in messages[user]:
                notBlocked = user not in info[self.username]['blocked'] and self.username not in info[user]['blocked']
                if notBlocked:
                    print("message sent")
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
                    packet = sub_packet + ' - ' + 'Login Successful'
                    self.clientSocket.send(packet.encode())
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

    print("\n===== Server is running =====")
    print("===== Waiting for connection request from clients...=====")

    no_threads = 0

    while True:
        serverSocket.listen()
        clientSockt, clientAddress = serverSocket.accept()
        clientThread = ClientThread(clientAddress, clientSockt, serverTimeout)
        clientThread.start()

