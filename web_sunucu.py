"""
QR Sipariş Web Sunucusu
========================
Müşteri telefonuyla QR okutup sipariş verebilir.
Aynı WiFi ağında çalışır.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for
from functools import wraps
from pathlib import Path
import json
from werkzeug.security import generate_password_hash, check_password_hash
import storage
from models import MasaDurumu, SiparisDurumu, SiparisKalemi
from menu_manager import MenuYoneticisi
from order_manager import SiparisYoneticisi

app = Flask(__name__)
app.secret_key = "restoran_qr_2024"

# ─── Kullanıcı Yönetimi ────────────────────────────────────────────
KULLANICI_DOSYA = Path(__file__).parent / "veri" / "kullanicilar.json"
KAYIT_KODU = "1234"   # Kayıt olmak için gereken kod

def kullanicilari_yukle():
    if not KULLANICI_DOSYA.exists():
        return {}
    try:
        return json.loads(KULLANICI_DOSYA.read_text(encoding="utf-8"))
    except Exception:
        return {}

def kullanicilari_kaydet(veri):
    KULLANICI_DOSYA.parent.mkdir(exist_ok=True)
    KULLANICI_DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")

def kullanici_bul(kullanici_adi):
    return kullanicilari_yukle().get(kullanici_adi)

PERSONEL_ROLLER = {"mutfak","kasa","yonetim","admin","garson"}
MUSTERI_ROL     = "musteri"

def login_gerekli(f):
    """Personel sayfaları için — giriş + personel rolü gerektirir."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "kullanici" not in session:
            return redirect(url_for("giris_ekran", sonraki=request.path))
        if session.get("rol") not in PERSONEL_ROLLER:
            return redirect(url_for("giris_ekran"))
        return f(*args, **kwargs)
    return wrapper

