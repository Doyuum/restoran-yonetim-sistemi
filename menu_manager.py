from typing import Dict, List, Optional

import storage
from models import Kategori, MenuOgesi


class MenuYoneticisi:
    def __init__(self):
        self.menu: Dict[int, MenuOgesi] = storage.menu_yukle()
        self._sonraki_id = max(self.menu.keys(), default=0) + 1

    def _kaydet(self):
        storage.menu_kaydet(self.menu)

    def oge_ekle(self, ad: str, kategori: Kategori, fiyat: float, aciklama: str = "", stok: int = -1, indirim_yuzdesi: float = 0.0) -> MenuOgesi:
        oge = MenuOgesi(
            id=self._sonraki_id,
            ad=ad,
            kategori=kategori,
            fiyat=fiyat,
            stok=stok,
            aciklama=aciklama,
            indirim_yuzdesi=indirim_yuzdesi,
        )
        self.menu[self._sonraki_id] = oge
        self._sonraki_id += 1
        self._kaydet()
        return oge

    def stok_guncelle(self, oge_id: int, miktar: int) -> bool:
        """Stoğu artırır (+ değer) veya azaltır (- değer).
        Stok 0 olunca ürün menüden gizlenir.
        Stok tekrar girilince ürün menüye geri döner."""
        if oge_id not in self.menu:
            return False
        oge = self.menu[oge_id]
        if oge.stok == -1:
            return True   # sınırsız stok, işlem yapma
        yeni_stok = max(0, oge.stok + miktar)
        oge.stok = yeni_stok
        self._kaydet()
        return True

    def oge_guncelle(
        self,
        oge_id: int,
        ad: Optional[str] = None,
        kategori: Optional[Kategori] = None,
        fiyat: Optional[float] = None,
        aciklama: Optional[str] = None,
        mevcut: Optional[bool] = None,
        stok: Optional[int] = None,
        indirim_yuzdesi: Optional[float] = None,
    ) -> bool:
        if oge_id not in self.menu:
            return False
        oge = self.menu[oge_id]
        if ad is not None:
            oge.ad = ad
        if kategori is not None:
            oge.kategori = kategori
        if fiyat is not None:
            oge.fiyat = fiyat
        if aciklama is not None:
            oge.aciklama = aciklama
        if mevcut is not None:
            oge.mevcut = mevcut
        if stok is not None:
            oge.stok = stok
            if stok == 0:
                oge.mevcut = False
            elif stok > 0:
                oge.mevcut = True
        if indirim_yuzdesi is not None:
            oge.indirim_yuzdesi = max(0.0, min(100.0, indirim_yuzdesi))
        self._kaydet()
        return True

    def oge_sil(self, oge_id: int) -> bool:
        if oge_id not in self.menu:
            return False
        del self.menu[oge_id]
        self._kaydet()
        return True

    def kategoriye_gore_listele(self, kategori: Optional[Kategori] = None) -> List[MenuOgesi]:
        ogeler = list(self.menu.values())
        if kategori:
            ogeler = [o for o in ogeler if o.kategori == kategori]
        return sorted(ogeler, key=lambda o: (o.kategori.value, o.ad))

    def mevcutlari_listele(self) -> List[MenuOgesi]:
        return [o for o in self.menu.values() if o.mevcut]

    def oge_bul(self, oge_id: int) -> Optional[MenuOgesi]:
        return self.menu.get(oge_id)

    def ara(self, arama: str) -> List[MenuOgesi]:
        arama = arama.lower()
        return [o for o in self.menu.values() if arama in o.ad.lower() or arama in o.aciklama.lower()]

    # (ad, kategori, fiyat, açıklama, stok)
    VARSAYILAN_ORNEKLER = [
        ("Mercimek Çorbası", Kategori.BASLANGIC, 140.0, "Geleneksel kırmızı mercimek çorbası", 30),
        ("Domates Çorbası",  Kategori.BASLANGIC, 140.0, "Taze domates ile hazırlanır",          25),
        ("Mevsim Salatası",  Kategori.SALATA,    175.0, "Taze mevsim sebzeleri",                20),
        ("Çoban Salatası",   Kategori.SALATA,    190.0, "Domates, salatalık, biber",            20),
        ("Izgara Köfte",     Kategori.ANA_YEMEK, 520.0, "El yapımı dana köfte, pilav ve salata ile", 18),
        ("Tavuk Şiş",        Kategori.ANA_YEMEK, 480.0, "Marine edilmiş tavuk, lavaş ile",     18),
        ("Karışık Pizza",    Kategori.PIZZA,     580.0, "Sucuk, mantar, biber, mısır",          12),
        ("Margarita Pizza",  Kategori.PIZZA,     500.0, "Domates sosu, mozzarella",             12),
        ("Künefe",           Kategori.TATLI,     320.0, "Antep fıstıklı, kaymak ile",           15),
        ("Sütlaç",           Kategori.TATLI,     200.0, "Fırın sütlaç",                         20),
        ("Ayran",            Kategori.ICECEK,     75.0, "Ev yapımı ayran",                      50),
        ("Türk Çayı",        Kategori.ICECEK,     50.0, "Demlik çay",                          100),
        ("Kola",             Kategori.ICECEK,    110.0, "330ml",                                40),
        ("Su",               Kategori.ICECEK,     45.0, "500ml",                                60),
    ]

    def varsayilan_menu_yukle(self):
        """Sistem ilk kurulduğunda örnek menü verileri oluşturur."""
        if self.menu:
            return
        for ad, kat, fiyat, aciklama, stok in self.VARSAYILAN_ORNEKLER:
            self.oge_ekle(ad, kat, fiyat, aciklama, stok=stok)

    def varsayilan_stoklari_uygula(self):
        """Mevcut menüdeki ürünleri isim eşleşmesiyle varsayılan stoklara günceller."""
        stok_tablosu = {ad: stok for ad, _, _, _, stok in self.VARSAYILAN_ORNEKLER}
        for oge in self.menu.values():
            if oge.ad in stok_tablosu:
                oge.stok = stok_tablosu[oge.ad]
                oge.mevcut = oge.stok > 0
        self._kaydet()
