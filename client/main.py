import sys
import json
import socket
import threading
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from game_logic import SHIPS, BOARD_SIZE, EMPTY, SHIP, MISS, HIT

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QCursor

from ui.start_screen_ui import Ui_StartScreen
from ui.waiting_screen_ui import Ui_WaitingScreen
from ui.placement_screen_ui import Ui_PlacementScreen
from ui.battle_screen_ui import Ui_BattleScreen
from ui.end_screen_ui import Ui_EndScreen

SHIP_LIST = list(SHIPS.items())

RENK_BOSLUK  = "#0f2c42"
RENK_GEMI    = "#4a90d9"
RENK_ISABET  = "#e74c3c"
RENK_ISKA    = "#7f8c8d"
RENK_HOVER   = "#f39c12"
RENK_YAZI    = "#ecf0f1"


# Sunucudan gelen mesajları Qt arayüzüne iletmek için sinyal sınıfı
class SinyalKoprusu(QObject):
    mesaj_geldi = pyqtSignal(dict)
    baglanti_kesildi = pyqtSignal()


# Tahta üzerindeki her bir kare
class Kare(QPushButton):
    def __init__(self, satir, sutun):
        super().__init__()
        self.satir = satir
        self.sutun = sutun
        self.tiklanabilir = False
        self.durum = EMPTY
        self.setFixedSize(42, 42)
        self.stili_guncelle()

    def durumu_degistir(self, yeni_durum):
        self.durum = yeni_durum
        self.stili_guncelle()

    def tiklanabilir_yap(self, aktif):
        self.tiklanabilir = aktif
        self.setCursor(QCursor(Qt.PointingHandCursor) if aktif else QCursor(Qt.ArrowCursor))
        self.stili_guncelle()

    def stili_guncelle(self):
        renkler = {EMPTY: RENK_BOSLUK, SHIP: RENK_GEMI, MISS: RENK_ISKA, HIT: RENK_ISABET}
        yazilar = {EMPTY: "", SHIP: "", MISS: "•", HIT: "✕"}
        arkaplan = renkler.get(self.durum, RENK_BOSLUK)
        hover = RENK_HOVER if self.tiklanabilir else arkaplan
        self.setText(yazilar.get(self.durum, ""))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {arkaplan};
                border: 1px solid #1e3a52;
                border-radius: 3px;
                color: white;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)


# 10x10 tahta widget'ı
class Tahta(QWidget):
    kare_tiklandi = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.kareler = {}
        ana_layout = QVBoxLayout(self)
        ana_layout.setSpacing(2)

        harf_satiri = QHBoxLayout()
        harf_satiri.addSpacing(26)
        for s in range(BOARD_SIZE):
            harf = QLabel(chr(65 + s))
            harf.setFixedWidth(42)
            harf.setAlignment(Qt.AlignCenter)
            harf.setStyleSheet(f"color: {RENK_YAZI}; font-size: 11px;")
            harf_satiri.addWidget(harf)
        ana_layout.addLayout(harf_satiri)

        for r in range(BOARD_SIZE):
            satir_layout = QHBoxLayout()
            satir_layout.setSpacing(2)
            numara = QLabel(str(r + 1))
            numara.setFixedWidth(24)
            numara.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            numara.setStyleSheet(f"color: {RENK_YAZI}; font-size: 11px;")
            satir_layout.addWidget(numara)
            for s in range(BOARD_SIZE):
                kare = Kare(r, s)
                kare.clicked.connect(lambda _, row=r, col=s: self._kare_tiklandi(row, col))
                self.kareler[(r, s)] = kare
                satir_layout.addWidget(kare)
            ana_layout.addLayout(satir_layout)

    def _kare_tiklandi(self, r, s):
        if self.kareler[(r, s)].tiklanabilir:
            self.kare_tiklandi.emit(r, s)

    def tahtayi_guncelle(self, izgara):
        for r in range(BOARD_SIZE):
            for s in range(BOARD_SIZE):
                self.kareler[(r, s)].durumu_degistir(izgara[r][s])

    def tiklanabilir_yap(self, aktif):
        for kare in self.kareler.values():
            kare.tiklanabilir_yap(aktif)
class BaslangicEkrani(QWidget):
    baglan_sinyali = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.ui = Ui_StartScreen()
        self.ui.setupUi(self)
        self.ui.connectBtn.clicked.connect(self.baglan)

    def baglan(self):
        ip = self.ui.ipInput.text().strip()
        try:
            port = int(self.ui.portInput.text().strip())
        except ValueError:
            self.ui.statusLabel.setText("Geçersiz port!")
            return
        self.ui.connectBtn.setEnabled(False)
        self.ui.statusLabel.setText("Bağlanılıyor...")
        self.baglan_sinyali.emit(ip, port)

    def hata_goster(self, mesaj):
        self.ui.statusLabel.setText(mesaj)
        self.ui.connectBtn.setEnabled(True)