def musteri_gerekli(f):
    """Müşteri sayfaları için — giriş + musteri rolü gerektirir."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "kullanici" not in session:
            return redirect(url_for("giris_ekran", sonraki=request.path))
        if session.get("rol") != MUSTERI_ROL:
            return redirect(url_for("giris_ekran"))
        return f(*args, **kwargs)
    return wrapper

# ─── Her istekte taze veri yükle ───────────────────────────────────

def _my():
    return MenuYoneticisi()

def _sy(my=None):
    if my is None:
        my = _my()
    return SiparisYoneticisi(my.menu, my)

def _maly():
    from malzeme_manager import MalzemeYoneticisi
    return MalzemeYoneticisi()

# ─── HTML Şablonları ───────────────────────────────────────────────

BASE = """
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Anadolu Sofrası</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; color: #222;
      background-color: #f0f2f5;
      background-image: repeating-linear-gradient(
        45deg,
        rgba(0,0,0,0.07) 0px, rgba(0,0,0,0.07) 2px,
        transparent 2px, transparent 50%
      ),
      repeating-linear-gradient(
        -45deg,
        rgba(0,0,0,0.07) 0px, rgba(0,0,0,0.07) 2px,
        transparent 2px, transparent 50%
      );
      background-size: 28px 28px;
    }
    .header { background: #0D1B2A; color: white; padding: 16px 20px;
              display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 10; }
    .header h1 { font-size: 1.2rem; }
    .header .sub { font-size: 0.8rem; opacity: 0.7; }
    .container { max-width: 600px; margin: 0 auto; padding: 16px; }
    .card { background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    .btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 10px;
           font-size: 1rem; font-weight: 600; cursor: pointer; text-align: center;
           text-decoration: none; margin-top: 8px; }
    .btn-primary   { background: #1B6CA8; color: white; }
    .btn-success   { background: #27ae60; color: white; }
    .btn-danger    { background: #e74c3c; color: white; }
    .btn-secondary { background: #ecf0f1; color: #333; }
    .btn:active    { opacity: 0.8; }
    .masa-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .masa-btn { padding: 18px 8px; border-radius: 12px; border: 2px solid transparent;
                font-size: 0.95rem; font-weight: 700; text-align: center; cursor: pointer;
                text-decoration: none; display: block; }
    .masa-bos  { background: #e8f5e9; border-color: #27ae60; color: #1e7e34; }
    .masa-dolu { background: #fde8e8; border-color: #e74c3c; color: #c0392b; pointer-events: none; }
    .masa-rezerve { background: #fff3cd; border-color: #f39c12; color: #856404; pointer-events: none; }
    .masa-kapasite { font-size: 0.72rem; font-weight: 400; display: block; opacity: 0.8; margin-top: 3px; }
    .kategori-baslik { font-size: 0.75rem; font-weight: 800; letter-spacing: 1.5px;
                       text-transform: uppercase; color: #1B6CA8; padding: 10px 0 4px;
                       border-bottom: 2px solid #1B6CA8; margin-bottom: 8px; }
    .urun-item { display: flex; align-items: center; justify-content: space-between;
                 padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
    .urun-item:last-child { border-bottom: none; }
    .urun-ad  { font-weight: 600; font-size: 0.95rem; }
    .urun-aciklama { font-size: 0.78rem; color: #888; margin-top: 2px; }
    .urun-fiyat { font-size: 0.9rem; font-weight: 700; color: #1B6CA8; white-space: nowrap; margin-left: 8px; }
    .urun-kampanya { font-size: 0.72rem; text-decoration: line-through; color: #aaa; }
    .urun-indirim-badge { background: #e74c3c; color: white; font-size: 0.65rem;
                          padding: 2px 6px; border-radius: 20px; margin-left: 4px; }
    .urun-tukendi { font-size: 0.8rem; color: #e74c3c; font-weight: 600; }
    .miktar-kontrol { display: flex; align-items: center; gap: 8px; }
    .miktar-btn { width: 32px; height: 32px; border-radius: 50%; border: 2px solid #1B6CA8;
                  background: white; color: #1B6CA8; font-size: 1.1rem; font-weight: 700;
                  cursor: pointer; display: flex; align-items: center; justify-content: center; }
    .miktar-sayi { font-weight: 700; min-width: 20px; text-align: center; }
    .sepet-footer { position: fixed; bottom: 0; left: 0; right: 0; background: white;
                    border-top: 1px solid #eee; padding: 12px 20px;
                    box-shadow: 0 -4px 12px rgba(0,0,0,.1); z-index: 100; }
    .sepet-satir { display: flex; justify-content: space-between; align-items: center;
                   padding: 6px 0; border-bottom: 1px solid #f5f5f5; }
    .sepet-satir:last-of-type { border-bottom: none; }
    .badge { background: #e74c3c; color: white; border-radius: 50%;
             width: 20px; height: 20px; font-size: 0.7rem; font-weight: 700;
             display: inline-flex; align-items: center; justify-content: center; }
    .toplam-satir { display: flex; justify-content: space-between; font-weight: 700;
                    font-size: 1.05rem; padding: 10px 0 4px; }
    .alert { display:none; } /* eski alert gizli, toast kullanılıyor */

    /* ── Toast Bildirimi ── */
    .toast-wrap {
      position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
      z-index: 9999; pointer-events: none;
      display: flex; flex-direction: column; align-items: center; gap: 10px;
    }
    .toast {
      pointer-events: auto;
      min-width: 200px; max-width: 90vw; width: max-content;
      background: white; border-radius: 14px;
      padding: 14px 18px 10px;
      box-shadow: 0 8px 32px rgba(0,0,0,.18), 0 2px 8px rgba(0,0,0,.1);
      border-left: 4px solid #1B6CA8;
      animation: toastIn .3s cubic-bezier(.34,1.56,.64,1);
      position: relative; overflow: hidden;
    }
    .toast.toast-success { border-left-color: #27ae60; }
    .toast.toast-danger  { border-left-color: #e74c3c; }
    .toast.toast-info    { border-left-color: #1B6CA8; }
    .toast-icon { font-size: 1.1rem; margin-right: 7px; }
    .toast-msg  { font-size: .88rem; font-weight: 600; color: #2c3e50; line-height: 1.4; }
    .toast-bar  {
      position: absolute; bottom: 0; left: 0; height: 3px;
      border-radius: 0 0 0 14px;
      animation: toastBar 3s linear forwards;
    }
    .toast.toast-success .toast-bar { background: #27ae60; }
    .toast.toast-danger  .toast-bar { background: #e74c3c; }
    .toast.toast-info    .toast-bar { background: #1B6CA8; }
    @keyframes toastIn {
      from { opacity: 0; transform: translateY(20px) scale(.92); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes toastBar {
      from { width: 100%; }
      to   { width: 0%; }
    }
    .toast.toast-out {
      animation: toastOut .3s ease forwards;
    }
    @keyframes toastOut {
      to { opacity: 0; transform: translateY(10px) scale(.94); }
    }
    .siparis-durum-badge { display: inline-block; padding: 4px 12px; border-radius: 20px;
                           font-size: 0.8rem; font-weight: 700; }
    .durum-bekliyor      { background: #fff3cd; color: #856404; }
    .durum-hazirlaniyor  { background: #d1ecf1; color: #0c5460; }
    .durum-hazir         { background: #d4edda; color: #155724; }
    .durum-servis        { background: #cce5ff; color: #004085; }
    .pb { padding-bottom: 140px; }
    input[type=text], textarea {
      width: 100%; padding: 10px 12px; border: 1.5px solid #ddd; border-radius: 8px;
      font-size: 0.95rem; margin-top: 6px; outline: none; }
    input:focus, textarea:focus { border-color: #1B6CA8; }
    label { font-size: 0.85rem; font-weight: 600; color: #555; }

    /* Sidebar */
    .layout { display: flex; min-height: 100vh; }
    .sidebar {
      width: 220px; min-width: 220px; background: #0D1B2A;
      display: flex; flex-direction: column;
      position: fixed; top: 0; left: 0; height: 100vh; z-index: 200;
      overflow: hidden;
      transition: width .3s cubic-bezier(.4,0,.2,1), min-width .3s cubic-bezier(.4,0,.2,1);
    }
    .sidebar.kapali { width: 0; min-width: 0; }
    .sidebar-inner { width: 220px; min-width: 220px; display: flex; flex-direction: column;
                     height: 100%; overflow-y: auto; padding: 20px 0; }
    .sidebar-logo {
      color: white; font-size: 1.2rem; font-weight: 800;
      padding: 16px 20px 24px; border-bottom: 1px solid rgba(255,255,255,.1);
      margin-bottom: 10px; white-space: nowrap;
    }
    .sidebar-logo span { color: #4ECDC4; }
    .sidebar a {
      display: flex; align-items: center; gap: 10px;
      color: rgba(255,255,255,.75); text-decoration: none;
      padding: 12px 20px; font-size: 0.95rem; font-weight: 500;
      transition: background .15s; white-space: nowrap;
    }
    .sidebar a:hover, .sidebar a.aktif { background: rgba(255,255,255,.1); color: white; }
    .sidebar a.aktif { border-left: 3px solid #4ECDC4; }
    .sidebar .sep {
      font-size: 0.7rem; font-weight: 700; letter-spacing: 1.5px;
      color: rgba(255,255,255,.3); padding: 16px 20px 4px;
      text-transform: uppercase; white-space: nowrap;
    }
    .main-wrap {
      margin-left: 220px; flex: 1; display: flex; flex-direction: column;
      transition: margin-left .3s cubic-bezier(.4,0,.2,1);
    }
    .main-wrap.genislet { margin-left: 0; }
    .header { position: sticky; top: 0; z-index: 100; }
    .container { max-width: 680px; }
    .toggle-btn {
      background: none; border: none; color: white; font-size: 1.4rem;
      cursor: pointer; padding: 4px 8px; border-radius: 6px; line-height:1;
      transition: background .15s; margin-right: 4px;
    }
    .toggle-btn:hover { background: rgba(255,255,255,.15); }

    /* Mobil: overlay sidebar */
    @media (max-width: 640px) {
      .sidebar { width: 0; min-width: 0; }
      .sidebar.mobil-acik { width: 220px; min-width: 220px; z-index: 300; }
      .main-wrap { margin-left: 0; }
      .mobil-overlay {
        display: block; position: fixed; inset: 0; z-index: 250;
        background: rgba(0,0,0,.45); opacity: 0;
        transition: opacity .3s; pointer-events: none;
      }
      .mobil-overlay.goster { opacity: 1; pointer-events: auto; }
    }
    @media (min-width: 641px) {
      .mobil-overlay { display: none !important; }
    }
  </style>
</head>
<body>
<div class="layout">

  <!-- SOL SIDEBAR -->
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-inner">
      <div class="sidebar-logo">🍽 Anadolu<span> Sofrası</span></div>

      <div class="sep">Sipariş</div>
      <a href="/" class="{{ 'aktif' if aktif_sayfa == 'masalar' else '' }}">🪑 Masalar</a>

      <div class="sep">Menü</div>
      <a href="/menu-listesi" class="{{ 'aktif' if aktif_sayfa == 'menu' else '' }}">📋 Menüyü Gör</a>

      <div class="sep">Hesabım</div>
      <a href="/siparislerim" class="{{ 'aktif' if aktif_sayfa == 'siparislerim' else '' }}">📦 Siparişlerim</a>
      <a href="/rezervasyon" class="{{ 'aktif' if aktif_sayfa == 'rezervasyon' else '' }}">📅 Rezervasyon</a>
      <a href="/bakhsis" class="{{ 'aktif' if aktif_sayfa == 'bakhsis' else '' }}">💰 Garson Bahşişi</a>

      <div style="margin-top:auto;padding:12px 14px;
                  border-top:1px solid rgba(255,255,255,.08)">
        <span style="font-size:.75rem;color:rgba(255,255,255,.3)">v1.0</span>
      </div>
    </div>
  </nav>

  <!-- Mobil karartma -->
  <div class="mobil-overlay" id="mobil-overlay" onclick="sidebarToggle()"></div>

  <!-- SAĞ İÇERİK -->
  <div class="main-wrap" id="main-wrap">
    <div class="header" style="justify-content:space-between">
      <div style="display:flex;align-items:center;gap:4px">
        <button class="toggle-btn" onclick="sidebarToggle()" title="Menüyü Aç/Kapat">☰</button>
        <div>
          <h1>🍽 Anadolu Sofrası</h1>
          <div class="sub">{{ alt_baslik }}</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-shrink:0">
        <span style="font-size:.78rem;color:rgba(255,255,255,.5);white-space:nowrap">
          👤 {{ session.get('kullanici','') }}
        </span>
        <a href="/cikis" style="font-size:.75rem;font-weight:700;color:#ff6b6b;
           background:rgba(255,107,107,.12);border:1px solid rgba(255,107,107,.3);
           padding:5px 12px;border-radius:8px;text-decoration:none;white-space:nowrap;
           transition:all .15s"
           onmouseover="this.style.background='rgba(255,107,107,.25)'"
           onmouseout="this.style.background='rgba(255,107,107,.12)'">Çıkış</a>
      </div>
    </div>
    <div class="container pb">
      {% block icerik %}{% endblock %}
    </div>
    {% block footer %}{% endblock %}
  </div>

</div>
<!-- Toast container -->
<div class="toast-wrap" id="toast-wrap"></div>

<script>
  /* ── Toast sistemi ── */
  var TOAST_ICONS = { success:'✅', danger:'❌', info:'ℹ️', warning:'⚠️' };

  function showToast(msg, tur) {
    tur = tur || 'info';
    var wrap = document.getElementById('toast-wrap');
    var t = document.createElement('div');
    t.className = 'toast toast-' + tur;
    t.innerHTML =
      '<span class="toast-icon">' + (TOAST_ICONS[tur]||'ℹ️') + '</span>' +
      '<span class="toast-msg">' + msg + '</span>' +
      '<div class="toast-bar"></div>';
    wrap.appendChild(t);
    setTimeout(function(){
      t.classList.add('toast-out');
      setTimeout(function(){ if(t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 3000);
  }


  var sb = document.getElementById('sidebar');
  var mw = document.getElementById('main-wrap');
  var ov = document.getElementById('mobil-overlay');
  var mobil = window.matchMedia('(max-width: 640px)').matches;

  if (!mobil && localStorage.getItem('sb') === '0') {
    sb.classList.add('kapali'); mw.classList.add('genislet');
  }

  function sidebarToggle() {
    if (window.matchMedia('(max-width: 640px)').matches) {
      // Mobil: overlay açılır/kapanır
      var acik = sb.classList.toggle('mobil-acik');
      ov.classList.toggle('goster', acik);
    } else {
      // Masaüstü: push sidebar
      sb.classList.toggle('kapali');
      mw.classList.toggle('genislet');
      localStorage.setItem('sb', sb.classList.contains('kapali') ? '0' : '1');
    }
  }
</script>
</body>
</html>
"""

MASA_SEC_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .ms-wrap { max-width: 860px; margin: 0 auto; }
  .ms-hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B3A5C 100%);
    border-radius: 16px; padding: 28px 28px 24px;
    margin-bottom: 20px; color: white;
    display: flex; align-items: center; gap: 18px;
  }
  .ms-hero-icon { font-size: 2.8rem; flex-shrink: 0; }
  .ms-hero h2 { font-size: 1.3rem; font-weight: 800; margin-bottom: 4px; }
  .ms-hero p  { font-size: .85rem; color: rgba(255,255,255,.6); }

  .ms-legend {
    display: flex; gap: 14px; flex-wrap: wrap;
    margin-bottom: 18px;
  }
  .ms-legend-item {
    display: flex; align-items: center; gap: 6px;
    font-size: .78rem; color: #666; font-weight: 500;
  }
  .ms-legend-dot {
    width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;
  }
  .ld-bos   { background: #27ae60; }
  .ld-dolu  { background: #e74c3c; }
  .ld-rezerve { background: #f39c12; }

  .ms-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
  }
  .ms-kart {
    border-radius: 14px; padding: 22px 14px 18px;
    text-align: center; text-decoration: none;
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    font-weight: 700; border: 2px solid transparent;
    transition: transform .18s, box-shadow .18s;
    position: relative;
  }
  .ms-kart.bos {
    background: #f0fdf4; border-color: #86efac; color: #166534;
    cursor: pointer;
  }
  .ms-kart.bos:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 28px rgba(39,174,96,.2);
    background: #dcfce7;
  }
  .ms-kart.benim {
    background: linear-gradient(135deg, #ebf8ff, #dbeafe);
    border-color: #60a5fa; color: #1e40af;
    cursor: pointer;
    animation: benim-parlama 2s ease-in-out infinite;
  }
  .ms-kart.benim:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 28px rgba(59,130,246,.25);
  }
  @keyframes benim-parlama {
    0%, 100% { box-shadow: 0 0 0 0 rgba(96,165,250,.3); }
    50%      { box-shadow: 0 0 16px 4px rgba(96,165,250,.25); }
  }
  .badge-benim { background: #60a5fa; color: white; }

  .ms-kart.dolu {
    background: #fff5f5; border-color: #fca5a5; color: #991b1b;
    cursor: not-allowed; opacity: .85;
  }
  .ms-kart.rezerve {
    background: #fffbeb; border-color: #fcd34d; color: #92400e;
    cursor: not-allowed; opacity: .85;
  }
  .ms-kart-icon { font-size: 1.6rem; }
  .ms-kart-no   { font-size: 1rem; font-weight: 800; }
  .ms-kart-alt  { font-size: .72rem; font-weight: 500; opacity: .75; }
  .ms-kart-badge {
    position: absolute; top: 10px; right: 10px;
    font-size: .62rem; font-weight: 700; padding: 2px 7px;
    border-radius: 20px; text-transform: uppercase; letter-spacing: .4px;
  }
  .badge-bos    { background: #86efac; color: #166534; }
  .badge-dolu   { background: #fca5a5; color: #991b1b; }
  .badge-rezerve{ background: #fcd34d; color: #92400e; }
</style>

{% if mesaj %}
<script>document.addEventListener('DOMContentLoaded',function(){showToast("{{ mesaj }}","{{ mesaj_tur }}");})</script>
{% endif %}

<div class="ms-wrap">
  <div class="ms-hero">
    <div class="ms-hero-icon">🪑</div>
    <div>
      {% if benim_masam %}
        <h2>Masa {{ benim_masam }}'de Oturuyorsunuz</h2>
        <p>Mavi kartınıza tıklayarak sipariş ekleyebilirsiniz.</p>
      {% else %}
        <h2>Masanızı Seçin</h2>
        <p>Yeşil masalar müsaittir. Seçiminizi yapıp menüden sipariş verebilirsiniz.</p>
      {% endif %}
    </div>
  </div>

  <div class="ms-legend">
    <div class="ms-legend-item"><div class="ms-legend-dot ld-bos"></div> Müsait</div>
    <div class="ms-legend-item"><div class="ms-legend-dot ld-dolu"></div> Dolu</div>
    <div class="ms-legend-item"><div class="ms-legend-dot ld-rezerve"></div> Rezerve</div>
    {% if benim_masam %}
    <div class="ms-legend-item"><div class="ms-legend-dot" style="background:#60a5fa"></div> Senin Masan</div>
    {% endif %}
  </div>

  <div class="ms-grid">
    {% for masa in masalar %}
      {% if masa.benim %}
        <a href="/masa/{{ masa.no }}" class="ms-kart benim">
          <span class="ms-kart-badge badge-benim">📍 Senin Masan</span>
          <span class="ms-kart-icon">⭐</span>
          <span class="ms-kart-no">Masa {{ masa.no }}</span>
          <span class="ms-kart-alt">Sipariş vermek için tıkla</span>
        </a>
      {% elif masa.durum == 'Boş' %}
        <a href="/masa/{{ masa.no }}" class="ms-kart bos">
          <span class="ms-kart-badge badge-bos">Müsait</span>
          <span class="ms-kart-icon">🍽</span>
          <span class="ms-kart-no">Masa {{ masa.no }}</span>
          <span class="ms-kart-alt">{{ masa.kapasite }} kişilik</span>
        </a>
      {% elif masa.durum == 'Rezerve' %}
        <span class="ms-kart rezerve">
          <span class="ms-kart-badge badge-rezerve">Rezerve</span>
          <span class="ms-kart-icon">🔒</span>
          <span class="ms-kart-no">Masa {{ masa.no }}</span>
          <span class="ms-kart-alt">{{ masa.kapasite }} kişilik</span>
        </span>
      {% else %}
        <span class="ms-kart dolu">
          <span class="ms-kart-badge badge-dolu">Dolu</span>
          <span class="ms-kart-icon">👥</span>
          <span class="ms-kart-no">Masa {{ masa.no }}</span>
          <span class="ms-kart-alt">{{ masa.kapasite }} kişilik</span>
        </span>
      {% endif %}
    {% endfor %}
  </div>
</div>
""").replace("{{ alt_baslik }}", "Masa Seçimi")

MENU_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .mn-wrap { max-width: 860px; margin: 0 auto; }

  /* Hero */
  .mn-hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B3A5C 100%);
    border-radius: 16px; padding: 22px 24px;
    margin-bottom: 16px; color: white;
    display: flex; align-items: center; gap: 16px;
  }
  .mn-hero-icon { font-size: 2.4rem; flex-shrink: 0; }
  .mn-hero h2  { font-size: 1.2rem; font-weight: 800; margin-bottom: 3px; }
  .mn-hero p   { font-size: .82rem; color: rgba(255,255,255,.6); }

  /* Sepet */
  .mn-sepet {
    background: white; border-radius: 14px; padding: 18px;
    margin-bottom: 14px; border: 2px solid #86efac;
    box-shadow: 0 4px 16px rgba(39,174,96,.12);
  }
  .mn-sepet-title {
    display: flex; align-items: center; gap: 8px;
    font-size: 1rem; font-weight: 800; color: #166534; margin-bottom: 12px;
  }
  .mn-sepet-satir {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 0; border-bottom: 1px solid #f0fdf4; font-size: .9rem;
  }
  .mn-sepet-satir:last-of-type { border-bottom: none; }
  .mn-sepet-item-adi { font-weight: 600; }
  .mn-sepet-adet {
    background: #166534; color: white; border-radius: 50%;
    width: 20px; height: 20px; font-size: .68rem; font-weight: 700;
    display: inline-flex; align-items: center; justify-content: center; margin-left: 6px;
  }
  .mn-sepet-fiyat { font-weight: 700; color: #166534; }
  .mn-sepet-toplam {
    display: flex; justify-content: space-between;
    font-weight: 800; font-size: 1.05rem;
    padding: 10px 0 2px; margin-top: 4px;
    border-top: 2px solid #dcfce7;
  }
  .mn-sepet-actions { display: flex; gap: 10px; margin-top: 12px; }
  .mn-sepet-btn {
    flex: 1; padding: 12px; border: none; border-radius: 10px;
    font-size: .9rem; font-weight: 700; cursor: pointer; text-align: center;
    text-decoration: none; transition: all .15s;
  }
  .mn-sepet-btn-onayla { background: #166534; color: white; }
  .mn-sepet-btn-onayla:hover { background: #14532d; }
  .mn-sepet-btn-iptal  { background: #fff5f5; color: #991b1b; border: 1.5px solid #fca5a5; }
  .mn-sepet-btn-iptal:hover { background: #fee2e2; }

  /* Filtreler */
  .mn-filtreler {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;
    padding: 14px 16px; background: white; border-radius: 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,.06);
  }
  .kat-btn {
    padding: 8px 16px; border-radius: 20px;
    border: 1.5px solid #dde3ea; background: white;
    color: #5d7080; font-size: .82rem; font-weight: 600;
    cursor: pointer; white-space: nowrap; transition: all .15s;
  }
  .kat-btn:hover { border-color: #1B6CA8; color: #1B6CA8; }
  .kat-btn.aktif {
    background: linear-gradient(135deg, #1B6CA8, #2980b9);
    color: white; border-color: transparent;
    box-shadow: 0 3px 10px rgba(27,108,168,.3);
  }

  /* Ürün kartları */
  .urun-kart {
    background: white; border-radius: 14px; padding: 0;
    margin-bottom: 10px; border: 1.5px solid #edf0f5;
    box-shadow: 0 1px 6px rgba(0,0,0,.05);
    transition: box-shadow .15s, border-color .15s;
    overflow: hidden;
  }
  .urun-kart:hover { box-shadow: 0 4px 16px rgba(0,0,0,.1); border-color: #bee3f8; }
  .urun-foto {
    width: 120px; height: 120px; object-fit: cover; border-radius: 10px;
    flex-shrink: 0; margin-left: 12px;
  }
  .urun-kart-body { padding: 14px 16px; display: flex; align-items: center; }
  .kat-blok { }
  .mn-kat-baslik {
    font-size: .7rem; font-weight: 800; letter-spacing: 1.8px;
    text-transform: uppercase; color: #2980b9;
    padding: 14px 0 8px; display: flex; align-items: center; gap: 8px;
  }
  .mn-kat-baslik::after {
    content: ''; flex: 1; height: 1.5px; background: #e8f4fd; border-radius: 2px;
  }
  .urun-item { display: flex; align-items: center; justify-content: space-between; }
  .urun-ad { font-weight: 700; font-size: .95rem; color: #1b2838; }
  .urun-aciklama { font-size: .76rem; color: #95a5a6; margin-top: 3px; }
  .urun-fiyat-wrap { display: flex; align-items: center; gap: 6px; margin-top: 6px; }
  .urun-fiyat { font-size: .92rem; font-weight: 800; color: #1B6CA8; }
  .urun-kampanya { font-size: .76rem; text-decoration: line-through; color: #bbb; }
  .urun-indirim-badge {
    background: linear-gradient(135deg, #e74c3c, #c0392b);
    color: white; font-size: .62rem; padding: 2px 7px;
    border-radius: 20px; font-weight: 700;
  }
  .urun-tukendi {
    font-size: .76rem; color: #e74c3c; font-weight: 700;
    background: #fff5f5; padding: 5px 10px; border-radius: 8px;
    border: 1px solid #fca5a5;
  }
  .ekle-btn {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, #1B6CA8, #2980b9);
    color: white; border: none; font-size: 1.3rem; font-weight: 700;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 3px 10px rgba(27,108,168,.3);
    transition: transform .15s, box-shadow .15s;
  }
  .ekle-btn:hover { transform: scale(1.1); box-shadow: 0 5px 16px rgba(27,108,168,.4); }
</style>

{% if mesaj %}
<script>document.addEventListener('DOMContentLoaded',function(){showToast("{{ mesaj }}","{{ mesaj_tur }}");})</script>
{% endif %}

<div class="mn-wrap">

  <!-- Hero -->
  <div class="mn-hero">
    <div class="mn-hero-icon">🍽</div>
    <div>
      <h2>Masa {{ masa_no }} — Menü</h2>
      <p>İstediğiniz ürünlerin yanındaki + butonuna tıklayın, sepete ekleyin.</p>
    </div>
  </div>

  <!-- Sepet -->
  {% if siparis and siparis.kalemler %}
  <div class="mn-sepet">
    <div class="mn-sepet-title">🛒 Sepetimdekiler</div>
    {% for k in siparis.kalemler %}
    <div class="mn-sepet-satir">
      <span class="mn-sepet-item-adi">{{ k.ad }} <span class="mn-sepet-adet">{{ k.miktar }}</span></span>
      <span class="mn-sepet-fiyat">{{ "%.2f"|format(k.toplam_kdv) }} ₺</span>
    </div>
    {% endfor %}
    <div class="mn-sepet-toplam">
      <span>Toplam <small style="font-weight:400;color:#888">(KDV dahil)</small></span>
      <span style="color:#166534;">{{ "%.2f"|format(siparis.genel_toplam) }} ₺</span>
    </div>
    <div class="mn-sepet-actions">
      <a href="/siparis/{{ siparis.id }}/onayla" class="mn-sepet-btn mn-sepet-btn-onayla">✅ Siparişi Onayla</a>
      <button type="button" class="mn-sepet-btn mn-sepet-btn-iptal"
              onclick="document.getElementById('iptal-modal').style.display='flex'">✕ İptal</button>
    </div>
  </div>

  <!-- İptal Onay Modalı -->
  <div id="iptal-modal" style="display:none;position:fixed;inset:0;z-index:9999;
       background:rgba(0,0,0,.45);backdrop-filter:blur(3px);
       align-items:center;justify-content:center">
    <div style="background:white;border-radius:20px;padding:28px 24px;
                max-width:340px;width:88%;box-shadow:0 24px 64px rgba(0,0,0,.25);
                animation:iptalIn .25s cubic-bezier(.34,1.56,.64,1);text-align:center">
      <div style="font-size:2.6rem;margin-bottom:10px">🗑️</div>
      <h3 style="font-size:1.05rem;font-weight:800;color:#1b2838;margin-bottom:8px">Siparişi İptal Et</h3>
      <p style="font-size:.86rem;color:#7f8c8d;line-height:1.6;margin-bottom:20px">
        Sepetinizdeki tüm ürünler silinecek.<br>
        <strong style="color:#c0392b">Emin misiniz?</strong>
      </p>
      <div style="display:flex;gap:10px">
        <button onclick="document.getElementById('iptal-modal').style.display='none'"
                style="flex:1;padding:13px;border:2px solid #dde3ea;border-radius:12px;
                       background:white;color:#5d7080;font-size:.92rem;font-weight:700;cursor:pointer">
          Hayır
        </button>
        <a href="/siparis/{{ siparis.id }}/iptal"
           style="flex:1;padding:13px;border-radius:12px;text-align:center;
                  background:linear-gradient(135deg,#e74c3c,#c0392b);
                  color:white;font-size:.92rem;font-weight:800;text-decoration:none;
                  box-shadow:0 4px 14px rgba(231,76,60,.3)">
          Evet, İptal Et
        </a>
      </div>
    </div>
  </div>
  <style>
    @keyframes iptalIn {
      from { opacity:0; transform:scale(.88) translateY(16px); }
      to   { opacity:1; transform:scale(1) translateY(0); }
    }
  </style>
  {% endif %}

  <!-- Kategori Filtreleri -->
  <div class="mn-filtreler">
    <button class="kat-btn aktif" onclick="kategoriSec(this, 'tumu')">🍽 Tümü</button>
    {% for kat in kategoriler %}
    <button class="kat-btn" onclick="kategoriSec(this, '{{ kat.id }}')">{{ kat.emoji }} {{ kat.ad }}</button>
    {% endfor %}
  </div>

  <!-- Ürünler -->
  {% set son_kat = namespace(val='') %}
  {% for urun in urunler %}
  <div class="urun-kart kat-blok" data-kat="{{ urun.kategori_id }}">
    {% if urun.kategori != son_kat.val %}
      <div class="mn-kat-baslik" style="padding:14px 16px 8px;">{{ urun.kategori }}</div>
      {% set son_kat.val = urun.kategori %}
    {% endif %}
    <div class="urun-kart-body">
      <div class="urun-item" style="flex:1;min-width:0;">
        <div style="flex:1;min-width:0;">
          <div class="urun-ad">{{ urun.ad }}</div>
          {% if urun.aciklama %}
            <div class="urun-aciklama">{{ urun.aciklama }}</div>
          {% endif %}
          <div class="urun-fiyat-wrap">
            {% if urun.indirim > 0 %}
              <span class="urun-kampanya">{{ "%.2f"|format(urun.fiyat_taban_kdv) }} ₺</span>
              <span class="urun-fiyat">{{ "%.2f"|format(urun.fiyat_kdv) }} ₺</span>
              <span class="urun-indirim-badge">-%{{ urun.indirim|int }}</span>
            {% else %}
              <span class="urun-fiyat">{{ "%.2f"|format(urun.fiyat_kdv) }} ₺</span>
            {% endif %}
          </div>
        </div>
        <img class="urun-foto" src="/static/menu/{{ urun.id }}.jpg"
             onerror="this.src='/static/menu/{{ urun.id }}.webp'; this.onerror=function(){this.src='/static/menu/{{ urun.id }}.gif'; this.onerror=function(){this.style.display='none';};};"
             alt="{{ urun.ad }}">
        <div style="flex-shrink:0; margin-left:14px;">
          {% if urun.tukendi %}
            <span class="urun-tukendi">{{ urun.tukendi_mesaj }}</span>
          {% else %}
            <form method="post" action="/kalem-ekle/{{ siparis.id if siparis else 0 }}/{{ urun.id }}">
              <input type="hidden" name="masa_no" value="{{ masa_no }}">
              <button class="ekle-btn" type="submit">+</button>
            </form>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
  {% endfor %}

</div>

<script>
  function kategoriSec(el, katId) {
    document.querySelectorAll('.kat-btn').forEach(b => b.classList.remove('aktif'));
    el.classList.add('aktif');
    document.querySelectorAll('.kat-blok').forEach(blok => {
      blok.style.display = (katId === 'tumu' || blok.dataset.kat === katId) ? '' : 'none';
    });
  }
</script>
""").replace("{{ alt_baslik }}", "Masa {{ masa_no }} — Menü")

SIPARIS_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .sd-wrap { max-width: 620px; margin: 0 auto; }
  .sd-hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B3A5C 100%);
    border-radius: 16px; padding: 22px 24px; margin-bottom: 16px;
    color: white; display: flex; align-items: center; gap: 16px;
  }
  .sd-hero-icon { font-size: 2.2rem; flex-shrink: 0; }
  .sd-hero h2 { font-size: 1.15rem; font-weight: 800; margin-bottom: 4px; }
  .sd-hero-durum {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: .78rem; padding: 4px 12px; border-radius: 20px;
    font-weight: 700; margin-top: 2px;
  }
  .durum-bekliyor    { background: #fef9ec; color: #b7791f; }
  .durum-hazirlaniyor{ background: #ebf8ff; color: #2b6cb0; }
  .durum-hazir       { background: #f0fff4; color: #276749; }
  .durum-servis      { background: #e8f4fd; color: #2c5282; }

  .sd-kalemler {
    background: white; border-radius: 14px; padding: 18px;
    margin-bottom: 12px; border: 1.5px solid #edf0f5;
    box-shadow: 0 2px 10px rgba(0,0,0,.06);
  }
  .sd-kalem-baslik {
    font-size: .7rem; font-weight: 800; letter-spacing: 1.5px;
    text-transform: uppercase; color: #95a5a6; margin-bottom: 12px;
  }
  .sd-satir {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 0; border-bottom: 1px solid #f8fafc; font-size: .9rem;
  }
  .sd-satir:last-of-type { border-bottom: none; }
  .sd-satir-ad { color: #2c3e50; font-weight: 500; }
  .sd-satir-fiyat { font-weight: 700; color: #1B6CA8; }
  .sd-kdv-satir {
    display: flex; justify-content: space-between;
    padding: 8px 0; font-size: .82rem; color: #95a5a6;
    border-top: 1px dashed #edf0f5; margin-top: 4px;
  }
  .sd-toplam {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 0 0; border-top: 2px solid #edf0f5; margin-top: 4px;
    font-size: 1.1rem; font-weight: 800;
  }
  .sd-toplam-tutar { color: #1B6CA8; font-size: 1.3rem; }

  .sd-back {
    display: flex; align-items: center; gap: 8px;
    background: white; border: 1.5px solid #dde3ea; color: #5d7080;
    padding: 11px 18px; border-radius: 10px; text-decoration: none;
    font-size: .88rem; font-weight: 600; transition: all .15s;
    width: fit-content;
  }
  .sd-back:hover { background: #f0f4f8; color: #2c3e50; border-color: #bcc5ce; }
</style>

<div class="sd-wrap">
  <div class="sd-hero">
    <div class="sd-hero-icon">📋</div>
    <div>
      <h2>Sipariş #{{ siparis.id }} — Masa {{ siparis.masa_no }}</h2>
      <span class="sd-hero-durum durum-{{ siparis.durum_css }}">● {{ siparis.durum }}</span>
    </div>
  </div>

  <div class="sd-kalemler">
    <div class="sd-kalem-baslik">Sipariş Detayı</div>
    {% for k in siparis.kalemler %}
    <div class="sd-satir">
      <span class="sd-satir-ad">{{ k.ad }} <span style="color:#95a5a6">× {{ k.miktar }}</span></span>
      <span class="sd-satir-fiyat">{{ "%.2f"|format(k.toplam_kdv) }} ₺</span>
    </div>
    {% endfor %}
    <div class="sd-kdv-satir">
      <span>KDV (%10)</span>
      <span>{{ "%.2f"|format(siparis.kdv) }} ₺</span>
    </div>
    <div class="sd-toplam">
      <span>Toplam</span>
      <span class="sd-toplam-tutar">{{ "%.2f"|format(siparis.genel_toplam) }} ₺</span>
    </div>
  </div>

  <a href="/masa/{{ siparis.masa_no }}" class="sd-back">← Menüye Dön</a>
</div>
""").replace("{{ alt_baslik }}", "Siparişim")

ONAY_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .onay-wrap { max-width: 520px; margin: 0 auto; }
  .onay-card {
    background: white; border-radius: 20px; padding: 40px 28px;
    text-align: center; border: 2px solid #86efac;
    box-shadow: 0 8px 32px rgba(39,174,96,.15); margin-bottom: 14px;
  }
  .onay-icon-ring {
    width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 18px;
    background: linear-gradient(135deg, #166534, #27ae60);
    display: flex; align-items: center; justify-content: center;
    font-size: 2.2rem;
    box-shadow: 0 6px 20px rgba(39,174,96,.3);
  }
  .onay-baslik { font-size: 1.4rem; font-weight: 900; color: #166534; margin-bottom: 6px; }
  .onay-alt    { font-size: .88rem; color: #95a5a6; margin-bottom: 18px; }
  .onay-no {
    background: #f0fdf4; border: 1.5px solid #86efac;
    border-radius: 10px; padding: 10px 18px; display: inline-block;
    font-size: .88rem; color: #166534;
  }
  .onay-no strong { font-size: 1.05rem; }
  .onay-actions { display: flex; flex-direction: column; gap: 10px; }
  .onay-btn {
    padding: 14px; border-radius: 12px; text-decoration: none;
    font-size: .95rem; font-weight: 700; text-align: center; transition: all .15s;
  }
  .onay-btn-takip {
    background: linear-gradient(135deg, #1B6CA8, #2980b9);
    color: white; box-shadow: 0 4px 14px rgba(27,108,168,.3);
  }
  .onay-btn-takip:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(27,108,168,.4); }
  .onay-btn-ana {
    background: white; color: #5d7080;
    border: 1.5px solid #dde3ea;
  }
  .onay-btn-ana:hover { background: #f0f4f8; }
</style>

<div class="onay-wrap">
  <div class="onay-card">
    <div class="onay-icon-ring">✓</div>
    <div class="onay-baslik">Sipariş Alındı!</div>
    <div class="onay-alt">Siparişiniz mutfağa iletildi, en kısa sürede hazırlanacak.</div>
    <div class="onay-no">Sipariş No: <strong>#{{ siparis_id }}</strong></div>
  </div>
  <div class="onay-actions">
    <a href="/siparis/{{ siparis_id }}" class="onay-btn onay-btn-takip">📍 Sipariş Durumunu Takip Et</a>
    <a href="/" class="onay-btn onay-btn-ana">← Ana Sayfaya Dön</a>
  </div>
</div>
""").replace("{{ alt_baslik }}", "Teşekkürler!")

NOT_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .not-wrap { max-width: 520px; margin: 0 auto; }
  .not-hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B3A5C 100%);
    border-radius: 16px; padding: 20px 24px; margin-bottom: 16px;
    color: white; display: flex; align-items: center; gap: 14px;
  }
  .not-hero-icon { font-size: 2rem; }
  .not-hero h2 { font-size: 1.1rem; font-weight: 800; margin-bottom: 2px; }
  .not-hero p  { font-size: .8rem; color: rgba(255,255,255,.6); }
  .not-card {
    background: white; border-radius: 14px; padding: 22px;
    border: 1.5px solid #edf0f5;
    box-shadow: 0 2px 10px rgba(0,0,0,.06); margin-bottom: 12px;
  }
  .not-field { margin-bottom: 16px; }
  .not-label {
    display: block; font-size: .78rem; font-weight: 700;
    color: #5d7080; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .5px;
  }
  .not-input {
    width: 100%; padding: 10px 13px; border: 1.5px solid #dde3ea;
    border-radius: 10px; font-size: .92rem; color: #2c3e50; transition: border .15s;
  }
  .not-input:focus { border-color: #2980b9; outline: none; box-shadow: 0 0 0 3px rgba(41,128,185,.1); }
  .not-adet { width: 90px !important; }
  .not-ekle-btn {
    width: 100%; padding: 13px; border: none; border-radius: 12px;
    background: linear-gradient(135deg, #1B6CA8, #2980b9);
    color: white; font-size: .95rem; font-weight: 700;
    cursor: pointer; box-shadow: 0 4px 14px rgba(27,108,168,.3);
    transition: all .15s;
  }
  .not-ekle-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(27,108,168,.4); }
  .not-back {
    display: flex; align-items: center; gap: 8px;
    background: white; border: 1.5px solid #dde3ea; color: #5d7080;
    padding: 11px 18px; border-radius: 10px; text-decoration: none;
    font-size: .88rem; font-weight: 600; transition: all .15s; width: fit-content;
  }
  .not-back:hover { background: #f0f4f8; }
</style>

<div class="not-wrap">
  <div class="not-hero">
    <div class="not-hero-icon">🛒</div>
    <div>
      <h2>Sepete Ekle</h2>
      <p>{{ urun_ad }}</p>
    </div>
  </div>

  <div class="not-card">
    <form method="post" action="{{ '/masa/' ~ masa_no ~ '/ilk-kalem-not/' ~ menu_id if ilk_kalem else '/kalem-ekle-not/' ~ siparis_id ~ '/' ~ menu_id }}">
      <input type="hidden" name="masa_no" value="{{ masa_no }}">
      <div class="not-field">
        <label class="not-label">Adet</label>
        <input class="not-input not-adet" type="number" name="miktar" value="1" min="1" max="20">
      </div>
      <div class="not-field">
        <label class="not-label">Özel Not <span style="font-weight:400;color:#bbb">(isteğe bağlı)</span></label>
        <input class="not-input" type="text" name="not_" placeholder="Örn: az tuzlu, iyi pişmiş...">
      </div>
      <button type="submit" class="not-ekle-btn">+ Sepete Ekle</button>
    </form>
  </div>
  <a href="/masa/{{ masa_no }}" class="not-back">← İptal</a>
</div>
""").replace("{{ alt_baslik }}", "Sepete Ekle")


REZERVASYON_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .rv-wrap { max-width: 500px; margin: 0 auto; }
  .rv-hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B3A5C 100%);
    border-radius: 16px; padding: 26px 24px; margin-bottom: 20px;
    color: white; text-align: center;
  }
  .rv-hero-icon { font-size: 2.8rem; margin-bottom: 10px; }
  .rv-hero h2  { font-size: 1.2rem; font-weight: 800; margin-bottom: 6px; }
  .rv-hero p   { font-size: .84rem; color: rgba(255,255,255,.6); line-height: 1.5; }

  .rv-card {
    background: white; border-radius: 14px; padding: 22px;
    border: 1.5px solid #edf0f5; box-shadow: 0 2px 10px rgba(0,0,0,.06);
    margin-bottom: 14px;
  }
  .rv-field { margin-bottom: 16px; }
  .rv-label {
    display: block; font-size: .78rem; font-weight: 700;
    color: #5d7080; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .5px;
  }
  .rv-input {
    width: 100%; padding: 11px 14px; border: 2px solid #dde3ea;
    border-radius: 10px; font-size: .95rem; color: #2c3e50;
    outline: none; transition: border .15s; background: white;
  }
  .rv-input:focus { border-color: #1B6CA8; box-shadow: 0 0 0 3px rgba(27,108,168,.1); }
  .rv-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .rv-btn {
    width: 100%; padding: 14px; border: none; border-radius: 12px;
    background: linear-gradient(135deg, #1B6CA8, #2980b9);
    color: white; font-size: .95rem; font-weight: 800;
    cursor: pointer; box-shadow: 0 4px 14px rgba(27,108,168,.3);
    transition: all .15s;
  }
  .rv-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(27,108,168,.4); }

  .rv-onay {
    text-align: center; padding: 28px 16px;
  }
  .rv-onay-icon {
    width: 72px; height: 72px; border-radius: 50%; margin: 0 auto 16px;
    background: linear-gradient(135deg, #27ae60, #2ecc71);
    display: flex; align-items: center; justify-content: center; font-size: 2rem;
    box-shadow: 0 6px 20px rgba(39,174,96,.4);
  }
  .rv-onay h3 { font-size: 1.2rem; font-weight: 800; color: #1b2838; margin-bottom: 8px; }
  .rv-onay p  { font-size: .88rem; color: #7f8c8d; line-height: 1.6; }
  .rv-detay {
    background: #f0fff4; border: 1.5px solid #86efac; border-radius: 12px;
    padding: 14px 18px; margin: 16px 0; text-align: left;
  }
  .rv-detay-satir {
    display: flex; justify-content: space-between;
    font-size: .88rem; padding: 5px 0; border-bottom: 1px solid #dcfce7;
  }
  .rv-detay-satir:last-child { border-bottom: none; }
  .rv-detay-satir span:first-child { color: #7f8c8d; }
  .rv-detay-satir span:last-child  { font-weight: 700; color: #166534; }
</style>

<div class="rv-wrap">
  {% if onaylandi %}
  <div class="rv-card">
    <div class="rv-onay">
      <div class="rv-onay-icon">📅</div>
      <h3>Rezervasyonunuz Alındı!</h3>
      <p>Sizi bekliyoruz. Lütfen belirtilen saatte restoranda olunuz.</p>
      <div class="rv-detay">
        <div class="rv-detay-satir"><span>📅 Tarih</span><span>{{ rv_tarih }}</span></div>
        <div class="rv-detay-satir"><span>🕐 Saat</span><span>{{ rv_saat }}</span></div>
        <div class="rv-detay-satir"><span>👥 Kişi</span><span>{{ rv_kisi }} kişi</span></div>
        <div class="rv-detay-satir"><span>🪑 Masa</span><span>Masa {{ rv_masa }}</span></div>
      </div>
      <a href="/rezervasyon" style="display:inline-block;margin-top:8px;padding:11px 24px;
         border-radius:10px;background:linear-gradient(135deg,#1B6CA8,#2980b9);
         color:white;font-weight:700;text-decoration:none;font-size:.9rem">
        Yeni Rezervasyon
      </a>
    </div>
  </div>
  {% else %}
  <div class="rv-hero">
    <div class="rv-hero-icon">📅</div>
    <h2>Masa Rezervasyonu</h2>
    <p>Tarih, saat ve kişi sayısını girin.<br>Size uygun masayı otomatik ayarlayalım.</p>
  </div>

  {% if hata %}
  <script>document.addEventListener('DOMContentLoaded',function(){showToast("{{ hata }}","danger");});</script>
  {% endif %}
  <form method="post" action="/rezervasyon">
    <div class="rv-card">
      <div class="rv-row">
        <div class="rv-field">
          <label class="rv-label">📅 Tarih</label>
          <input class="rv-input" type="date" name="tarih" required
                 min="{{ bugun }}" value="{{ bugun }}">
        </div>
        <div class="rv-field">
          <label class="rv-label">🕐 Saat</label>
          <input class="rv-input" type="time" name="saat" required value="19:00">
        </div>
      </div>
      <div class="rv-field">
        <label class="rv-label">👥 Kişi Sayısı</label>
        <input class="rv-input" type="number" name="kisi" min="1" max="20" value="2" required>
      </div>
      <div class="rv-field">
        <label class="rv-label">📞 Telefon <span style="font-weight:400;color:#bbb">(isteğe bağlı)</span></label>
        <input class="rv-input" type="tel" name="telefon" placeholder="05xx xxx xx xx" inputmode="numeric" pattern="[0-9 +()\-]*" oninput="this.value=this.value.replace(/[^0-9 +()\-]/g,'')">
      </div>
      <div class="rv-field">
        <label class="rv-label">📝 Not <span style="font-weight:400;color:#bbb">(isteğe bağlı)</span></label>
        <input class="rv-input" type="text" name="not_" placeholder="Doğum günü, özel istek...">
      </div>
      <button type="submit" class="rv-btn">📅 Rezervasyon Yap</button>
    </div>
  </form>
  {% endif %}
</div>
""").replace("{{ alt_baslik }}", "Rezervasyon")


BAKHSIS_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<style>
  .bk-wrap { max-width: 480px; margin: 0 auto; }

  .bk-hero {
    background: linear-gradient(135deg, #7B2FBE 0%, #4A1070 100%);
    border-radius: 16px; padding: 28px 24px;
    margin-bottom: 20px; color: white; text-align: center;
  }
  .bk-hero-icon { font-size: 3rem; margin-bottom: 10px; }
  .bk-hero h2  { font-size: 1.3rem; font-weight: 800; margin-bottom: 6px; }
  .bk-hero p   { font-size: .85rem; color: rgba(255,255,255,.65); line-height: 1.5; }

  .bk-card {
    background: white; border-radius: 14px; padding: 22px;
    border: 1.5px solid #edf0f5;
    box-shadow: 0 2px 10px rgba(0,0,0,.06); margin-bottom: 14px;
  }
  .bk-card-title {
    font-size: .72rem; font-weight: 800; letter-spacing: 1.5px;
    text-transform: uppercase; color: #95a5a6; margin-bottom: 16px;
  }

  /* Hızlı tutar butonları */
  .bk-hizli { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
  .bk-hizli-btn {
    padding: 14px 8px; border-radius: 12px;
    border: 2px solid #e8d5f8; background: #faf5ff;
    color: #7B2FBE; font-size: .92rem; font-weight: 800;
    cursor: pointer; text-align: center; transition: all .15s;
  }
  .bk-hizli-btn:hover, .bk-hizli-btn.secili {
    background: linear-gradient(135deg, #7B2FBE, #9B59B6);
    color: white; border-color: transparent;
    box-shadow: 0 4px 14px rgba(123,47,190,.35);
  }

  /* Manuel giriş */
  .bk-tutar-wrap {
    display: flex; align-items: center; gap: 0;
    border: 2px solid #dde3ea; border-radius: 12px; overflow: hidden;
    transition: border-color .15s;
  }
  .bk-tutar-wrap:focus-within { border-color: #7B2FBE; box-shadow: 0 0 0 3px rgba(123,47,190,.12); }
  .bk-tutar-lira {
    padding: 12px 14px; background: #f9f5ff; color: #7B2FBE;
    font-size: 1.1rem; font-weight: 800; border-right: 2px solid #e8d5f8;
  }
  .bk-tutar-input {
    flex: 1; padding: 12px 14px; border: none; font-size: 1.1rem;
    font-weight: 700; color: #2c3e50; outline: none; background: white;
  }

  /* Not alanı */
  .bk-not-input {
    width: 100%; padding: 11px 14px; border: 2px solid #dde3ea;
    border-radius: 12px; font-size: .92rem; color: #2c3e50;
    outline: none; transition: border .15s; margin-top: 14px;
  }
  .bk-not-input:focus { border-color: #7B2FBE; box-shadow: 0 0 0 3px rgba(123,47,190,.12); }

  /* Gönder butonu */
  .bk-gonder {
    width: 100%; padding: 14px; border: none; border-radius: 12px;
    background: linear-gradient(135deg, #7B2FBE, #9B59B6);
    color: white; font-size: 1rem; font-weight: 800;
    cursor: pointer; box-shadow: 0 4px 14px rgba(123,47,190,.35);
    transition: all .15s; margin-top: 4px;
  }
  .bk-gonder:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(123,47,190,.45); }
  .bk-gonder:active { transform: none; }

  /* Teşekkür ekranı */
  .bk-tesekkur {
    text-align: center; padding: 32px 16px;
  }
  .bk-tesekkur-icon {
    width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 18px;
    background: linear-gradient(135deg, #7B2FBE, #9B59B6);
    display: flex; align-items: center; justify-content: center; font-size: 2.2rem;
    box-shadow: 0 8px 24px rgba(123,47,190,.4);
  }
  .bk-tesekkur h3 { font-size: 1.3rem; font-weight: 800; color: #2c3e50; margin-bottom: 8px; }
  .bk-tesekkur p  { font-size: .9rem; color: #7f8c8d; line-height: 1.6; }
  .bk-tesekkur-tutar {
    display: inline-block; background: #faf5ff; color: #7B2FBE;
    font-size: 1.5rem; font-weight: 800; padding: 10px 28px;
    border-radius: 50px; border: 2px solid #e8d5f8; margin: 14px 0 20px;
  }
  .bk-yeni-btn {
    display: inline-block; padding: 12px 28px; border-radius: 12px;
    background: linear-gradient(135deg, #7B2FBE, #9B59B6);
    color: white; font-size: .92rem; font-weight: 700;
    text-decoration: none; box-shadow: 0 4px 14px rgba(123,47,190,.3);
    transition: all .15s;
  }
  .bk-yeni-btn:hover { transform: translateY(-2px); }
</style>

<div class="bk-wrap">

  {% if gonderildi %}
  <!-- Teşekkür ekranı -->
  <div class="bk-card">
    <div class="bk-tesekkur">
      <div class="bk-tesekkur-icon">🌟</div>
      <h3>Teşekkürler!</h3>
      <p>Garsonumuza bahşiş gönderdiniz.<br>Bu nezaketten dolayı çok mutlu olduk!</p>
      <div class="bk-tesekkur-tutar">{{ "%.2f"|format(gonderilen_tutar) }} ₺</div>
      <br>
      <a href="/bakhsis" class="bk-yeni-btn">Tekrar Bahşiş Gönder</a>
    </div>
  </div>
  {% else %}
  <!-- Hero -->
  <div class="bk-hero">
    <div class="bk-hero-icon">💰</div>
    <h2>Garson Bahşişi</h2>
    <p>Hizmetinizden memnun kaldıysanız garsonumuza<br>teşekkürünüzü bahşiş olarak iletebilirsiniz.</p>
  </div>

  <form method="post" action="/bakhsis" id="bkForm">
    <div class="bk-card">
      <div class="bk-card-title">Hızlı Seçim</div>
      <div class="bk-hizli">
        <button type="button" class="bk-hizli-btn" onclick="hizliSec(this, 10)">₺10</button>
        <button type="button" class="bk-hizli-btn" onclick="hizliSec(this, 20)">₺20</button>
        <button type="button" class="bk-hizli-btn" onclick="hizliSec(this, 50)">₺50</button>
        <button type="button" class="bk-hizli-btn" onclick="hizliSec(this, 100)">₺100</button>
      </div>
      <div class="bk-card-title" style="margin-bottom:10px">Tutar Girin</div>
      <div class="bk-tutar-wrap">
        <div class="bk-tutar-lira">₺</div>
        <input class="bk-tutar-input" type="number" id="tutarInput" name="tutar"
               min="1" max="9999" placeholder="0" required>
      </div>
      <input class="bk-not-input" type="text" name="not_" maxlength="100"
             placeholder="Teşekkür notu (isteğe bağlı)...">
    </div>

    <button type="submit" class="bk-gonder">🌟 Bahşiş Gönder</button>
  </form>
  {% endif %}

</div>

<script>
  function hizliSec(btn, tutar) {
    document.querySelectorAll('.bk-hizli-btn').forEach(b => b.classList.remove('secili'));
    btn.classList.add('secili');
    document.getElementById('tutarInput').value = tutar;
  }
</script>
""").replace("{{ alt_baslik }}", "Garson Bahşişi")


# ─── Yardımcı: sipariş bilgisi ──────────────────────────────────────

def _siparis_bilgi(siparis):
    kalemler = []
    for k in siparis.kalemler:
        kalemler.append({
            "ad": k.menu_ogesi.ad,
            "miktar": k.miktar,
            "toplam_kdv": k.toplam * 1.10,
        })
    durum_css_map = {
        "Bekliyor": "bekliyor",
        "Hazırlanıyor": "hazirlaniyor",
        "Hazır": "hazir",
        "Servis Edildi": "servis",
        "Garson Aldı": "servis",
    }
    return {
        "id": siparis.id,
        "masa_no": siparis.masa_no,
        "kalemler": kalemler,
        "durum": siparis.durum.value,
        "durum_css": durum_css_map.get(siparis.durum.value, "bekliyor"),
        "kdv": siparis.kdv,
        "genel_toplam": siparis.genel_toplam,
    }


def _sepet_bilgi(siparis):
    """Sepetteki kalemlerin listesi (şablon için)."""
    kalemler = []
    for k in siparis.kalemler:
        kalemler.append({
            "ad": k.menu_ogesi.ad,
            "miktar": k.miktar,
            "toplam_kdv": k.toplam * 1.10,
        })
    return {
        "id": siparis.id,
        "masa_no": siparis.masa_no,
        "kalemler": kalemler,
        "genel_toplam": siparis.genel_toplam,
    }


# ─── Routes ────────────────────────────────────────────────────────

@app.route("/")
def ana_sayfa():
    if "kullanici" not in session:
        return redirect("/giris")
    rol = session.get("rol","musteri")
    if rol in PERSONEL_ROLLER:
        return redirect("/personel/mutfak")
    # Müşterinin masası hâlâ geçerli mi kontrol et
    benim_masam = session.get("masa_no")
    if benim_masam:
        sy = _sy()
        masa = sy.masalar.get(benim_masam)
        if not masa or masa.durum != MasaDurumu.DOLU:
            session.pop("masa_no", None)
            session.modified = True
            storage.musteri_masa_sil(session.get("kullanici",""))
    # Müşteri ana sayfası → masa seçimi
    return masa_sec_goster()

def masa_sec_goster():
    sy = _sy()
    benim_masam = session.get("masa_no")  # müşterinin oturduğu masa
    masalar = [
        {"no": m.no, "kapasite": m.kapasite, "durum": m.durum.value,
         "benim": (m.no == benim_masam)}
        for m in sorted(sy.masalar.values(), key=lambda x: x.no)
    ]
    mesaj     = request.args.get("mesaj", "")
    mesaj_tur = request.args.get("tur", "info")
    return render_template_string(
        MASA_SEC_HTML,
        alt_baslik="Masa Seçimi",
        aktif_sayfa="masalar",
        masalar=masalar,
        benim_masam=benim_masam,
        mesaj=mesaj,
        mesaj_tur=mesaj_tur,
        kullanici=session.get("kullanici",""),
    )


@app.route("/masa/<int:masa_no>")
@musteri_gerekli
def menu_goster(masa_no):
    my = _my()
    sy = _sy(my)
    mesaj     = request.args.get("mesaj", "")
    mesaj_tur = request.args.get("tur", "info")

    # Müşteri zaten başka masada oturuyor mu?
    benim_masam = session.get("masa_no")
    if benim_masam and benim_masam != masa_no:
        return redirect(url_for("ana_sayfa",
            mesaj=f"Zaten Masa {benim_masam}'de oturuyorsunuz! Önce mevcut siparişinizi tamamlayın.",
            tur="danger"))

    masa = sy.masalar.get(masa_no)
    if not masa:
        return redirect(url_for("ana_sayfa", mesaj="Masa bulunamadı.", tur="danger"))
    if masa.durum.value == "Rezerve":
        return redirect(url_for("ana_sayfa", mesaj="Bu masa rezerve edilmiş.", tur="danger"))
    if masa.durum.value == "Dolu":
        # Kendi masası mı?
        if benim_masam == masa_no:
            if masa.aktif_siparis_id:
                s = sy.siparis_bul(masa.aktif_siparis_id)
                if s:
                    if s.durum.value == "Bekliyor":
                        # Sepete ekleme yapabilir
                        return redirect(url_for("siparis_menu", siparis_id=masa.aktif_siparis_id))
                    elif s.durum.value in ("Ödendi", "İptal"):
                        # Bu sipariş kapanmış ama masada başka aktif sipariş olabilir
                        aktif_var = any(
                            sp.masa_no == masa_no
                            and sp.durum.value not in ("Ödendi", "İptal")
                            for sp in sy.siparisler.values()
                        )
                        if aktif_var:
                            # Hâlâ aktif sipariş var → masayı boşaltma, menüyü göster
                            pass
                        else:
                            masa.durum = MasaDurumu.BOS
                            masa.aktif_siparis_id = None
                            storage.masalar_kaydet(sy.masalar)
                        # Aşağı düş, menüyü göster
                    else:
                        # Hazırlanıyor/Hazır/Servis → menüyü aç, yeni sipariş verebilsin
                        # Masayı boşaltma! Dolu kalsın.
                        pass
            else:
                pass  # aktif_siparis_id yok ama dolu ve benim masam → menüyü göster
        else:
            # Başkasının masası
            return redirect(url_for("ana_sayfa", mesaj="Bu masa dolu.", tur="danger"))

    # Boş masa (veya kendi masası yeniden açıldı): menüyü göster
    KAT_EMOJI = {"Başlangıç":"🥣","Ana Yemek":"🍖","Pizza":"🍕",
                 "Salata":"🥗","Tatlı":"🍮","İçecek":"🥤","Diğer":"🍽"}
    maly = _maly()
    urunler = []
    kategoriler_dict = {}
    for o in my.kategoriye_gore_listele():
        if not o.mevcut:
            continue
        kat_id = o.kategori.value.replace(" ","_").replace("ı","i").replace("İ","I")
        tukendi = (o.stok == 0) or (not maly.yapilabilir_mi(o.ad))
        urunler.append({
            "id": o.id, "ad": o.ad,
            "kategori": o.kategori.value, "kategori_id": kat_id,
            "aciklama": o.aciklama,
            "fiyat_kdv": o.kdv_dahil_fiyat,
            "fiyat_taban_kdv": o.kdv_dahil_taban,
            "indirim": o.indirim_yuzdesi, "tukendi": tukendi,
            "tukendi_mesaj": "Tükendi" if o.stok == 0 else "Yeterli stok yok",
        })
        if kat_id not in kategoriler_dict:
            kategoriler_dict[kat_id] = {
                "id": kat_id, "ad": o.kategori.value,
                "emoji": KAT_EMOJI.get(o.kategori.value, "🍽"),
            }

    # + butonu /masa/<no>/ilk-kalem/<menu_id> adresine POST eder
    HTML = MENU_HTML.replace(
        'action="/kalem-ekle/{{ siparis.id if siparis else 0 }}/{{ urun.id }}"',
        'action="/masa/{{ masa_no }}/ilk-kalem/{{ urun.id }}"'
    )
    return render_template_string(HTML,
        alt_baslik=f"Masa {masa_no} — Menü",
        aktif_sayfa="masalar",
        masa_no=masa_no, siparis=None,
        urunler=urunler, kategoriler=list(kategoriler_dict.values()),
        mesaj=mesaj, mesaj_tur=mesaj_tur)


@app.route("/masa/<int:masa_no>/ilk-kalem/<int:menu_id>", methods=["POST"])
@musteri_gerekli
def ilk_kalem_ekle(masa_no, menu_id):
    """İlk ürün için not/miktar sayfasını göster."""
    my = _my()
    sy = _sy(my)
    masa = sy.masalar.get(masa_no)
    if not masa:
        return redirect(url_for("ana_sayfa", mesaj="Masa bulunamadı.", tur="danger"))
    benim_masam = session.get("masa_no")
    if masa.durum.value == "Dolu" and benim_masam != masa_no:
        return redirect(url_for("ana_sayfa", mesaj="Bu masa dolu.", tur="danger"))
    if masa.durum.value == "Rezerve":
        return redirect(url_for("ana_sayfa", mesaj="Bu masa rezerve.", tur="danger"))
    oge = my.oge_bul(menu_id)
    urun_ad = oge.ad if oge else "Ürün"
    return render_template_string(
        NOT_HTML,
        alt_baslik="Sepete Ekle",
        aktif_sayfa="masalar",
        siparis_id=0,
        menu_id=menu_id,
        masa_no=masa_no,
        urun_ad=urun_ad,
        ilk_kalem=True,
    )


@app.route("/masa/<int:masa_no>/ilk-kalem-not/<int:menu_id>", methods=["POST"])
@musteri_gerekli
def ilk_kalem_not_ekle(masa_no, menu_id):
    """Not/miktar onayı sonrası siparişi oluştur ve kalemi ekle."""
    miktar = request.form.get("miktar", 1, type=int)
    not_   = request.form.get("not_", "")
    my = _my()
    sy = _sy(my)

    masa = sy.masalar.get(masa_no)
    if not masa:
        return redirect(url_for("ana_sayfa", mesaj="Masa bulunamadı.", tur="danger"))
    benim_masam = session.get("masa_no")
    if masa.durum.value == "Dolu" and benim_masam != masa_no:
        return redirect(url_for("ana_sayfa", mesaj="Bu masa dolu.", tur="danger"))
    if masa.durum.value == "Rezerve":
        return redirect(url_for("ana_sayfa", mesaj="Bu masa rezerve.", tur="danger"))

    ek = (masa.durum.value == "Dolu" and benim_masam == masa_no)
    siparis, mesaj_s = sy.siparis_olustur(masa_no=masa_no, ek_siparis=ek)
    if not siparis:
        return redirect(url_for("ana_sayfa", mesaj=mesaj_s, tur="danger"))

    ok, mesaj = sy.kalem_ekle(siparis.id, menu_id, miktar, not_)
    session["masa_no"] = masa_no
    sip_listesi = session.get("siparislerim", [])
    if siparis.id not in sip_listesi:
        sip_listesi.append(siparis.id)
        session["siparislerim"] = sip_listesi
    session.modified = True
    # Kalıcı olarak kaydet (çıkış/yeniden giriş sonrası geri yüklemek için)
    storage.musteri_masa_kaydet(session["kullanici"], masa_no, sip_listesi)
    tur = "success" if ok else "danger"
    return redirect(url_for("siparis_menu", siparis_id=siparis.id, mesaj=mesaj, tur=tur))


@app.route("/siparis/<int:siparis_id>/menu")
def siparis_menu(siparis_id):
    mesaj     = request.args.get("mesaj", "")
    mesaj_tur = request.args.get("tur", "info")
    my = _my()
    sy = _sy(my)

    siparis = sy.siparis_bul(siparis_id)
    if not siparis:
        return redirect(url_for("masa_sec", mesaj="Sipariş bulunamadı.", tur="danger"))
    if siparis.durum.value not in ("Bekliyor",):
        return redirect(url_for("siparis_goster", siparis_id=siparis_id))

    KAT_EMOJI = {
        "Başlangıç": "🥣",
        "Ana Yemek": "🍖",
        "Pizza":     "🍕",
        "Salata":    "🥗",
        "Tatlı":     "🍮",
        "İçecek":    "🥤",
        "Diğer":     "🍽",
    }

    maly = _maly()
    urunler = []
    kategoriler_dict = {}
    for o in my.kategoriye_gore_listele():
        if not o.mevcut:
            continue
        kat_id = o.kategori.value.replace(" ", "_").replace("ı","i").replace("İ","I")
        # Stok kontrolü: sayılı stok bittiyse VEYA malzeme yetersizse tükendi
        tukendi = (o.stok == 0) or (not maly.yapilabilir_mi(o.ad))
        urunler.append({
            "id": o.id,
            "ad": o.ad,
            "kategori": o.kategori.value,
            "kategori_id": kat_id,
            "aciklama": o.aciklama,
            "fiyat_kdv": o.kdv_dahil_fiyat,
            "fiyat_taban_kdv": o.kdv_dahil_taban,
            "indirim": o.indirim_yuzdesi,
            "tukendi": tukendi,
        })
        if kat_id not in kategoriler_dict:
            kategoriler_dict[kat_id] = {
                "id": kat_id,
                "ad": o.kategori.value,
                "emoji": KAT_EMOJI.get(o.kategori.value, "🍽"),
            }

    return render_template_string(
        MENU_HTML,
        alt_baslik=f"Masa {siparis.masa_no} — Menü",
        aktif_sayfa="masalar",
        masa_no=siparis.masa_no,
        siparis=_sepet_bilgi(siparis),
        urunler=urunler,
        kategoriler=list(kategoriler_dict.values()),
        mesaj=mesaj,
        mesaj_tur=mesaj_tur,
    )


@app.route("/kalem-ekle/<int:siparis_id>/<int:menu_id>", methods=["POST"])
def kalem_ekle(siparis_id, menu_id):
    masa_no = request.form.get("masa_no", type=int)
    # Not eklemek için ara sayfa göster
    my = _my()
    oge = my.oge_bul(menu_id)
    urun_ad = oge.ad if oge else "Ürün"
    return render_template_string(
        NOT_HTML,
        alt_baslik="Sepete Ekle",
        aktif_sayfa="masalar",
        siparis_id=siparis_id,
        menu_id=menu_id,
        masa_no=masa_no,
        urun_ad=urun_ad,
        ilk_kalem=False,
    )


@app.route("/kalem-ekle-not/<int:siparis_id>/<int:menu_id>", methods=["POST"])
def kalem_ekle_not(siparis_id, menu_id):
    masa_no = request.form.get("masa_no", type=int)
    miktar  = request.form.get("miktar", 1, type=int)
    not_    = request.form.get("not_", "")

    my = _my()
    sy = _sy(my)
    ok, mesaj = sy.kalem_ekle(siparis_id, menu_id, miktar, not_)
    tur = "success" if ok else "danger"
    return redirect(url_for("siparis_menu", siparis_id=siparis_id, mesaj=mesaj, tur=tur))


@app.route("/siparis/<int:siparis_id>/onayla")
def siparis_onayla(siparis_id):
    my = _my()
    sy = _sy(my)
    siparis = sy.siparis_bul(siparis_id)
    if not siparis or not siparis.kalemler:
        return redirect(url_for("masa_sec", mesaj="Boş sipariş onaylanamaz.", tur="danger"))
    sy.durum_guncelle(siparis_id, SiparisDurumu.HAZIRLANIYOR)
    return render_template_string(
        ONAY_HTML,
        alt_baslik="Teşekkürler!",
        aktif_sayfa="masalar",
        siparis_id=siparis_id,
    )


@app.route("/siparis/<int:siparis_id>/iptal")
def siparis_iptal(siparis_id):
    sy = _sy()
    s = sy.siparis_bul(siparis_id)
    sy.durum_guncelle(siparis_id, SiparisDurumu.IPTAL)
    # Masada başka aktif sipariş kalmadıysa session'ı da temizle
    if s and s.masa_no:
        kapali = {SiparisDurumu.ODENDI, SiparisDurumu.IPTAL}
        baska_aktif = any(
            sp.masa_no == s.masa_no and sp.id != siparis_id and sp.durum not in kapali
            for sp in sy.siparisler.values()
        )
        if not baska_aktif:
            session.pop("masa_no", None)
            session.modified = True
            storage.musteri_masa_sil(session.get("kullanici",""))
    return redirect(url_for("ana_sayfa", mesaj="Siparişiniz iptal edildi.", tur="info"))


@app.route("/siparis/<int:siparis_id>")
def siparis_goster(siparis_id):
    sy = _sy()
    siparis = sy.siparis_bul(siparis_id)
    if not siparis:
        return redirect(url_for("ana_sayfa", mesaj="Sipariş bulunamadı.", tur="danger"))
    # Sipariş ödendi veya iptal olduysa masa_no'yu temizle
    if siparis.durum in (SiparisDurumu.ODENDI, SiparisDurumu.IPTAL):
        if session.get("masa_no") == siparis.masa_no:
            session.pop("masa_no", None)
            session.modified = True
            storage.musteri_masa_sil(session.get("kullanici",""))
    return render_template_string(
        SIPARIS_HTML,
        alt_baslik="Siparişim",
        aktif_sayfa="sorgula",
        siparis=_siparis_bilgi(siparis),
    )


@app.route("/api/siparis/<int:siparis_id>")
def api_siparis(siparis_id):
    """AJAX ile sipariş durumu sorgulama (opsiyonel)."""
    sy = _sy()
    siparis = sy.siparis_bul(siparis_id)
    if not siparis:
        return jsonify({"hata": "Bulunamadı"}), 404
    return jsonify({
        "id": siparis.id,
        "durum": siparis.durum.value,
        "genel_toplam": siparis.genel_toplam,
    })


@app.route("/menu-listesi")
def menu_listesi():
    """Sipariş vermeden sadece menüyü görüntüle."""
    my = _my()
    maly = _maly()
    KAT_EMOJI = {"Başlangıç":"🥣","Ana Yemek":"🍖","Pizza":"🍕",
                 "Salata":"🥗","Tatlı":"🍮","İçecek":"🥤","Diğer":"🍽"}
    urunler = []
    kategoriler_dict = {}
    for o in my.kategoriye_gore_listele():
        if not o.mevcut:
            continue
        kat_id = o.kategori.value.replace(" ","_").replace("ı","i").replace("İ","I")
        tukendi = (o.stok == 0) or (not maly.yapilabilir_mi(o.ad))
        urunler.append({
            "id": o.id, "ad": o.ad,
            "kategori": o.kategori.value, "kategori_id": kat_id,
            "aciklama": o.aciklama,
            "fiyat_kdv": o.kdv_dahil_fiyat,
            "fiyat_taban_kdv": o.kdv_dahil_taban,
            "indirim": o.indirim_yuzdesi, "tukendi": tukendi,
            "tukendi_mesaj": "Tükendi" if o.stok == 0 else "Yeterli stok yok",
        })
        if kat_id not in kategoriler_dict:
            kategoriler_dict[kat_id] = {
                "id": kat_id, "ad": o.kategori.value,
                "emoji": KAT_EMOJI.get(o.kategori.value, "🍽"),
            }

    HTML = MENU_HTML.replace(
        '<button class="miktar-btn" type="submit">+</button>', ''
    ).replace(
        '<form method="post"', '<form style="display:none" method="post"'
    )
    return render_template_string(HTML,
        alt_baslik="Menü", aktif_sayfa="menu",
        masa_no="-", siparis=None,
        urunler=urunler, kategoriler=list(kategoriler_dict.values()),
        mesaj="", mesaj_tur="info")



SORGULA_HTML = BASE.replace("{% block icerik %}{% endblock %}", """
<div class="card">
  <div style="font-weight:700; margin-bottom:12px;">🔍 Siparişimi Sorgula</div>
  <form method="get" action="/siparis-sorgula">
    <label>Sipariş Numarası</label>
    <input type="number" name="id" placeholder="Örn: 5" min="1"
           value="{{ sorgu_id or '' }}">
    <button type="submit" class="btn btn-primary" style="margin-top:10px;">Sorgula</button>
  </form>
</div>
{% if siparis %}
<div class="card">
  <div style="font-size:1rem; font-weight:700; margin-bottom:10px;">
    Sipariş #{{ siparis.id }} — Masa {{ siparis.masa_no }}
  </div>
  <div class="siparis-durum-badge durum-{{ siparis.durum_css }}">{{ siparis.durum }}</div>
  <div style="margin-top:14px;">
    {% for k in siparis.kalemler %}
    <div class="sepet-satir">
      <span>{{ k.ad }} × {{ k.miktar }}</span>
      <span>{{ "%.2f"|format(k.toplam_kdv) }} ₺</span>
    </div>
    {% endfor %}
    <div class="toplam-satir">
      <span>TOPLAM</span>
      <span style="color:#1B6CA8;">{{ "%.2f"|format(siparis.genel_toplam) }} ₺</span>
    </div>
  </div>
</div>
{% elif sorgu_id %}
<div class="alert alert-danger">Sipariş #{{ sorgu_id }} bulunamadı.</div>
{% endif %}
""").replace("{{ alt_baslik }}", "Siparişim Nerede?")


@app.route("/rezervasyon", methods=["GET", "POST"])
@musteri_gerekli
def rezervasyon_ekrani():
    from datetime import date
    bugun = date.today().isoformat()
    onaylandi = False
    rv_tarih = rv_saat = rv_kisi = rv_masa = ""

    if request.method == "POST":
        tarih   = request.form.get("tarih", "")
        saat    = request.form.get("saat", "")
        kisi    = request.form.get("kisi", 2, type=int)
        telefon = request.form.get("telefon", "")
        not_    = request.form.get("not_", "")
        musteri = session.get("kullanici", "Misafir")

        if tarih and saat and kisi:
            # Kullanıcının aktif rezervasyonu var mı?
            musteri = session.get("kullanici", "Misafir")
            mevcut_rezervler = storage.rezervasyon_listesi_yukle()
            aktif_rv = any(
                r.get("musteri") == musteri and r.get("durum") != "İptal"
                for r in mevcut_rezervler
            )
            if aktif_rv:
                return render_template_string(
                    REZERVASYON_HTML,
                    alt_baslik="Rezervasyon", aktif_sayfa="rezervasyon",
                    onaylandi=False, bugun=bugun,
                    hata="Zaten aktif bir rezervasyonunuz var. Yeni rezervasyon yapmak için mevcut rezervasyonunuzu iptal edin.",
                    rv_tarih="", rv_saat="", rv_kisi="", rv_masa="",
                )

            # Uygun masa bul: kapasitesi >= kisi, o tarih+saatte başka rezervasyon yok
            sy = _sy()
            mevcut_rezervler = storage.rezervasyon_listesi_yukle()

            # O tarih+saatte dolu olan masalar (±1 saat tolerans)
            from datetime import datetime, timedelta
            try:
                istek_dt = datetime.strptime(f"{tarih} {saat}", "%Y-%m-%d %H:%M")
            except Exception:
                istek_dt = None

            dolu_masalar = set()
            if istek_dt:
                for r in mevcut_rezervler:
                    if r.get("durum") == "İptal":
                        continue
                    if r.get("tarih") != tarih:
                        continue
                    try:
                        r_dt = datetime.strptime(f"{r['tarih']} {r['saat']}", "%Y-%m-%d %H:%M")
                        fark = abs((istek_dt - r_dt).total_seconds()) / 3600
                        if fark < 1.5:
                            dolu_masalar.add(r.get("masa_no"))
                    except Exception:
                        pass

            # Kapasite >= kisi olan ve o saatte boş masaları bul
            uygun = [
                m for m in sorted(sy.masalar.values(), key=lambda x: x.kapasite)
                if m.kapasite >= kisi and m.no not in dolu_masalar
            ]

            if uygun:
                secilen_masa = uygun[0]
                kayit = storage.rezervasyon_ekle(
                    musteri=musteri, tarih=tarih, saat=saat,
                    kisi=kisi, masa_no=secilen_masa.no,
                    telefon=telefon, not_=not_
                )
                # Masayı rezerve et
                secilen_masa.durum = MasaDurumu.REZERVE
                storage.masalar_kaydet(sy.masalar)
                onaylandi = True
                rv_tarih  = tarih
                rv_saat   = saat
                rv_kisi   = kisi
                rv_masa   = secilen_masa.no
            else:
                return render_template_string(
                    REZERVASYON_HTML,
                    alt_baslik="Rezervasyon", aktif_sayfa="rezervasyon",
                    onaylandi=False, bugun=bugun, hata="",
                    mesaj=f"{kisi} kişilik uygun masa bulunamadı. Lütfen farklı saat deneyin.",
                    mesaj_tur="danger"
                )

    return render_template_string(
        REZERVASYON_HTML,
        alt_baslik="Rezervasyon", aktif_sayfa="rezervasyon",
        onaylandi=onaylandi, bugun=bugun, hata="",
        rv_tarih=rv_tarih, rv_saat=rv_saat, rv_kisi=rv_kisi, rv_masa=rv_masa,
        mesaj="", mesaj_tur="info"
    )


@app.route("/bakhsis", methods=["GET", "POST"])
@musteri_gerekli
def bakhsis_ekrani():
    gonderildi = False
    gonderilen_tutar = 0.0
    if request.method == "POST":
        tutar = request.form.get("tutar", 0, type=float)
        not_  = request.form.get("not_", "")
        if tutar and tutar > 0:
            musteri = session.get("kullanici", "Misafir")
            storage.bakhsis_ekle(tutar, musteri, not_)
            gonderildi = True
            gonderilen_tutar = tutar
    return render_template_string(
        BAKHSIS_HTML,
        alt_baslik="Garson Bahşişi",
        aktif_sayfa="bakhsis",
        gonderildi=gonderildi,
        gonderilen_tutar=gonderilen_tutar,
    )


@app.route("/siparislerim")
@musteri_gerekli
def siparislerim():
    sy  = _sy()
    ids = session.get("siparislerim", [])
    siparisler = []
    for sid in ids:
        s = sy.siparis_bul(sid)
        if s:
            siparisler.append(_siparis_bilgi(s))

    DURUM_RENK = {
        "bekliyor": ("fef9ec","b7791f"),
        "hazirlaniyor": ("ebf8ff","2b6cb0"),
        "hazir": ("f0fff4","276749"),
        "servis": ("e8f4fd","2c5282"),
        "odendi": ("f7fafc","718096"),
        "iptal": ("fff5f5","c53030"),
    }
    icerik = """
    <style>
      .slr-wrap { max-width:680px; margin:0 auto; }
      .slr-hero {
        background:linear-gradient(135deg,#0D1B2A 0%,#1B3A5C 100%);
        border-radius:16px;padding:22px 24px;margin-bottom:18px;
        color:white;display:flex;align-items:center;gap:16px;
      }
      .slr-hero-icon{font-size:2.2rem}
      .slr-hero h2{font-size:1.15rem;font-weight:800;margin-bottom:3px}
      .slr-hero p{font-size:.82rem;color:rgba(255,255,255,.6)}
      .slr-kart{
        background:white;border-radius:14px;padding:18px 20px;
        margin-bottom:12px;border:1.5px solid #edf0f5;
        box-shadow:0 2px 10px rgba(0,0,0,.06);
      }
      .slr-kart-top{
        display:flex;justify-content:space-between;align-items:center;
        margin-bottom:12px;
      }
      .slr-kart-no{font-size:1rem;font-weight:800;color:#1b2838}
      .slr-durum{
        font-size:.72rem;font-weight:700;padding:4px 10px;
        border-radius:20px;
      }
      .slr-kalemler{
        font-size:.84rem;color:#5d7080;
        border-top:1px solid #f0f4f8;padding-top:10px;margin-bottom:10px;
      }
      .slr-kalem{padding:3px 0}
      .slr-kart-alt{
        display:flex;justify-content:space-between;align-items:center;
        border-top:1px solid #f0f4f8;padding-top:10px;
      }
      .slr-tutar{font-weight:800;font-size:1rem;color:#1B6CA8}
      .slr-takip{
        background:#ebf8ff;color:#2b6cb0;border:1px solid #bee3f8;
        padding:6px 14px;border-radius:8px;text-decoration:none;
        font-size:.8rem;font-weight:700;transition:all .15s;
      }
      .slr-takip:hover{background:#2b6cb0;color:white}
      .slr-bos{
        background:white;border-radius:16px;padding:48px 24px;
        text-align:center;border:2px dashed #dde3ea;
      }
      .slr-bos-icon{font-size:3rem;margin-bottom:14px}
      .slr-bos-yaz{font-size:.95rem;color:#95a5a6;margin-bottom:16px}
      .slr-bos-link{
        background:linear-gradient(135deg,#1B6CA8,#2980b9);color:white;
        padding:12px 24px;border-radius:10px;text-decoration:none;
        font-weight:700;font-size:.9rem;
      }
    </style>
    <div class="slr-wrap">
      <div class="slr-hero">
        <div class="slr-hero-icon">📦</div>
        <div>
          <h2>Siparişlerim</h2>
          <p>Bu oturumda verdiğiniz siparişler aşağıda listeleniyor.</p>
        </div>
      </div>
    """

    if siparisler:
        # Aynı masadaki siparişleri grupla
        from collections import OrderedDict
        masa_gruplari = OrderedDict()
        for s in siparisler:
            mno = s['masa_no'] or 0
            if mno not in masa_gruplari:
                masa_gruplari[mno] = []
            masa_gruplari[mno].append(s)

        for mno, grup in reversed(list(masa_gruplari.items())):
            masa_str = f"Masa {mno}" if mno else "Paket"
            # Tüm kalemleri birleştir
            birlesik_kalemler = {}
            toplam_tutar = 0.0
            siparis_nolar = []
            durum_listesi = []
            for s in grup:
                siparis_nolar.append(f"#{s['id']}")
                durum_listesi.append(s)
                toplam_tutar += s['genel_toplam']
                for k in s['kalemler']:
                    key = k['ad']
                    if key in birlesik_kalemler:
                        birlesik_kalemler[key] += k['miktar']
                    else:
                        birlesik_kalemler[key] = k['miktar']

            kalemler_html = "".join(
                f'<div class="slr-kalem">• {ad} <span style="color:#bbb">×{miktar}</span></div>'
                for ad, miktar in birlesik_kalemler.items()
            )

            # Durum rozetleri
            durum_html = ""
            for s in grup:
                bg, fg = DURUM_RENK.get(s['durum_css'], ("f7fafc","718096"))
                durum_html += f'<span class="slr-durum" style="background:#{bg};color:#{fg};margin-left:4px">● #{s["id"]} {s["durum"]}</span>'

            # Takip linkleri
            takip_html = ""
            for s in grup:
                takip_html += f'<a href="/siparis/{s["id"]}" class="slr-takip" style="margin-left:4px">#{s["id"]} Takip →</a>'

            icerik += f"""
            <div class="slr-kart">
              <div class="slr-kart-top">
                <div class="slr-kart-no">🪑 {masa_str} <span style="font-size:.78rem;color:#95a5a6;font-weight:400">({", ".join(siparis_nolar)})</span></div>
                <div style="display:flex;flex-wrap:wrap;gap:4px">{durum_html}</div>
              </div>
              <div class="slr-kalemler">{kalemler_html}</div>
              <div class="slr-kart-alt">
                <span class="slr-tutar">{toplam_tutar:.2f} ₺</span>
                <div style="display:flex;flex-wrap:wrap;gap:4px">{takip_html}</div>
              </div>
            </div>"""
        icerik += "</div>"
    else:
        icerik += """
        <div class="slr-bos">
          <div class="slr-bos-icon">🍽</div>
          <div class="slr-bos-yaz">Henüz bu oturumda siparişiniz yok.</div>
          <a href="/" class="slr-bos-link">Sipariş Vermek İçin Tıklayın</a>
        </div></div>"""

    tpl = BASE.replace("{% block icerik %}{% endblock %}", icerik)\
              .replace("{% block footer %}{% endblock %}","")
    return render_template_string(tpl,
        alt_baslik="Siparişlerim", aktif_sayfa="siparislerim",
        kullanici=session.get("kullanici",""))

@app.route("/siparis-sorgula")
def siparis_sorgula():
    sorgu_id = request.args.get("id", type=int)
    siparis  = None
    if sorgu_id:
        sy = _sy()
        s  = sy.siparis_bul(sorgu_id)
        if s:
            siparis = _siparis_bilgi(s)
    return render_template_string(SORGULA_HTML,
        alt_baslik="Siparişim Nerede?", aktif_sayfa="sorgula",
        sorgu_id=sorgu_id, siparis=siparis)


# ══════════════════════════════════════════════════════
#  BİRLEŞİK GİRİŞ / KAYIT SAYFALARI
# ══════════════════════════════════════════════════════

GIRIS_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Giriş — Anadolu Sofrası</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;min-height:100vh;display:flex;align-items:center;
         justify-content:center;
         background-color:#0f0c29;
         background-image:
           repeating-linear-gradient(45deg,rgba(255,255,255,0.07) 0px,rgba(255,255,255,0.07) 2px,transparent 2px,transparent 50%),
           repeating-linear-gradient(-45deg,rgba(255,255,255,0.07) 0px,rgba(255,255,255,0.07) 2px,transparent 2px,transparent 50%),
           linear-gradient(135deg,#0f0c29,#302b63,#24243e);
         background-size:28px 28px,28px 28px,cover;
    }
    .wrap{width:100%;max-width:460px;padding:20px}
    .kart{background:white;border-radius:20px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.5)}
    .kart-ust{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:32px 32px 24px;text-align:center}
    .kart-ust .ikon{font-size:3rem}
    .kart-ust h1{color:white;font-size:1.6rem;font-weight:800;margin-top:10px}
    .kart-ust p{color:rgba(255,255,255,.5);font-size:.85rem;margin-top:4px}
    .tabs{display:flex;margin:0}
    .tab{flex:1;padding:14px;border:none;cursor:pointer;font-size:.9rem;font-weight:700;
         transition:all .2s;border-bottom:3px solid transparent}
    .tab.musteri{background:#f8f9ff;color:#555}
    .tab.personel{background:#f8f9ff;color:#555}
    .tab.aktif.musteri{background:white;color:#1B6CA8;border-bottom-color:#1B6CA8}
    .tab.aktif.personel{background:white;color:#e94560;border-bottom-color:#e94560}
    .form-alan{padding:28px 32px}
    .form-grup{margin-bottom:16px}
    label{display:block;font-size:.8rem;font-weight:700;color:#555;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
    input,select{width:100%;padding:12px 14px;border:1.5px solid #e0e0e0;border-radius:10px;font-size:.95rem;outline:none;transition:border .2s;background:#fafafa}
    input:focus{border-color:#1B6CA8;background:white}
    .btn-submit{width:100%;padding:14px;border:none;border-radius:10px;font-size:1rem;font-weight:800;
                cursor:pointer;margin-top:6px;transition:all .2s;letter-spacing:.5px}
    .btn-musteri{background:linear-gradient(135deg,#1B6CA8,#2980b9);color:white}
    .btn-personel{background:linear-gradient(135deg,#e94560,#c0392b);color:white}
    .btn-submit:hover{opacity:.9;transform:translateY(-1px)}
    .alt{text-align:center;margin-top:16px;font-size:.85rem;color:#888}
    .alt a{color:#1B6CA8;font-weight:700;text-decoration:none}
    .alert{padding:10px 14px;border-radius:8px;margin-bottom:14px;font-size:.85rem}
    .alert-danger{background:#fde8e8;color:#c0392b;border-left:3px solid #e74c3c}
    .rol-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:6px}
    .rol-btn{padding:10px 4px;border:2px solid #ddd;border-radius:8px;text-align:center;
             cursor:pointer;font-size:.75rem;font-weight:700;color:#555;background:white;
             transition:all .2s;line-height:1.3}
    .rol-btn.sec{border-color:#e94560;background:#e94560;color:white}
    .rol-btn .ri{font-size:1.1rem;display:block;margin-bottom:2px}
    .ayrac{display:flex;align-items:center;gap:10px;margin:18px 0;color:#ccc;font-size:.8rem}
    .ayrac::before,.ayrac::after{content:'';flex:1;height:1px;background:#eee}
  </style>
</head>
<body>
<div class="wrap">
  <div class="kart">
    <div class="kart-ust">
      <div class="ikon">🍽</div>
      <h1>Anadolu Sofrası</h1>
      <p>Hoş geldiniz, lütfen giriş yapın</p>
    </div>

    <div class="tabs">
      <button class="tab musteri aktif" onclick="secTab('musteri')">👤 Müşteri</button>
      <button class="tab personel" onclick="secTab('personel')">🔧 Personel</button>
    </div>

    <div class="form-alan">
      {% if mesaj %}
      <div class="alert alert-danger">{{ mesaj }}</div>
      {% endif %}

      <!-- MÜŞTERİ GİRİŞ -->
      <div id="panel-m-giris">
        <form method="post" action="/giris">
          <input type="hidden" name="tip" value="musteri">
          <input type="hidden" name="mod" value="giris">
          <input type="hidden" name="sonraki" value="{{ sonraki }}">
          <div class="form-grup">
            <label>Kullanıcı Adı</label>
            <input type="text" name="kullanici_adi" placeholder="adınız" autofocus>
          </div>
          <div class="form-grup">
            <label>Şifre</label>
            <input type="password" name="sifre" placeholder="••••••">
          </div>
          <button type="submit" class="btn-submit btn-musteri">Giriş Yap →</button>
        </form>
        <div class="ayrac">veya</div>
        <div class="alt">Hesabın yok mu? <a href="#" onclick="secPanel('m-kayit')">Kayıt Ol</a></div>
      </div>

      <!-- MÜŞTERİ KAYIT -->
      <div id="panel-m-kayit" style="display:none">
        <form method="post" action="/giris">
          <input type="hidden" name="tip" value="musteri">
          <input type="hidden" name="mod" value="kayit">
          <div class="form-grup">
            <label>Kullanıcı Adı</label>
            <input type="text" name="kullanici_adi" placeholder="adınız (min. 3 karakter)">
          </div>
          <div class="form-grup">
            <label>Şifre</label>
            <input type="password" name="sifre" placeholder="••••••">
          </div>
          <div class="form-grup">
            <label>Şifre Tekrar</label>
            <input type="password" name="sifre2" placeholder="••••••">
          </div>
          <button type="submit" class="btn-submit btn-musteri">Kayıt Ol →</button>
        </form>
        <div class="alt" style="margin-top:14px">Hesabın var mı? <a href="#" onclick="secPanel('m-giris')">Giriş Yap</a></div>
      </div>

      <!-- PERSONEL GİRİŞ -->
      <div id="panel-p-giris" style="display:none">
        <form method="post" action="/giris">
          <input type="hidden" name="tip" value="personel">
          <input type="hidden" name="mod" value="giris">
          <input type="hidden" name="sonraki" value="{{ sonraki }}">
          <div class="form-grup">
            <label>Kullanıcı Adı</label>
            <input type="text" name="kullanici_adi" placeholder="personel adı">
          </div>
          <div class="form-grup">
            <label>Şifre</label>
            <input type="password" name="sifre" placeholder="••••••">
          </div>
          <button type="submit" class="btn-submit btn-personel">Personel Girişi →</button>
        </form>
        <div class="ayrac">veya</div>
        <div class="alt">Yeni personel hesabı: <a href="#" onclick="secPanel('p-kayit')">Kayıt Ol</a></div>
      </div>

      <!-- PERSONEL KAYIT -->
      <div id="panel-p-kayit" style="display:none">
        <form method="post" action="/giris">
          <input type="hidden" name="tip" value="personel">
          <input type="hidden" name="mod" value="kayit">
          <div class="form-grup">
            <label>Kullanıcı Adı</label>
            <input type="text" name="kullanici_adi" placeholder="min. 3 karakter">
          </div>
          <div class="form-grup">
            <label>Şifre</label>
            <input type="password" name="sifre" placeholder="••••••">
          </div>
          <div class="form-grup">
            <label>Şifre Tekrar</label>
            <input type="password" name="sifre2" placeholder="••••••">
          </div>
          <div class="form-grup">
            <label>Rol Seç</label>
            <div class="rol-grid">
              <div class="rol-btn sec" onclick="rolSec(this,'mutfak')"><span class="ri">🍳</span>Mutfak</div>
              <div class="rol-btn" onclick="rolSec(this,'garson')"><span class="ri">🍽</span>Garson</div>
              <div class="rol-btn" onclick="rolSec(this,'kasa')"><span class="ri">💰</span>Kasa</div>
              <div class="rol-btn" onclick="rolSec(this,'yonetim')"><span class="ri">🛠</span>Yönetim</div>
              <div class="rol-btn" onclick="rolSec(this,'admin')"><span class="ri">👑</span>Admin</div>
            </div>
            <input type="hidden" name="rol" id="rol-val" value="mutfak">
          </div>
          <div class="form-grup">
            <label>Kayıt Kodu</label>
            <input type="password" name="kayit_kodu" placeholder="Yöneticiden alın">
          </div>
          <button type="submit" class="btn-submit btn-personel">Kayıt Ol →</button>
        </form>
        <div class="alt" style="margin-top:14px"><a href="#" onclick="secPanel('p-giris')">← Giriş Yap</a></div>
      </div>
    </div>
  </div>
</div>
<script>
var aktifTab = '{{ aktif_tip }}', aktifPanel = aktifTab === 'personel' ? 'p-giris' : 'm-giris';
document.addEventListener('DOMContentLoaded', function(){ secTab(aktifTab); });
function secTab(t) {
  aktifTab = t;
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('aktif'));
  document.querySelector('.tab.' + t).classList.add('aktif');
  secPanel(t === 'musteri' ? 'm-giris' : 'p-giris');
}
function secPanel(p) {
  aktifPanel = p;
  ['m-giris','m-kayit','p-giris','p-kayit'].forEach(id => {
    document.getElementById('panel-'+id).style.display = id === p ? '' : 'none';
  });
}
function rolSec(el, rol) {
  document.querySelectorAll('.rol-btn').forEach(b => b.classList.remove('sec'));
  el.classList.add('sec');
  document.getElementById('rol-val').value = rol;
}
</script>
</body></html>"""

@app.route("/giris", methods=["GET","POST"])
def giris_ekran():
    sonraki    = request.args.get("sonraki", "")
    mesaj      = request.args.get("mesaj", "")
    aktif_tip  = request.args.get("aktif_tip", "musteri")
    if "kullanici" in session:
        return _rota_rol()

    if request.method == "POST":
        tip   = request.form.get("tip","musteri")
        aktif_tip = tip
        mod   = request.form.get("mod","giris")
        kadi  = request.form.get("kullanici_adi","").strip()
        sifre = request.form.get("sifre","")
        sonraki = request.form.get("sonraki","")

        if mod == "giris":
            kullanici = kullanici_bul(kadi)
            if kullanici and check_password_hash(kullanici["sifre_hash"], sifre):
                hesap_rol = kullanici["rol"]
                # Tab uyumsuzluğu kontrolü
                if tip == "personel" and hesap_rol == "musteri":
                    mesaj = "Bu bir müşteri hesabıdır. Müşteri tabından giriş yapın."
                elif tip == "musteri" and hesap_rol in PERSONEL_ROLLER:
                    mesaj = "Bu bir personel hesabıdır. Personel tabından giriş yapın."
                else:
                    session["kullanici"] = kadi
                    session["rol"]       = hesap_rol
                    if sonraki and sonraki.startswith("/"):
                        return redirect(sonraki)
                    return _rota_rol()
            else:
                mesaj = "Kullanıcı adı veya şifre hatalı."

        elif mod == "kayit":
            sifre2 = request.form.get("sifre2","")
            kayit_kodu = request.form.get("kayit_kodu","")
            rol = request.form.get("rol","musteri") if tip == "personel" else "musteri"

            if len(kadi) < 3:
                mesaj = "Kullanıcı adı en az 3 karakter olmalı."
            elif len(sifre) < 4:
                mesaj = "Şifre en az 4 karakter olmalı."
            elif sifre != sifre2:
                mesaj = "Şifreler eşleşmiyor."
            elif kullanici_bul(kadi):
                mesaj = "Bu kullanıcı adı zaten alınmış."
            elif tip == "personel" and kayit_kodu != KAYIT_KODU:
                mesaj = "Kayıt kodu hatalı."
            else:
                kullanicilar = kullanicilari_yukle()
                kullanicilar[kadi] = {"sifre_hash": generate_password_hash(sifre), "rol": rol}
                kullanicilari_kaydet(kullanicilar)
                session["kullanici"] = kadi
                session["rol"]       = rol
                return _rota_rol()

    return render_template_string(GIRIS_HTML, mesaj=mesaj, sonraki=sonraki, aktif_tip=aktif_tip)

def _rota_rol():
    """Giriş sonrası role göre yönlendir."""
    rol = session.get("rol","musteri")
    if rol == "musteri":
        # Daha önce masaya oturmuş mu? Varsa session'a geri yükle
        kullanici = session.get("kullanici","")
        kayit = storage.musteri_masa_yukle(kullanici)
        if kayit:
            masa_no = kayit.get("masa_no")
            siparislerim = kayit.get("siparislerim", [])
            # Masa hâlâ dolu mu kontrol et
            sy = _sy()
            masa = sy.masalar.get(masa_no)
            if masa and masa.durum == MasaDurumu.DOLU:
                session["masa_no"]      = masa_no
                session["siparislerim"] = siparislerim
                session.modified = True
            else:
                # Masa artık boş, kaydı temizle
                storage.musteri_masa_sil(kullanici)
        return redirect("/")
    if rol == "mutfak":
        return redirect("/personel/mutfak")
    if rol == "garson":
        return redirect("/personel/garson")
    if rol == "kasa":
        return redirect("/personel/kasa")
    return redirect("/personel/yonetim")

@app.route("/cikis")
def cikis_ekran():
    session.clear()
    return redirect("/giris")

# Eski rotalar → yeni sisteme yönlendir
@app.route("/personel/giris")
def pers_giris_eski():
    return redirect("/giris")

@app.route("/personel/cikis")
def cikis():
    session.clear()
    return redirect("/giris")

@app.route("/personel")
def personel_ana():
    if "kullanici" in session and session.get("rol") in PERSONEL_ROLLER:
        return redirect("/personel/mutfak")
    return redirect("/giris")

# ══════════════════════════════════════════════════════
#  PERSONEL ARAYÜZÜ
# ══════════════════════════════════════════════════════

PERS_BASE = """
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="{{ refresh_meta }}" content="{{ refresh_sec }}">
  <title>{{ sayfa_baslik }} — Panel</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;color:#2c3e50;display:flex;min-height:100vh;
      background-color:#f0f2f5;
      background-image:repeating-linear-gradient(45deg,rgba(0,0,0,0.07) 0px,rgba(0,0,0,0.07) 2px,transparent 2px,transparent 50%),
      repeating-linear-gradient(-45deg,rgba(0,0,0,0.07) 0px,rgba(0,0,0,0.07) 2px,transparent 2px,transparent 50%);
      background-size:28px 28px;
    }

    /* ── SIDEBAR ── */
    .pside{
      width:230px;min-width:230px;
      background:linear-gradient(180deg,#1b2838 0%,#243447 100%);
      position:fixed;top:0;left:0;height:100vh;z-index:200;
      overflow:hidden;
      transition:width .35s cubic-bezier(.4,0,.2,1),min-width .35s cubic-bezier(.4,0,.2,1);
      box-shadow:4px 0 20px rgba(0,0,0,.18);
    }
    .pside.kapali{width:0;min-width:0}

    /* ── MOBİL SIDEBAR OVERLAY ── */
    @media (max-width: 768px) {
      .pside { width: 0; min-width: 0; }
      .pside.mobil-acik { width: 230px; min-width: 230px; }
      .pmain { margin-left: 0 !important; }
    }
    .p-mobil-overlay{
      display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);
      z-index:199;
    }
    .p-mobil-overlay.goster{display:block}
    .pside-inner{width:230px;min-width:230px;display:flex;flex-direction:column;
                 height:100%;overflow-y:auto}

    .pside-brand{
      display:flex;align-items:center;gap:10px;
      padding:22px 18px 18px;
      border-bottom:1px solid rgba(255,255,255,.07);
      margin-bottom:8px;white-space:nowrap;
    }
    .pside-brand-icon{
      width:36px;height:36px;background:linear-gradient(135deg,#f39c12,#e67e22);
      border-radius:10px;display:flex;align-items:center;justify-content:center;
      font-size:1.1rem;flex-shrink:0;
    }
    .pside-brand-text{color:white;font-size:.95rem;font-weight:800;line-height:1.2}
    .pside-brand-text span{display:block;font-size:.65rem;font-weight:400;
                           color:rgba(255,255,255,.45);margin-top:1px}

    .pside-group{margin:4px 10px 2px;padding:6px 8px 2px;
                 font-size:.6rem;font-weight:700;letter-spacing:1.8px;
                 text-transform:uppercase;color:rgba(255,255,255,.28);white-space:nowrap}

    .pside a{
      display:flex;align-items:center;gap:10px;
      color:rgba(255,255,255,.6);text-decoration:none;
      margin:2px 10px;padding:10px 12px;border-radius:8px;
      font-size:.88rem;font-weight:500;transition:all .18s;white-space:nowrap;
    }
    .pside a .ni{font-size:1rem;width:20px;text-align:center;flex-shrink:0}
    .pside a:hover{background:rgba(255,255,255,.09);color:white}
    .pside a.ak{
      background:linear-gradient(90deg,rgba(243,156,18,.25),rgba(243,156,18,.08));
      color:#f7c948;font-weight:600;
      border:1px solid rgba(243,156,18,.2);
    }

    .pside-footer{
      margin-top:auto;padding:14px 18px;
      border-top:1px solid rgba(255,255,255,.07);
      font-size:.72rem;color:rgba(255,255,255,.3);white-space:nowrap;
    }

    /* ── MAIN ── */
    .pmain{margin-left:230px;flex:1;display:flex;flex-direction:column;
           transition:margin-left .35s cubic-bezier(.4,0,.2,1);min-height:100vh}
    .pmain.genislet{margin-left:0}

    /* ── HEADER ── */
    .phead{
      background:white;color:#2c3e50;padding:0 24px;height:62px;
      display:flex;align-items:center;justify-content:space-between;
      position:sticky;top:0;z-index:100;
      border-bottom:1px solid #e8ecf0;
      box-shadow:0 2px 12px rgba(0,0,0,.06);
    }
    .phead-left{display:flex;align-items:center;gap:12px}
    .phead-title{font-size:1.05rem;font-weight:700;color:#1b2838}
    .phead .sub{font-size:.72rem;color:#95a5a6;margin-top:1px}
    .phead-right{display:flex;align-items:center;gap:10px}

    .toggle-btn-p{
      background:none;border:1.5px solid #dde3ea;color:#5d7080;font-size:1.1rem;
      cursor:pointer;padding:6px 9px;border-radius:8px;line-height:1;
      transition:all .15s;
    }
    .toggle-btn-p:hover{background:#f0f4f8;border-color:#bcc5ce;color:#2c3e50}

    .phead-user{
      display:flex;align-items:center;gap:7px;
      background:#f4f6fb;border:1px solid #dde3ea;
      border-radius:8px;padding:6px 10px;font-size:.78rem;color:#5d7080;
    }
    .phead-user strong{color:#2c3e50}

    .phead-exit{
      background:#fff1f3;border:1px solid #fbc8d0;color:#c0392b;
      font-size:.78rem;font-weight:600;padding:6px 12px;border-radius:8px;
      text-decoration:none;transition:all .15s;
    }
    .phead-exit:hover{background:#c0392b;color:white;border-color:#c0392b}

    .phead-refresh{font-size:.7rem;color:#95a5a6;
                   background:#f0f4f8;border-radius:6px;padding:4px 8px}

    /* ── CONTENT ── */
    .pcont{padding:24px;max-width:1120px}

    .card{
      background:white;border-radius:12px;padding:20px;margin-bottom:16px;
      box-shadow:0 1px 4px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04);
      border:1px solid #edf0f5;
    }
    .card h2{font-size:.95rem;font-weight:700;margin-bottom:16px;
             color:#1b2838;display:flex;align-items:center;gap:7px}
    .card-divider{border:none;border-top:1px solid #f0f2f7;margin:14px 0}

    table{width:100%;border-collapse:collapse;font-size:.88rem}
    thead tr{background:#f8fafc}
    th{padding:10px 13px;text-align:left;font-weight:700;color:#5d7080;
       font-size:.78rem;letter-spacing:.4px;text-transform:uppercase;
       border-bottom:2px solid #edf0f5}
    td{padding:10px 13px;border-bottom:1px solid #f2f4f8;vertical-align:top;color:#3a4a5a}
    tr:last-child td{border-bottom:none}
    tr:hover td{background:#fafbfd}

    .badge{display:inline-flex;align-items:center;padding:3px 10px;
           border-radius:20px;font-size:.73rem;font-weight:700;gap:4px}
    .b-bek{background:#fef9ec;color:#b7791f;border:1px solid #f6e05e}
    .b-haz{background:#ebf8ff;color:#2b6cb0;border:1px solid #bee3f8}
    .b-hazir{background:#f0fff4;color:#276749;border:1px solid #9ae6b4}
    .b-servis{background:#e8f4fd;color:#2c5282;border:1px solid #90cdf4}
    .b-odendi{background:#f7fafc;color:#718096;border:1px solid #e2e8f0}
    .b-iptal{background:#fff5f5;color:#c53030;border:1px solid #fed7d7}

    .btn{display:inline-flex;align-items:center;gap:5px;
         padding:7px 14px;border:none;border-radius:8px;
         font-size:.82rem;font-weight:600;cursor:pointer;text-decoration:none;margin:2px;
         transition:all .15s}
    .btn-sm{padding:5px 10px;font-size:.76rem}
    .btn-primary{background:#2980b9;color:white}
    .btn-primary:hover{background:#2471a3}
    .btn-success{background:#27ae60;color:white}
    .btn-success:hover{background:#219a52}
    .btn-warning{background:#f39c12;color:white}
    .btn-warning:hover{background:#d68910}
    .btn-danger{background:#e74c3c;color:white}
    .btn-danger:hover{background:#cb4335}
    .btn-secondary{background:#ecf0f1;color:#5d6d7e;border:1px solid #dde1e7}
    .btn-secondary:hover{background:#dde3ea;color:#2c3e50}
    .btn-dark{background:#1b2838;color:white}
    .btn-dark:hover{background:#243447}

    .alert{padding:11px 15px;border-radius:9px;margin-bottom:14px;
           font-size:.86rem;display:flex;align-items:flex-start;gap:8px;
           border:1px solid transparent}
    .alert-success{background:#f0fff4;color:#276749;border-color:#9ae6b4}
    .alert-danger{background:#fff5f5;color:#c53030;border-color:#fed7d7}
    .alert-info{background:#ebf8ff;color:#2b6cb0;border-color:#bee3f8}

    .form-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
    input[type=text],input[type=number],select{
      padding:8px 11px;border:1.5px solid #dde3ea;border-radius:8px;
      font-size:.88rem;color:#2c3e50;background:white;transition:border .15s}
    input:focus,select:focus{border-color:#2980b9;outline:none;
      box-shadow:0 0 0 3px rgba(41,128,185,.12)}

    .kalem-liste{margin:6px 0 0 8px;font-size:.83rem;color:#617080}
    .kalem-liste li{margin-bottom:3px}

    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    .grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
    .stat-kart{
      background:white;border-radius:12px;padding:20px;
      box-shadow:0 1px 4px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04);
      border:1px solid #edf0f5;text-align:center;
    }
    .stat-kart-icon{font-size:1.8rem;margin-bottom:8px}
    .stat-sayi{font-size:2rem;font-weight:800;color:#1b2838;line-height:1}
    .stat-etiket{font-size:.76rem;color:#95a5a6;margin-top:6px;font-weight:500}

    .masa-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px}
    .masa-kart{padding:14px 8px;border-radius:10px;text-align:center;
               font-weight:700;font-size:.88rem;border:1.5px solid transparent}
    .mk-bos{background:#f0fff4;color:#276749;border-color:#9ae6b4}
    .mk-dolu{background:#fff5f5;color:#c53030;border-color:#fed7d7}
    .mk-rez{background:#fef9ec;color:#b7791f;border-color:#f6e05e}

    .page-title{
      font-size:1.3rem;font-weight:800;color:#1b2838;
      margin-bottom:6px;display:flex;align-items:center;gap:8px
    }
    .page-sub{font-size:.82rem;color:#95a5a6;margin-bottom:20px}
  </style>
</head>
<body>

<!-- MOBİL OVERLAY -->
<div class="p-mobil-overlay" id="p-mobil-ov" onclick="psidebarToggle()"></div>

<!-- SIDEBAR -->
<nav class="pside" id="pside">
  <div class="pside-inner">
    <div class="pside-brand">
      <div class="pside-brand-icon">🍽</div>
      <div class="pside-brand-text">
        Anadolu Sofrası
        <span>Yönetim Paneli</span>
      </div>
    </div>

    <div class="pside-group">Terminaller</div>
    <a href="/personel/mutfak" class="{{ 'ak' if ak=='mutfak' else '' }}">
      <span class="ni">🍳</span> Mutfak
    </a>
    <a href="/personel/garson" class="{{ 'ak' if ak=='garson' else '' }}">
      <span class="ni">🍽</span> Garson
    </a>
    <a href="/personel/kasa" class="{{ 'ak' if ak=='kasa' else '' }}">
      <span class="ni">💳</span> Kasa
    </a>

    <div class="pside-group">Yönetim</div>
    <a href="/personel/yonetim"  class="{{ 'ak' if ak=='yonetim'  else '' }}">
      <span class="ni">📊</span> Genel Bakış
    </a>
    <a href="/personel/rezervasyonlar" class="{{ 'ak' if ak=='rezervasyonlar' else '' }}">
      <span class="ni">📅</span> Rezervasyonlar
    </a>
    <a href="/personel/menu"     class="{{ 'ak' if ak=='menu'     else '' }}">
      <span class="ni">📋</span> Menü Düzenle
    </a>
    <a href="/personel/masalar"  class="{{ 'ak' if ak=='masalar'  else '' }}">
      <span class="ni">🪑</span> Masalar
    </a>
    <a href="/personel/malzeme"  class="{{ 'ak' if ak=='malzeme'  else '' }}">
      <span class="ni">📦</span> Malzeme Stok
    </a>
    <a href="/personel/kampanya" class="{{ 'ak' if ak=='kampanya' else '' }}">
      <span class="ni">🏷</span> Kampanyalar
    </a>

    <a href="/personel/bakhsis" class="{{ 'ak' if ak=='bakhsis' else '' }}">
      <span class="ni">💰</span> Bahşiş Takibi
    </a>

  </div>
</nav>

<!-- ANA İÇERİK -->
<div class="pmain" id="pmain">
  <div class="phead">
    <div class="phead-left">
      <button class="toggle-btn-p" onclick="psidebarToggle()" title="Menüyü Aç/Kapat">☰</button>
      <div>
        <div class="phead-title">{{ sayfa_baslik }}</div>
        <div class="sub">Anadolu Sofrası · Personel Paneli</div>
      </div>
    </div>
    <div class="phead-right">
      {% if otoyenile %}
      <span class="phead-refresh">⟳ Otomatik yenileme</span>
      {% endif %}
      <div class="phead-user">
        👤 <strong>{{ session.get('kullanici','') }}</strong>
      </div>
      <a href="/personel/cikis" class="phead-exit">Çıkış →</a>
    </div>
  </div>

  <div class="pcont">
    {% block icerik %}{% endblock %}
  </div>
</div>

<!-- Personel Toast -->
<div id="p-toast-wrap" style="position:fixed;bottom:28px;left:50%;transform:translateX(-50%);
     z-index:9999;pointer-events:none;display:flex;flex-direction:column;align-items:center;gap:10px"></div>

{% if mesaj %}
<script>
document.addEventListener('DOMContentLoaded', function(){
  pShowToast("{{ mesaj }}", "{{ mesaj_tur }}");
});
</script>
{% endif %}

<script>
  var P_ICONS = { success:'✅', danger:'❌', info:'ℹ️', warning:'⚠️' };
  function pShowToast(msg, tur) {
    tur = tur || 'info';
    var colors = { success:'#27ae60', danger:'#e74c3c', info:'#2980b9', warning:'#f39c12' };
    var wrap = document.getElementById('p-toast-wrap');
    var t = document.createElement('div');
    t.style.cssText = 'pointer-events:auto;min-width:200px;max-width:90vw;width:max-content;' +
      'background:white;border-radius:14px;padding:14px 18px 10px;' +
      'box-shadow:0 8px 32px rgba(0,0,0,.18);border-left:4px solid ' + (colors[tur]||'#2980b9') + ';' +
      'position:relative;overflow:hidden;animation:pToastIn .3s cubic-bezier(.34,1.56,.64,1)';
    t.innerHTML =
      '<span style="font-size:1.1rem;margin-right:7px">' + (P_ICONS[tur]||'ℹ️') + '</span>' +
      '<span style="font-size:.88rem;font-weight:600;color:#2c3e50;line-height:1.4">' + msg + '</span>' +
      '<div style="position:absolute;bottom:0;left:0;height:3px;border-radius:0 0 0 14px;' +
        'background:' + (colors[tur]||'#2980b9') + ';animation:pToastBar 3s linear forwards"></div>';
    wrap.appendChild(t);
    setTimeout(function(){
      t.style.animation = 'pToastOut .3s ease forwards';
      setTimeout(function(){ if(t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 3000);
  }

  var ps = document.getElementById('pside');
  var pm = document.getElementById('pmain');
  var pov = document.getElementById('p-mobil-ov');

  function _pMobil() { return window.matchMedia('(max-width: 768px)').matches; }

  if (!_pMobil() && localStorage.getItem('psb') === '0') {
    ps.classList.add('kapali'); pm.classList.add('genislet');
  }

  function psidebarToggle() {
    if (_pMobil()) {
      var acik = ps.classList.toggle('mobil-acik');
      pov.classList.toggle('goster', acik);
    } else {
      ps.classList.toggle('kapali');
      pm.classList.toggle('genislet');
      localStorage.setItem('psb', ps.classList.contains('kapali') ? '0' : '1');
    }
  }
</script>
<style>
  @keyframes pToastIn  { from{opacity:0;transform:translateY(20px) scale(.92)} to{opacity:1;transform:translateY(0) scale(1)} }
  @keyframes pToastOut { to{opacity:0;transform:translateY(10px) scale(.94)} }
  @keyframes pToastBar { from{width:100%} to{width:0%} }
</style>
</body></html>
"""

def _prender(template_str, **kw):
    kw.setdefault("mesaj", "")
    kw.setdefault("mesaj_tur", "info")
    kw.setdefault("otoyenile", False)
    kw.setdefault("refresh_meta", "refresh" if kw.get("otoyenile") else "X-no-refresh")
    kw.setdefault("refresh_sec", 12)
    return render_template_string(PERS_BASE.replace("{% block icerik %}{% endblock %}", template_str), **kw)

def _durum_badge(durum_str):
    m = {"Bekliyor":"b-bek","Hazırlanıyor":"b-haz","Hazır":"b-hazir",
         "Servis Edildi":"b-servis","Garson Aldı":"b-servis",
         "Ödendi":"b-odendi","İptal":"b-iptal"}
    cls = m.get(durum_str, "b-bek")
    return f'<span class="badge {cls}">{durum_str}</span>'

# ─── MUTFAK ───────────────────────────────────────────
@app.route("/personel/mutfak")
@login_gerekli
def pers_mutfak():
    sy = _sy()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")
    MUTFAK_D = {"Bekliyor","Hazırlanıyor","Hazır"}
    siparisler = [s for s in sy.aktif_siparisler() if s.durum.value in MUTFAK_D]
    siparisler.sort(key=lambda s: s.olusturma_zamani)

    satirlar = ""
    for s in siparisler:
        masa = f"Masa {s.masa_no}" if s.masa_no else "Paket"
        saat = s.olusturma_zamani.strftime("%H:%M")
        badge = _durum_badge(s.durum.value)
        kalemler = "".join(f"<li>{k.menu_ogesi.ad} x{k.miktar}{'  <em>('+k.not_+')</em>' if k.not_ else ''}</li>" for k in s.kalemler)

        if s.durum.value == "Bekliyor":
            aksiyon = f'<form method="post" action="/personel/mutfak/guncelle"><input type="hidden" name="sid" value="{s.id}"><button class="btn btn-warning btn-sm">▶ Hazırlanıyor</button></form>'
        elif s.durum.value == "Hazırlanıyor":
            aksiyon = f'<form method="post" action="/personel/mutfak/guncelle"><input type="hidden" name="sid" value="{s.id}"><button class="btn btn-success btn-sm">✔ Hazır</button></form>'
        else:
            aksiyon = '<span style="color:#27ae60;font-weight:700;font-size:.8rem">✔ Hazır</span>'

        satirlar += f"""<tr>
          <td><strong>#{s.id}</strong></td>
          <td>{masa}</td>
          <td>{badge}</td>
          <td>{saat}</td>
          <td><ul class="kalem-liste">{kalemler}</ul></td>
          <td>{aksiyon}</td>
        </tr>"""

    if not satirlar:
        satirlar = '<tr><td colspan="6" style="text-align:center;color:#888;padding:30px">✅ Bekleyen sipariş yok</td></tr>'

    html = f"""
    <div style="margin-bottom:10px;display:flex;gap:10px;align-items:center">
      <a href="/personel/mutfak" class="btn btn-dark btn-sm">⟳ Yenile</a>
      <span style="font-size:.8rem;color:#888">Sayfa her 12 sn otomatik yenilenir</span>
    </div>
    <div class="card">
      <h2>Aktif Siparişler</h2>
      <table>
        <thead><tr><th>#</th><th>Masa</th><th>Durum</th><th>Saat</th><th>Ürünler</th><th>İşlem</th></tr></thead>
        <tbody>{satirlar}</tbody>
      </table>
    </div>"""
    return _prender(html, sayfa_baslik="Mutfak Terminali", ak="mutfak",
                    otoyenile=True, mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/mutfak/guncelle", methods=["POST"])
@login_gerekli
def pers_mutfak_guncelle():
    sid = request.form.get("sid", type=int)
    sy  = _sy()
    s   = sy.siparis_bul(sid)
    if s:
        if s.durum.value == "Bekliyor":
            sy.durum_guncelle(sid, SiparisDurumu.HAZIRLANIYOR)
            mesaj = f"#{sid} → Hazırlanıyor"
        elif s.durum.value == "Hazırlanıyor":
            sy.durum_guncelle(sid, SiparisDurumu.HAZIR)
            mesaj = f"#{sid} → Hazır ✔"
        else:
            mesaj = "Durum değiştirilemedi."
    else:
        mesaj = "Sipariş bulunamadı."
    return redirect(url_for("pers_mutfak", mesaj=mesaj, tur="success"))

# ─── GARSON PANELİ ────────────────────────────────────
@app.route("/personel/garson")
@login_gerekli
def pers_garson():
    sy = _sy()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")

    # Hazır ve Garson Aldı siparişleri
    GARSON_D = {"Hazır", "Garson Aldı", "Servis Edildi"}
    siparisler = [s for s in sy.aktif_siparisler() if s.durum.value in GARSON_D]
    siparisler.sort(key=lambda s: s.olusturma_zamani)

    kartlar = ""
    for s in siparisler:
        masa = f"Masa {s.masa_no}" if s.masa_no else "Paket"
        saat = s.olusturma_zamani.strftime("%H:%M")
        badge = _durum_badge(s.durum.value)
        def _kalem_html(k):
            not_html = f' <span style="font-size:.75rem;color:#7f8c8d;font-style:italic">— {k.not_}</span>' if k.not_ else ""
            return (f'<div style="padding:4px 0;border-bottom:1px solid #f5f5f5;font-size:.88rem">'
                    f'<span style="font-weight:600">{k.menu_ogesi.ad}</span>'
                    f' <span style="color:#95a5a6">×{k.miktar}</span>{not_html}</div>')
        kalemler = "".join(_kalem_html(k) for k in s.kalemler)

        # Buton: hangi duruma geçebilir?
        if s.durum.value == "Hazır":
            aksiyon = f"""
            <form method="post" action="/personel/garson/durum" style="flex:1">
              <input type="hidden" name="sid" value="{s.id}">
              <input type="hidden" name="durum" value="Garson Aldı">
              <button style="width:100%;padding:10px;border:none;border-radius:10px;
                             background:linear-gradient(135deg,#f39c12,#e67e22);
                             color:white;font-weight:800;font-size:.88rem;cursor:pointer">
                📦 Aldım
              </button>
            </form>"""
        elif s.durum.value == "Garson Aldı":
            aksiyon = f"""
            <form method="post" action="/personel/garson/durum" style="flex:1">
              <input type="hidden" name="sid" value="{s.id}">
              <input type="hidden" name="durum" value="Servis Edildi">
              <button style="width:100%;padding:10px;border:none;border-radius:10px;
                             background:linear-gradient(135deg,#27ae60,#2ecc71);
                             color:white;font-weight:800;font-size:.88rem;cursor:pointer">
                ✅ Servis Edildi
              </button>
            </form>"""
        else:
            aksiyon = '<div style="flex:1;text-align:center;font-size:.82rem;color:#27ae60;font-weight:700;padding:10px">✔ Teslim Edildi</div>'

        durum_renk = {"Hazır":"#e8f8f5","Garson Aldı":"#fef9ec","Servis Edildi":"#f0fff4"}.get(s.durum.value,"#f8f9fa")
        sol_renk   = {"Hazır":"#27ae60","Garson Aldı":"#f39c12","Servis Edildi":"#2ecc71"}.get(s.durum.value,"#95a5a6")

        kartlar += f"""
        <div style="background:{durum_renk};border-radius:14px;padding:18px;
                    border-left:5px solid {sol_renk};margin-bottom:12px;
                    box-shadow:0 2px 8px rgba(0,0,0,.06)">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">
            <div style="display:flex;align-items:center;gap:10px">
              <span style="font-size:1.1rem">🪑</span>
              <strong style="font-size:1rem">{masa}</strong>
              <span style="font-size:.78rem;color:#95a5a6">#{s.id} · {saat}</span>
            </div>
            {badge}
          </div>
          <div style="margin-bottom:14px">{kalemler}</div>
          <div style="display:flex;gap:10px">{aksiyon}</div>
        </div>"""

    bos_mesaj = ""
    if not kartlar:
        bos_mesaj = """
        <div style="text-align:center;padding:60px 20px;color:#95a5a6">
          <div style="font-size:3rem;margin-bottom:14px">🍽</div>
          <div style="font-size:1rem;font-weight:700">Servis bekleyen sipariş yok</div>
          <div style="font-size:.85rem;margin-top:6px">Mutfaktan hazır sipariş gelince burada görünür</div>
        </div>"""

    html = f"""
    <style>
      .gr-wrap {{ max-width:760px;margin:0 auto }}
      .gr-ozet {{ display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px }}
      .gr-stat {{ flex:1;min-width:140px;border-radius:14px;padding:18px 20px;color:white;text-align:center }}
      .gr-stat-val {{ font-size:1.8rem;font-weight:900;line-height:1 }}
      .gr-stat-lbl {{ font-size:.72rem;opacity:.8;margin-top:5px;text-transform:uppercase;letter-spacing:.8px;font-weight:700 }}
    </style>
    <div class="gr-wrap">
      <div class="gr-ozet">
        <div class="gr-stat" style="background:linear-gradient(135deg,#27ae60,#2ecc71)">
          <div class="gr-stat-val">{sum(1 for s in siparisler if s.durum.value=='Hazır')}</div>
          <div class="gr-stat-lbl">Hazır / Bekliyor</div>
        </div>
        <div class="gr-stat" style="background:linear-gradient(135deg,#f39c12,#e67e22)">
          <div class="gr-stat-val">{sum(1 for s in siparisler if s.durum.value=='Garson Aldı')}</div>
          <div class="gr-stat-lbl">Yolda</div>
        </div>
        <div class="gr-stat" style="background:linear-gradient(135deg,#2980b9,#5dade2)">
          <div class="gr-stat-val">{sum(1 for s in siparisler if s.durum.value=='Servis Edildi')}</div>
          <div class="gr-stat-lbl">Teslim Edildi</div>
        </div>
      </div>
      {kartlar or bos_mesaj}
    </div>"""

    return _prender(html, sayfa_baslik="Garson Paneli", ak="garson",
                    mesaj=mesaj, mesaj_tur=mesaj_tur, otoyenile=True, refresh_sec=10)


@app.route("/personel/garson/durum", methods=["POST"])
@login_gerekli
def pers_garson_durum():
    sid   = request.form.get("sid", type=int)
    durum = request.form.get("durum","")
    sy    = _sy()
    durum_map = {
        "Garson Aldı":   SiparisDurumu.GARSON_ALDI,
        "Servis Edildi": SiparisDurumu.SERVIS_EDILDI,
    }
    if sid and durum in durum_map:
        sy.durum_guncelle(sid, durum_map[durum])
        mesaj = f"Sipariş #{sid} → {durum}"
        return redirect(url_for("pers_garson", mesaj=mesaj, tur="success"))
    return redirect(url_for("pers_garson"))


# ─── KASA ─────────────────────────────────────────────
@app.route("/personel/kasa")
@login_gerekli
def pers_kasa():
    sy = _sy()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")
    KASA_D = {"Servis Edildi"}
    siparisler = [s for s in sy.aktif_siparisler() if s.durum.value in KASA_D]
    siparisler.sort(key=lambda s: s.olusturma_zamani)

    satirlar = ""
    for s in siparisler:
        masa = f"Masa {s.masa_no}" if s.masa_no else "Paket"
        badge = _durum_badge(s.durum.value)
        satirlar += f"""<tr>
          <td><strong>#{s.id}</strong></td>
          <td>{masa}</td>
          <td>{badge}</td>
          <td style="font-weight:700;color:#1B6CA8">{s.genel_toplam:.2f} ₺</td>
          <td><a href="/personel/kasa/{s.id}" class="btn btn-primary btn-sm">Detay / Ödeme</a></td>
        </tr>"""

    if not satirlar:
        satirlar = '<tr><td colspan="5" style="text-align:center;color:#888;padding:30px">Ödeme bekleyen sipariş yok</td></tr>'

    html = f"""
    <div style="margin-bottom:10px">
      <a href="/personel/kasa" class="btn btn-dark btn-sm">⟳ Yenile</a>
    </div>
    <div class="card">
      <h2>Siparişler</h2>
      <table>
        <thead><tr><th>#</th><th>Masa</th><th>Durum</th><th>Tutar</th><th>İşlem</th></tr></thead>
        <tbody>{satirlar}</tbody>
      </table>
    </div>"""
    return _prender(html, sayfa_baslik="Kasa Terminali", ak="kasa",
                    otoyenile=True, mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/kasa/<int:sid>")
@login_gerekli
def pers_kasa_detay(sid):
    sy = _sy()
    s  = sy.siparis_bul(sid)
    if not s:
        return redirect(url_for("pers_kasa", mesaj="Sipariş bulunamadı.", tur="danger"))
    mesaj     = request.args.get("mesaj", "")
    mesaj_tur = request.args.get("tur", "info")
    masa = f"Masa {s.masa_no}" if s.masa_no else "Paket"
    kalem_satirlari = ""
    for k in s.kalemler:
        kalem_satirlari += f"<tr><td>{k.menu_ogesi.ad}</td><td>x{k.miktar}</td><td style='font-weight:600'>{k.toplam*1.1:.2f} ₺</td></tr>"

    html = f"""
    <div class="card">
      <h2>#{sid} — {masa} &nbsp; {_durum_badge(s.durum.value)}</h2>
      <table style="margin-bottom:14px">
        <thead><tr><th>Ürün</th><th>Adet</th><th>Tutar (KDV)</th></tr></thead>
        <tbody>{kalem_satirlari}</tbody>
      </table>
      <div style="text-align:right;font-size:1.1rem;font-weight:700;color:#1B6CA8;margin-bottom:16px">
        Toplam: {s.genel_toplam:.2f} ₺
      </div>
      <hr style="margin-bottom:14px">

      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <form method="post" action="/personel/kasa/islem">
          <input type="hidden" name="sid" value="{sid}">
          <input type="hidden" name="islem" value="iptal">
          <button class="btn btn-danger">❌ İptal Et</button>
        </form>
      </div>
    </div>

    <div class="card">
      <h2>💰 Ödeme Al</h2>
      <form method="post" action="/personel/kasa/odeme">
        <input type="hidden" name="sid" value="{sid}">
        <div class="form-row">
          <label style="font-weight:600">Alınan Tutar (₺):</label>
          <input type="number" name="alindi" step="0.01" min="0"
                 value="{s.genel_toplam:.2f}" style="width:140px">
          <button class="btn btn-success">✔ Ödemeyi Onayla</button>
        </div>
        <div style="font-size:.85rem;color:#888">
          Tahsilat tutarı girin, para üstü otomatik hesaplanır.
        </div>
      </form>
    </div>
    <a href="/personel/kasa" class="btn btn-secondary">← Geri</a>
    """
    return _prender(html, sayfa_baslik=f"Kasa — Sipariş #{sid}", ak="kasa",
                    mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/kasa/islem", methods=["POST"])
@login_gerekli
def pers_kasa_islem():
    sid   = request.form.get("sid", type=int)
    islem = request.form.get("islem","")
    sy    = _sy()
    if islem == "garson":
        sy.durum_guncelle(sid, SiparisDurumu.GARSON_ALDI)
        mesaj = f"#{sid} → Garson Aldı"
    elif islem == "servis":
        sy.durum_guncelle(sid, SiparisDurumu.SERVIS_EDILDI)
        mesaj = f"#{sid} → Servis Edildi"
    elif islem == "iptal":
        sy.durum_guncelle(sid, SiparisDurumu.IPTAL)
        mesaj = f"#{sid} iptal edildi."
    else:
        mesaj = "Bilinmeyen işlem."
    return redirect(url_for("pers_kasa", mesaj=mesaj, tur="success"))

@app.route("/personel/kasa/odeme", methods=["POST"])
@login_gerekli
def pers_kasa_odeme():
    sid    = request.form.get("sid", type=int)
    alindi = request.form.get("alindi", 0, type=float)
    sy     = _sy()
    s      = sy.siparis_bul(sid)
    if not s:
        return redirect(url_for("pers_kasa", mesaj="Sipariş bulunamadı.", tur="danger"))
    para_ustu = alindi - s.genel_toplam
    if para_ustu < 0:
        # Eksik ödeme → detay sayfasına hata ile geri dön
        return redirect(url_for("pers_kasa_detay", sid=sid,
                                mesaj=f"Eksik ödeme! {abs(para_ustu):.2f} ₺ eksik girdiniz.",
                                tur="danger"))
    sy.durum_guncelle(sid, SiparisDurumu.ODENDI)
    return redirect(url_for("pers_kasa_adisyon", sid=sid,
                            alindi=f"{alindi:.2f}", para_ustu=f"{para_ustu:.2f}"))

# ─── ADİSYON ──────────────────────────────────────────
@app.route("/personel/kasa/adisyon/<int:sid>")
@login_gerekli
def pers_kasa_adisyon(sid):
    from datetime import datetime
    sy = _sy()
    s  = sy.siparis_bul(sid)
    if not s:
        return redirect(url_for("pers_kasa"))
    alindi    = request.args.get("alindi",    f"{s.genel_toplam:.2f}")
    para_ustu = request.args.get("para_ustu", "0.00")
    tarih     = datetime.now().strftime("%d.%m.%Y")
    saat      = datetime.now().strftime("%H:%M")
    masa_str  = f"Masa {s.masa_no}" if s.masa_no else "Paket"

    kalem_satirlari = ""
    for k in s.kalemler:
        birim_kdv = k.menu_ogesi.fiyat * 1.1
        toplam_kdv = birim_kdv * k.miktar
        kalem_satirlari += f"""
        <tr>
          <td style="padding:5px 2px">{k.menu_ogesi.ad}</td>
          <td style="padding:5px 2px;text-align:center">{k.miktar}</td>
          <td style="padding:5px 2px;text-align:right">{birim_kdv:.2f} ₺</td>
          <td style="padding:5px 2px;text-align:right;font-weight:600">{toplam_kdv:.2f} ₺</td>
        </tr>"""

    ara_toplam = s.genel_toplam / 1.1
    kdv_tutar  = s.genel_toplam - ara_toplam

    html = f"""
    <style>
      .adi-wrap {{
        max-width: 420px; margin: 0 auto;
      }}
      .adi-actions {{
        display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;
      }}
      .adi-ticket {{
        background: white; border-radius: 14px;
        border: 1.5px solid #edf0f5;
        box-shadow: 0 2px 16px rgba(0,0,0,.08);
        overflow: hidden;
        font-family: 'Courier New', monospace;
      }}
      .adi-header {{
        background: linear-gradient(135deg,#1b2838,#243447);
        color: white; text-align: center; padding: 22px 20px 18px;
      }}
      .adi-header-logo  {{ font-size: 1.8rem; margin-bottom: 4px; }}
      .adi-header-isim  {{ font-size: 1.1rem; font-weight: 800; letter-spacing: 1px; }}
      .adi-header-alt   {{ font-size: .72rem; opacity: .6; margin-top: 3px; }}
      .adi-header-tarih {{
        margin-top: 12px; font-size: .78rem; opacity: .75;
        display: flex; justify-content: center; gap: 16px;
      }}
      .adi-kesik {{
        border: none; border-top: 2px dashed #dde3ea; margin: 0;
      }}
      .adi-bilgi {{
        padding: 12px 18px;
        display: flex; justify-content: space-between;
        font-size: .82rem; color: #5d7080;
        background: #f8fafc;
      }}
      .adi-bilgi strong {{ color: #1b2838; }}
      .adi-table-wrap {{ padding: 4px 18px 0; }}
      .adi-table {{
        width: 100%; border-collapse: collapse;
        font-size: .8rem;
      }}
      .adi-table thead tr {{
        border-bottom: 1.5px solid #edf0f5;
      }}
      .adi-table th {{
        padding: 6px 2px; color: #95a5a6;
        font-weight: 700; font-size: .7rem;
        text-transform: uppercase; letter-spacing: .5px;
      }}
      .adi-table th:last-child,
      .adi-table td:last-child {{ text-align: right; }}
      .adi-table tbody tr {{
        border-bottom: 1px solid #f8fafc;
      }}
      .adi-table tbody tr:last-child {{ border-bottom: none; }}
      .adi-ozet {{
        padding: 10px 18px; border-top: 1.5px solid #edf0f5;
        font-size: .82rem;
      }}
      .adi-ozet-satir {{
        display: flex; justify-content: space-between;
        padding: 3px 0; color: #5d7080;
      }}
      .adi-ozet-toplam {{
        display: flex; justify-content: space-between;
        padding: 8px 0 4px; font-size: 1.1rem; font-weight: 900;
        border-top: 2px solid #1b2838; color: #1b2838; margin-top: 4px;
      }}
      .adi-odeme {{
        padding: 10px 18px 14px;
        background: #f0fdf4;
        border-top: 1.5px solid #86efac;
      }}
      .adi-odeme-satir {{
        display: flex; justify-content: space-between;
        font-size: .85rem; padding: 3px 0;
      }}
      .adi-odeme-satir.para-ustu {{
        font-weight: 800; font-size: .95rem; color: #166534;
        border-top: 1px dashed #86efac; margin-top: 6px; padding-top: 8px;
      }}
      .adi-footer {{
        text-align: center; padding: 14px 18px 18px;
        font-size: .75rem; color: #95a5a6;
        border-top: 2px dashed #edf0f5;
      }}
      .adi-footer strong {{ color: #1b2838; display: block; margin-bottom: 3px; }}

      @media print {{
        body * {{ visibility: hidden !important; }}
        .adi-ticket, .adi-ticket * {{ visibility: visible !important; }}
        .adi-ticket {{
          position: fixed !important; top: 0; left: 0;
          width: 80mm !important; box-shadow: none !important;
          border: none !important;
        }}
        .adi-actions {{ display: none !important; }}
      }}
    </style>

    <div class="adi-wrap">
      <div class="adi-actions">
        <button onclick="window.print()" class="btn btn-primary">🖨 Yazdır</button>
        <a href="/personel/kasa" class="btn btn-secondary">← Kasaya Dön</a>
      </div>

      <div class="adi-ticket">

        <!-- Başlık -->
        <div class="adi-header">
          <div class="adi-header-logo">🍽</div>
          <div class="adi-header-isim">ANADOLU SOFRASI</div>
          <div class="adi-header-alt">Sipariş Fişi</div>
          <div class="adi-header-tarih">
            <span>📅 {tarih}</span>
            <span>🕐 {saat}</span>
          </div>
        </div>

        <hr class="adi-kesik">

        <!-- Sipariş Bilgisi -->
        <div class="adi-bilgi">
          <span>Sipariş: <strong>#{sid}</strong></span>
          <span>Masa: <strong>{masa_str}</strong></span>
        </div>

        <hr class="adi-kesik">

        <!-- Ürünler -->
        <div class="adi-table-wrap">
          <table class="adi-table">
            <thead>
              <tr>
                <th style="text-align:left">Ürün</th>
                <th style="text-align:center">Adet</th>
                <th style="text-align:right">Birim</th>
                <th style="text-align:right">Tutar</th>
              </tr>
            </thead>
            <tbody>
              {kalem_satirlari}
            </tbody>
          </table>
        </div>

        <!-- Özet -->
        <div class="adi-ozet">
          <div class="adi-ozet-satir">
            <span>Ara Toplam</span>
            <span>{ara_toplam:.2f} ₺</span>
          </div>
          <div class="adi-ozet-satir">
            <span>KDV (%10)</span>
            <span>{kdv_tutar:.2f} ₺</span>
          </div>
          <div class="adi-ozet-toplam">
            <span>TOPLAM</span>
            <span>{s.genel_toplam:.2f} ₺</span>
          </div>
        </div>

        <!-- Ödeme -->
        <div class="adi-odeme">
          <div class="adi-odeme-satir">
            <span>Alınan</span>
            <span>{alindi} ₺</span>
          </div>
          <div class="adi-odeme-satir para-ustu">
            <span>Para Üstü</span>
            <span>{para_ustu} ₺</span>
          </div>
        </div>

        <!-- Alt -->
        <div class="adi-footer">
          <strong>Teşekkür Ederiz!</strong>
          Tekrar Bekleriz 😊
        </div>

      </div>
    </div>
    """
    return _prender(html, sayfa_baslik=f"Adisyon — #{sid}", ak="kasa")

# ─── YÖNETİM GENEL ────────────────────────────────────
@app.route("/personel/yonetim")
@login_gerekli
def pers_yonetim():
    sy  = _sy()
    my  = _my()
    ozet = sy.gunluk_ozet()
    aktif = len(sy.aktif_siparisler())
    toplam_menu = len(list(my.kategoriye_gore_listele()))

    populer_html = ""
    if ozet["en_populer"]:
        medals = ["🥇","🥈","🥉"]
        for i,(ad,adet) in enumerate(ozet["en_populer"][:5]):
            medal = medals[i] if i < 3 else f"{i+1}."
            pct   = int((adet / max(a for _,a in ozet["en_populer"])) * 100)
            populer_html += f"""
            <div style="margin-bottom:14px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
                <span style="font-weight:600;font-size:.9rem">{medal} {ad}</span>
                <span style="font-size:.82rem;color:#2980b9;font-weight:700">{adet} sipariş</span>
              </div>
              <div style="background:#edf0f5;border-radius:20px;height:7px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#2980b9,#5dade2);
                            height:100%;width:{pct}%;border-radius:20px;
                            transition:width .6s ease"></div>
              </div>
            </div>"""
    else:
        populer_html = '<p style="color:#95a5a6;font-size:.88rem">Bugün henüz sipariş alınmadı.</p>'

    # Admin yeniden başlatma bloğu
    if session.get("rol") == "admin":
        admin_blok = """
    <!-- Yeniden Başlat Onay Modalı -->
    <div id="yb-modal" style="display:none;position:fixed;inset:0;z-index:9999;
         background:rgba(0,0,0,.45);backdrop-filter:blur(3px);
         align-items:center;justify-content:center">
      <div style="background:white;border-radius:20px;padding:32px 28px;
                  max-width:380px;width:90%;box-shadow:0 24px 64px rgba(0,0,0,.25);
                  animation:ybIn .25s cubic-bezier(.34,1.56,.64,1)">
        <div style="text-align:center;margin-bottom:20px">
          <div style="font-size:3rem;margin-bottom:10px">🔄</div>
          <h2 style="font-size:1.15rem;font-weight:800;color:#1b2838;margin-bottom:8px">
            Yeniden Başlat
          </h2>
          <p style="font-size:.88rem;color:#7f8c8d;line-height:1.6">
            Sunucu kapatılıp yeniden açılacak.<br>
            Aktif siparişler ve veriler korunur.<br>
            <strong style="color:#c0392b">Devam etmek istiyor musunuz?</strong>
          </p>
        </div>
        <div style="display:flex;gap:10px;margin-top:4px">
          <button onclick="document.getElementById('yb-modal').style.display='none'"
                  style="flex:1;padding:14px;border:2px solid #dde3ea;border-radius:12px;
                         background:white;color:#5d7080;font-size:.95rem;font-weight:700;
                         cursor:pointer;transition:all .15s"
                  onmouseover="this.style.background='#f0f4f8'"
                  onmouseout="this.style.background='white'">
            İptal
          </button>
          <form method="post" action="/personel/yeniden-baslat" style="flex:1">
            <button type="submit"
                    style="width:100%;padding:14px;border:none;border-radius:12px;
                           background:linear-gradient(135deg,#e74c3c,#c0392b);
                           color:white;font-size:.95rem;font-weight:800;cursor:pointer;
                           box-shadow:0 4px 14px rgba(231,76,60,.35);transition:all .15s"
                    onmouseover="this.style.transform='translateY(-1px)'"
                    onmouseout="this.style.transform=''">
              Evet, Başlat
            </button>
          </form>
        </div>
      </div>
    </div>
    <style>
      @keyframes ybIn {
        from { opacity:0; transform:scale(.88) translateY(16px); }
        to   { opacity:1; transform:scale(1) translateY(0); }
      }
    </style>

    <div class="card" style="margin-top:0;border:2px solid #fde8e8;background:#fffafa">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px">
        <div>
          <h2 style="color:#c0392b;margin-bottom:6px">🔄 Sistem Yönetimi</h2>
          <p style="font-size:.84rem;color:#7f8c8d;line-height:1.55">
            Sunucuyu tamamen kapatıp yeniden başlatır.<br>
            Aktif siparişler etkilenmez, veriler korunur.
          </p>
        </div>
        <button onclick="document.getElementById('yb-modal').style.display='flex'"
                style="padding:12px 26px;
                       background:linear-gradient(135deg,#e74c3c,#c0392b);
                       color:white;border:none;border-radius:10px;
                       font-size:.95rem;font-weight:800;cursor:pointer;
                       box-shadow:0 4px 14px rgba(231,76,60,.35);transition:all .15s"
                onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(231,76,60,.5)'"
                onmouseout="this.style.transform='';this.style.boxShadow='0 4px 14px rgba(231,76,60,.35)'">
          🔄 Yeniden Başlat
        </button>
      </div>
    </div>"""
    else:
        admin_blok = ""

    html = f"""
    <style>
      .sc-wrap{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px}}
      @media(max-width:900px){{.sc-wrap{{grid-template-columns:repeat(2,1fr)}}}}
      .sc{{border-radius:14px;padding:22px 20px;position:relative;overflow:hidden;
           box-shadow:0 2px 12px rgba(0,0,0,.08)}}
      .sc::before{{content:'';position:absolute;right:-18px;top:-18px;
                  width:80px;height:80px;border-radius:50%;
                  background:rgba(255,255,255,.12)}}
      .sc-icon{{font-size:1.6rem;margin-bottom:10px}}
      .sc-val{{font-size:2.1rem;font-weight:900;color:white;line-height:1}}
      .sc-lbl{{font-size:.72rem;color:rgba(255,255,255,.75);margin-top:6px;font-weight:600;
               text-transform:uppercase;letter-spacing:.8px}}
      .sc-1{{background:linear-gradient(135deg,#2980b9,#5dade2)}}
      .sc-2{{background:linear-gradient(135deg,#27ae60,#58d68d)}}
      .sc-3{{background:linear-gradient(135deg,#f39c12,#f7dc6f)}}
      .sc-4{{background:linear-gradient(135deg,#8e44ad,#bb8fce)}}

      .qc-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:0}}
      @media(max-width:900px){{.qc-grid{{grid-template-columns:repeat(2,1fr)}}}}
      .qc{{border-radius:12px;padding:18px 16px;text-decoration:none;
           border:1.5px solid #edf0f5;background:white;
           display:flex;flex-direction:column;align-items:flex-start;gap:8px;
           transition:all .2s;box-shadow:0 1px 4px rgba(0,0,0,.05)}}
      .qc:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.1);
                border-color:#2980b9}}
      .qc-icon{{font-size:1.6rem}}
      .qc-title{{font-weight:700;font-size:.9rem;color:#1b2838}}
      .qc-desc{{font-size:.74rem;color:#95a5a6}}

      .lower-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:0}}
      @media(max-width:800px){{.lower-grid{{grid-template-columns:1fr}}}}
    </style>

    <!-- İstatistik Kartları -->
    <div class="sc-wrap">
      <div class="sc sc-1">
        <div class="sc-val">{aktif}</div>
        <div class="sc-lbl">Aktif Sipariş</div>
      </div>
      <div class="sc sc-2">
        <div class="sc-val">{ozet['siparis_sayisi']}</div>
        <div class="sc-lbl">Bugün Ödenen</div>
      </div>
      <div class="sc sc-3">
        <div class="sc-val">{ozet['toplam_ciro']:.0f} ₺</div>
        <div class="sc-lbl">Günlük Ciro</div>
      </div>
      <div class="sc sc-4">
        <div class="sc-val">{toplam_menu}</div>
        <div class="sc-lbl">Menüde Ürün</div>
      </div>
    </div>

    <!-- Alt bölüm -->
    <div class="lower-grid">
      <!-- Popüler Ürünler -->
      <div class="card">
        <h2>🏆 Bugünün En Çok Sipariş Edilenleri</h2>
        {populer_html}
      </div>

      <!-- Hızlı Erişim -->
      <div class="card">
        <h2>⚡ Hızlı Erişim</h2>
        <div class="qc-grid">
          <a href="/personel/menu" class="qc">
            <span class="qc-icon">📋</span>
            <span class="qc-title">Menü</span>
            <span class="qc-desc">Ürün düzenle</span>
          </a>
          <a href="/personel/masalar" class="qc">
            <span class="qc-icon">🪑</span>
            <span class="qc-title">Masalar</span>
            <span class="qc-desc">Rezervasyon</span>
          </a>
          <a href="/personel/malzeme" class="qc">
            <span class="qc-icon">📦</span>
            <span class="qc-title">Stok</span>
            <span class="qc-desc">Malzeme takibi</span>
          </a>
          <a href="/personel/kampanya" class="qc">
            <span class="qc-icon">🏷</span>
            <span class="qc-title">Kampanya</span>
            <span class="qc-desc">İndirimler</span>
          </a>
        </div>
      </div>
    </div>

    {admin_blok}
    """
    return _prender(html, sayfa_baslik="Genel Bakış", ak="yonetim")

# ─── MENÜ YÖNETİMİ ────────────────────────────────────
@app.route("/personel/menu")
@login_gerekli
def pers_menu():
    my  = _my()
    maly = _maly()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")
    satirlar = ""
    for o in my.kategoriye_gore_listele():
        tukendi = (o.stok == 0) or (not maly.yapilabilir_mi(o.ad))
        durum = "✓ Mevcut" if o.mevcut and not tukendi else ("⚠ Tükendi" if tukendi else "✗ Kapalı")
        dur_cls = "color:#27ae60" if o.mevcut and not tukendi else "color:#e74c3c"
        indirim = f"%{o.indirim_yuzdesi:.0f}" if o.indirim_yuzdesi > 0 else "—"
        toggle_label = "Kapat" if o.mevcut else "Aç"
        satirlar += f"""<tr>
          <td>{o.id}</td><td>{o.kategori.value}</td><td><strong>{o.ad}</strong></td>
          <td>{o.fiyat:.2f} ₺</td><td>{o.kdv_dahil_fiyat:.2f} ₺</td>
          <td>{indirim}</td>
          <td style="{dur_cls};font-weight:600">{durum}</td>
          <td>
            <a href="/personel/menu/duzenle/{o.id}" class="btn btn-primary btn-sm">Düzenle</a>
            <form method="post" action="/personel/menu/toggle" style="display:inline">
              <input type="hidden" name="oge_id" value="{o.id}">
              <button class="btn btn-secondary btn-sm">{toggle_label}</button>
            </form>
          </td>
        </tr>"""
    html = f"""
    <div style="margin-bottom:12px">
      <a href="/personel/menu/ekle" class="btn btn-success">+ Yeni Ürün</a>
    </div>
    <div class="card">
      <h2>Menü Listesi</h2>
      <div style="overflow-x:auto">
      <table>
        <thead><tr><th>ID</th><th>Kategori</th><th>Ürün</th><th>Fiyat</th><th>KDV Dahil</th><th>İndirim</th><th>Durum</th><th>İşlem</th></tr></thead>
        <tbody>{satirlar}</tbody>
      </table></div>
    </div>"""
    return _prender(html, sayfa_baslik="Menü Yönetimi", ak="menu", mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/menu/toggle", methods=["POST"])
@login_gerekli
def pers_menu_toggle():
    oge_id = request.form.get("oge_id", type=int)
    my = _my()
    o  = my.oge_bul(oge_id)
    if o:
        my.oge_guncelle(oge_id, mevcut=not o.mevcut)
        mesaj = f"'{o.ad}' {'açıldı' if not o.mevcut else 'kapatıldı'}."
    else:
        mesaj = "Ürün bulunamadı."
    return redirect(url_for("pers_menu", mesaj=mesaj, tur="success"))

@app.route("/personel/menu/ekle", methods=["GET","POST"])
@login_gerekli
def pers_menu_ekle():
    from models import Kategori as KatEnum
    my = _my()
    mesaj = ""
    if request.method == "POST":
        ad  = request.form.get("ad","").strip()
        kat = request.form.get("kategori","")
        try:
            fiyat = float(request.form.get("fiyat","0").replace(",","."))
            aciklama = request.form.get("aciklama","").strip()
            kategori = KatEnum(kat)
            my.oge_ekle(ad, kategori, fiyat, aciklama)
            return redirect(url_for("pers_menu", mesaj=f"'{ad}' eklendi.", tur="success"))
        except Exception as e:
            mesaj = f"Hata: {e}"

    kat_options = "".join(f'<option value="{k.value}">{k.value}</option>' for k in KatEnum)
    html = f"""
    <div class="card">
      <h2>Yeni Ürün Ekle</h2>
      <form method="post">
        <div class="form-row"><label>Ürün Adı:</label>
          <input type="text" name="ad" required style="width:220px"></div>
        <div class="form-row"><label>Kategori:</label>
          <select name="kategori">{kat_options}</select></div>
        <div class="form-row"><label>Fiyat (KDV hariç ₺):</label>
          <input type="number" name="fiyat" step="0.01" min="0" style="width:120px"></div>
        <div class="form-row"><label>Açıklama:</label>
          <input type="text" name="aciklama" style="width:280px"></div>
        <button class="btn btn-success" style="margin-top:8px">Ekle</button>
        <a href="/personel/menu" class="btn btn-secondary" style="margin-top:8px">İptal</a>
      </form>
    </div>"""
    return _prender(html, sayfa_baslik="Yeni Ürün", ak="menu", mesaj=mesaj, mesaj_tur="danger" if mesaj else "info")

@app.route("/personel/menu/duzenle/<int:oge_id>", methods=["GET","POST"])
@login_gerekli
def pers_menu_duzenle(oge_id):
    my = _my()
    o  = my.oge_bul(oge_id)
    if not o:
        return redirect(url_for("pers_menu", mesaj="Ürün bulunamadı.", tur="danger"))
    if request.method == "POST":
        try:
            yeni_ad   = request.form.get("ad","").strip() or None
            fiyat_str = request.form.get("fiyat","")
            yeni_fiyat = float(fiyat_str.replace(",",".")) if fiyat_str else None
            yeni_aciklama = request.form.get("aciklama","").strip() or None
            my.oge_guncelle(oge_id, ad=yeni_ad, fiyat=yeni_fiyat, aciklama=yeni_aciklama)
            return redirect(url_for("pers_menu", mesaj=f"'{o.ad}' güncellendi.", tur="success"))
        except Exception as e:
            pass
    html = f"""
    <div class="card">
      <h2>Düzenle — {o.ad}</h2>
      <form method="post">
        <div class="form-row"><label>Ürün Adı:</label>
          <input type="text" name="ad" value="{o.ad}" style="width:220px"></div>
        <div class="form-row"><label>Fiyat (KDV hariç ₺):</label>
          <input type="number" name="fiyat" step="0.01" value="{o.fiyat:.2f}" style="width:120px"></div>
        <div class="form-row"><label>Açıklama:</label>
          <input type="text" name="aciklama" value="{o.aciklama or ''}" style="width:280px"></div>
        <button class="btn btn-primary" style="margin-top:8px">Kaydet</button>
        <a href="/personel/menu" class="btn btn-secondary" style="margin-top:8px">İptal</a>
      </form>
    </div>"""
    return _prender(html, sayfa_baslik="Ürün Düzenle", ak="menu")

# ─── MASA YÖNETİMİ ────────────────────────────────────
@app.route("/personel/masalar")
@login_gerekli
def pers_masalar():
    sy = _sy()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")
    kartlar = ""
    for m in sorted(sy.masalar.values(), key=lambda x: x.no):
        if m.durum.value == "Boş":
            cls, etiket = "mk-bos", "Boş"
        elif m.durum.value == "Rezerve":
            cls, etiket = "mk-rez", "Rezerve"
        else:
            cls, etiket = "mk-dolu", "Dolu"

        if m.durum.value == "Dolu" and m.aktif_siparis_id:
            s = sy.siparis_bul(m.aktif_siparis_id)
            extra = f"<br><small>#{m.aktif_siparis_id} · {s.genel_toplam:.0f}₺</small>" if s else ""
        elif m.durum.value == "Rezerve":
            extra = f'<br><form method="post" action="/personel/masalar/rezerve" style="margin-top:6px"><input type="hidden" name="masa_no" value="{m.no}"><button class="btn btn-warning btn-sm">Kaldır</button></form>'
        else:
            extra = f'<br><form method="post" action="/personel/masalar/rezerve" style="margin-top:6px"><input type="hidden" name="masa_no" value="{m.no}"><button class="btn btn-secondary btn-sm">Rezerve Et</button></form>'

        kartlar += f'<div class="masa-kart {cls}">Masa {m.no}<br><small>{m.kapasite} kişi · {etiket}</small>{extra}</div>'

    html = f"""
    <div class="card">
      <h2>Masa Durumları</h2>
      <div class="masa-grid">{kartlar}</div>
    </div>
    <div class="card">
      <h2>Dolu Masayı Boşalt</h2>
      <form method="post" action="/personel/masalar/bosalt">
        <div class="form-row">
          <label>Masa No:</label>
          <input type="number" name="masa_no" min="1" style="width:80px">
          <button class="btn btn-danger">Masayı Boşalt</button>
        </div>
        <div style="font-size:.8rem;color:#888">Aktif siparişi olmayan dolu masayı manuel boşaltır.</div>
      </form>
    </div>"""
    return _prender(html, sayfa_baslik="Masa Yönetimi", ak="masalar", mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/masalar/rezerve", methods=["POST"])
@login_gerekli
def pers_masa_rezerve():
    masa_no = request.form.get("masa_no", type=int)
    sy = _sy()
    masa = sy.masalar.get(masa_no)
    if not masa:
        return redirect(url_for("pers_masalar", mesaj="Masa bulunamadı.", tur="danger"))
    if masa.durum.value == "Dolu":
        return redirect(url_for("pers_masalar", mesaj="Dolu masa rezerve edilemez.", tur="danger"))
    if masa.durum.value == "Rezerve":
        masa.durum = MasaDurumu.BOS
        mesaj = f"Masa {masa_no} rezervasyonu kaldırıldı."
    else:
        masa.durum = MasaDurumu.REZERVE
        mesaj = f"Masa {masa_no} rezerve edildi."
    storage.masalar_kaydet(sy.masalar)
    return redirect(url_for("pers_masalar", mesaj=mesaj, tur="success"))

@app.route("/personel/masalar/bosalt", methods=["POST"])
@login_gerekli
def pers_masa_bosalt():
    masa_no = request.form.get("masa_no", type=int)
    sy = _sy()
    masa = sy.masalar.get(masa_no)
    if not masa:
        return redirect(url_for("pers_masalar", mesaj="Masa bulunamadı.", tur="danger"))
    masa.durum = MasaDurumu.BOS
    masa.aktif_siparis_id = None
    storage.masalar_kaydet(sy.masalar)
    return redirect(url_for("pers_masalar", mesaj=f"Masa {masa_no} boşaltıldı.", tur="success"))

# ─── MALZEME YÖNETİMİ ─────────────────────────────────
@app.route("/personel/malzeme")
@login_gerekli
def pers_malzeme():
    from malzeme_manager import MalzemeYoneticisi as MY
    maly = _maly()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")
    ad_to_m = {m.ad: m for m in maly.malzemeler.values()}
    tablo = ""
    for kat_ad, m_adlari in MY.KATEGORILER.items():
        tablo += f'<tr><td colspan="4" style="background:#1a1a2e;color:white;font-weight:700;padding:8px 12px">▸ {kat_ad}</td></tr>'
        for ad in m_adlari:
            m = ad_to_m.get(ad)
            if not m: continue
            uyari = " ⚠" if m.miktar < 200 else ""
            uyari_cls = "color:#e74c3c;font-weight:700" if m.miktar < 200 else ""
            tablo += f"""<tr>
              <td>{m.id}</td><td>{m.ad}</td>
              <td style="{uyari_cls}">{m.miktar:.0f} {m.birim}{uyari}</td>
              <td>
                <form method="post" action="/personel/malzeme/guncelle" style="display:flex;gap:6px;align-items:center">
                  <input type="hidden" name="malzeme_id" value="{m.id}">
                  <input type="number" name="miktar" step="1" min="0" placeholder="Yeni miktar" style="width:110px">
                  <button class="btn btn-primary btn-sm">Güncelle</button>
                </form>
              </td>
            </tr>"""
    html = f"""
    <div class="card">
      <h2>Malzeme Stok Takibi</h2>
      <div style="overflow-x:auto">
      <table>
        <thead><tr><th>ID</th><th>Malzeme</th><th>Mevcut Stok</th><th>Güncelle</th></tr></thead>
        <tbody>{tablo}</tbody>
      </table></div>
    </div>"""
    return _prender(html, sayfa_baslik="Malzeme Stok", ak="malzeme", mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/malzeme/guncelle", methods=["POST"])
@login_gerekli
def pers_malzeme_guncelle():
    malzeme_id = request.form.get("malzeme_id", type=int)
    miktar     = request.form.get("miktar", type=float)
    maly = _maly()
    m = maly.malzemeler.get(malzeme_id)
    if m and miktar is not None:
        maly.stok_set(malzeme_id, miktar)
        mesaj = f"'{m.ad}' → {miktar:.0f} {m.birim} olarak güncellendi."
        tur = "success"
    else:
        mesaj = "Güncelleme başarısız."
        tur = "danger"
    return redirect(url_for("pers_malzeme", mesaj=mesaj, tur=tur))

# ─── KAMPANYA YÖNETİMİ ────────────────────────────────
@app.route("/personel/kampanya")
@login_gerekli
def pers_kampanya():
    my = _my()
    mesaj     = request.args.get("mesaj","")
    mesaj_tur = request.args.get("tur","info")
    satirlar = ""
    for o in my.kategoriye_gore_listele():
        if o.indirim_yuzdesi > 0:
            indirim_bilgi = f'%{o.indirim_yuzdesi:.0f} → {o.kdv_dahil_fiyat:.2f} ₺'
            kaldir = f'<form method="post" action="/personel/kampanya/kaldir" style="display:inline"><input type="hidden" name="oge_id" value="{o.id}"><button class="btn btn-danger btn-sm">Kaldır</button></form>'
        else:
            indirim_bilgi = "—"
            kaldir = ""
        satirlar += f"""<tr>
          <td>{o.id}</td><td>{o.ad}</td>
          <td>{o.kdv_dahil_fiyat:.2f} ₺</td>
          <td>{indirim_bilgi}</td>
          <td>
            <form method="post" action="/personel/kampanya/uygula" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
              <input type="hidden" name="oge_id" value="{o.id}">
              <input type="number" name="yuzde" min="1" max="99" step="1" placeholder="%" style="width:70px">
              <button class="btn btn-warning btn-sm">Uygula</button>
            </form>
            {kaldir}
          </td>
        </tr>"""
    html = f"""
    <div class="card">
      <h2>Kampanya / İndirim Yönetimi</h2>
      <div style="overflow-x:auto">
      <table>
        <thead><tr><th>ID</th><th>Ürün</th><th>KDV Dahil Fiyat</th><th>Mevcut İndirim</th><th>İşlem</th></tr></thead>
        <tbody>{satirlar}</tbody>
      </table></div>
    </div>"""
    return _prender(html, sayfa_baslik="Kampanya Yönetimi", ak="kampanya", mesaj=mesaj, mesaj_tur=mesaj_tur)

@app.route("/personel/kampanya/uygula", methods=["POST"])
@login_gerekli
def pers_kampanya_uygula():
    oge_id = request.form.get("oge_id", type=int)
    yuzde  = request.form.get("yuzde", type=float)
    my = _my()
    o  = my.oge_bul(oge_id)
    if o and yuzde and 0 < yuzde < 100:
        my.oge_guncelle(oge_id, indirim_yuzdesi=yuzde)
        mesaj = f"'{o.ad}' → %{yuzde:.0f} indirim uygulandı."
        tur = "success"
    else:
        mesaj = "Geçersiz değer (1–99 arası girin)."
        tur = "danger"
    return redirect(url_for("pers_kampanya", mesaj=mesaj, tur=tur))

@app.route("/personel/kampanya/kaldir", methods=["POST"])
@login_gerekli
def pers_kampanya_kaldir():
    oge_id = request.form.get("oge_id", type=int)
    my = _my()
    o  = my.oge_bul(oge_id)
    if o:
        my.oge_guncelle(oge_id, indirim_yuzdesi=0.0)
        mesaj = f"'{o.ad}' indirimi kaldırıldı."
    else:
        mesaj = "Ürün bulunamadı."
    return redirect(url_for("pers_kampanya", mesaj=mesaj, tur="success"))


# ─── REZERVASYON YÖNETİMİ ─────────────────────────────
@app.route("/personel/rezervasyonlar")
@login_gerekli
def pers_rezervasyonlar():
    from datetime import date
    mesaj     = request.args.get("mesaj", "")
    mesaj_tur = request.args.get("tur", "info")
    bugun     = date.today().isoformat()

    liste = storage.rezervasyon_listesi_yukle()
    # En yeni önce
    liste = sorted(liste, key=lambda r: (r.get("tarih",""), r.get("saat","")))

    # Bugün ve gelecek
    gelecek = [r for r in liste if r.get("tarih","") >= bugun and r.get("durum") != "İptal"]
    gecmis  = [r for r in liste if r.get("tarih","") < bugun or r.get("durum") == "İptal"]

    def satir(r):
        durum = r.get("durum","")
        durum_renk = {"Onaylandı":"#d4edda;color:#155724", "İptal":"#f8d7da;color:#721c24"}.get(durum,"#fff3cd;color:#856404")
        return f"""
        <tr>
          <td style="font-weight:700">#{r['id']}</td>
          <td>{r.get('tarih','')} {r.get('saat','')}</td>
          <td>{r.get('musteri','')}</td>
          <td style="text-align:center">{r.get('kisi','')} kişi</td>
          <td style="text-align:center;font-weight:700">Masa {r.get('masa_no','')}</td>
          <td>{r.get('telefon','') or '—'}</td>
          <td style="font-style:italic;color:#7f8c8d;font-size:.82rem">{r.get('not_','') or '—'}</td>
          <td><span style="padding:3px 10px;border-radius:20px;font-size:.78rem;font-weight:700;background:{durum_renk}">{durum}</span></td>
          <td>
            {'<form method="post" action="/personel/rezervasyon/iptal" style="display:inline"><input type="hidden" name="rid" value="' + str(r["id"]) + '"><button class="btn btn-danger btn-sm">İptal</button></form>' if durum != "İptal" else ''}
          </td>
        </tr>"""

    gelecek_html = "".join(satir(r) for r in gelecek) or '<tr><td colspan="9" style="text-align:center;color:#aaa;padding:20px">Rezervasyon yok</td></tr>'
    gecmis_html  = "".join(satir(r) for r in reversed(gecmis[-20:])) or '<tr><td colspan="9" style="text-align:center;color:#aaa;padding:20px">Geçmiş rezervasyon yok</td></tr>'

    tablo_stili = "width:100%;border-collapse:collapse;font-size:.88rem"
    th = "text-align:left;padding:9px 10px;color:#7f8c8d;font-size:.72rem;letter-spacing:.5px;font-weight:800;background:#f8fafc;border-bottom:2px solid #edf0f5"

    html = f"""
    <div style="max-width:1000px;margin:0 auto">

      <!-- Özet -->
      <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px">
        <div style="flex:1;min-width:160px;background:linear-gradient(135deg,#1B6CA8,#2980b9);
                    border-radius:14px;padding:18px 20px;color:white">
          <div style="font-size:.72rem;opacity:.75;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Bugün & Gelecek</div>
          <div style="font-size:1.8rem;font-weight:900">{len(gelecek)}</div>
        </div>
        <div style="flex:1;min-width:160px;background:linear-gradient(135deg,#27ae60,#2ecc71);
                    border-radius:14px;padding:18px 20px;color:white">
          <div style="font-size:.72rem;opacity:.75;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Bugün</div>
          <div style="font-size:1.8rem;font-weight:900">{sum(1 for r in gelecek if r.get('tarih')==bugun)}</div>
        </div>
        <div style="flex:1;min-width:160px;background:linear-gradient(135deg,#8e44ad,#9b59b6);
                    border-radius:14px;padding:18px 20px;color:white">
          <div style="font-size:.72rem;opacity:.75;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Toplam Kişi (bugün)</div>
          <div style="font-size:1.8rem;font-weight:900">{sum(r.get('kisi',0) for r in gelecek if r.get('tarih')==bugun)}</div>
        </div>
      </div>

      <!-- Gelecek Rezervasyonlar -->
      <div class="card" style="margin-bottom:16px">
        <h2 style="margin-bottom:14px">📅 Aktif Rezervasyonlar</h2>
        <div style="overflow-x:auto">
          <table style="{tablo_stili}">
            <thead><tr>
              <th style="{th}">#</th><th style="{th}">Tarih / Saat</th>
              <th style="{th}">Müşteri</th><th style="{th}">Kişi</th>
              <th style="{th}">Masa</th><th style="{th}">Telefon</th>
              <th style="{th}">Not</th><th style="{th}">Durum</th><th style="{th}"></th>
            </tr></thead>
            <tbody>{gelecek_html}</tbody>
          </table>
        </div>
      </div>

      <!-- Geçmiş -->
      <div class="card">
        <h2 style="margin-bottom:14px">🕘 Geçmiş / İptal (Son 20)</h2>
        <div style="overflow-x:auto">
          <table style="{tablo_stili}">
            <thead><tr>
              <th style="{th}">#</th><th style="{th}">Tarih / Saat</th>
              <th style="{th}">Müşteri</th><th style="{th}">Kişi</th>
              <th style="{th}">Masa</th><th style="{th}">Telefon</th>
              <th style="{th}">Not</th><th style="{th}">Durum</th><th style="{th}"></th>
            </tr></thead>
            <tbody>{gecmis_html}</tbody>
          </table>
        </div>
      </div>
    </div>"""
    return _prender(html, sayfa_baslik="Rezervasyon Yönetimi", ak="rezervasyonlar",
                    mesaj=mesaj, mesaj_tur=mesaj_tur)


@app.route("/personel/rezervasyon/iptal", methods=["POST"])
@login_gerekli
def pers_rezervasyon_iptal():
    rid = request.form.get("rid", type=int)
    liste = storage.rezervasyon_listesi_yukle()
    iptal_masa_no = None
    for r in liste:
        if r["id"] == rid:
            r["durum"] = "İptal"
            iptal_masa_no = r.get("masa_no")
            break
    storage.rezervasyon_kaydet(liste)

    # İptal edilen rezervasyonun masasını boşalt
    if iptal_masa_no:
        sy = _sy()
        masa = sy.masalar.get(iptal_masa_no)
        if masa and masa.durum == MasaDurumu.REZERVE:
            # Başka aktif rezervasyon var mı bu masa için?
            baska = any(
                r.get("masa_no") == iptal_masa_no and r.get("durum") != "İptal" and r["id"] != rid
                for r in liste
            )
            if not baska:
                masa.durum = MasaDurumu.BOS
                storage.masalar_kaydet(sy.masalar)

    return redirect(url_for("pers_rezervasyonlar", mesaj=f"Rezervasyon #{rid} iptal edildi.", tur="info"))


# ─── BAHŞİŞ TAKİBİ ────────────────────────────────────
@app.route("/personel/bakhsis")
@login_gerekli
def pers_bakhsis():
    from datetime import datetime
    SAYFA_BOYUTU = 10

    liste = storage.bakhsis_listesi_yukle()
    # En yeni en üstte
    liste_ters = list(reversed(liste))

    toplam       = sum(b["tutar"] for b in liste)
    bugun        = datetime.now().date().isoformat()
    bugun_toplam = sum(b["tutar"] for b in liste if b.get("zaman","").startswith(bugun))

    toplam_kayit = len(liste_ters)
    toplam_sayfa = max(1, -(-toplam_kayit // SAYFA_BOYUTU))  # ceiling div

    sayfa = request.args.get("sayfa", 1, type=int)
    sayfa = max(1, min(sayfa, toplam_sayfa))

    baslangic = (sayfa - 1) * SAYFA_BOYUTU
    bitis     = baslangic + SAYFA_BOYUTU
    sayfa_veri = liste_ters[baslangic:bitis]

    # Tablo satırları
    satirlar = ""
    for b in sayfa_veri:
        zaman = b.get("zaman","")[:16].replace("T"," ")
        not_  = b.get("not_","") or "—"
        satirlar += f"""
        <tr>
          <td style="color:#7f8c8d;font-size:.82rem;padding:11px 12px;border-bottom:1px solid #f5f5f5">{zaman}</td>
          <td style="font-weight:600;padding:11px 12px;border-bottom:1px solid #f5f5f5">{b.get('musteri','—')}</td>
          <td style="font-style:italic;color:#95a5a6;font-size:.85rem;padding:11px 12px;border-bottom:1px solid #f5f5f5">{not_}</td>
          <td style="font-weight:800;color:#7B2FBE;text-align:right;padding:11px 12px;border-bottom:1px solid #f5f5f5">{b['tutar']:.2f} ₺</td>
        </tr>"""

    # Sayfalama butonları
    def sayfa_url(s):
        return f"/personel/bakhsis?sayfa={s}"

    pager = ""
    if toplam_sayfa > 1:
        btn_style_base = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "min-width:36px;height:36px;padding:0 10px;border-radius:8px;"
            "font-size:.85rem;font-weight:700;text-decoration:none;transition:all .15s;"
        )
        btn_normal  = btn_style_base + "background:white;border:1.5px solid #dde3ea;color:#5d7080;"
        btn_aktif   = btn_style_base + "background:linear-gradient(135deg,#7B2FBE,#9B59B6);border:1.5px solid transparent;color:white;box-shadow:0 3px 10px rgba(123,47,190,.3);"
        btn_disable = btn_style_base + "background:#f5f5f5;border:1.5px solid #eee;color:#ccc;pointer-events:none;"

        parts = []

        # ← Geri
        if sayfa > 1:
            parts.append(f'<a href="{sayfa_url(sayfa-1)}" style="{btn_normal}">&#8592; Geri</a>')
        else:
            parts.append(f'<span style="{btn_disable}">&#8592; Geri</span>')

        # Sayfa numaraları — pencere: max 5 buton
        pencere_bas = max(1, sayfa - 2)
        pencere_bit = min(toplam_sayfa, pencere_bas + 4)
        pencere_bas = max(1, pencere_bit - 4)

        if pencere_bas > 1:
            parts.append(f'<a href="{sayfa_url(1)}" style="{btn_normal}">1</a>')
            if pencere_bas > 2:
                parts.append(f'<span style="display:inline-flex;align-items:center;color:#bbb;padding:0 4px">…</span>')

        for s in range(pencere_bas, pencere_bit + 1):
            stil = btn_aktif if s == sayfa else btn_normal
            parts.append(f'<a href="{sayfa_url(s)}" style="{stil}">{s}</a>')

        if pencere_bit < toplam_sayfa:
            if pencere_bit < toplam_sayfa - 1:
                parts.append(f'<span style="display:inline-flex;align-items:center;color:#bbb;padding:0 4px">…</span>')
            parts.append(f'<a href="{sayfa_url(toplam_sayfa)}" style="{btn_normal}">{toplam_sayfa}</a>')

        # İleri →
        if sayfa < toplam_sayfa:
            parts.append(f'<a href="{sayfa_url(sayfa+1)}" style="{btn_normal}">İleri &#8594;</a>')
        else:
            parts.append(f'<span style="{btn_disable}">İleri &#8594;</span>')

        pager = f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    flex-wrap:wrap;gap:10px;margin-top:16px;padding-top:14px;
                    border-top:1px solid #f0f0f0">
          <span style="font-size:.82rem;color:#95a5a6">
            Toplam <strong style="color:#2c3e50">{toplam_kayit}</strong> kayıt —
            Sayfa <strong style="color:#2c3e50">{sayfa}</strong> / <strong style="color:#2c3e50">{toplam_sayfa}</strong>
          </span>
          <div style="display:flex;gap:6px;flex-wrap:wrap">{''.join(parts)}</div>
        </div>"""

    if not liste:
        icerik = "<p style='color:#aaa;text-align:center;padding:40px 16px'>Henüz bahşiş bulunmuyor.</p>"
    else:
        icerik = f"""
        <div style="overflow-x:auto">
          <table style="width:100%;border-collapse:collapse;font-size:.9rem">
            <thead>
              <tr style="background:#f8fafc;border-bottom:2px solid #edf0f5">
                <th style="text-align:left;padding:10px 12px;color:#7f8c8d;font-size:.72rem;letter-spacing:.8px;font-weight:800">TARİH</th>
                <th style="text-align:left;padding:10px 12px;color:#7f8c8d;font-size:.72rem;letter-spacing:.8px;font-weight:800">MÜŞTERİ</th>
                <th style="text-align:left;padding:10px 12px;color:#7f8c8d;font-size:.72rem;letter-spacing:.8px;font-weight:800">NOT</th>
                <th style="text-align:right;padding:10px 12px;color:#7f8c8d;font-size:.72rem;letter-spacing:.8px;font-weight:800">TUTAR</th>
              </tr>
            </thead>
            <tbody>{satirlar}</tbody>
          </table>
        </div>
        {pager}"""

    html = f"""
    <div class="card" style="max-width:860px;margin:0 auto">
      <!-- Özet Kartlar -->
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px">
        <div style="flex:1;min-width:180px;background:linear-gradient(135deg,#7B2FBE,#9B59B6);
                    border-radius:14px;padding:20px 22px;color:white">
          <div style="font-size:.72rem;opacity:.75;font-weight:700;letter-spacing:1px;
                      text-transform:uppercase;margin-bottom:6px">Toplam Bahşiş</div>
          <div style="font-size:1.8rem;font-weight:800">{toplam:.2f} ₺</div>
          <div style="font-size:.78rem;opacity:.65;margin-top:4px">{toplam_kayit} işlem</div>
        </div>
        <div style="flex:1;min-width:180px;background:linear-gradient(135deg,#27ae60,#2ecc71);
                    border-radius:14px;padding:20px 22px;color:white">
          <div style="font-size:.72rem;opacity:.75;font-weight:700;letter-spacing:1px;
                      text-transform:uppercase;margin-bottom:6px">Bugün</div>
          <div style="font-size:1.8rem;font-weight:800">{bugun_toplam:.2f} ₺</div>
          <div style="font-size:.78rem;opacity:.65;margin-top:4px">{bugun}</div>
        </div>
      </div>

      <!-- Başlık -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <h3 style="font-size:.78rem;font-weight:800;letter-spacing:1.5px;
                   text-transform:uppercase;color:#95a5a6;margin:0">İşlem Geçmişi</h3>
        <span style="font-size:.8rem;color:#7B2FBE;font-weight:700;background:#faf5ff;
                     padding:4px 12px;border-radius:20px;border:1px solid #e8d5f8">
          Sayfa {sayfa} / {toplam_sayfa}
        </span>
      </div>

      {icerik}
    </div>"""
    return _prender(html, sayfa_baslik="Bahşiş Takibi", ak="bakhsis")


# ─── YENİDEN BAŞLAT ────────────────────────────────────
@app.route("/personel/yeniden-baslat", methods=["POST"])
@login_gerekli
def pers_yeniden_baslat():
    if session.get("rol") != "admin":
        return redirect(url_for("pers_yonetim", mesaj="Yetkiniz yok.", tur="danger"))

    import threading, time, subprocess
    from pathlib import Path as _Path

    def _baslat():
        time.sleep(1)   # yanıtın tarayıcıya ulaşmasını bekle
        main_py = str(_Path(__file__).parent / "main.py")
        subprocess.Popen([sys.executable, main_py])
        os._exit(0)

    threading.Thread(target=_baslat, daemon=True).start()

    html = """
    <div style="max-width:460px;margin:60px auto;text-align:center">
      <div style="font-size:3rem;margin-bottom:16px">🔄</div>
      <h2 style="font-size:1.3rem;font-weight:800;color:#2c3e50;margin-bottom:10px">
        Sistem Yeniden Başlatılıyor…
      </h2>
      <p style="color:#7f8c8d;font-size:.9rem;margin-bottom:24px;line-height:1.6">
        Sunucu kapatılıp tekrar açılıyor.<br>
        Birkaç saniye içinde otomatik olarak yönlendirileceksiniz.
      </p>
      <div style="width:100%;height:6px;background:#eee;border-radius:3px;overflow:hidden">
        <div id="pbar" style="height:100%;width:0;background:linear-gradient(90deg,#7B2FBE,#2980b9);
             border-radius:3px;transition:width 4s linear"></div>
      </div>
    </div>
    <script>
      setTimeout(function(){ document.getElementById('pbar').style.width='100%'; }, 100);
      setTimeout(function(){ window.location='/personel/yonetim'; }, 5000);
    </script>"""
    return _prender(html, sayfa_baslik="Yeniden Başlatılıyor", ak="yonetim")


def sunucu_baslat(port: int = 5000):
    """Thread olarak başlatılır."""
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)   # Flask log'larını kapat
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
