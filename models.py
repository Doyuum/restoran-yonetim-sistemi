# models.py — Veri modelleri (sınıf tanımları)
# Bu dosya veritabanı yerine kullandığımız Python nesnelerini tanımlar.
# Enum: sabit seçenekler için (durumlar, kategoriler)
# dataclass: veri tutan basit sınıflar için Python'un kısayolu

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# Enum kullandık çünkü kategori değerlerinin sabit ve hatalı girilmez olmasını istedik.
# Örneğin "Ana Yemek" yerine "ana yemek" yazılmasını engeller.
class Kategori(Enum):
    BASLANGIC = "Başlangıç"
    ANA_YEMEK = "Ana Yemek"
    TATLI     = "Tatlı"
    ICECEK    = "İçecek"
    SALATA    = "Salata"
    PIZZA     = "Pizza"
    DIGER     = "Diğer"


# Siparişin geçtiği 7 aşama — durum makinesi (state machine) mantığı
# Müşteri → Mutfak → Garson → Kasa sırası bu enum ile takip edilir
class SiparisDurumu(Enum):
    BEKLIYOR      = "Bekliyor"       # Mutfak henüz görmedi
    HAZIRLANIYOR  = "Hazırlanıyor"   # Mutfak hazırlıyor
    HAZIR         = "Hazır"          # Mutfak hazırladı, garson alacak
    GARSON_ALDI   = "Garson Aldı"    # Garson mutfaktan aldı
    SERVIS_EDILDI = "Servis Edildi"  # Masaya bırakıldı
    ODENDI        = "Ödendi"         # Kasa ödemeyi aldı
    IPTAL         = "İptal"          # İptal edildi


# Masanın 3 olası durumu
class MasaDurumu(Enum):
    BOS     = "Boş"      # Müşteri yok, oturulabilir
    DOLU    = "Dolu"     # Aktif sipariş var
    REZERVE = "Rezerve"  # Önceden ayrılmış, müşteri seçemez


# @dataclass: __init__, __repr__ gibi metodları otomatik oluşturur
# Manuel yazmak yerine sadece alanları tanımlarız
@dataclass
class MenuOgesi:
    id: int
    ad: str
    kategori: Kategori
    fiyat: float                   # KDV HARİÇ taban fiyat
    aciklama: str = ""
    mevcut: bool = True
    stok: int = -1                 # -1 = sınırsız, 0 = tükendi, >0 = sayılı stok
    indirim_yuzdesi: float = 0.0   # 0 = indirim yok, 50.0 = %50 indirim

    # @property: fonksiyon gibi çalışır ama parantez koymadan erişilir (urun.efektif_fiyat)
    @property
    def efektif_fiyat(self) -> float:
        """İndirim varsa düşülmüş KDV HARİÇ fiyatı döndürür."""
        if self.indirim_yuzdesi > 0:
            return self.fiyat * (1 - self.indirim_yuzdesi / 100)
        return self.fiyat

    @property
    def kdv_dahil_fiyat(self) -> float:
        """Müşteriye gösterilen fiyat: indirimli + %10 KDV eklenmiş."""
        return self.efektif_fiyat * 1.10

    @property
    def kdv_dahil_taban(self) -> float:
        """Kampanya gösteriminde üzeri çizili gösterilen orijinal fiyat."""
        return self.fiyat * 1.10

    @property
    def stok_durumu(self) -> str:
        if self.stok == -1:
            return ""           # Sınırsız stok, gösterilmez
        if self.stok == 0:
            return "Tükendi"
        return "Yeterli stok yok"

    @property
    def siparis_verilebilir(self) -> bool:
        """Hem mevcut hem de stokta var mı?"""
        return self.mevcut and self.stok != 0

    # to_dict / from_dict: Python nesnesini JSON'a çevirip geri okumak için
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ad": self.ad,
            "kategori": self.kategori.value,
            "fiyat": self.fiyat,
            "aciklama": self.aciklama,
            "mevcut": self.mevcut,
            "stok": self.stok,
            "indirim_yuzdesi": self.indirim_yuzdesi,
        }

    @staticmethod
    def from_dict(data: dict) -> "MenuOgesi":
        """JSON'dan okunan sözlüğü MenuOgesi nesnesine çevirir."""
        return MenuOgesi(
            id=data["id"],
            ad=data["ad"],
            kategori=Kategori(data["kategori"]),
            fiyat=data["fiyat"],
            aciklama=data.get("aciklama", ""),
            mevcut=data.get("mevcut", True),
            stok=data.get("stok", -1),
            indirim_yuzdesi=data.get("indirim_yuzdesi", 0.0),
        )


