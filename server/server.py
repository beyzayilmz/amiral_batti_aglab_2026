"""sunucu "beyin " görevi görür. istemcilerden gelen istekleri alır, işler ve yanıt verir.
    oyun mantığını yönetir: kim kazanır, kim kaybeder, hangi hamleler geçerli, vb."""

#TODO: send() broadcast(), gemi verileri geçerli mi?, rakibin tüm gemileri battı mı?, her oyuncu için ayrı thread, gelen mesajı işle, start()

import socket
import threading
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game_logic import Board, SHIP, WATER, HIT, MISS, BOARD_SIZE

HOST = '0.0.0.0' # Tüm ağ arayüzlerinde dinle
PORT = 5555 # İstemcilerin bağlanacağı port numarası

class BattleshipServer:
    def __init__(self):
        self.clients = [] # Bağlı istemcilerin listesi
        self.current_turn = 0 #0 veya 1, hangi oyuncunun sırası olduğunu
        self.game_started = False #iki oyuncu da hazır mı
        self.lock = threading.Lock() #iki thread aynı anda shared resource'a erişmesin diye lock
        self.boards = [None, None]
        self.names = [None, None]
        self.ready = [False, False] #her oyuncunun hazır olup olmadığını tutar

    #mesaj gönderme fonksiyonu
    def send(self, sock, msg:dict): #bir istemciye mesaj 
        try:
            data = json.dumps(msg) + "\n"
            sock.sendall(data.encode())
        except Exception as e:
            print(f"Error sending message: {e}")

    def broadcast(self, msg:dict, exclude_sock=None): #herkese mesaj
        for sock, _ in self.clients:
            if sock != exclude_sock:
                self.send(sock, msg)

    #istemciden gelen mesajları okuma
    def recv_line(self, sock):
        buffer = b""

        while True:
            try:
                data = sock.recv(1024)
                if not data:
                    return None
                buffer += data
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    return json.loads(line.decode())
            except Exception as e:
                print(f"Error receiving message: {e}")
                return None            
                 
