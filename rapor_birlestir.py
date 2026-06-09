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

def rapor_olustur(dosya, hafta_no, konu, bolumler):
    doc = SimpleDocTemplate(dosya, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm)

    def p(text, bold=False, size=10, align=TA_LEFT, space_after=4, leading=14, justify=False):
        fname = 'Helvetica-Bold' if bold else 'Helvetica'
        al = TA_JUSTIFY if justify else align
        return ParagraphStyle('_', fontName=fname, fontSize=size,
                              alignment=al, spaceAfter=space_after, leading=leading)

    story = []

    # Logo + Üniversite adı
    logo_img = Image(LOGO, width=5*cm, height=None)
    logo_img.hAlign = 'LEFT'
    uni_para = Paragraph('<b><font size=18>DOĞUŞ ÜNİVERSİTESİ</font></b>',
                         ParagraphStyle('uni', fontName='Helvetica-Bold', fontSize=18, alignment=TA_LEFT))
    uni_t = Table([[logo_img, uni_para]], colWidths=[5.5*cm, 11*cm])
    uni_t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
    story.append(uni_t)
    story.append(Spacer(1, 0.4*cm))

    # Bilgi tablosu
    mavi = colors.HexColor('#1F4E79')
    th_st = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER)
    td_b  = ParagraphStyle('tdb', fontName='Helvetica-Bold', fontSize=9)
    td_n  = ParagraphStyle('tdn', fontName='Helvetica', fontSize=9)

    bilgi = [
        [Paragraph('MESLEK YÜKSEKOKULU\n2025 - 2026 EĞİTİM - ÖĞRETİM YILI / BAHAR DÖNEMİ', th_st), ''],
        [Paragraph('Adı / Name', td_b),           Paragraph('PYTHON PROGRAMLAMA', td_n)],
        [Paragraph('DERS Kodu / Code', td_b),      Paragraph('BLP 276', td_n)],
        [Paragraph('Sorumlusu / Lecturer', td_b),  Paragraph('Öğr.Gör. İLKER DURAN', td_n)],
        [Paragraph('PROJE HAFTALIK RAPORU', th_st), ''],
    ]
    bilgi_t = Table(bilgi, colWidths=[8*cm, 8.6*cm])
    bilgi_t.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)), ('SPAN', (0,4), (1,4)),
        ('BACKGROUND', (0,0), (1,0), mavi), ('TEXTCOLOR', (0,0), (1,0), colors.white),
        ('BACKGROUND', (0,4), (1,4), mavi), ('TEXTCOLOR', (0,4), (1,4), colors.white),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (1,3), [colors.white, colors.HexColor('#F2F2F2')]),
        ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(bilgi_t)
    story.append(Spacer(1, 0.3*cm))

    # Hafta/Konu tablosu
    hk = [
        [Paragraph('HAFTA', td_b), Paragraph(f'{hafta_no}. Hafta', td_n)],
        [Paragraph('KONU',  td_b), Paragraph(konu, td_n)],
    ]
    hk_t = Table(hk, colWidths=[4*cm, 12.6*cm])
    hk_t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(hk_t)
    story.append(Spacer(1, 0.5*cm))

    # Başlık
    story.append(Paragraph('<u><b>HAFTALIK YAPILAN İŞLEMLER</b></u>',
        ParagraphStyle('ust', fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.4*cm))

    # Bölümler
    normal = ParagraphStyle('n', fontName='Helvetica', fontSize=10, leading=15,
                             alignment=TA_JUSTIFY, spaceAfter=6)
    bold_h = ParagraphStyle('bh', fontName='Helvetica-Bold', fontSize=10,
                             spaceBefore=8, spaceAfter=4)

    for b in bolumler:
        story.append(Paragraph(b['baslik'], bold_h))
        for sat in b['icerik']:
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
    imza_t = Table(imza_data, colWidths=[4*cm, 7*cm, 5.6*cm])
    imza_t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), mavi), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F2F2F2'), colors.white]),
    ]))
    story.append(imza_t)
    story.append(Spacer(1, 0.8*cm))
    alt = ParagraphStyle('alt', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)
    story.append(Table([[Paragraph('Öğr.Gör. İlker Duran', alt)]], colWidths=[16.6*cm]))
    story.append(Table([[Paragraph('İmza', alt)]], colWidths=[16.6*cm]))

    doc.build(story)
    print(f'Oluşturuldu: {dosya}')


