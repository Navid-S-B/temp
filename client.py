"""
    Python 3
    Usage: python3 TCPClient3.py localhost 12000
    coding: utf-8
    
    Author: Navid Bhuiyan
"""

from socket import *
import sys
import json

class Client():

    def __init__(self, serverPort):
        self.serverHost = "127.0.0.1"
        self.serverPort = serverPort
        self.serverAddress = (self.serverHost, self.serverPort)
        self.clientSocket = socket(AF_INET, SOCK_STREAM)
        self.connection = True
        self.message = "user credentials request"
        self.authenticated = False

    """
    Create a connection from the client to the server.
    """
    def start(self):
        
        self.clientSocket.connect(self.serverAddress)
        while self.connection:
            self.clientSocket.sendall(self.message.encode())
            # receive response from the server
            # 1024 is a suggested packet size, you can specify it as 2048 or others
            if self.authenticated:
                command = input("===== Enter any valid commands =====\n")
            message = self.clientSocket.recv(1024)
            receivedMessage = message.decode()
            self.message_handler(receivedMessage)
    
    """
    Handles messages from server.
    """
    def message_handler(self, receivedMessage):
        # Break down messages
        messages = receivedMessage.split('-')
        received_function = messages[0]
        if (len(messages) == 2):
            message_flag = messages[1].lstrip()
        else:
            message_flag = None
        # Process them
        if received_function == "":
            print("[recv] Message from server is empty!")
        elif "timeout" in receivedMessage:
            print(receivedMessage.split('-')[1])
            self.close()
        elif "user credentials request" in received_function:
            if message_flag != None:
                print(message_flag)
            if message_flag == "login successful":
                self.message = ""
                self.authenticated = True
                print("Welcome to the greatest messaging application ever!")
            else:
                self.login()
        elif "download filename" in received_function:
            print("[recv] You need to provide the file name you want to download")

    def login(self):
        credentials = {}
        self.username = input("Username: ")
        self.password = input("Password: ")
        credentials['username'] = self.username
        credentials['password'] = self.password
        self.message = json.dumps(credentials)
        
    def command_handler(self, command):
        pass

    def close(self):
        self.connection = False
        self.clientSocket.close()
    
    """
    Convert json packets
    """
    def convert_json(self, json_str):
        return json.loads(json_str)

if __name__ == "__main__":
    #Server would be running on the same host as Client
    if len(sys.argv) != 3:
        print("\n===== Error usage, python3 TCPClient3.py SERVER_IP SERVER_PORT ======\n");
        exit(0)
    serverPort = int(sys.argv[1])
    client = Client(serverPort)
    client.start()
