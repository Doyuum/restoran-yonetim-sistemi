# main.py — Sistemin başlangıç noktası
# Bu dosya çalıştırılınca her şey başlar:
# 1. Web sunucusu arka planda başlar (Flask)
# 2. Cloudflare Tunnel ile internete açılır
# 3. QR kod ekrana yazdırılır
# 4. GitHub'a otomatik push başlar

import os
import sys
import time
import socket
import threading
from pathlib import Path

# Windows'ta Türkçe karakterlerin terminalde bozulmaması için UTF-8 ayarı
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("chcp 65001 >nul 2>&1")
    os.system("mode con: cols=70 lines=50")


def kapat_dugmesini_bloke_et():
    """CMD penceresinin sağ üstündeki X butonunu devre dışı bırakır.
    Sistem yanlışlıkla kapatılmasın diye."""
    try:
        import ctypes
        hwnd  = ctypes.windll.kernel32.GetConsoleWindow()
        hmenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        ctypes.windll.user32.DeleteMenu(hmenu, 0xF060, 0x00000000)
    except Exception:
        pass


def yerel_ip() -> str:
    """Bilgisayarın yerel ağ IP adresini bulur.
    Google DNS'e (8.8.8.8) bağlanmaya çalışarak hangi ağ kartının
    kullanıldığını öğreniyoruz — gerçek bağlantı yapmıyor."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def local_hostname_url(port: int) -> str:
    """Bilgisayar adından .local mDNS adresi üretir.
    192.168.x.x yerine daha kolay okunur bir adres sağlar."""
    try:
        ad = socket.gethostname()
        return f"http://{ad}.local:{port}"
    except Exception:
        return ""


def wifi_adi() -> str:
    """Bağlı olunan WiFi ağının adını (SSID) döndürür.
    Müşterilere hangi ağa bağlanmaları gerektiğini göstermek için."""
    try:
        import subprocess
        sonuc = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            encoding="utf-8", errors="ignore"
        )
        for satir in sonuc.splitlines():
            satir = satir.strip()
            if satir.startswith("SSID") and "BSSID" not in satir:
                return satir.split(":", 1)[1].strip()
    except Exception:
        pass
    return "Tespit edilemedi"


def qr_yazdir(url: str):
    """Verilen URL için terminalde ASCII QR kod yazdırır.
    Müşteriler telefonlarıyla okutarak siteye erişir."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception:
        print("  (QR kütüphanesi yüklü değil)")


def ekrani_goster(url: str, ssid: str, kolay_url: str = "", cf_url: str = ""):
    """Terminali temizleyip sistem bilgilerini ve QR kodu gösterir."""
    os.system("cls")
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║        ANADOLU SOFRASI — SİSTEM ÇALIŞIYOR           ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print(f"  IP adresi      :  {url}")
    if kolay_url:
        print(f"  Kolay adres    :  {kolay_url}")
    if cf_url:
        print(f"  İnternet (CF)  :  {cf_url}")
    else:
        print(f"  İnternet (CF)  :  bağlanıyor...")
    print()
    print("  PERSONEL ERİŞİM ADRESLERİ:")
    yerel = kolay_url or url
    print(f"    Mutfak    →  {yerel}/personel/mutfak")
    print(f"    Kasa      →  {yerel}/personel/kasa")
    print(f"    Yonetim   →  {yerel}/personel/yonetim")
    print()
    print("  ──────────────────────────────────────────────────────")
    print()
    print(f"  📶 WiFi Ağı  :  {ssid}")
    print(f"  🌐 WiFi Adresi  :  {yerel}")
    if cf_url:
        print(f"  🌍 Mobil Veri   :  {cf_url}")
    print()
    print(f"  WiFi üzerinden QR kodu okutun:\n")
    qr_yazdir(yerel)
    if cf_url:
        print(f"\n  Mobil veri için QR:\n")
        qr_yazdir(cf_url)
    print()
    print("  ──────────────────────────────────────────────────────")
    print("  Bu pencereyi KAPATIRSANIZ sistem durur.")
    print("  ══════════════════════════════════════════════════════")


def web_sunucu_baslat(port: int = 5000):
    """Flask web sunucusunu ayrı bir thread'de başlatır.
    Thread kullanmak zorundayız çünkü Flask sonsuz döngüde çalışır —
    aynı thread'de çalıştırırsak ana program bloke olur."""
    from web_sunucu import sunucu_baslat
    t = threading.Thread(target=sunucu_baslat, args=(port,), daemon=True)
    t.start()


_cf_proc = None  # Cloudflare process referansı — program boyunca yaşasın


