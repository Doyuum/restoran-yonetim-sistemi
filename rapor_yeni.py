import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from pypdf import PdfWriter, PdfReader

BASE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(BASE, 'raporlar', 'logo.png')
mavi = colors.HexColor('#1F4E79')

th_st = ParagraphStyle('th',  fontName='Helvetica-Bold', fontSize=9,  alignment=TA_CENTER)
td_b  = ParagraphStyle('tdb', fontName='Helvetica-Bold', fontSize=9)
td_n  = ParagraphStyle('tdn', fontName='Helvetica',      fontSize=9)
normal= ParagraphStyle('n',   fontName='Helvetica',      fontSize=10, leading=15, alignment=TA_JUSTIFY, spaceAfter=5)
bold_h= ParagraphStyle('bh',  fontName='Helvetica-Bold', fontSize=10, spaceBefore=8, spaceAfter=3)
madde = ParagraphStyle('m',   fontName='Helvetica',      fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=3, leftIndent=14)


def rapor_olustur(dosya, hafta_no, konu, bolumler):
    doc = SimpleDocTemplate(dosya, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=1.5*cm, bottomMargin=2*cm)
    story = []

    # Logo + Üniversite
    logo_img = Image(LOGO, width=5*cm, height=None)
    uni_para = Paragraph('<b><font size=18>DOĞUŞ ÜNİVERSİTESİ</font></b>',
        ParagraphStyle('uni', fontName='Helvetica-Bold', fontSize=18, alignment=TA_LEFT))
    uni_t = Table([[logo_img, uni_para]], colWidths=[5.5*cm, 11*cm])
    uni_t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    story.append(uni_t)
    story.append(Spacer(1, 0.4*cm))

    # Bilgi tablosu
    bilgi = [
        [Paragraph('MESLEK YÜKSEKOKULU\n2025 - 2026 EĞİTİM - ÖĞRETİM YILI / BAHAR DÖNEMİ', th_st), ''],
        [Paragraph('Adı / Name', td_b),          Paragraph('PYTHON PROGRAMLAMA', td_n)],
        [Paragraph('DERS Kodu / Code', td_b),     Paragraph('BLP 276', td_n)],
        [Paragraph('Sorumlusu / Lecturer', td_b), Paragraph('Öğr.Gör. İLKER DURAN', td_n)],
        [Paragraph('PROJE HAFTALIK RAPORU', th_st), ''],
    ]
    bt = Table(bilgi, colWidths=[8*cm, 8.6*cm])
    bt.setStyle(TableStyle([
        ('SPAN',(0,0),(1,0)),('SPAN',(0,4),(1,4)),
        ('BACKGROUND',(0,0),(1,0),mavi),('TEXTCOLOR',(0,0),(1,0),colors.white),
        ('BACKGROUND',(0,4),(1,4),mavi),('TEXTCOLOR',(0,4),(1,4),colors.white),
        ('BOX',(0,0),(-1,-1),0.5,colors.black),
        ('INNERGRID',(0,0),(-1,-1),0.5,colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1),(1,3),[colors.white,colors.HexColor('#F2F2F2')]),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(bt)
    story.append(Spacer(1, 0.3*cm))

    # Hafta/Konu
    hk = [
        [Paragraph('HAFTA', td_b), Paragraph(f'{hafta_no}. Hafta', td_n)],
        [Paragraph('KONU',  td_b), Paragraph(konu, td_n)],
    ]
    hkt = Table(hk, colWidths=[4*cm, 12.6*cm])
    hkt.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.5,colors.black),
        ('INNERGRID',(0,0),(-1,-1),0.5,colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(hkt)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph('<u><b>HAFTALIK YAPILAN İŞLEMLER</b></u>',
        ParagraphStyle('ust', fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.4*cm))

    for b in bolumler:
        story.append(Paragraph(b['baslik'], bold_h))
        for sat in b['icerik']:
            if sat.startswith('•'):
                story.append(Paragraph(sat, madde))
            else:
                story.append(Paragraph(sat, normal))

    story.append(Spacer(1, 1*cm))

    # İmza tablosu
    imza_data = [
        [Paragraph('<b>NUMARA</b>', th_st),
         Paragraph('<b>GRUP ÜYELERİNİN İSİMLERİ</b>', th_st),
         Paragraph('<b>İMZA</b>', th_st)],
        [Paragraph('202407124023', td_n), Paragraph('Ege Recep Alembeyli', td_n), ''],
        [Paragraph('202407124030', td_n), Paragraph('Taha Saranbeyli', td_n), ''],
        ['', '', ''],
    ]
    it = Table(imza_data, colWidths=[4*cm, 7*cm, 5.6*cm])
    it.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.5,colors.black),
        ('INNERGRID',(0,0),(-1,-1),0.5,colors.black),
        ('BACKGROUND',(0,0),(-1,0),mavi),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F2F2F2'),colors.white]),
    ]))
    story.append(it)
    story.append(Spacer(1, 0.8*cm))
    alt = ParagraphStyle('alt', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)
    story.append(Table([[Paragraph('Öğr.Gör. İlker Duran', alt)]], colWidths=[16.6*cm]))
    story.append(Table([[Paragraph('İmza', alt)]], colWidths=[16.6*cm]))
    doc.build(story)
    print(f'Oluşturuldu: {os.path.basename(dosya)}')