@dataclass
class SiparisKalemi:
    """Siparişin tek bir satırı: hangi ürün, kaç tane, özel not var mı."""
    menu_ogesi: MenuOgesi
    miktar: int
    not_: str = ""

    @property
    def toplam(self) -> float:
        """Bu kalemin KDV hariç toplam tutarı (indirim uygulanmış)."""
        return self.menu_ogesi.efektif_fiyat * self.miktar

    def to_dict(self) -> dict:
        return {
            "menu_ogesi_id":  self.menu_ogesi.id,
            "menu_ogesi_ad":  self.menu_ogesi.ad,
            "fiyat":          self.menu_ogesi.efektif_fiyat,
            "miktar":         self.miktar,
            "not_":           self.not_,
        }


@dataclass
class Siparis:
    """Tek bir masanın siparişi. Birden fazla SiparisKalemi barındırır."""
    id: int
    masa_no: Optional[int]
    kalemler: List[SiparisKalemi] = field(default_factory=list)  # Boş liste ile başlar
    durum: SiparisDurumu = SiparisDurumu.BEKLIYOR
    olusturma_zamani: datetime = field(default_factory=datetime.now)
    notlar: str = ""

    @property
    def ara_toplam(self) -> float:
        """Tüm kalemlerin KDV hariç toplamı."""
        return sum(k.toplam for k in self.kalemler)

    @property
    def kdv(self) -> float:
        """Ara toplamın %10'u."""
        return self.ara_toplam * 0.10

    @property
    def genel_toplam(self) -> float:
        """Müşteriye yansıtılan KDV dahil toplam tutar."""
        return self.ara_toplam + self.kdv

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "masa_no":          self.masa_no,
            "kalemler":         [k.to_dict() for k in self.kalemler],
            "durum":            self.durum.value,
            "olusturma_zamani": self.olusturma_zamani.isoformat(),
            "notlar":           self.notlar,
        }


@dataclass
class Malzeme:
    """Mutfak malzemesi: adı, ne kadar kaldığı ve birimi (gram/litre vb.)."""
    id: int
    ad: str
    miktar: float
    birim: str = "g"

    @property
    def miktar_str(self) -> str:
        """1000g üzeriyse kg olarak gösterir (okunması kolay)."""
        if self.birim == "g" and self.miktar >= 1000:
            return f"{self.miktar / 1000:.2f} kg"
        return f"{self.miktar:.0f} {self.birim}"

    def to_dict(self) -> dict:
        return {"id": self.id, "ad": self.ad, "miktar": self.miktar, "birim": self.birim}

    @staticmethod
    def from_dict(data: dict) -> "Malzeme":
        return Malzeme(
            id=data["id"],
            ad=data["ad"],
            miktar=data["miktar"],
            birim=data.get("birim", "g"),
        )


@dataclass
class Masa:
    """Restoran masası: numarası, kapasitesi ve şu anki durumu."""
    no: int
    kapasite: int
    durum: MasaDurumu = MasaDurumu.BOS
    aktif_siparis_id: Optional[int] = None  # Hangi sipariş bu masaya bağlı

    def to_dict(self) -> dict:
        return {
            "no":               self.no,
            "kapasite":         self.kapasite,
            "durum":            self.durum.value,
            "aktif_siparis_id": self.aktif_siparis_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "Masa":
        return Masa(
            no=data["no"],
            kapasite=data["kapasite"],
            durum=MasaDurumu(data["durum"]),
            aktif_siparis_id=data.get("aktif_siparis_id"),
        )