# ─── 1. HAFTA ───
rapor_olustur(os.path.join(BASE, 'raporlar', 'hafta1_duzenlendi.pdf'), 1,
    'Proje Tanımı ve Temel Özellikler', [
    {'baslik': '1.1. Proje Amacının Tanımlanması', 'icerik': [
        'Bu proje, restoranların günlük operasyonlarını tek bir platform üzerinden dijital olarak yönetmesine olanak tanıyan çok terminalli bir Python uygulamasıdır. Trello ve benzeri yönetim araçlarından ilham alınarak geliştirilmiş bu sistem; sipariş takibi, masa yönetimi, mutfak koordinasyonu ve kasa işlemlerini birbirinden bağımsız terminaller aracılığıyla sunar.',
        'Sistem temel olarak şu işlemleri gerçekleştirmektedir: Müşteriler sipariş ekranından masa seçerek ürün siparişi verebilmektedir. Mutfak terminali gelen siparişleri anlık olarak görmekte ve durum güncellemesi yapabilmektedir. Kasa terminali ödemeleri almakta ve para üstü hesaplamaktadır. Yönetim terminali ise menü, stok, kampanya ve malzeme yönetimini kapsamaktadır.',
        'Günümüzde küçük ve orta ölçekli restoranlar sipariş yönetimini çoğunlukla kağıt kalem ile ya da mesajlaşma uygulamaları üzerinden yürütmektedir. Bu durum sipariş karışıklığına, mutfak ile kasa arasındaki koordinasyon eksikliğine ve stok takibinin güçleşmesine yol açmaktadır. RestoranSys; müşteriden mutfağa, garsondan kasaya uzanan tüm süreci tek bir çatı altında dijitalleştirerek bu sorunları çözmektedir.',
    ]},
    {'baslik': '1.2. Proje Türü ve Kapsamı', 'icerik': [
        'Geliştirilen uygulama, tamamen Python 3 ile yazılmış terminal tabanlı çok katmanlı bir yönetim sistemidir. Herhangi bir ek web sunucusuna veya tarayıcıya ihtiyaç duymaksızın komut satırı üzerinden doğrudan çalıştırılabilmektedir. Veriler JSON dosyalarında saklanmakta; böylece hafif, hızlı ve kurulum gerektirmeyen bir yapı elde edilmektedir.',
        'Uygulama; restoran sahipleri, mutfak personeli, garsonlar ve kasiyer olmak üzere farklı rol gruplarını hedef kitle olarak benimsemektedir. Proje kapsamında dört temel terminal modülü ele alınmaktadır: Müşteri Terminali, Mutfak Terminali, Kasa Terminali ve Yönetim Terminali. Her terminal bağımsız çalışmakla birlikte aynı veri tabanını paylaşmaktadır.',
        'Kullanılan Teknolojiler: Python 3.10+, json (veri kalıcılığı), dataclasses ve enum (veri modelleri), pathlib (dosya yönetimi), msvcrt (gerçek zamanlı klavye girişi).',
    ]},
    {'baslik': '1.3. Sistem Bileşenleri ve Akış', 'icerik': [
        'Terminal Bileşeni: Sisteme erişim, terminal seçim ekranıyla başlamaktadır. Müşteri terminali şifresiz açılırken Mutfak, Kasa ve Yönetim terminalleri şifre korumalıdır. Her terminal kendi yetki sınırları içinde işlem yapabilmekte; aynı JSON veri tabanı üzerinden eş zamanlı çalışabilmektedir.',
        'Sipariş Bileşeni: Proje içerisinde siparişler oluşturulabilmekte, düzenlenebilmekte ve durumları güncellenebilmektedir. Her sipariş; masa numarası, kalemler, KDV dahil toplam tutar ve sipariş notu bilgilerini barındırmaktadır.',
        'Veri Bileşeni: Tüm menü, sipariş, masa ve malzeme verileri JSON dosyalarında kalıcı olarak saklanmaktadır. Sistem her yeniden başlatıldığında mevcut veriler yüklenerek kullanıcıya sunulmaktadır.',
        'Menü Bileşeni: Oturum açan yönetici; menüye ürün ekleyebilmekte, fiyat ve stok güncelleyebilmekte, kampanya/indirim uygulayabilmektedir.',
        'Sistem akışı: Müşteri girişi → Masa seç → Sipariş ver → Mutfak onayı → Garson servisi → Kasa ödemesi',
    ]},
    {'baslik': '1.4. Temel Özelliklerin Belirlenmesi', 'icerik': [
        '1. Çok Terminalli Mimari: Uygulama Müşteri, Mutfak, Kasa ve Yönetim olmak üzere dört bağımsız terminal moduna sahiptir. Her terminal farklı yetki seviyesinde çalışır; Müşteri terminali şifresizken diğerleri şifre korumalıdır.',
        '2. Stok ve Malzeme Yönetimi: Menü ürünlerinin porsiyon stoğu anlık takip edilmektedir. Sipariş verildiğinde tarife göre malzemeler otomatik düşülmektedir.',
        '3. Kampanya ve İndirim Sistemi: Yönetim terminali üzerinden herhangi bir ürüne yüzde tabanlı indirim uygulanabilmektedir.',
        '4. KDV Dahil Fiyatlandırma: Müşteri ekranında tüm fiyatlar KDV dahil (%10) olarak gösterilmektedir.',
        '5. QR Anlık Menü Raporu: Herhangi bir ekranda QR yazıldığında ürün listesi, stok durumu ve kampanya bilgileri anında görüntülenmektedir.',
        '6. Masa Rezervasyon Sistemi: Personel, masaları Boş, Dolu veya Rezerve olarak işaretleyebilmektedir.',
        '7. Otomatik Zaman Aşımı ve Güvenlik: Müşteri ekranında 20 saniye hareketsizlik durumunda sipariş otomatik iptal edilir.',
    ]},
])