# ═══════════════════════════════════════════════
# 1. HAFTA – Problem Tanımı ve Sistem Tasarımı
# ═══════════════════════════════════════════════
rapor_olustur(os.path.join(BASE,'raporlar','hafta1.pdf'), 1,
    'Problem Tanımı ve Sistem Tasarımı', [
    {'baslik': '1.1. Proje Amacının Tanımlanması', 'icerik': [
        'Bu proje, küçük ve orta ölçekli restoranların günlük operasyonlarını tek bir dijital platform üzerinden yönetmesine olanak tanıyan çok terminalli bir Python web uygulamasıdır (RestoranSys). Proje kapsamında sipariş alma, mutfak koordinasyonu, ödeme işlemleri ve yönetim paneli gibi temel restoran süreçleri eksiksiz biçimde dijitalleştirilmiştir.',
        'Hangi kullanıcı ihtiyacını çözdüğü: Günümüzde küçük ve orta ölçekli restoranlar sipariş yönetimini çoğunlukla kâğıt-kalem ya da mesajlaşma uygulamaları üzerinden yürütmektedir. Bu durum sipariş karışıklıklarına, mutfak-kasa koordinasyon eksikliğine ve stok takibinin güçleşmesine yol açmaktadır. RestoranSys; müşteriden mutfağa, garsondan kasaya uzanan tüm süreci tek bir çatı altında toplayarak bu sorunları ortadan kaldırmaktadır. Anlık stok takibi, otomatik malzeme düşme sistemi ve kampanya/indirim modülü ile restoranın hem operasyonel hem de ticari verimliliği artırılmaktadır.',
    ]},
    {'baslik': '1.2. Proje Türü ve Kapsamı', 'icerik': [
        'Proje Türü: Flask tabanlı çok terminalli web uygulaması. Müşteriler QR kod ile masadan tarayıcı üzerinden sisteme erişmektedir. Aynı zamanda personel paneli ayrı bir web arayüzü olarak sunulmaktadır.',
        'Uygulama kapsamında dört temel terminal modülü bulunmaktadır: Müşteri Terminali (şifresiz, QR ile erişim), Mutfak Terminali (şifre korumalı), Kasa Terminali (şifre korumalı) ve Yönetim Terminali (şifre korumalı, tam yetki). Her terminal bağımsız çalışmakla birlikte aynı JSON veri tabanını paylaşmaktadır.',
        'Kullanılan Teknolojiler:',
        '• Python 3.10+ — temel programlama dili',
        '• Flask — web sunucu çerçevesi (web arayüzü ve API)',
        '• JSON — kalıcı veri depolama (menü, sipariş, masa, malzeme)',
        '• dataclasses & enum — nesne veri modelleri',
        '• pathlib — dosya sistemi yönetimi',
        '• qrcode — masa başı QR kod üretimi',
        '• Cloudflare Tunnel — internet üzerinden erişim',
    ]},
    {'baslik': '1.3. Sistem Bileşenleri ve Akış', 'icerik': [
        'Kullanıcı Bileşeni: Sisteme dört farklı rol üzerinden erişilmektedir: Müşteri (şifresiz, QR ile), Mutfak Personeli, Garson ve Yönetici/Kasa. Her rol kendi yetki sınırları içinde işlem yapabilmektedir.',
        'Veri Bileşeni: Tüm veriler (menü.json, siparişler.json, masalar.json, malzemeler.json) JSON dosyalarında tutulmaktadır. Sistem her yeniden başlatıldığında veriler otomatik yüklenmektedir.',
        'İşlem Mantığı Bileşeni: Siparişler altı aşamalı durum makinesiyle izlenmektedir: Bekliyor → Hazırlanıyor → Hazır → Teslim Edildi → Ödendi → İptal. Her geçiş ilgili terminal tarafından onaylanmaktadır.',
        'Arayüz Bileşeni: Flask ile oluşturulan web arayüzü tamamen mobil uyumludur; müşteriler herhangi bir uygulama indirmeksizin sadece tarayıcıdan sistemi kullanabilmektedir.',
        'Sistem Akışı: Müşteri girişi → Masa seç → Menüden sipariş ver → Siparişi onayla → Mutfak hazırlar → Garson teslim eder → Kasa ödeme alır → Masa boşalır',
    ]},
    {'baslik': '1.4. Temel Özelliklerin Belirlenmesi', 'icerik': [
        'Projenin ana fonksiyonları aşağıdaki şekilde belirlenmiştir:',
        '• Kullanıcı girişi ve yetki yönetimi (login — müşteri / personel ayrımı)',
        '• Masa seçimi ve QR kod ile oturum açma',
        '• Menüden ürün seçimi ve sepete ekleme (veri ekleme)',
        '• Sipariş listeleme ve durum takibi (listeleme)',
        '• Mutfak ve garson terminalleri üzerinden sipariş durumu güncelleme (güncelleme)',
        '• Sipariş iptali ve ürün çıkarma (silme)',
        '• Stok ve malzeme takibi (otomatik düşme)',
        '• Kampanya ve indirim yönetimi (analiz)',
        '• Günlük ciro ve sipariş istatistikleri (analiz / dashboard)',
        '• Masa rezervasyon sistemi',
        '• Bahşiş takip modülü',
    ]},
])

