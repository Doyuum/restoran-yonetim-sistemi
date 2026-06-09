"""
Restoran Yönetim Sistemi — Başlatıcı
======================================
Çalıştır:  python main.py

Tek CMD penceresi: sunucu bilgisi + QR kod birlikte gösterilir.
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("chcp 65001 >nul 2>&1")
    os.system("mode con: cols=70 lines=50")


def kapat_dugmesini_bloke_et():
    try:
        import ctypes
        hwnd  = ctypes.windll.kernel32.GetConsoleWindow()
        hmenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        ctypes.windll.user32.DeleteMenu(hmenu, 0xF060, 0x00000000)
    except Exception:
        pass


def yerel_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def local_hostname_url(port: int) -> str:
    """Bilgisayar adından .local mDNS adresi üret."""
    try:
        ad = socket.gethostname()
        return f"http://{ad}.local:{port}"
    except Exception:
        return ""


def wifi_adi() -> str:
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
    from web_sunucu import sunucu_baslat
    t = threading.Thread(target=sunucu_baslat, args=(port,), daemon=True)
    t.start()


_cf_proc = None  # Global referans — GC'den korusun

def cloudflare_tunnel_baslat(port: int = 5000) -> str:
    """
    cloudflared quick-tunnel başlatır, public URL'yi döndürür.
    cloudflared.exe restoran klasöründe veya masaüstünde olmalı.
    """
    global _cf_proc
    import subprocess, re, os
    from pathlib import Path

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

        # URL'yi yakala (60 sn timeout)
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

        # Stdout'u arka planda boşalt — pipe dolmasın, cloudflared çökmesin
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
    time.sleep(0.8)

    ip        = yerel_ip()
    url       = f"http://{ip}:{WEB_PORT}"
    kolay_url = local_hostname_url(WEB_PORT)

    # Cloudflare Tunnel arka planda başlat
    cf_url = ""
    def _cf_baslat():
        nonlocal cf_url
        print("  Cloudflare Tunnel bağlanıyor...")
        cf_url = cloudflare_tunnel_baslat(WEB_PORT)
        ssid = wifi_adi()
        ekrani_goster(url, ssid, kolay_url, cf_url)

    threading.Thread(target=_cf_baslat, daemon=True).start()

    # İlk ekran (tunnel henüz hazır değil)
    ssid = wifi_adi()
    ekrani_goster(url, ssid, kolay_url, cf_url)

    # Arka planda her 30 saniyede ekranı tazele (WiFi adı değişebilir)
    def _yenile():
        while True:
            time.sleep(30)
            yeni_ssid = wifi_adi()
            ekrani_goster(url, yeni_ssid, kolay_url, cf_url)

    threading.Thread(target=_yenile, daemon=True).start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n  Sistem kapatildi.")


def github_otoguncelle():
    """Her 1 dakikada bir değişiklik varsa GitHub'a push atar."""
    klasor = Path(__file__).parent
    while True:
        time.sleep(60)
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=klasor, capture_output=True, text=True
            )
            if result.stdout.strip():
                subprocess.run(["git", "add", "-A"], cwd=klasor, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Otomatik guncelleme"],
                    cwd=klasor, capture_output=True
                )
                subprocess.run(["git", "push"], cwd=klasor, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    t = threading.Thread(target=github_otoguncelle, daemon=True)
    t.start()
    main()
