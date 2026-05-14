# ⚓ Amiral Battı — Çok Oyunculu Ağ Tabanlı Oyun

Fatih Sultan Mehmet Vakıf Üniversitesi  
Bilgisayar Ağları Dersi — 2025/2026 Bahar Dönemi  


---

## Proje Hakkında

Python ve PyQt5 kullanılarak geliştirilmiş, TCP tabanlı çok oyunculu Amiral Battı oyunudur. İki oyuncu, merkezi bir sunucu üzerinden birbirine bağlanarak 10×10'luk ızgaralarda savaş gemilerini yerleştirir ve sırayla birbirinin gemilerini batırmaya çalışır.

---

## Özellikler

- İstemci-sunucu (client-server) mimarisi
- TCP soket iletişimi, JSON mesaj protokolü
- PyQt5 ile kullanıcı dostu grafik arayüz
- Gemi yerleştirme ekranı (yatay/dikey yön seçimi)
- Gerçek zamanlı savaş ekranı (isabet/ıska gösterimi, istatistikler)
- Rakip bağlantısı koptuğunda otomatik yeniden eşleştirme
- Uygulama kapatılmadan tekrar oynama (rematch) desteği
- Birden fazla oyun çiftini aynı anda yönetebilen oda (room) tabanlı sunucu

---

## Gereksinimler

```
Python 3.8+
PyQt5
```

Kurulum:

```bash
pip install PyQt5
```

---

## Klasör Yapısı

```
amiral_batti_aglab_2026/
├── game_logic.py          # Oyun kuralları ve veri yapıları
├── server/
│   └── server.py          # Sunucu uygulaması (konsol)
├── client/
│   ├── main.py            # İstemci uygulaması ve PyQt5 arayüzü
│   ├── network.py         # TCP iletişim katmanı
│   └── ui/                # Qt Designer ekran dosyaları
│       ├── start_screen_ui.py
│       ├── waiting_screen_ui.py
│       ├── placement_screen_ui.py
│       ├── battle_screen_ui.py
│       └── end_screen_ui.py
├── requirements.txt
└── README.md
```

---

## Çalıştırma

### 1. Sunucuyu Başlat

```bash
cd server
python server.py
```

Sunucu varsayılan olarak `0.0.0.0:8888` adresini dinler.

### 2. İstemciyi Başlat (her oyuncu için ayrı terminal)

```bash
cd client
python main.py
```

Açılan ekranda sunucu IP adresini ve portu (`8888`) girerek bağlanın.  
Yerel ağda oynuyorsanız IP olarak `127.0.0.1` veya sunucunun yerel IP'sini kullanın.

---

## Oyun Akışı

1. İki oyuncu sunucuya bağlanır, otomatik eşleştirme gerçekleşir
2. Her oyuncu 5 gemisini ızgarasına yerleştirir ve onaylar
3. Her iki oyuncu hazır olduğunda savaş başlar
4. Oyuncular sırayla rakip ızgarasına tıklayarak atış yapar
5. Tüm gemileri batırılan oyuncu kaybeder
6. Oyun sonu ekranında **Tekrar Oyna** ile yeni oyun başlatılabilir

### Gemiler

| Gemi | Boyut |
|------|-------|
| Uçak Gemisi | 5 |
| Zırhlı | 4 |
| Kruvazör | 3 |
| Destroyer | 3 |
| Denizaltı | 2 |

---

## Mesaj Protokolü

Sunucu-istemci iletişimi JSON formatında, newline ile sonlandırılmış mesajlar üzerinden yürütülür.

| Mesaj Tipi | Yön | Açıklama |
|---|---|---|
| `place_ship` | İstemci → Sunucu | Gemi yerleştirme |
| `confirm_placement` | İstemci → Sunucu | Yerleştirmeyi onayla |
| `shoot` | İstemci → Sunucu | Atış koordinatı |
| `welcome` | Sunucu → İstemci | Oyuncu ID bildirimi |
| `start_placement` | Sunucu → İstemci | Yerleştirme aşaması başladı |
| `battle_start` | Sunucu → İstemci | Savaş başladı |
| `shoot_result` | Sunucu → İstemci | Atış sonucu (hit/miss/sunk/win) |
| `opponent_disconnected` | Sunucu → İstemci | Rakip bağlantısı kesildi |

---

## Notlar

- Sunucu grafik arayüz içermez, konsol uygulamasıdır.
- Okul ağında AWS bağlantısı güvenlik duvarı nedeniyle kesilebilir; yerel ağda sorunsuz çalışır.
- Sunucu kodu AWS EC2 üzerinde çalışmaya uygundur (port 8888 açık olmalıdır).
