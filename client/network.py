import socket

class NetworkClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_id = None
        self.buffer = b""

    def connect(self, host, port):
        self.socket.connect((host,port))    

    def send(self, message):
        self.socket.send((message + "\n").encode())

    def recv_line(self):
        while b"\n" not in self.buffer:
            data = self.socket.recv(1024)
            if not data:
                return None
            self.buffer += data
            
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line.decode()         
    
    def disconnect(self):
        self.socket.close()