"""
QR Ekranı — Ayrı CMD penceresinde sürekli gösterir.
"""
import os
import sys
import time
import socket
import threading
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    os.system("chcp 65001 >nul 2>&1")
    os.system("mode con: cols=60 lines=40")
    try:
        import ctypes
        hwnd  = ctypes.windll.kernel32.GetConsoleWindow()
        hmenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        ctypes.windll.user32.DeleteMenu(hmenu, 0xF060, 0x00000000)
    except Exception:
        pass

WEB_PORT  = 5000
PID_DOSYA = Path(__file__).parent / "veri" / "qr_pid.txt"


def yerel_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def wifi_adi() -> str:
    """Bağlı WiFi ağ adını (SSID) döndürür."""
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


def qr_goster(url: str):
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
        pass


def _ana_izle(ana_pid: int):
    """Ana personel terminali kapanırsa bu pencereyi de kapat."""
    def _kontrol():
        while True:
            time.sleep(2)
            try:
                import psutil
                if not psutil.pid_exists(ana_pid):
                    PID_DOSYA.unlink(missing_ok=True)
                    os._exit(0)
            except Exception:
                break
    threading.Thread(target=_kontrol, daemon=True).start()


def main():
    # Kendi PID'ini dosyaya yaz
    PID_DOSYA.parent.mkdir(exist_ok=True)
    PID_DOSYA.write_text(str(os.getpid()))

    # Komut satırından ana PID al
    if len(sys.argv) > 1:
        try:
            _ana_izle(int(sys.argv[1]))
        except ValueError:
            pass

    ip  = yerel_ip()
    url = f"http://{ip}:{WEB_PORT}"
    ssid = wifi_adi()

    try:
        while True:
            os.system("cls")
            print("═" * 50)
            print("  📱  QR SİPARİŞ SİSTEMİ")
            print("═" * 50)
            print(f"\n  📶 WiFi Ağı :  {ssid}")
            print(f"  🌐 Adres    :  {url}")
            print(f"\n  Telefonunuzu  \"{ssid}\"  ağına bağlayın")
            print(f"  ve aşağıdaki QR kodu okutun:\n")
            qr_goster(url)
            print(f"\n  ➜  {url}")
            print(f"\n  Veya tarayıcıya yukarıdaki adresi yazın.")
            print("\n" + "═" * 50)
            print("  [Bu pencereyi kapatmayın]")
            print("═" * 50)
            ssid = wifi_adi()   # Her döngüde güncelle
            time.sleep(30)
    finally:
        PID_DOSYA.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