# ═══════════════════════════════════════════════
# 2. HAFTA – Temel Fonksiyonların Geliştirilmesi
# ═══════════════════════════════════════════════
rapor_olustur(os.path.join(BASE,'raporlar','hafta2.pdf'), 2,
    'Temel Fonksiyonların Geliştirilmesi', [
    {'baslik': '2.1. Veri Yapısının Kurulması', 'icerik': [
        'Kullanılan Veri Yapıları: Verileri bellekte düzenli tutmak için Python sözlük (dict) ve liste (list) yapıları kullanılmıştır. Nesne modellemeleri için ise @dataclass ve Enum sınıfları tercih edilmiştir. Örneğin Siparis, MenuOgesi ve Masa varlıkları birer dataclass olarak tanımlanmış; sipariş durumları (Bekliyor, Hazırlanıyor, Hazır, Ödendi vb.) ise SiparisDurumu adlı Enum ile ifade edilmiştir.',
        'Veri Kaydetme: Harici bir veritabanı yerine, sistemin hafifliğini ve taşınabilirliğini korumak amacıyla tüm veriler JSON dosyalarında (menu.json, masalar.json, siparisler.json, malzemeler.json, kullanicilar.json) kalıcı olarak saklanmaktadır. storage.py modülü okuma/yazma işlemlerini merkezi olarak yönetmektedir.',
    ]},
    {'baslik': '2.2. CRUD İşlemleri', 'icerik': [
        'Create (Ekleme): Yönetim panelinden menüye yeni ürün eklenebilmekte, malzeme stoku oluşturulabilmekte ve yeni kullanıcı kaydı yapılabilmektedir. Müşteri tarafında ise masa seçildikten sonra yeni sipariş kaydı otomatik oluşturulmaktadır.',
        'Read (Görüntüleme): Menü ürünleri kategori bazlı listelenmekte; aktif siparişler mutfak ve kasa terminallerinde anlık görüntülenmektedir. Yönetim panelinde günlük ciro, sipariş geçmişi ve malzeme stokları raporlanmaktadır.',
        'Update (Güncelleme): Ürünlerin fiyat, stok ve indirim bilgileri yönetim panelinden güncellenebilmektedir. Siparişlerin durumu (Bekliyor → Hazırlanıyor → Hazır → Ödendi) mutfak, garson ve kasa terminalleri aracılığıyla aşama aşama güncellenmektedir.',
        'Delete (Silme): Yönetim panelinden menü ürünleri pasif hale getirilebilmekte ya da silinebilmektedir. Müşteri siparişi onaylamadan önce sepetteki ürünleri çıkarabilmekte; personel aktif rezervasyonları iptal edebilmektedir.',
    ]},
    {'baslik': '2.3. Temel İşlevlerin Çalışması', 'icerik': [
        'Dinamik Hesaplamalar: Sepete ürün eklendiğinde ara toplam, KDV (%10) ve genel toplam otomatik hesaplanmaktadır. Kampanyalı ürünlerde indirim tutarı da anlık olarak güncellenmektedir.',
        'Reçete ve Stok Düşümü: Sipariş onaylandığında; ürün porsiyon stoğu bir azaltılmakta, çorba gibi özel ürünlerin tarife dosyasındaki iç malzemeler (un, tereyağı vb.) gramaj bazında arka planda otomatik düşülmektedir. Stok sıfırlandığında ürün menüde "Tükendi" olarak işaretlenmektedir.',
        'Kasa Akışı: Kasa terminalinde müşteri ödemesi alındığında para üstü hesaplanmakta, ödeme kaydı oluşturulmakta ve ilgili masa otomatik olarak "Boş" durumuna geçirilmektedir.',
    ]},
    {'baslik': '2.4. Hata Kontrolleri', 'icerik': [
        'Mantıksal Kontroller: Dolu masaya yeni müşteri atanması, stoksuz ürünün sipariş edilmesi, rezerve masanın müşteri tarafından seçilmesi gibi geçersiz işlemler sunucu tarafında if-else kontrolleriyle engellenmiş ve kullanıcıya anlaşılır hata mesajı döndürülmüştür.',
        'Try-Except Kullanımı: JSON dosyası okunamadığında, geçersiz veri tipinde form gönderildiğinde ve beklenmedik sunucu hatalarında try-except blokları devreye girerek sistemin çökmesi önlenmektedir. Flask hata işleyicileri (error handler) ile 404 ve 500 hataları da özelleştirilmiştir.',
        'Oturum Güvenliği: Flask session mekanizması ile kullanıcı oturumları yönetilmektedir. Yetkisiz sayfalara erişim girişimlerinde kullanıcı otomatik olarak giriş ekranına yönlendirilmektedir.',
    ]},
])

