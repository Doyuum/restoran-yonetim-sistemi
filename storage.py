import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from models import Kategori, Malzeme, Masa, MasaDurumu, MenuOgesi, Siparis, SiparisDurumu, SiparisKalemi

VERI_DIZINI = os.path.join(os.path.dirname(__file__), "veri")
MENU_DOSYASI = os.path.join(VERI_DIZINI, "menu.json")
SIPARIS_DOSYASI = os.path.join(VERI_DIZINI, "siparisler.json")
MASA_DOSYASI = os.path.join(VERI_DIZINI, "masalar.json")
MALZEME_DOSYASI = os.path.join(VERI_DIZINI, "malzemeler.json")
BAKHSIS_DOSYASI  = os.path.join(VERI_DIZINI, "bakhsisler.json")
MUSTERI_MASA_DOSYASI  = os.path.join(VERI_DIZINI, "musteri_masalar.json")
REZERVASYON_DOSYASI   = os.path.join(VERI_DIZINI, "rezervasyonlar.json")


def _dizin_olustur():
    os.makedirs(VERI_DIZINI, exist_ok=True)


# ---------- MENU ----------

def menu_yukle() -> Dict[int, MenuOgesi]:
    _dizin_olustur()
    if not os.path.exists(MENU_DOSYASI):
        return {}
    with open(MENU_DOSYASI, "r", encoding="utf-8") as f:
        veriler = json.load(f)
    return {int(k): MenuOgesi.from_dict(v) for k, v in veriler.items()}


