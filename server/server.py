"""sunucu "beyin " görevi görür. istemcilerden gelen istekleri alır, işler ve yanıt verir.
    oyun mantığını yönetir: kim kazanır, kim kaybeder, hangi hamleler geçerli, vb."""

#TODO: send() broadcast(), gemi verileri geçerli mi?, rakibin tüm gemileri battı mı?, her oyuncu için ayrı thread, gelen mesajı işle, start()

import socket
import threading

HOST = '0.0.0.0' # Tüm ağ arayüzlerinde dinle
PORT = 5555 # İstemcilerin bağlanacağı port numarası

GRID_SIZE = 10 # Oyun alanının boyutu (10x10)
SHIPS = [5, 4, 3, 3, 2] # Amiral Battı standart gemi boyutları

class BattleshipServer:
    def __init__(self):
        self.clients = [] # Bağlı istemcilerin listesi
        self.grids = [None, None] #her oyuncunun gemi koordinatları (ilk başta gemiler yerleşmediği için none)
        self.shots = [{}, {}] #her oyuncunun attığı atışları tutar
        self.ships_placed = [False, False] #her oyuncunun gemilerini yerleştirip yerleştirmediği bilgisi
        self.current_turn = 0 #0 veya 1, hangi oyuncunun sırası olduğunu
        self.game_started = False #iki oyuncu da hazır mı
        self.lock = threading.Lock() #iki thread aynı anda shared resource'a erişmesin diye lock