# ═══════════════════════════════════════════════════════
# 3. HAFTA – Gelişmiş Özellikler ve Proje Zenginleştirme
# ═══════════════════════════════════════════════════════
rapor_olustur(os.path.join(BASE,'raporlar','hafta3.pdf'), 3,
    'Gelişmiş Özellikler ve Proje Zenginleştirme', [
    {'baslik': '3.1. Projeye Özgü Gelişmiş Özellikler', 'icerik': [
        'QR Kod Tabanlı Sipariş Sistemi: Bu haftanın en önemli yeniliği, QR kod tabanlı gerçek zamanlı sipariş sistemidir. Her masaya özgü bir QR kod üretilmekte; müşteriler telefon kameralarıyla kodu okutarak kendi cihazlarından sipariş verebilmektedir. Bu siparişler anlık olarak mutfak ve kasa terminallerine iletilmektedir.',
        'Kategori Filtreleme: Web menü arayüzüne Başlangıç, Ana Yemek, Pizza, Salata, Tatlı ve İçecek kategorilerine ait filtre butonları eklenmiştir. Müşteriler bu butonlara tıkladığında yalnızca ilgili kategorinin ürünleri görüntülenmektedir.',
        'İstatistik ve Günlük Rapor: Yönetim panelinden erişilebilen günlük rapor sistemi; sipariş sayısını, toplam cirosunu ve en çok sipariş edilen ürünlerin listesini sunmaktadır.',
        'Kampanya ve İndirim Yönetimi: Herhangi bir ürüne yüzdelik indirim uygulanabilmekte; müşteriye orijinal fiyat ile indirimli fiyat birlikte gösterilmektedir.',
        'Cloudflare Tunnel Entegrasyonu: Sistem sadece yerel ağda değil, Cloudflare Tunnel aracılığıyla mobil veri üzerinden de erişilebilir hale getirilmiştir.',
    ]},
    {'baslik': '3.2. Kullanıcı Deneyimi (UI/UX)', 'icerik': [
        'Web arayüzü tamamen mobil uyumlu (responsive) olarak tasarlanmıştır. Her menü ürünü kendi kartında gösterilmekte; ürün adı, açıklaması, fiyatı (KDV dahil) ve sepete ekleme butonu tek bir bakışta algılanabilecek şekilde düzenlenmiştir.',
        'Kampanyalı ürünlerde eski fiyat üzeri çizili olarak gösterilmekte, indirim oranı renkli rozet ile vurgulanmaktadır. Sipariş onaylandıktan sonra müşteri, siparişinin durumunu takip edebildiği bir durum sayfasına yönlendirilmektedir.',
        'Personel panelinde sabit sol kenar çubuğu (sidebar) ile hızlı sayfa geçişi sağlanmış; mobil cihazlarda sidebar overlay moduna geçerek içeriğin kapanması önlenmiştir. Toast bildirim sistemi ile tüm işlem sonuçları anlık olarak kullanıcıya gösterilmektedir.',
    ]},
    {'baslik': '3.3. Modüler Kod Yapısı', 'icerik': [
        'Proje başından itibaren modüler bir mimari ile geliştirilmiştir. Her işlev kendi dosyasında ayrı bir modül olarak tanımlanmıştır:',
        '• models.py — veri modelleri (Siparis, MenuOgesi, Masa, SiparisDurumu)',
        '• storage.py — JSON okuma/yazma işlemleri',
        '• menu_manager.py — menü yönetimi (MenuYoneticisi sınıfı)',
        '• order_manager.py — sipariş yönetimi (SiparisYoneticisi sınıfı)',
        '• malzeme_manager.py — malzeme stok takibi (MalzemeYoneticisi sınıfı)',
        '• web_sunucu.py — Flask web sunucusu ve tüm route\'lar',
        '• main.py — sistem başlatıcı',
        'Nesne yönelimli programlama (OOP) ilkeleri tercih edilmiştir. MenuYoneticisi, SiparisYoneticisi ve MalzemeYoneticisi sınıfları kendi sorumluluk alanlarını kapsülleyerek bağımsız birimler halinde çalışmaktadır.',
    ]},
    {'baslik': '3.4. Performans ve Temizlik', 'icerik': [
        'Tekrar eden kod blokları fonksiyonlara taşınmış; her fonksiyon tek bir görevi yerine getirmektedir. Flask uygulaması, web sunucusu arka planda ayrı bir thread üzerinde çalıştırılarak terminal arayüzü ile birbirini bloke etmesi önlenmiştir.',
        'JSON tabanlı kalıcı depolama sayesinde veriler hızlı okunup yazılmakta, gereksiz dosya işlemleri önlenmektedir. Mutfak ve kasa terminalleri, yeni siparişleri görebilmek için her döngüde JSON verilerini yenilemektedir. Bu yaklaşım gereksiz bellek kullanımını minimize ederek sistemin kararlı çalışmasını sağlamaktadır.',
    ]},
])