def menu_kaydet(menu: Dict[int, MenuOgesi]):
    _dizin_olustur()
    with open(MENU_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({str(k): v.to_dict() for k, v in menu.items()}, f, ensure_ascii=False, indent=2)


# ---------- MASALAR ----------

def masalar_yukle() -> Dict[int, Masa]:
    _dizin_olustur()
    if not os.path.exists(MASA_DOSYASI):
        return {}
    with open(MASA_DOSYASI, "r", encoding="utf-8") as f:
        veriler = json.load(f)
    return {int(k): Masa.from_dict(v) for k, v in veriler.items()}


def masalar_kaydet(masalar: Dict[int, Masa]):
    _dizin_olustur()
    with open(MASA_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({str(k): v.to_dict() for k, v in masalar.items()}, f, ensure_ascii=False, indent=2)


# ---------- SİPARİŞLER ----------

def siparisler_yukle(menu: Dict[int, MenuOgesi]) -> Dict[int, Siparis]:
    _dizin_olustur()
    if not os.path.exists(SIPARIS_DOSYASI):
        return {}
    with open(SIPARIS_DOSYASI, "r", encoding="utf-8") as f:
        veriler = json.load(f)

    siparisler = {}
    for k, v in veriler.items():
        kalemler = []
        for kalim in v.get("kalemler", []):
            ogesi_id = kalim["menu_ogesi_id"]
            if ogesi_id in menu:
                kalemler.append(SiparisKalemi(
                    menu_ogesi=menu[ogesi_id],
                    miktar=kalim["miktar"],
                    not_=kalim.get("not_", ""),
                ))
            else:
                # Menüden silinmiş ama geçmiş siparişte var; geçici nesne oluştur
                gecici = MenuOgesi(
                    id=ogesi_id,
                    ad=kalim.get("menu_ogesi_ad", "Bilinmiyor"),
                    kategori=Kategori.DIGER,
                    fiyat=kalim.get("fiyat", 0.0),
                )
                kalemler.append(SiparisKalemi(
                    menu_ogesi=gecici,
                    miktar=kalim["miktar"],
                    not_=kalim.get("not_", ""),
                ))

        siparisler[int(k)] = Siparis(
            id=v["id"],
            masa_no=v.get("masa_no"),
            kalemler=kalemler,
            durum=SiparisDurumu(v["durum"]),
            olusturma_zamani=datetime.fromisoformat(v["olusturma_zamani"]),
            notlar=v.get("notlar", ""),
        )
    return siparisler


def siparisler_kaydet(siparisler: Dict[int, Siparis]):
    _dizin_olustur()
    with open(SIPARIS_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({str(k): v.to_dict() for k, v in siparisler.items()}, f, ensure_ascii=False, indent=2)


# ---------- MALZEMELER ----------

def malzeme_yukle() -> Dict[int, "Malzeme"]:
    _dizin_olustur()
    if not os.path.exists(MALZEME_DOSYASI):
        return {}
    with open(MALZEME_DOSYASI, "r", encoding="utf-8") as f:
        veriler = json.load(f)
    return {int(k): Malzeme.from_dict(v) for k, v in veriler.items()}


def malzeme_kaydet(malzemeler: Dict[int, "Malzeme"]):
    _dizin_olustur()
    with open(MALZEME_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({str(k): v.to_dict() for k, v in malzemeler.items()}, f, ensure_ascii=False, indent=2)


# ---------- BAHŞİŞLER ----------

def bakhsis_listesi_yukle() -> list:
    _dizin_olustur()
    if not os.path.exists(BAKHSIS_DOSYASI):
        return []
    with open(BAKHSIS_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)


def rezervasyon_listesi_yukle() -> list:
    _dizin_olustur()
    if not os.path.exists(REZERVASYON_DOSYASI):
        return []
    try:
        return json.loads(open(REZERVASYON_DOSYASI, encoding="utf-8").read())
    except Exception:
        return []


def rezervasyon_kaydet(liste: list):
    _dizin_olustur()
    with open(REZERVASYON_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)


def rezervasyon_ekle(musteri: str, tarih: str, saat: str, kisi: int, masa_no: int, telefon: str = "", not_: str = "") -> dict:
    liste = rezervasyon_listesi_yukle()
    yeni_id = max((r["id"] for r in liste), default=0) + 1
    kayit = {
        "id": yeni_id,
        "musteri": musteri,
        "telefon": telefon,
        "tarih": tarih,
        "saat": saat,
        "kisi": kisi,
        "masa_no": masa_no,
        "not_": not_,
        "durum": "Onaylandı",
        "olusturma": __import__("datetime").datetime.now().isoformat(),
    }
    liste.append(kayit)
    rezervasyon_kaydet(liste)
    return kayit


def musteri_masa_kaydet(kullanici: str, masa_no: int, siparis_listesi: list):
    """Müşterinin masa ve sipariş bilgisini kalıcı olarak sakla."""
    _dizin_olustur()
    try:
        veri = json.loads(open(MUSTERI_MASA_DOSYASI, encoding="utf-8").read()) if os.path.exists(MUSTERI_MASA_DOSYASI) else {}
    except Exception:
        veri = {}
    veri[kullanici] = {"masa_no": masa_no, "siparislerim": siparis_listesi}
    with open(MUSTERI_MASA_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def musteri_masa_yukle(kullanici: str):
    """Müşterinin kayıtlı masa/sipariş bilgisini döndür. Yoksa None."""
    if not os.path.exists(MUSTERI_MASA_DOSYASI):
        return None
    try:
        veri = json.loads(open(MUSTERI_MASA_DOSYASI, encoding="utf-8").read())
        return veri.get(kullanici)
    except Exception:
        return None


def musteri_masa_sil(kullanici: str):
    """Müşterinin kayıtlı masa bilgisini temizle."""
    if not os.path.exists(MUSTERI_MASA_DOSYASI):
        return
    try:
        veri = json.loads(open(MUSTERI_MASA_DOSYASI, encoding="utf-8").read())
        veri.pop(kullanici, None)
        with open(MUSTERI_MASA_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def bakhsis_ekle(tutar: float, musteri: str, not_: str = ""):
    liste = bakhsis_listesi_yukle()
    from datetime import datetime
    liste.append({
        "tutar": tutar,
        "musteri": musteri,
        "not_": not_,
        "zaman": datetime.now().isoformat(),
    })
    _dizin_olustur()
    with open(BAKHSIS_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
