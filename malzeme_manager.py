# malzeme_manager.py — Mutfak malzeme stok takibi
# Sipariş verildiğinde hangi malzemeden ne kadar kullanılacağını bilir
# ve stoktan otomatik düşer. İptal olursa malzemeleri iade eder.

from typing import Dict, List, Optional, Tuple

import storage
from models import Malzeme


class MalzemeYoneticisi:

    # Tarifler: hangi yemek hangi malzemeden kaç gram kullanır
    # Bu sözlük sayesinde sipariş gelince otomatik stok düşürülür
    TARIFLER: Dict[str, Dict[str, float]] = {
        # Başlangıçlar
        "Mercimek Çorbası": {
            "Kırmızı Mercimek": 80,
            "Tereyağı":         15,
            "Un":               10,
            "Salça":            20,
            "Pul Biber":         2,
        },
        "Domates Çorbası": {
            "Domates":  150,
            "Tereyağı":  15,
            "Un":        10,
            "Krema":     30,
        },
        # Ana Yemekler
        "Izgara Köfte": {
            "Dana Kıyma": 200,
            "Soğan":       50,
        },
        "Tavuk Şiş": {
            "Tavuk Göğsü": 250,
            "Sarımsak":     10,
        },
        # Pizza
        "Karışık Pizza": {
            "Pizza Hamuru": 300,
            "Sucuk":         80,
            "Mantar":        60,
            "Biber":         40,
            "Mısır":         30,
        },
        "Margarita Pizza": {
            "Pizza Hamuru":  300,
            "Domates Sosu":   80,
            "Mozzarella":    120,
        },
        # Salatalar
        "Mevsim Salatası": {
            "Marul":      100,
            "Domates":     80,
            "Salatalık":   60,
        },
        "Çoban Salatası": {
            "Domates":    100,
            "Salatalık":   80,
            "Biber":       50,
        },
        # Tatlılar
        "Künefe": {
            "Kadayıf":      150,
            "Peynir":       100,
            "Antep Fıstığı": 30,
        },
        "Sütlaç": {
            "Süt":    250,
            "Pirinç":  40,
            "Şeker":   30,
        },
    }

    # Malzemeleri kategorilere ayırdık — yönetim ekranında gruplanmış göstermek için
    KATEGORILER = {
        "Et & Tavuk":       ["Dana Kıyma", "Tavuk Göğsü", "Sucuk"],
        "Sebzeler":         ["Domates", "Soğan", "Sarımsak", "Biber", "Salatalık", "Marul", "Mantar", "Mısır"],
        "Süt Ürünleri":     ["Tereyağı", "Krema", "Peynir", "Mozzarella", "Süt"],
        "Bakliyat & Tahıl": ["Kırmızı Mercimek", "Un", "Pizza Hamuru", "Pirinç", "Kadayıf"],
        "Baharat & Sos":    ["Salça", "Pul Biber", "Domates Sosu", "Şeker"],
        "Kuruyemiş":        ["Antep Fıstığı"],
    }

    # İlk kurulumda stok yoksa bu değerlerle başlatılır (gram cinsinden)
    VARSAYILAN_MALZEMELER = [
        ("Dana Kıyma",       3600, "g"),
        ("Tavuk Göğsü",      4500, "g"),
        ("Sucuk",             960, "g"),
        ("Domates",          4000, "g"),
        ("Soğan",            1000, "g"),
        ("Sarımsak",          200, "g"),
        ("Biber",             960, "g"),
        ("Salatalık",        1600, "g"),
        ("Marul",            2000, "g"),
        ("Mantar",            720, "g"),
        ("Mısır",             360, "g"),
        ("Tereyağı",         1500, "g"),
        ("Krema",             800, "g"),
        ("Peynir",           1500, "g"),
        ("Mozzarella",       1440, "g"),
        ("Süt",              5000, "g"),
        ("Kırmızı Mercimek", 2500, "g"),
        ("Un",                800, "g"),
        ("Pizza Hamuru",     3600, "g"),
        ("Pirinç",            800, "g"),
        ("Kadayıf",          2250, "g"),
        ("Salça",             650, "g"),
        ("Pul Biber",         120, "g"),
        ("Domates Sosu",      960, "g"),
        ("Şeker",             600, "g"),
        ("Antep Fıstığı",     450, "g"),
    ]

    def __init__(self):
        # Başlangıçta malzemeleri dosyadan yükle
        self.malzemeler: Dict[int, Malzeme] = storage.malzeme_yukle()
        self._sonraki_id = max(self.malzemeler.keys(), default=0) + 1
        # Dosya boşsa varsayılan malzemeleri ekle
        if not self.malzemeler:
            self._varsayilan_yukle()

    def _kaydet(self):
        """Bellekteki malzemeleri JSON dosyasına yazar."""
        storage.malzeme_kaydet(self.malzemeler)

    def _varsayilan_yukle(self):
        """İlk çalıştırmada stok sıfırsa varsayılan malzemeleri ekler."""
        for ad, miktar, birim in self.VARSAYILAN_MALZEMELER:
            self._ekle(ad, miktar, birim)

    def _ekle(self, ad: str, miktar: float, birim: str = "g") -> Malzeme:
        m = Malzeme(id=self._sonraki_id, ad=ad, miktar=miktar, birim=birim)
        self.malzemeler[self._sonraki_id] = m
        self._sonraki_id += 1
        self._kaydet()
        return m

    def stok_guncelle(self, malzeme_id: int, miktar: float) -> bool:
        """Mevcut stoka miktar ekler (negatif değer verilirse düşer)."""
        if malzeme_id not in self.malzemeler:
            return False
        # max(0) ile stok hiçbir zaman eksi olmaz
        self.malzemeler[malzeme_id].miktar = max(0.0, self.malzemeler[malzeme_id].miktar + miktar)
        self._kaydet()
        return True

    def stok_set(self, malzeme_id: int, yeni_miktar: float) -> bool:
        """Stoku doğrudan belirli bir değere ayarlar."""
        if malzeme_id not in self.malzemeler:
            return False
        self.malzemeler[malzeme_id].miktar = max(0.0, yeni_miktar)
        self._kaydet()
        return True

    def malzeme_bul_ad(self, ad: str) -> Optional[Malzeme]:
        """İsme göre malzeme nesnesini bulur. Bulamazsa None döner."""
        for m in self.malzemeler.values():
            if m.ad == ad:
                return m
        return None

    def tarif_uygula(self, menu_oge_ad: str, porsiyon: int = 1) -> Tuple[bool, str]:
        """
        Sipariş onaylanınca çağrılır.
        1. Önce tüm malzemelerin yeterliliğini kontrol eder (yetersizse False döner)
        2. Kontrol geçilirse malzemeleri stoktan düşer
        Tarifi olmayan ürünler için hiçbir şey yapmaz (True döner).
        """
        if menu_oge_ad not in self.TARIFLER:
            return True, ""  # Tarif yoksa sorun yok, geç

        tarif = self.TARIFLER[menu_oge_ad]

        # Önce kontrol et — eksik malzeme varsa düşme yapma
        for malzeme_ad, gram in tarif.items():
            m = self.malzeme_bul_ad(malzeme_ad)
            if m and m.miktar < gram * porsiyon:
                return False, f"Malzeme yetersiz: {malzeme_ad} (gereken: {gram * porsiyon}g, mevcut: {m.miktar:.0f}g)"

        # Kontrol geçildi, malzemeleri düş
        for malzeme_ad, gram in tarif.items():
            m = self.malzeme_bul_ad(malzeme_ad)
            if m:
                m.miktar = max(0.0, m.miktar - gram * porsiyon)
        self._kaydet()
        return True, ""

    def tarif_iade(self, menu_oge_ad: str, porsiyon: int = 1):
        """
        Sipariş iptal edilince çağrılır.
        Düşülen malzemeleri stoka geri ekler.
        """
        if menu_oge_ad not in self.TARIFLER:
            return
        tarif = self.TARIFLER[menu_oge_ad]
        for malzeme_ad, gram in tarif.items():
            m = self.malzeme_bul_ad(malzeme_ad)
            if m:
                m.miktar += gram * porsiyon
        self._kaydet()

    def yapilabilir_mi(self, menu_oge_ad: str, porsiyon: int = 1) -> bool:
        """
        Menüde göstermeden önce kontrol: bu yemeği yapacak malzeme var mı?
        Tarifi olmayan ürünler için True döner (sınırsız sayılır).
        """
        if menu_oge_ad not in self.TARIFLER:
            return True
        for malzeme_ad, gram in self.TARIFLER[menu_oge_ad].items():
            m = self.malzeme_bul_ad(malzeme_ad)
            if m and m.miktar < gram * porsiyon:
                return False
        return True

    def listele(self) -> List[Malzeme]:
        """Tüm malzemeleri alfabetik sırayla döndürür."""
        return sorted(self.malzemeler.values(), key=lambda m: m.ad)
