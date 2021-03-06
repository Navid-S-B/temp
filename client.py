"""
    Python 3
    Usage: python3 TCPClient3.py localhost 12000
    coding: utf-8
    
    Author: Navid Bhuiyan
"""

from socket import *
import sys
import json
from threading import Thread

class Client():

    def __init__(self, serverPort):
        self.serverHost = "127.0.0.1"
        self.serverPort = serverPort
        self.serverAddress = (self.serverHost, self.serverPort)
        self.serverMessagesAddress = (self.serverHost, self.serverPort + 100)
        self.clientSocket = socket(AF_INET, SOCK_STREAM)
        self.clientMessageSocket = socket(AF_INET, SOCK_STREAM)
        self.connection = True
        self.messageConnection = True
        self.packet = "user credentials request"
        self.authenticated = False
        self.messaging_enabled = False
    
    """
    Recieve messages
    """
    def message_reciever(self):
        self.clientMessageSocket.connect(self.serverMessagesAddress)
        while self.messageConnection:
            packet = self.clientMessageSocket.recv(1024)
            if "cloee" in packet.decode():
                break
            receivedpacket = packet.decode()
            print(receivedpacket)

    """
    Create a connection from the client to the server.
    """
    def start(self):

        self.clientSocket.connect(self.serverAddress)
        # Handle commands
        while self.connection:
            # Handle messages concurrently for live messaging
            if not self.authenticated:
                self.clientSocket.sendall(self.packet.encode())
                # receive response from the server
                # 1024 is a suggested packet size, you can specify it as 2048 or others
                packet = self.clientSocket.recv(1024)
                receivedpacket = packet.decode()
                self.packetHandler(receivedpacket)
            else:
                if not self.messaging_enabled:
                    self.t2 = Thread(target = self.message_reciever, daemon = True)
                    self.t2.start()
                    self.messaging_enabled = True
                command = input("===== Enter any valid commands =====\n")
                self.command_handler(command)

    """
    Handles commands made from user
    """
    def command_handler(self, command):
        if "message" in command:
            self.send_message(command)
        elif "broadcast" in command:
            self.broadcast(command)
        elif "whoelse" == command:
            self.whoelse(command)
        elif "whoelsesince" in command:
            self.whoelsesince(command)
        elif "logout" == command:
            self.logout(command)
        elif "block" in command:
            self.block(command)
        elif "startprivate" in command:
            self.startPrivate(command)
        else:
            print("Unknown Command")

    def startPrivate(self, command):
        self.clientSocket.sendall(command.encode())
    
    """
    Block users.
    """
    def block(self, command):
        self.clientSocket.sendall(command.encode())
    
    """
    Logout user.
    """
    def logout(self, command):
        # End session
        self.clientSocket.sendall(command.encode())
        sys.exit(0)

    """
    Get active members since past time
    """
    def whoelsesince(self, command):
        self.clientSocket.sendall(command.encode())

    """
    Send message to broadcast
    """
    def broadcast(self, command):
        self.clientSocket.sendall(command.encode())
    
    """
    Find everyone else online
    """
    def whoelse(self, command):
        self.clientSocket.sendall(command.encode())

    """
    Send messages
    """
    def send_message(self, command):
        command_split = command.split(' ')
        user = command_split[1]
        message = " ".join(command_split[2:])
        json_packet = {
            "sender": self.username,
            "recipient": user,
            "message": message
        }
        json_str = json.dumps(json_packet)
        self.clientMessageSocket.sendall(json_str.encode())

    """
    Handles packets from server.
    """
    def packetHandler(self, receivedpacket):
        # Break down packets
        packets = receivedpacket.split('-')
        received_function = packets[0]
        if (len(packets) > 1):
            packet_flag = packets[1].lstrip()
        else:
            packet_flag = None
        # Process them
        if received_function == "":
            print("[recv] packet from server is empty!")
        elif "timeout" in receivedpacket:
            print(packet_flag)
            self.close()
        elif "user credentials request" in received_function:
            if packet_flag != None:
                print(packet_flag)
            if packet_flag == "Login Successful":
                self.packet = ""
                self.authenticated = True
                print("Welcome to the greatest messaging application ever!")
            else:
                self.login()
        
    """
    Trigger login prompt
    """
    def login(self):
        credentials = {}
        self.username = input("Username: ")
        self.password = input("Password: ")
        credentials['username'] = self.username
        credentials['password'] = self.password
        self.packet = json.dumps(credentials)

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
    if len(sys.argv) != 2:
        print("\n===== Error usage, python3 TCPClient3.py SERVER_IP SERVER_PORT ======\n");
        exit(0)
    serverPort = int(sys.argv[1])
    client = Client(serverPort)
    client.start()
