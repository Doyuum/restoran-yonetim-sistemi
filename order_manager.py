from datetime import datetime
from typing import Dict, List, Optional, Tuple

import storage
from models import (
    Masa, MasaDurumu, MenuOgesi, Siparis, SiparisDurumu, SiparisKalemi
)
from menu_manager import MenuYoneticisi


class SiparisYoneticisi:
    def __init__(self, menu: Dict[int, MenuOgesi], menu_yoneticisi=None, malzeme_yoneticisi=None):
        self.menu = menu
        self.my = menu_yoneticisi
        self.maly = malzeme_yoneticisi
        self.siparisler: Dict[int, Siparis] = storage.siparisler_yukle(menu)
        self.masalar: Dict[int, Masa] = storage.masalar_yukle()
        self._sonraki_id = self._gunluk_sonraki_id()
        self._son_gun = datetime.now().date()
        if not self.masalar:
            self._varsayilan_masalar_olustur()

    def _gunluk_sonraki_id(self) -> int:
        """Bugüne ait siparişlerin max ID'si + 1. Bugün sipariş yoksa 1."""
        bugun = datetime.now().date()
        bugunun_idleri = [
            s.id for s in self.siparisler.values()
            if s.olusturma_zamani.date() == bugun
        ]
        return max(bugunun_idleri, default=0) + 1

    def _varsayilan_masalar_olustur(self):
        kapasiteler = [2, 2, 4, 4, 4, 6, 6, 8]
        for i, kap in enumerate(kapasiteler, start=1):
            self.masalar[i] = Masa(no=i, kapasite=kap)
        storage.masalar_kaydet(self.masalar)

    def _kaydet(self):
        storage.siparisler_kaydet(self.siparisler)
        storage.masalar_kaydet(self.masalar)

    # ---------- SİPARİŞ OLUŞTURMA ----------

    def siparis_olustur(self, masa_no: Optional[int] = None, notlar: str = "", ek_siparis: bool = False) -> Tuple[Optional[Siparis], str]:
        # Gün değiştiyse sayacı sıfırla
        bugun = datetime.now().date()
        if bugun != self._son_gun:
            self._sonraki_id = 1
            self._son_gun = bugun

        if masa_no is not None:
            if masa_no not in self.masalar:
                return None, f"Masa {masa_no} bulunamadı."
            masa = self.masalar[masa_no]
            if masa.durum == MasaDurumu.DOLU and not ek_siparis:
                return None, f"Masa {masa_no} zaten dolu (Sipariş #{masa.aktif_siparis_id})."

        siparis = Siparis(
            id=self._sonraki_id,
            masa_no=masa_no,
            notlar=notlar,
        )
        self.siparisler[self._sonraki_id] = siparis
        self._sonraki_id += 1

        if masa_no is not None:
            self.masalar[masa_no].durum = MasaDurumu.DOLU
            self.masalar[masa_no].aktif_siparis_id = siparis.id

        self._kaydet()
        return siparis, "Sipariş oluşturuldu."

    # ---------- KALEM EKLEME / ÇIKARMA ----------

    def kalem_ekle(self, siparis_id: int, menu_id: int, miktar: int = 1, not_: str = "") -> Tuple[bool, str]:
        if siparis_id not in self.siparisler:
            return False, "Sipariş bulunamadı."
        siparis = self.siparisler[siparis_id]
        if siparis.durum in (SiparisDurumu.ODENDI, SiparisDurumu.IPTAL):
            return False, f"Kapalı siparişe ({siparis.durum.value}) kalem eklenemez."
        if menu_id not in self.menu:
            return False, "Menü kalemi bulunamadı."
        oge = self.menu[menu_id]
        if not oge.siparis_verilebilir:
            return False, f"'{oge.ad}' şu an mevcut değil veya tükendi."

        # Stok yeterli mi?
        if oge.stok != -1 and oge.stok < miktar:
            return False, f"'{oge.ad}' için yeterli stok yok."

        # Aynı ürün varsa miktarı artır
        for kalem in siparis.kalemler:
            if kalem.menu_ogesi.id == menu_id:
                if oge.stok != -1 and oge.stok < miktar:
                    return False, f"'{oge.ad}' için yeterli stok yok."
                kalem.miktar += miktar
                if self.my:
                    self.my.stok_guncelle(menu_id, -miktar)
                self._kaydet()
                return True, f"'{oge.ad}' miktarı güncellendi (x{kalem.miktar})."

        # Malzeme kontrolü (çorbalar için)
        if self.maly:
            ok, msg = self.maly.tarif_uygula(oge.ad, miktar)
            if not ok:
                return False, msg

        siparis.kalemler.append(SiparisKalemi(menu_ogesi=oge, miktar=miktar, not_=not_))
        if self.my:
            self.my.stok_guncelle(menu_id, -miktar)
        self._kaydet()
        return True, f"'{oge.ad}' siparişe eklendi."

    def kalem_cikar(self, siparis_id: int, menu_id: int, miktar: int = 1) -> Tuple[bool, str]:
        if siparis_id not in self.siparisler:
            return False, "Sipariş bulunamadı."
        siparis = self.siparisler[siparis_id]
        for i, kalem in enumerate(siparis.kalemler):
            if kalem.menu_ogesi.id == menu_id:
                if kalem.miktar <= miktar:
                    siparis.kalemler.pop(i)
                    # Stoku iade et
                    if self.my:
                        self.my.stok_guncelle(menu_id, kalem.miktar)
                    # Malzemeyi iade et
                    if self.maly:
                        self.maly.tarif_iade(kalem.menu_ogesi.ad, kalem.miktar)
                    self._kaydet()
                    return True, f"'{kalem.menu_ogesi.ad}' siparişten çıkarıldı."
                kalem.miktar -= miktar
                self._kaydet()
                return True, f"'{kalem.menu_ogesi.ad}' miktarı güncellendi (x{kalem.miktar})."
        return False, "Kalem siparişte bulunamadı."

    # ---------- DURUM GÜNCELLEME ----------

    def durum_guncelle(self, siparis_id: int, yeni_durum: SiparisDurumu) -> Tuple[bool, str]:
        if siparis_id not in self.siparisler:
            return False, "Sipariş bulunamadı."
        siparis = self.siparisler[siparis_id]
        eski_durum = siparis.durum
        siparis.durum = yeni_durum

        # Sipariş kapandıysa masayı boşalt — ama başka aktif sipariş varsa boşaltma
        if yeni_durum in (SiparisDurumu.ODENDI, SiparisDurumu.IPTAL) and siparis.masa_no:
            masa_no = siparis.masa_no
            if masa_no in self.masalar:
                kapali = {SiparisDurumu.ODENDI, SiparisDurumu.IPTAL}
                aktif_var = any(
                    s.masa_no == masa_no and s.id != siparis_id and s.durum not in kapali
                    for s in self.siparisler.values()
                )
                if aktif_var:
                    # Başka aktif sipariş var, masayı boşaltma
                    pass
                else:
                    self.masalar[masa_no].durum = MasaDurumu.BOS
                    self.masalar[masa_no].aktif_siparis_id = None

        self._kaydet()
        return True, f"Durum: {eski_durum.value} → {yeni_durum.value}"

    # ---------- YENİLE ----------

    def yenile(self):
        """JSON dosyalarından taze veri yükler (QR web siparişleri için)."""
        self.siparisler = storage.siparisler_yukle(self.menu)
        self.masalar    = storage.masalar_yukle()
        mevcut_max = max(self.siparisler.keys(), default=0) + 1
        if mevcut_max > self._sonraki_id:
            self._sonraki_id = mevcut_max

    # ---------- SORGULAR ----------

    def aktif_siparisler(self) -> List[Siparis]:
        kapali = {SiparisDurumu.ODENDI, SiparisDurumu.IPTAL}
        return [s for s in self.siparisler.values() if s.durum not in kapali]

    def masa_siparisi(self, masa_no: int) -> Optional[Siparis]:
        masa = self.masalar.get(masa_no)
        if masa and masa.aktif_siparis_id:
            return self.siparisler.get(masa.aktif_siparis_id)
        return None

    def siparis_bul(self, siparis_id: int) -> Optional[Siparis]:
        return self.siparisler.get(siparis_id)

    # ---------- RAPORLAMA ----------

    def gunluk_ozet(self, tarih: Optional[datetime] = None) -> dict:
        hedef = (tarih or datetime.now()).date()
        gun_siparisler = [
            s for s in self.siparisler.values()
            if s.olusturma_zamani.date() == hedef and s.durum == SiparisDurumu.ODENDI
        ]
        toplam_ciro = sum(s.genel_toplam for s in gun_siparisler)

        urun_sayac: Dict[str, int] = {}
        for s in gun_siparisler:
            for k in s.kalemler:
                urun_sayac[k.menu_ogesi.ad] = urun_sayac.get(k.menu_ogesi.ad, 0) + k.miktar

        en_populer = sorted(urun_sayac.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "tarih": hedef.strftime("%d.%m.%Y"),
            "siparis_sayisi": len(gun_siparisler),
            "toplam_ciro": toplam_ciro,
            "en_populer": en_populer,
        }
