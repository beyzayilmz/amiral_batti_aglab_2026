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
import time

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
        self.game_state = game_logic.GameState()

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_PLAYERS)
        print(f"Server {HOST}:{PORT} üzerinde dinleniyor.")

        while True: #client bağlanırsa kabul edecek
            client_socket, address = server_socket.accept()
            print(f"Yeni bağlantı: {address}")

            if len(self.clients) >=  MAX_PLAYERS:
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
            #pass düzeltme: cpu yorar sleep ile beklicez
            time.sleep(1)
        with self.lock:
            if not self.game_started and len(self.clients) == MAX_PLAYERS:
                self.game_started = True
                self.broadcast("GAME_START") #oyun başladı mesajı gönder

        while True:
            try:
                message = client_socket.recv(1024).decode()
                if not message:
                    break
                self.process_msg(player_id, message) 
            except: 
                break
            print(f"Oyuncu {player_id} bağlantısı kesildi.")
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()                            

    def broadcast(self, message):
        for client in self.clients:
            client.send(message.encode())  

    def send_private_msg(self, player_id, message):    
        target_socket = self.clients[player_id]
        target_socket.send(message.encode())    

    def process_msg(self, player_id, message):
        parts = message.strip().split(":")
        command = parts[0]
        if command == "SHOT":
            row, col = int(parts[1]), int(parts[2])
            result = self.game_state.shoot(player_id, row, col)
            self.send_private_msg(player_id, f"SHOT_RESULT:{result}")

            opponent_id = 1 - player_id
            self.send_private_msg(opponent_id, f"OPPONENT_SHOT:{row}:{col}:{result}")

            if self.game_state.phase == "gameover":
                self.broadcast(f"GAME_OVER:Player {player_id} wins!")
                self.send_private_msg(player_id, "YOU_WIN")
                self.send_private_msg(opponent_id, "YOU_LOSE")

        elif command == "PLACE":
            row, col, length = int(parts[1]), int(parts[2]), int(parts[3])   
            horizontal = parts[4] == "H"
            result = self.game_state.place_ship(player_id, row, col, length, horizontal)
            if result:
                self.send_private_msg(player_id, "PLACE_SUCCESS")
            else:
                self.send_private_msg(player_id, "PLACE_FAIL")
                
        elif command == "READY":
            result = self.game_state.confirm_placement(player_id)
            if result:
                self.send_private_msg(player_id, "READY_SUCCESS")
                if self.game_state.phase == "battle":
                    self.broadcast("BATTLE_START")        

if __name__ == "__main__":
    server = BattleshipServer()
    server.start()

    '''#mesaj gönderme fonksiyonu
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
                return None       '''     
                 
