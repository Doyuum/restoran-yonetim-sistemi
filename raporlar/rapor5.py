# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
    FONT = 'Arial'
    FONTB = 'Arial-Bold'
except Exception:
    FONT = 'Helvetica'
    FONTB = 'Helvetica-Bold'

doc = SimpleDocTemplate(
    'BLP_Grup11_5Hafta_Rapor.pdf',
    pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm,
    topMargin=1.5*cm, bottomMargin=2*cm
)
story = []

def ps(name, bold=False, size=9, align=0):
    return ParagraphStyle(name, fontName=FONTB if bold else FONT, fontSize=size, alignment=align)

def h3(txt):
    return Paragraph(f'<b>{txt}</b>',
        ParagraphStyle('h3', fontName=FONTB, fontSize=10, spaceBefore=12, spaceAfter=6))

def p(txt):
    return Paragraph(txt,
        ParagraphStyle('body', fontName=FONT, fontSize=10, leading=16,
                       firstLineIndent=1*cm, spaceAfter=6))

# LOGO
story.append(Image('logo.png', width=14*cm, height=1.1*cm))
story.append(Spacer(1, 0.5*cm))

# ÜST TABLO
baslik_tablo = Table([
    [Paragraph('MESLEK YÜKSEKOKULU\n2025 – 2026 EĞİTİM – ÖĞRETİM YILI/ BAHAR DÖNEMİ', ps('c', True, 10, 1))],
    [Paragraph('Adı / Name', ps('l', True)), Paragraph('PYTHON PROGRAMLAMA', ps('l'))],
    [Paragraph('DERS Kodu / Code', ps('l', True)), Paragraph('BLP 276', ps('l'))],
    [Paragraph('Sorumlusu / Lecturer', ps('l', True)), Paragraph('Öğr.Gör. İLKER DURAN', ps('l'))],
    [Paragraph('PROJE HAFTALIKRAPORU', ps('c', True, 10, 1))],
], colWidths=[8*cm, 8*cm])
baslik_tablo.setStyle(TableStyle([
    ('GRID',        (0,0),(-1,-1), 0.5, colors.black),
    ('SPAN',        (0,0),(1,0)),
    ('SPAN',        (0,4),(1,4)),
    ('ALIGN',       (0,0),(1,0),  'CENTER'),
    ('ALIGN',       (0,4),(1,4),  'CENTER'),
    ('TOPPADDING',  (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',(0,0),(-1,-1),4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(baslik_tablo)
story.append(Spacer(1, 0.5*cm))

# HAFTA / KONU
hk = Table([
    [Paragraph('HAFTA', ps('b', True)), Paragraph('5. Hafta', ps('n'))],
    [Paragraph('KONU',  ps('b', True)), Paragraph('Final Teslim ve Sunum', ps('n'))],
], colWidths=[4*cm, 12*cm])
hk.setStyle(TableStyle([
    ('GRID',        (0,0),(-1,-1), 0.5, colors.black),
    ('TOPPADDING',  (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',(0,0),(-1,-1),4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(hk)
story.append(Spacer(1, 0.8*cm))

story.append(Paragraph(
    '<u><b>HAFTALIK YAPILAN İŞLEMLER</b></u>',
    ParagraphStyle('baslik', fontName=FONTB, fontSize=11, alignment=1, spaceAfter=16)
))

# 5.1
story.append(h3('5.1. Projenin Tamamlanması'))
story.append(p(
    'bu hafta projenin tüm temel özellikleri eksiksiz çalışır hale getirildi. müşteri tarafında '
    'qr kod ile masa seçimi, menüden sipariş verme, sipariş takibi ve garson bahşişi ekranları '
    'sorunsuz çalışıyor. personel tarafında mutfak, garson, kasa ve yönetim panelleri işlevsel '
    'durumda. masa rezervasyonu, malzeme stok takibi, kampanya yönetimi ve günlük rapor '
    'özeti de tamamlandı.'
))
story.append(p(
    'cloudflare tunnel ile internet üzerinden erişim de eklendi böylece sistem sadece yerel '
    'ağda değil mobil veri üzerinden de kullanılabilir hale geldi. tüm veriler json dosyalarına '
    'kaydedildiği için program yeniden başlatılsa bile hiçbir bilgi kaybolmuyor.'
))

# 5.2
story.append(h3('5.2. Kod ve Proje Düzeni'))
story.append(p(
    'proje dosyaları düzenli bir yapıda tutuldu. ana modüller birbirinden ayrı dosyalara '
    'bölündü: models.py veri modellerini, storage.py dosya okuma/yazma işlemlerini, '
    'menu_manager.py menü yönetimini, order_manager.py sipariş yönetimini, '
    'malzeme_manager.py stok takibini, web_sunucu.py web arayüzünü, main.py ise '
    'sistemin başlatılmasını üstleniyor.'
))
story.append(p(
    'veri dosyaları ayrı bir veri/ klasöründe tutuluyor. her modülün görevi net şekilde '
    'ayrıldığı için kodun okunması ve üzerinde değişiklik yapılması kolayLAştı. '
    'main.py çalıştırıldığında sistem tek komutla ayağa kalkıyor ve konsolda sunucu '
    'adresi ile qr kod gösteriliyor.'
))

# 5.3
story.append(h3('5.3. Sunum Kalitesi'))
story.append(p(
    'sunum için sistemin gerçek kullanım akışını gösteren bir demo hazırlandı. önce müşteri '
    'hesabıyla giriş yapılıp qr kod ile masaya oturuldu, menüden sipariş verildi. ardından '
    'mutfak ekranında siparişin göründüğü ve hazırlandı butonuyla ilerlediği gösterildi. '
    'garson panelinden teslim alındı, kasa terminalinde ödeme yapıldı.'
))
story.append(p(
    'ikinci demoda yönetim paneli gösterildi: menüye ürün ekleme, stok güncelleme, '
    'masa rezervasyonu yapma ve günlük ciro raporu inceleme adımları sırayla anlatıldı. '
    'projenin hangi sorunu çözdüğü ve nasıl çalıştığı net biçimde aktarıldı.'
))

# 5.4
story.append(h3('5.4. Projeye Hakimiyet'))
story.append(p(
    'proje boyunca her modülü kendimiz yazdığımız için sistemin tamamına hakimiz. '
    'sunum sırasında sorulan soruları kodun ilgili satırlarını göstererek yanıtladık. '
    'sipariş akışının adım adım nasıl ilerlediğini, masaların hangi koşullarda boşaldığını '
    've stok kontrolünün nerede devreye girdiğini açıkladık.'
))
story.append(p(
    'dört hafta boyunca her hafta bir önceki haftanın üzerine ekleyerek büyüttüğümüz bu '
    'proje, python ile gerçek dünyada kullanılabilir bir sistem yapılabileceğini gösterdi. '
    'başlangıçta sadece sipariş almayı hedeflerken rezervasyon, stok, kampanya ve '
    'internet erişimi gibi özellikler de eklenerek hedeflerin ötesine geçildi.'
))

story.append(Spacer(1, 3*cm))

# ÜYE TABLOSU
uye = Table([
    [Paragraph('NUMARA', ps('b', True, 9, 1)),
     Paragraph('GRUP ÜYELERİNİN İSİMLERİ', ps('b', True, 9, 1)),
     Paragraph('İMZA', ps('b', True, 9, 1))],
    [Paragraph('202407124023', ps('v', False, 9, 1)),
     Paragraph('Ege Recep Alembeyli', ps('v', False, 9, 1)), ''],
    [Paragraph('202407124030', ps('v', False, 9, 1)),
     Paragraph('Taha Saranbeyli', ps('v', False, 9, 1)), ''],
    ['', '', ''],
], colWidths=[4.5*cm, 7*cm, 4.5*cm])
uye.setStyle(TableStyle([
    ('GRID',        (0,0),(-1,-1), 0.5, colors.black),
    ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
    ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
    ('TOPPADDING',  (0,0),(-1,-1), 6),
    ('BOTTOMPADDING',(0,0),(-1,-1),6),
]))
story.append(uye)
story.append(Spacer(1, 1.5*cm))

# İMZA
imza = Table([
    ['', Paragraph('Öğr.Gör. İlker Duran',
        ParagraphStyle('r', fontName=FONT, fontSize=10, alignment=2))],
    ['', Paragraph('İmza',
        ParagraphStyle('r2', fontName=FONT, fontSize=10, alignment=2))],
], colWidths=[10*cm, 6*cm])
story.append(imza)

doc.build(story)
print('Olusturuldu: BLP_Grup11_5Hafta_Rapor.pdf')
