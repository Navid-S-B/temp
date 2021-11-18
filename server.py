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
    def __init__(self, clientAddress, clientSocket, timeout):
        
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        self.clientAlive = True
        self.data = None
        self.username = None
        # Handle time class
        self.timeout_duration = timeout
        self.timeout = None
        self.timeout_enabled = False
    
    """
    Run server
    """
    def run(self):
        
        message = ''

        while self.clientAlive:

            # Handling timeout
            if self.timeout_enabled:
                difference = int(time.time() - self.timeout)
                if difference == self.timeout_duration:
                    self.timeout_enabled = False
                    self.timeout = None
                else:
                    continue
            
            self.data = self.clientSocket.recv(1024)
            message = self.data.decode()

            # if the message from client is empty, the client would be off-line then set the client as offline (alive=Flase)
            if message == '':
                self.clientAlive = False
                print(f"===== the user at {self.username} disconnected =====")
                break

            # TODO: Change later
            if message == "user credentials request":
                self.process_login()
            elif message == 'download':
                print("[recv] Download request")
                message = 'download filename'
                print("[send] " + message)
                self.clientSocket.send(message.encode())
            else:
                print("[recv] " + message)
                print("[send] Cannot understand this message")
                message = 'Cannot understand this message'
                self.clientSocket.send(message.encode())

    """
    Convert json packets
    """
    def convert_json(self, json_str):
        return json.loads(json_str)

    """
    Cache user data to share amongst threads
    """
    def save_data(self):
        pass

    """
    Process the login.
    """
    def process_login(self):
        # Tell client to log in
        sub_message = "user credentials request"
        self.clientSocket.send(sub_message.encode())
        # Sort login
        i = 0
        data_lock = Lock()
        f = open("credentials.txt", 'r+')
        match_username = False
        match_password = False
        while (i < 3):
            # Convert json
            self.data = self.clientSocket.recv(1024)
            data = self.data.decode()
            data = self.convert_json(data)
            for line in f.readlines():
                credentials = line.split()
                temp_username = credentials[0]
                temp_password = credentials[1]
                match_username = temp_username == data["username"]
                match_password = temp_password == data["password"]
                if match_username and match_password:
                    self.username = temp_username
                    message = sub_message + ' - ' + 'login successful'
                    print(f"==== {self.username} logged on ====")
                    self.clientSocket.send(message.encode())
                if match_username:
                    message = sub_message + ' - ' + "Invalid Password. Please try again"
                    self.clientSocket.send(message.encode())
                    break
            if not match_username:
                # Ensure synchronisation
                self.username = data['username']
                with data_lock:
                    f.write(f"\n{data['username']},{data['password']}")
                f.close()
                message = sub_message + ' - ' + 'login successful'
                self.clientSocket.send(message.encode())
                print(f"==== {self.username} logged on ====")
                return
            i += 1
        # Timeout
        self.timeout = time.time()
        self.timeout_enabled = True
        message = "timeout - Your account is blocked due to multiple login failures. Please try again later"
        self.clientSocket.send(message.encode())

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

    while True:
        serverSocket.listen()
        clientSockt, clientAddress = serverSocket.accept()
        clientThread = ClientThread(clientAddress, clientSockt, serverTimeout)
        clientThread.start()