# ─── 2. HAFTA ───
rapor_olustur(os.path.join(BASE, 'raporlar', 'hafta2_duzenlendi.pdf'), 2,
    'Temel Fonksiyonların Geliştirilmesi', [
    {'baslik': '2.1. Veri Yapısının Kurulması', 'icerik': [
        'Veri Yapıları: Verileri bellekte düzenli tutmak için Sözlük (Dict) ve Liste yapıları; nesne modellemeleri için ise Dataclass ve Enum yapıları kullanılmıştır.',
        'Veri Kaydetme: Harici bir veritabanı yerine, sistemin hafifliğini korumak amacıyla veriler (menü, masa, sipariş, malzeme) kalıcı olarak JSON dosyalarında (menu.json, masalar.json vb.) saklanmaktadır.',
    ]},
    {'baslik': '2.2. CRUD İşlemleri', 'icerik': [
        'Create (Ekleme): Yönetim ekranından menüye yeni ürün, diğer terminallerden ise yeni siparişler oluşturulabilmektedir.',
        'Read (Görüntüleme): Ürünler, aktif siparişler ve masa durumları listelenebilmekte; QR komutuyla detaylı stok/indirim raporu okunabilmektedir.',
        'Update (Güncelleme): Ürünlerin fiyat/stok bilgileri ve siparişlerin işlem durumları (Bekliyor, Hazır, Ödendi vb.) anlık olarak güncellenebilmektedir.',
        'Delete (Silme): Menüden ürün silme ve sipariş iptali/ürün çıkarma işlemleri yapılabilmektedir.',
    ]},
    {'baslik': '2.3. Temel İşlevlerin Çalışması', 'icerik': [
        'Dinamik Hesaplamalar: KDV dahil tutarlar, ara toplamlar ve indirimler otomatik olarak hesaplanmaktadır.',
        'Reçete ve Stok Düşümü: Sipariş alındığında ürün stokları ve çorba gibi özel ürünlerin reçetesindeki iç malzemeler (un, tereyağı vb.) gramaj bazında arka planda otomatik düşülmektedir.',
        'Kasa Akışı: Kasa terminalinde alınan tahsilat üzerinden para üstü hesaplanmakta ve ödeme sonrası ilgili masa boşa çıkarılmaktadır.',
    ]},
    {'baslik': '2.4. Hata Kontrolleri', 'icerik': [
        'Mantıksal Kontroller: Dolu masaya yeni müşteri atanması veya stoksuz ürünün sipariş edilmesi gibi geçersiz işlemler if-else bloklarıyla engellenmiştir.',
        'Try-Except Kullanımı: Sayısal değer beklenen yerlere harf girilmesi durumu try-except ValueError bloğu ile yakalanarak sistemin çökmesi önlenmiştir.',
        'Müşteri ekranındaki 20 saniyelik eylemsizlik, özel ZamanAsimi hatası ile kontrol edilerek siparişler güvenli bir şekilde iptal edilmektedir.',
    ]},
])

# ─── TÜMÜNÜ BİRLEŞTİR ───
dosyalar = [
    os.path.join(BASE, 'raporlar', 'hafta1_duzenlendi.pdf'),
    os.path.join(BASE, 'raporlar', 'hafta2_duzenlendi.pdf'),
    os.path.join(BASE, 'raporlar', 'BLP_Grup11_3Hafta_Rapor.pdf'),
    os.path.join(BASE, 'raporlar', 'BLP_Grup11_4Hafta_Rapor.pdf.pdf'),
    os.path.join(BASE, 'raporlar', 'BLP_Grup11_5Hafta_Rapor.pdf.pdf'),
]

writer = PdfWriter()
for d in dosyalar:
    reader = PdfReader(d)
    for page in reader.pages:
        writer.add_page(page)
    print(f'{os.path.basename(d)}: {len(reader.pages)} sayfa')

cikti = os.path.join(BASE, 'raporlar', 'BLP_Grup11_TumHaftalar.pdf')
with open(cikti, 'wb') as f:
    writer.write(f)
print(f'\nBirlestirildi: {cikti}')

# Geçici dosyaları sil
for d in dosyalar[:2]:
    os.remove(d)
print('Gecici dosyalar silindi.')