def cloudflare_tunnel_baslat(port: int = 5000) -> str:
    """
    Cloudflare Quick Tunnel başlatır ve public HTTPS URL'sini döndürür.
    Bu sayede sistem yerel ağ dışından (mobil veri ile) de erişilebilir.
    cloudflared.exe'nin restoran klasöründe veya masaüstünde olması gerekir.
    """
    global _cf_proc
    import subprocess, re, os
    from pathlib import Path

    # cloudflared.exe'yi olası konumlarda ara
    adaylar = [
        Path(__file__).parent / "cloudflared.exe",
        Path(os.environ.get("USERPROFILE", ""), "Desktop", "cloudflared.exe"),
        Path("cloudflared.exe"),
    ]
    cf_path = next((str(p) for p in adaylar if Path(p).exists()), None)
    if not cf_path:
        print("  cloudflared.exe bulunamadı.")
        return ""

    try:
        # cloudflared'i arka planda başlat, çıktısını okuyacağız
        _cf_proc = subprocess.Popen(
            [cf_path, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        bulunan_url = ""
        import time as _time

        # Çıktıdan trycloudflare.com URL'sini yakala (60 sn bekle)
        bitis = _time.time() + 60
        while _time.time() < bitis:
            satir = _cf_proc.stdout.readline()
            if not satir:
                _time.sleep(0.05)
                continue
            eslesme = re.search(r"https://([a-z0-9][a-z0-9\-]+[a-z0-9])\.trycloudflare\.com", satir)
            if eslesme:
                subdomain = eslesme.group(1)
                if subdomain not in ("api", "update", "assets", "www"):
                    bulunan_url = eslesme.group(0)
                    break

        # Pipe dolmasın diye stdout'u arka planda boşalt
        def _stdout_drainer():
            try:
                for _ in _cf_proc.stdout:
                    pass
            except Exception:
                pass

        threading.Thread(target=_stdout_drainer, daemon=True).start()
        return bulunan_url

    except Exception as e:
        print(f"  Cloudflare tunnel hatası: {e}")
    return ""


def kapanirken_temizle(sy):
    """Program kapanırken dolu masaları boşa çeker.
    atexit ile kayıt edilir — program kapanırken otomatik çalışır."""
    import atexit
    import storage
    from models import MasaDurumu
    def _temizle():
        for masa in sy.masalar.values():
            if masa.durum == MasaDurumu.DOLU:
                masa.durum = MasaDurumu.BOS
                masa.aktif_siparis_id = None
        storage.masalar_kaydet(sy.masalar)
    atexit.register(_temizle)


def main():
    kapat_dugmesini_bloke_et()
    print("  Sistem başlatılıyor...")

    # Tüm yönetici sınıflarını başlat
    from menu_manager import MenuYoneticisi
    from order_manager import SiparisYoneticisi
    from malzeme_manager import MalzemeYoneticisi

    my   = MenuYoneticisi()
    my.varsayilan_menu_yukle()
    my.varsayilan_stoklari_uygula()
    maly = MalzemeYoneticisi()
    sy   = SiparisYoneticisi(my.menu, my, maly)
    kapanirken_temizle(sy)

    WEB_PORT = 5000
    web_sunucu_baslat(WEB_PORT)
    time.sleep(0.8)  # Sunucunun ayağa kalkması için kısa bekleme

    ip        = yerel_ip()
    url       = f"http://{ip}:{WEB_PORT}"
    kolay_url = local_hostname_url(WEB_PORT)

    # Cloudflare Tunnel arka planda başlat — bağlanınca ekranı yenile
    cf_url = ""
    def _cf_baslat():
        nonlocal cf_url
        print("  Cloudflare Tunnel bağlanıyor...")
        cf_url = cloudflare_tunnel_baslat(WEB_PORT)
        ssid = wifi_adi()
        ekrani_goster(url, ssid, kolay_url, cf_url)

    threading.Thread(target=_cf_baslat, daemon=True).start()

    # İlk ekranı hemen göster (CF henüz hazır değil)
    ssid = wifi_adi()
    ekrani_goster(url, ssid, kolay_url, cf_url)

    # Her 30 saniyede ekranı tazele — WiFi adı veya CF URL değişebilir
    def _yenile():
        while True:
            time.sleep(30)
            yeni_ssid = wifi_adi()
            ekrani_goster(url, yeni_ssid, kolay_url, cf_url)

    threading.Thread(target=_yenile, daemon=True).start()

    try:
        while True:
            time.sleep(60)  # Ana thread canlı kalsın
    except KeyboardInterrupt:
        print("\n  Sistem kapatildi.")


def github_otoguncelle():
    """Her 1 dakikada bir git status kontrol eder.
    Değişiklik varsa otomatik olarak commit atıp GitHub'a push eder.
    Değişiklik yoksa bekler, gereksiz commit atmaz."""
    klasor = Path(__file__).parent
    while True:
        time.sleep(60)  # 1 dakika bekle
        try:
            import subprocess
            # --porcelain: değişiklik varsa çıktı verir, yoksa boş kalır
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=klasor, capture_output=True, text=True
            )
            if result.stdout.strip():  # Değişiklik var mı?
                subprocess.run(["git", "add", "-A"], cwd=klasor, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", "Otomatik guncelleme"],
                    cwd=klasor, capture_output=True
                )
                subprocess.run(["git", "push"], cwd=klasor, capture_output=True)
        except Exception:
            pass  # Hata olursa sessizce geç, sistemi çökertme


if __name__ == "__main__":
    # GitHub otogüncellemeyi daemon thread olarak başlat
    # daemon=True: ana program kapanınca bu thread de otomatik kapanır
    t = threading.Thread(target=github_otoguncelle, daemon=True)
    t.start()
    main()