# ═══════════════════════════════════════════════════
# 4. HAFTA – Test, Senaryolar ve Değerlendirme
# ═══════════════════════════════════════════════════
rapor_olustur(os.path.join(BASE,'raporlar','hafta4.pdf'), 4,
    'Test, Senaryolar ve Değerlendirme', [
    {'baslik': '4.1. Senaryo Tabanlı Testler', 'icerik': [
        'Bu hafta sistemi test etmek için birkaç farklı senaryo denendi. Birinci senaryoda; müşteri hesabıyla giriş yapılarak QR kod ile masaya sipariş verildi, menüden ürün seçilip onaylandıktan sonra siparişin mutfak ekranına geçtiği görüldü. Ardından mutfaktan "Hazırlandı" işlemi yapılınca sipariş kasa ekranına geçti. Bu senaryo eksiksiz çalıştı.',
        'İkinci senaryoda malzeme stoğu sıfırlandı; o malzemeyi kullanan yemeğin menüde otomatik olarak "Tükendi" işaretiyle kapandığı doğrulandı. Malzeme tekrar eklenince ürünün yeniden aktif hale geldiği gözlemlendi.',
        'Üçüncü senaryoda dolu masaya yeni sipariş açılmaya çalışıldı, sistem engelledi. Rezerve masayı seçme girişiminde de sistem doğru şekilde uyarı verdi. Bu senaryolar beklenen sonuçları verdi.',
        'Dördüncü senaryoda kampanya modülü test edildi: ürüne %20 indirim uygulandı, müşteri ekranında eski fiyat üzeri çizili ve indirimli fiyat birlikte gösterildiği doğrulandı.',
    ]},
    {'baslik': '4.2. Hataların Giderilmesi', 'icerik': [
        'Testler sırasında tespit edilen hatalar ve uygulanan düzeltmeler şu şekildedir:',
        '• Müşteri masa seçip sipariş vermeden çıkınca masa dolu kalıyordu → Oturum temizlendiğinde masa durumu otomatik boşaltılacak şekilde düzeltildi.',
        '• Sipariş numaraları her gün 1\'den başlamıyordu → Gün değişimini kontrol eden bir yapı eklendi, artık her sabah sipariş numarası sıfırlanmaktadır.',
        '• Türkçe karakter sorunu terminalde bozuk çıkıyordu → sys.stdout.reconfigure(encoding="utf-8") ve chcp 65001 komutu eklenerek düzeltildi.',
        '• Personel giriş ekranında hatalı giriş sonrasında müşteri sekmesine yönleniyordu → aktif_tip parametresi ile sekme kalıcılığı sağlandı.',
        '• Rezervasyon iptal edildiğinde masa otomatik boşalmıyordu → İptal işlemi sırasında masa durumu kontrol edilerek BOS\'a alındı.',
    ]},
    {'baslik': '4.3. Projenin Amaca Uygunluğu', 'icerik': [
        'Projeye başlarken belirlenen hedefler şunlardı: müşterilerin sipariş verebilmesi, mutfağın siparişi görmesi ve kasanın ödeme alması. Bu üç temel hedef tam olarak çalışmaktadır.',
        'Bunlara ek olarak: malzeme takibi, kampanya sistemi, günlük rapor, masa rezervasyonu, bahşiş modülü, Cloudflare üzerinden internet erişimi ve tam mobil uyum da eklenerek hedeflerin oldukça ötesine geçilmiştir. Veriler dosyaya kaydedildiği için program kapansa bile hiçbir bilgi silinmemektedir.',
    ]},
    {'baslik': '4.4. Gerçek Hayat Uyumu', 'icerik': [
        'Sistemin gerçek bir restoranda kullanılabileceği değerlendirilmektedir. Müşteriler masadan QR okutup telefon üzerinden sipariş verebildiği için garson ihtiyacı azalmakta; mutfak siparişleri sırayla görmekte; kasa ödeme ve para üstü hesabını kolayca yapabilmektedir.',
        'Sistemin çalışması için tek şart restoranın bir WiFi ağına sahip olmasıdır; internet bağlantısı zorunlu değildir, sadece yerel ağ yeterlidir. Bu da sistemi düşük maliyetle uygulanabilir kılmaktadır. İsteğe bağlı olarak Cloudflare Tunnel ile internet erişimi de etkinleştirilebilmektedir.',
    ]},
])