class BeklemEkrani(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_WaitingScreen()
        self.ui.setupUi(self)

    def mesaj_guncelle(self, mesaj):
        self.ui.waitLabel.setText(mesaj)


class OyunSonuEkrani(QWidget):
    tekrar_oyna = pyqtSignal()
    cikis = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_EndScreen()
        self.ui.setupUi(self)
        self.ui.playAgainBtn.clicked.connect(self.tekrar_oyna.emit)
        self.ui.quitBtn.clicked.connect(self.cikis.emit)

    def sonucu_goster(self, kazandi_mi):
        if kazandi_mi:
            self.ui.resultLabel.setText("🏆 KAZANDIN!")
            self.ui.resultLabel.setStyleSheet("color: #f1c40f; font-size: 42px; font-weight: bold;")
            self.ui.subLabel.setText("Tebrikler! Tüm rakip gemilerini batırdın.")
        else:
            self.ui.resultLabel.setText("💀 KAYBETTİN!")
            self.ui.resultLabel.setStyleSheet("color: #e74c3c; font-size: 42px; font-weight: bold;")
            self.ui.subLabel.setText("Tüm gemilerin battı. Tekrar dene!")
class YerlestirmeEkrani(QWidget):
    gemi_yerlestirildi = pyqtSignal(int, int, int, bool)
    onaylandi = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_PlacementScreen()
        self.ui.setupUi(self)
        self.siradaki_gemi = 0
        self.yatay = True

        # Tahta widget'ını UI'daki boş alana yerleştir
        self.tahta = Tahta()
        layout = QVBoxLayout(self.ui.boardWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tahta)

        self.tahta.tiklanabilir_yap(True)
        self.tahta.kare_tiklandi.connect(self.kare_secildi)

        self.ui.directionBtn.clicked.connect(self.yonu_degistir)
        self.ui.confirmBtn.clicked.connect(self.onaylandi.emit)

        self.gemi_etiketleri = [
            self.ui.ship1Label, self.ui.ship2Label, self.ui.ship3Label,
            self.ui.ship4Label, self.ui.ship5Label
        ]
        self.bilgiyi_guncelle()

    def bilgiyi_guncelle(self):
        if self.siradaki_gemi < len(SHIP_LIST):
            isim, uzunluk = SHIP_LIST[self.siradaki_gemi]
            yon = "Yatay" if self.yatay else "Dikey"
            self.ui.infoLabel.setText(f"Yerleştir: {isim} ({uzunluk}) | Yön: {yon}")
        else:
            self.ui.infoLabel.setText("Tüm gemiler yerleştirildi! Onaylayın.")

    def yonu_degistir(self):
        self.yatay = not self.yatay
        self.ui.directionBtn.setText("↔ Yatay" if self.yatay else "↕ Dikey")
        self.bilgiyi_guncelle()

    def kare_secildi(self, satir, sutun):
        if self.siradaki_gemi >= len(SHIP_LIST):
            return
        _, uzunluk = SHIP_LIST[self.siradaki_gemi]
        self.gemi_yerlestirildi.emit(satir, sutun, uzunluk, self.yatay)

    def yerlesme_sonucu(self, basarili, tahta_durumu):
        if basarili:
            etiket = self.gemi_etiketleri[self.siradaki_gemi]
            stil = etiket.styleSheet() + " text-decoration: line-through;"
            etiket.setStyleSheet(stil)
            self.siradaki_gemi += 1
            if self.siradaki_gemi >= len(SHIP_LIST):
                self.ui.confirmBtn.setEnabled(True)
                self.tahta.tiklanabilir_yap(False)
        self.tahta.tahtayi_guncelle(tahta_durumu)
        self.bilgiyi_guncelle()

    def durum_goster(self, mesaj):
        self.ui.statusLabel.setText(mesaj)

    def sifirla(self):
        self.siradaki_gemi = 0
        self.yatay = True
        self.ui.directionBtn.setText("↔ Yatay")
        self.ui.confirmBtn.setEnabled(False)
        self.tahta.tiklanabilir_yap(True)
        for r in range(BOARD_SIZE):
            for s in range(BOARD_SIZE):
                self.tahta.kareler[(r, s)].durumu_degistir(EMPTY)
        self.ui.statusLabel.setText("")
        self.bilgiyi_guncelle()


class SavasEkrani(QWidget):
    atis_yapildi = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.ui = Ui_BattleScreen()
        self.ui.setupUi(self)
        self.benim_siram = False
        self.isabet = 0
        self.iska = 0
        self.batan_gemi = 0

        # Kendi tahtam
        self.kendi_tahtam = Tahta()
        layout1 = QVBoxLayout(self.ui.myBoardWidget)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.addWidget(self.kendi_tahtam)

        # Rakip tahtası
        self.rakip_tahtasi = Tahta()
        layout2 = QVBoxLayout(self.ui.oppBoardWidget)
        layout2.setContentsMargins(0, 0, 0, 0)
        layout2.addWidget(self.rakip_tahtasi)

        self.rakip_tahtasi.kare_tiklandi.connect(self.atis_yap)

    def atis_yap(self, satir, sutun):
        if self.benim_siram:
            self.atis_yapildi.emit(satir, sutun)

    def guncelle(self, kendi_tahta, rakip_tahta, siradaki, oyuncu_id):
        self.kendi_tahtam.tahtayi_guncelle(kendi_tahta)
        self.rakip_tahtasi.tahtayi_guncelle(rakip_tahta)
        self.benim_siram = (siradaki == oyuncu_id)
        self.rakip_tahtasi.tiklanabilir_yap(self.benim_siram)

        if self.benim_siram:
            self.ui.statusLabel.setText("🎯 Senin sıran! Rakip tahtasına tıkla.")
            self.ui.statusLabel.setStyleSheet("color: #2ecc71; font-size: 13px; font-weight: bold;")
        else:
            self.ui.statusLabel.setText("⏳ Rakibin hamlesini bekle...")
            self.ui.statusLabel.setStyleSheet("color: #e74c3c; font-size: 13px; font-weight: bold;")

    def istatistik_guncelle(self, sonuc):
        if sonuc in ("hit", "sunk", "win"):
            self.isabet += 1
            self.ui.hitsValue.setText(str(self.isabet))
        elif sonuc == "miss":
            self.iska += 1
            self.ui.missesValue.setText(str(self.iska))
        if sonuc in ("sunk", "win"):
            self.batan_gemi += 1
            self.ui.sunkValue.setText(f"{self.batan_gemi}/5")

    def sifirla_istatistik(self):
        self.isabet = self.iska = self.batan_gemi = 0
        self.ui.hitsValue.setText("0")
        self.ui.missesValue.setText("0")
        self.ui.sunkValue.setText("0/5")

    def bilgi_goster(self, mesaj):
        self.ui.infoLabel.setText(mesaj)

class AnaEkran(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Amiral Battı")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet("background-color: #0d1b2a;")

        self.oyuncu_id = None
        self.soket = None
        self.sinyaller = SinyalKoprusu()
        self.sinyaller.mesaj_geldi.connect(self.mesaji_isle)
        self.sinyaller.baglanti_kesildi.connect(self.baglanti_koptu)

        self.yigin = QStackedWidget()
        self.setCentralWidget(self.yigin)

        self.baslangic = BaslangicEkrani()
        self.bekleme = BeklemEkrani()
        self.yerlestirme = YerlestirmeEkrani()
        self.savas = SavasEkrani()
        self.oyun_sonu = OyunSonuEkrani()

        self.yigin.addWidget(self.baslangic)    # 0
        self.yigin.addWidget(self.bekleme)      # 1
        self.yigin.addWidget(self.yerlestirme)  # 2
        self.yigin.addWidget(self.savas)        # 3
        self.yigin.addWidget(self.oyun_sonu)    # 4

        self.baslangic.baglan_sinyali.connect(self.sunucuya_baglan)
        self.yerlestirme.gemi_yerlestirildi.connect(self.gemi_yerlestime_gonder)
        self.yerlestirme.onaylandi.connect(self.onay_gonder)
        self.savas.atis_yapildi.connect(self.atis_gonder)
        self.oyun_sonu.tekrar_oyna.connect(self.tekrar_oyna)
        self.oyun_sonu.cikis.connect(self.close)

        self.ekran_goster(0)

    def ekran_goster(self, index):
        self.yigin.setCurrentIndex(index)

    def sunucuya_baglan(self, ip, port):
        try:
            self.soket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.soket.connect((ip, port))
            threading.Thread(target=self.veri_al, daemon=True).start()
            self.bekleme.mesaj_guncelle("Bağlandı! Rakip bekleniyor...")
            self.ekran_goster(1)
        except Exception as hata:
            self.baslangic.hata_goster(f"Bağlantı hatası: {hata}")

    def veri_al(self):
        tampon = b""
        try:
            while True:
                veri = self.soket.recv(4096)
                if not veri:
                    break
                tampon += veri
                while b"\n" in tampon:
                    satir, tampon = tampon.split(b"\n", 1)
                    mesaj = json.loads(satir.decode("utf-8"))
                    self.sinyaller.mesaj_geldi.emit(mesaj)
        except Exception:
            pass
        self.sinyaller.baglanti_kesildi.emit()

    def mesaj_gonder(self, veri):
        try:
            metin = json.dumps(veri, ensure_ascii=False) + "\n"
            self.soket.sendall(metin.encode("utf-8"))
        except Exception as hata:
            print(f"Gönderme hatası: {hata}")

    def mesaji_isle(self, mesaj):
        tur = mesaj.get("type")

        if tur == "welcome":
            self.oyuncu_id = mesaj["player_id"]
            self.bekleme.mesaj_guncelle(f"Oyuncu {self.oyuncu_id + 1} olarak bağlandınız.\nRakip bekleniyor...")

        elif tur == "start_placement":
            self.yerlestirme.sifirla()
            QTimer.singleShot(100, lambda: self.ekran_goster(2))

        elif tur == "place_result":
            self.yerlestirme.yerlesme_sonucu(mesaj["success"], mesaj["my_board"])
            if mesaj["success"]:
                self.yerlestirme.durum_goster("✔ Gemi yerleştirildi!")
            else:
                self.yerlestirme.durum_goster("❌ Geçersiz konum! Tekrar dene.")

        elif tur == "confirm_result":
            if mesaj["success"]:
                self.yerlestirme.durum_goster("✔ Onaylandı. Rakip bekleniyor...")
                self.yerlestirme.ui.confirmBtn.setEnabled(False)
            else:
                self.yerlestirme.durum_goster(f"❌ {mesaj.get('message', 'Hata')}")

        elif tur == "opponent_ready":
            self.yerlestirme.durum_goster("Rakip hazır! Sen de onayla.")

        elif tur == "battle_start":
            self.savas.guncelle(
                mesaj["my_board"], mesaj["opponent_board"],
                mesaj["current_turn"], self.oyuncu_id
            )
            self.ekran_goster(3)

        elif tur == "shoot_result":
            sonuclar = {
                "miss": "Iskalama! 💨",
                "hit": "İSABET! 🎯",
                "sunk": "GEMİ BATTIRILDI! 🔥",
                "win": "OYUN BİTTİ!"
            }
            kim = "Sen" if mesaj["shooter"] == self.oyuncu_id else "Rakip"
            self.savas.bilgi_goster(f"{kim}: {sonuclar.get(mesaj['result'], '')}")
            if mesaj["shooter"] == self.oyuncu_id:
                self.savas.istatistik_guncelle(mesaj["result"])
            self.savas.guncelle(
                mesaj["my_board"], mesaj["opponent_board"],
                mesaj["current_turn"], self.oyuncu_id
            )
            if mesaj["result"] == "win":
                kazandi = (mesaj["winner"] == self.oyuncu_id)
                self.oyun_sonu.sonucu_goster(kazandi)
                QTimer.singleShot(1000, lambda: self.ekran_goster(4))

        elif tur == "shoot_error":
            self.savas.bilgi_goster(f"Hata: {mesaj['reason']}")

        elif tur == "opponent_wants_rematch":
            self.oyun_sonu.ui.subLabel.setText("Rakip tekrar oynamak istiyor, bekliyor...")

        elif tur == "opponent_disconnected":
            QMessageBox.warning(self, "Bağlantı Kesildi", "Rakip bağlantıyı kesti!")
            self.ekran_goster(0)

    def baglanti_koptu(self):
        QMessageBox.critical(self, "Hata", "Sunucu bağlantısı kesildi!")
        self.ekran_goster(0)

    def gemi_yerlestime_gonder(self, satir, sutun, uzunluk, yatay):
        self.mesaj_gonder({"type": "place_ship", "row": satir, "col": sutun,
                           "length": uzunluk, "horizontal": yatay})

    def onay_gonder(self):
        self.mesaj_gonder({"type": "confirm_placement"})

    def atis_gonder(self, satir, sutun):
        self.mesaj_gonder({"type": "shoot", "row": satir, "col": sutun})

    def tekrar_oyna(self):
        self.savas.sifirla_istatistik()
        self.mesaj_gonder({"type": "play_again"})
        self.bekleme.mesaj_guncelle("Yeni oyun başlatılıyor...")
        self.ekran_goster(1)


if __name__ == "__main__":
    uygulama = QApplication(sys.argv)
    uygulama.setApplicationName("Amiral Battı")
    pencere = AnaEkran()
    pencere.show()
    sys.exit(uygulama.exec_())