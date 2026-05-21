from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class Kategori(Enum):
    BASLANGIC = "Başlangıç"
    ANA_YEMEK = "Ana Yemek"
    TATLI = "Tatlı"
    ICECEK = "İçecek"
    SALATA = "Salata"
    PIZZA = "Pizza"
    DIGER = "Diğer"


class SiparisDurumu(Enum):
    BEKLIYOR      = "Bekliyor"
    HAZIRLANIYOR  = "Hazırlanıyor"
    HAZIR         = "Hazır"
    GARSON_ALDI   = "Garson Aldı"
    SERVIS_EDILDI = "Servis Edildi"
    ODENDI        = "Ödendi"
    IPTAL         = "İptal"


class MasaDurumu(Enum):
    BOS    = "Boş"
    DOLU   = "Dolu"
    REZERVE = "Rezerve"


@dataclass
class MenuOgesi:
    id: int
    ad: str
    kategori: Kategori
    fiyat: float                  # KDV HARİÇ taban fiyat
    aciklama: str = ""
    mevcut: bool = True
    stok: int = -1                # -1 = sınırsız, 0+ = sayılı
    indirim_yuzdesi: float = 0.0  # 0 = indirim yok, 50 = %50 indirim

    # ── Fiyat hesapları ──────────────────────────────────────────

    @property
    def efektif_fiyat(self) -> float:
        """İndirim uygulanmış KDV HARİÇ fiyat."""
        if self.indirim_yuzdesi > 0:
            return self.fiyat * (1 - self.indirim_yuzdesi / 100)
        return self.fiyat

    @property
    def kdv_dahil_fiyat(self) -> float:
        """İndirimli + KDV DAHİL fiyat (müşteriye gösterilen)."""
        return self.efektif_fiyat * 1.10

    @property
    def kdv_dahil_taban(self) -> float:
        """İndirimsiz KDV DAHİL fiyat (kampanya gösterimi için)."""
        return self.fiyat * 1.10

    # ── Stok / durum ────────────────────────────────────────────

    @property
    def stok_durumu(self) -> str:
        if self.stok == -1:
            return ""
        if self.stok == 0:
            return "Tükendi"
        return "Yeterli stok yok"

    @property
    def siparis_verilebilir(self) -> bool:
        return self.mevcut and self.stok != 0

    # ── Serileştirme ─────────────────────────────────────────────

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
    menu_ogesi: MenuOgesi
    miktar: int
    not_: str = ""

    @property
    def toplam(self) -> float:
        """İndirim uygulanmış KDV HARİÇ toplam."""
        return self.menu_ogesi.efektif_fiyat * self.miktar

    def to_dict(self) -> dict:
        return {
            "menu_ogesi_id": self.menu_ogesi.id,
            "menu_ogesi_ad": self.menu_ogesi.ad,
            "fiyat": self.menu_ogesi.efektif_fiyat,
            "miktar": self.miktar,
            "not_": self.not_,
        }


@dataclass
class Siparis:
    id: int
    masa_no: Optional[int]
    kalemler: List[SiparisKalemi] = field(default_factory=list)
    durum: SiparisDurumu = SiparisDurumu.BEKLIYOR
    olusturma_zamani: datetime = field(default_factory=datetime.now)
    notlar: str = ""

    @property
    def ara_toplam(self) -> float:
        return sum(k.toplam for k in self.kalemler)

    @property
    def kdv(self) -> float:
        return self.ara_toplam * 0.10

    @property
    def genel_toplam(self) -> float:
        return self.ara_toplam + self.kdv

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "masa_no": self.masa_no,
            "kalemler": [k.to_dict() for k in self.kalemler],
            "durum": self.durum.value,
            "olusturma_zamani": self.olusturma_zamani.isoformat(),
            "notlar": self.notlar,
        }


@dataclass
class Malzeme:
    id: int
    ad: str
    miktar: float
    birim: str = "g"

    @property
    def miktar_str(self) -> str:
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
    no: int
    kapasite: int
    durum: MasaDurumu = MasaDurumu.BOS
    aktif_siparis_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "no": self.no,
            "kapasite": self.kapasite,
            "durum": self.durum.value,
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