# ═══════════════════════════════════════════════
# 5. HAFTA – Final Teslim ve Sunum
# ═══════════════════════════════════════════════
rapor_olustur(os.path.join(BASE,'raporlar','hafta5.pdf'), 5,
    'Final Teslim ve Sunum', [
    {'baslik': '5.1. Projenin Tamamlanması', 'icerik': [
        'Bu hafta projenin tüm temel özellikleri eksiksiz çalışır hale getirildi. Müşteri tarafında QR kod ile masa seçimi, menüden sipariş verme, sepet yönetimi, sipariş takibi ve garson bahşişi ekranları sorunsuz çalışmaktadır. Personel tarafında mutfak, garson, kasa ve yönetim panelleri işlevsel durumdadır.',
        'Masa rezervasyon sistemi, malzeme stok takibi, kampanya yönetimi ve günlük rapor özeti tamamlanmıştır. Cloudflare Tunnel entegrasyonu ile sistem sadece yerel ağda değil, mobil veri üzerinden de kullanılabilir hale getirilmiştir. Tüm veriler JSON dosyalarına kaydedildiği için program yeniden başlatılsa bile hiçbir bilgi kaybolmamaktadır.',
    ]},
    {'baslik': '5.2. Kod ve Proje Düzeni', 'icerik': [
        'Proje dosyaları düzenli ve anlaşılır bir yapıda organize edilmiştir. Ana modüller birbirinden ayrı dosyalara bölünmüştür:',
        '• models.py — veri modelleri',
        '• storage.py — dosya okuma/yazma işlemleri',
        '• menu_manager.py — menü yönetimi',
        '• order_manager.py — sipariş yönetimi',
        '• malzeme_manager.py — malzeme stok takibi',
        '• web_sunucu.py — Flask web arayüzü',
        '• main.py — sistem başlatıcı',
        'Veri dosyaları ayrı bir veri/ klasöründe, rapor dosyaları raporlar/ klasöründe, menü görselleri static/menu/ klasöründe tutulmaktadır. main.py çalıştırıldığında sistem tek komutla ayağa kalkmakta ve konsolda sunucu adresi ile QR kod gösterilmektedir. Proje GitHub\'a yüklenmiş olup otomatik commit/push sistemi ile her değişiklik kayıt altına alınmaktadır.',
    ]},
    {'baslik': '5.3. Sunum Kalitesi', 'icerik': [
        'Sunum için sistemin gerçek kullanım akışını gösteren iki demo hazırlandı. Birinci demoda; müşteri hesabıyla giriş yapıldı, QR kod ile masaya oturuldu, menüden sipariş verildi. Ardından mutfak ekranında siparişin göründüğü ve "Hazırlandı" butonuyla ilerlediği gösterildi. Garson panelinden teslim alındı, kasa terminalinde ödeme yapıldı.',
        'İkinci demoda yönetim paneli tanıtıldı: menüye ürün ekleme, stok güncelleme, kampanya tanımlama, masa rezervasyonu yapma ve günlük ciro raporu inceleme adımları sırayla anlatıldı. Projenin hangi sorunu çözdüğü ve nasıl çalıştığı net biçimde aktarıldı.',
    ]},
    {'baslik': '5.4. Projeye Hakimiyet', 'icerik': [
        'Proje boyunca her modül ekip tarafından yazıldığından, sistemin tamamına hakimiyet tam düzeydedir. Sunum sırasında sorulan sorular; kodun ilgili satırları gösterilerek yanıtlandı. Sipariş akışının adım adım nasıl ilerlediği, masaların hangi koşullarda boşaldığı ve stok kontrolünün nerede devreye girdiği ayrıntılı olarak açıklandı.',
        'Beş hafta boyunca her hafta bir önceki haftanın üzerine ekleyerek büyütülen bu proje, Python ile gerçek dünyada kullanılabilir bir sistem yapılabileceğini ortaya koymuştur. Başlangıçta yalnızca sipariş almayı hedeflerken rezervasyon, stok, kampanya, mobil uyum ve internet erişimi gibi özellikler de eklenerek hedeflerin oldukça ötesine geçilmiştir.',
    ]},
])

# ═══════════════════════════
# TÜM RAPORLARI BİRLEŞTİR
# ═══════════════════════════
dosyalar = [
    os.path.join(BASE,'raporlar','hafta1.pdf'),
    os.path.join(BASE,'raporlar','hafta2.pdf'),
    os.path.join(BASE,'raporlar','hafta3.pdf'),
    os.path.join(BASE,'raporlar','hafta4.pdf'),
    os.path.join(BASE,'raporlar','hafta5.pdf'),
]

writer = PdfWriter()
for d in dosyalar:
    reader = PdfReader(d)
    for page in reader.pages:
        writer.add_page(page)
    print(f'{os.path.basename(d)}: {len(reader.pages)} sayfa')

cikti = os.path.join(BASE,'raporlar','BLP_Grup11_TumHaftalar.pdf')
with open(cikti,'wb') as f:
    writer.write(f)
print(f'\nBirleştirildi: BLP_Grup11_TumHaftalar.pdf')

# Tek tek dosyaları sil
for d in dosyalar:
    os.remove(d)
print('Geçici dosyalar silindi.')
