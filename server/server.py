"""sunucu "beyin " görevi görür. istemcilerden gelen istekleri alır, işler ve yanıt verir.
    oyun mantığını yönetir: kim kazanır, kim kaybeder, hangi hamleler geçerli, vb."""

#TODO: send() broadcast(), gemi verileri geçerli mi?, rakibin tüm gemileri battı mı?, her oyuncu için ayrı thread, gelen mesajı işle, start()

import socket
import threading
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import game_logic

HOST = '0.0.0.0' # Tüm ağ arayüzlerinde dinle
PORT = 5555 # İstemcilerin bağlanacağı port numarası
MAX_PLAYERS = 2

class BattleshipServer:
    def __init__(self):
        self.clients = [] # Bağlı istemcilerin listesi
        self.current_turn = 0 #0 veya 1, hangi oyuncunun sırası olduğunu
        self.game_started = False #iki oyuncu da hazır mı
        self.lock = threading.Lock() #iki thread aynı anda shared resource'a erişmesin diye lock
        self.players = {}

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_PLAYERS)
        print(f"Server {HOST}:{PORT} üzerinde dinleniyor.")

        while True: #client bağlanırsa kabul edecek
            client_socket, address = server_socket.accept()
            print(f"Yeni bağlantı: {address}")

            if len(self.clients) <= MAX_PLAYERS:
                client_socket.send("FULL\n".encode()) #clienta oyun dolu mesajı gönder
                client_socket.close()
                continue

            self.clients.append(client_socket)
            player_id = len(self.clients) - 1
            print(f"Oyuncu {player_id} bağlandı.")

            thread = threading.Thread(target = self.handle_client, args = (client_socket, player_id))
            thread.daemon = True
            thread.start()

    def handle_client(self, client_socket, player_id):
        client_socket.send(f"Player ID: {player_id}\n".encode()) #clienta player id'si gönder
        print(f"Oyuncu {player_id} e id gönderildi")

        #iki oyuncu bağlanana kadar bekle
        while len(self.clients) < MAX_PLAYERS:
            pass


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
                 
