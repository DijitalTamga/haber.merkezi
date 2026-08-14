# ==============================================================================
# 🤖 DİJİTAL TAMGA V10.0 - GITHUB ACTIONS TEK REPO SÜRÜMÜ
# ==============================================================================
# Bu dosya haber.merkezi reposunun bot/ klasöründe, GitHub Actions cron ile çalışır.
# Sırlar (API anahtarları/tokenlar) repo Secrets'tan environment variable olarak okunur.

import feedparser
import tweepy
import requests
import os
import time
import random
import json
from datetime import datetime
import pytz
from google import genai
from PIL import Image
import io

# ==========================================
# 🔐 ŞİFRE ALANI (repo Secrets üzerinden environment variable olarak gelir)
# ==========================================
GECERLI_GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()]
aktif_key_index = 0

API_KEY = os.environ["TWITTER_API_KEY"]
API_SECRET = os.environ["TWITTER_API_SECRET"]
ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["TWITTER_ACCESS_TOKEN_SECRET"]

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_KANAL_ID = "@dijitaltamga"

X_KULLANICI_ADI = "DijitalTamga"

# FACEBOOK & INSTAGRAM (ID'ler sır değil, sabit kalabilir)
FACEBOOK_PAGE_ID = "950664831471039"
INSTAGRAM_ACCOUNT_ID = "17841443216654962"
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]

# ==========================================
# BAĞLANTILAR
# ==========================================
client_x = tweepy.Client(
    consumer_key=API_KEY, consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET
)
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api_v1 = tweepy.API(auth)

# GEMİNİ AKTİVASYONU
gemini = genai.Client(api_key=GECERLI_GEMINI_API_KEYS[aktif_key_index])
MODEL = "gemini-2.5-flash"

# ==========================================
# TALİMATLAR
# ==========================================
toplu_puanlama_talimati = """Sen Dijital Tamga'nın genel yayın yönetmenisin. Amacın Türk milliyetçiliği, savunma sanayii ve güvenlik haberlerini öne çıkarmak. Ekonomi, teknoloji ve spor haberlerini de aynı milli çıkar süzgecinden değerlendireceksin.
Sana numaralandırılmış haber başlıkları verilecek. Her bir habere 1 ile 10 arasında önem puanı ver.
- Savunma, terörle mücadele, jeopolitik, milli hamleler: 8, 9 veya 10.
- Türk savunma sanayii/teknoloji atılımları (yerli üretim, ihracat, yeni sistemler): 8, 9 veya 10.
- Türkiye ekonomisini doğrudan ilgilendiren büyük gelişmeler (Merkez Bankası kararları, büyük ihracat/yatırım rakamları, kritik kur/enflasyon haberleri): 7, 8 veya 9.
- Türk sporcu/takımların uluslararası önemli başarıları (şampiyonluk, rekor, milli takım): 7, 8 veya 9.
- Sıradan ekonomi haberleri (rutin piyasa hareketleri, şirket haberleri): 3, 4, 5.
- Sıradan spor haberleri (transfer, rutin maç sonucu), magazin, kaza: 1, 2, 3, 4, 5.
CEVABIN SIRASIYLA SADECE NUMARALAR VE PUANLARDAN OLUŞMALIDIR. Örnek:
[0] 8
[1] 3
[2] 9
Başka hiçbir açıklama ekleme."""

üretim_talimati = """Sen Dijital Tamga baş editörüsün. Sana bir haber başlığı ve kısa içeriği verilecek.
Bu haberi okuyup hem bir sosyal medya paylaşımı (Tweet) hem de sitemiz için tam bir makale üretmeni istiyorum.
Kurallar: Siyasal İslam argümanlarından, dini söylem ve jargondan kesinlikle uzak durarak; sadece Türk ırkına mensup bir Türkçünün (Türk milliyetçisinin) bakış açısıyla yazacaksın. Aşırı ofansif olmayacaksın ama rasyonel ve vurucu olacaksın.

LÜTFEN CEVABINI SADECE AŞAĞIDAKİ FORMATTA VER (Başka hiçbir açıklama ekleme):

[TWEET]
📰 HABER: Haberin kısa özeti.
📌 NOT: Vurgulu kısa değerlendirme.
#etiket1 #etiket2 #etiket3
[MAKALE_BASLIK]
Makalenin Vurucu Başlığı
[MAKALE_ICERIK]
1. Paragraf...
2. Paragraf...
3. Paragraf..."""

rss_linkleri = [
    # ===== TÜRKİYE =====
    "https://www.aa.com.tr/tr/rss/default?cat=guncel",
    "https://www.trthaber.com/manset_articles.rss",
    "https://www.savunmasanayist.com/feed/",
    "https://www.ntv.com.tr/son-dakika.rss",
    "https://www.haberturk.com/rss",
    "https://www.hurriyet.com.tr/rss/gundem",
    "https://www.cumhuriyet.com.tr/rss/son_dakika.xml",
    "https://www.karar.com/rss",
    "https://t24.com.tr/rss",
    "https://medyascope.tv/feed/",
    "https://www.birgun.net/rss",
    # ===== EKONOMİ =====
    "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
    "https://www.trthaber.com/ekonomi_articles.rss",
    "https://www.bloomberght.com/rss",
    "https://www.dunya.com/rss",
    "https://www.hurriyet.com.tr/rss/ekonomi",
    # ===== TEKNOLOJİ =====
    "https://www.aa.com.tr/tr/rss/default?cat=bilim-teknoloji",
    "https://webrazzi.com/feed/",
    "https://www.donanimhaber.com/rss/tum/",
    "https://www.hurriyet.com.tr/rss/teknoloji",
    # ===== SPOR =====
    "https://www.aa.com.tr/tr/rss/default?cat=spor",
    "https://www.trthaber.com/spor_articles.rss",
    "https://www.hurriyet.com.tr/rss/spor",
    # ===== ULUSLARARASI =====
    "https://feeds.reuters.com/reuters/topNews",
    "https://feeds.apnews.com/rss/apf-topnews",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.ft.com/rss/home",
    "https://www.wsj.com/xml/rss/3_7085.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.lemonde.fr/rss/une.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

PAYLASILANLAR_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "paylasilanlar.json")

def yukle_paylasilanlar():
    if os.path.exists(PAYLASILANLAR_DOSYASI):
        try:
            with open(PAYLASILANLAR_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Dosya okunamadı: {e}")
            return []
    return []

def kaydet_paylasilanlar(liste):
    dizin = os.path.dirname(PAYLASILANLAR_DOSYASI)
    if not os.path.exists(dizin):
        os.makedirs(dizin)
    try:
        with open(PAYLASILANLAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logla(f"⚠️ Paylaşılanlar kaydedilemedi: {e}")

paylasilan_haberler = yukle_paylasilanlar()

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================
import subprocess
import re

def git_komutu_calistir(komut, dizin):
    try:
        sonuc = subprocess.run(komut, cwd=dizin, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, sonuc.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def siteye_makale_ekle(baslik, icerik, resim_url="", uretilen_gorsel_bytes=None):
    """Makaleyi Hugo sitesine markdown olarak ekler ve GitHub'a pushlar.
    Dönüş: başarılıysa (site_url, kapak_resim_url, uretilen_gorsel_yerel_yolu) - başarısızsa None."""
    site_dizini = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    posts_dizini = os.path.join(site_dizini, "content", "posts")

    if not os.path.exists(posts_dizini):
        os.makedirs(posts_dizini)

    import urllib.parse

    # Dosya ismini temizle (SEO uyumlu URL için)
    temiz_isim = re.sub(r'[^a-zA-Z0-9]', '-', baslik.lower().replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c'))
    temiz_isim = re.sub(r'-+', '-', temiz_isim).strip('-')
    gecerli_tarih = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+03:00")
    dosya_adi = f"{temiz_isim}.md"
    dosya_yolu = os.path.join(posts_dizini, dosya_adi)

    # Üretilen görsel varsa siteye kaydet, kapak URL'ini ona göre belirle
    kapak_resim_url = resim_url
    uretilen_gorsel_yerel_yolu = None
    if uretilen_gorsel_bytes:
        uploads_dizini = os.path.join(site_dizini, "static", "uploads")
        if not os.path.exists(uploads_dizini):
            os.makedirs(uploads_dizini)
        gorsel_dosya_adi = f"{temiz_isim}.jpg"
        uretilen_gorsel_yerel_yolu = os.path.join(uploads_dizini, gorsel_dosya_adi)
        try:
            with open(uretilen_gorsel_yerel_yolu, "wb") as f:
                f.write(uretilen_gorsel_bytes)
            kapak_resim_url = f"https://dijitaltamga.github.io/haber.merkezi/uploads/{gorsel_dosya_adi}"
            logla(f"🖼️ Üretilen kapak görseli kaydedildi: {gorsel_dosya_adi}")
        except Exception as e:
            logla(f"⚠️ Üretilen görsel kaydedilemedi: {e}")
            uretilen_gorsel_yerel_yolu = None

    kapak_resmi_alani = f'cover:\n    image: "{kapak_resim_url}"' if kapak_resim_url else ""

    md_icerik = f"""---
title: "{baslik.replace('"', "'")}"
date: {gecerli_tarih}
draft: false
{kapak_resmi_alani}
---

{icerik}
"""
    try:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(md_icerik)
        logla(f"📝 Makale dosyası oluşturuldu: {dosya_adi}")

        # Git Push İşlemleri
        logla("🚀 Site güncelleniyor (GitHub'a gönderiliyor)...")
        git_komutu_calistir("git pull", site_dizini)
        git_komutu_calistir("git add .", site_dizini)
        temiz_baslik = baslik.replace('"', '')
        git_komutu_calistir(f'git commit -m "Yeni Haber: {temiz_baslik}"', site_dizini)
        basarili, cikti = git_komutu_calistir("git push", site_dizini)
        if basarili:
            logla("✅ Site başarıyla güncellendi! (GitHub Actions yayına alacak)")
            # Yayınlanması için yaklaşık 2 dakika GitHub Actions'u bekle
            logla("⏳ Sitenin yayına girmesi için 120 saniye bekleniyor...")
            time.sleep(120)

            # Sitenin Linkini Oluştur
            site_url = f"https://dijitaltamga.github.io/haber.merkezi/posts/{temiz_isim}/"
            return site_url, kapak_resim_url, uretilen_gorsel_yerel_yolu
        else:
            logla(f"⚠️ Git Push hatası: {cikti}")
            return None

    except Exception as e:
        logla(f"⚠️ Makale kaydetme hatası: {e}")
        return None

def logla(mesaj):
    tr_saat = datetime.now(pytz.timezone('Europe/Istanbul')).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{tr_saat}] {mesaj}", flush=True)

def gemini_sor(prompt):
    """Yapay zekaya soru sorar. 429 alırsa diğer API anahtarlarına geçer."""
    global aktif_key_index, gemini
    
    denenen_key_sayisi = 0
    toplam_key = len(GECERLI_GEMINI_API_KEYS)
    
    genel_deneme = 0
    while genel_deneme < 3:
        try:
            time.sleep(5)  # Her istekten önce 5 sn bekle (rate limit koruması)
            cevap = gemini.models.generate_content(model=MODEL, contents=prompt)
            return cevap.text.strip()
        except Exception as e:
            hata = str(e)
            if "429" in hata:
                denenen_key_sayisi += 1
                if denenen_key_sayisi < toplam_key:
                    # Diğer key'e geç
                    aktif_key_index = (aktif_key_index + 1) % toplam_key
                    logla(f"🔄 Mevcut anahtarın limiti doldu. YEDEK anahtara geçiliyor... ({aktif_key_index + 1}/{toplam_key})")
                    gemini = genai.Client(api_key=GECERLI_GEMINI_API_KEYS[aktif_key_index])
                    time.sleep(2)
                    continue # Döngüye devam et (genel_deneme artmaz)
                else:
                    # Tüm keyler denendi ve hepsi 429 verdi
                    genel_deneme += 1
                    denenen_key_sayisi = 0 # Bir sonraki genel deneme için sıfırla
                    if genel_deneme < 3:
                        logla(f"⏳ TÜM API anahtarlarının limiti doldu (429). Deneme {genel_deneme}/3. 60 saniye bekleniyor...")
                        time.sleep(60)
                    else:
                        logla("🛑 Günlük TÜM API kotaları doldu! 2 saat sonra tekrar denenecek...")
                        logla("   (Google kotaları Pasifik Saatine göre sıfırlar. TR saatiyle yaklaşık Sabah 11:00'de sıfırlanır)")
                        time.sleep(7200)  # 2 saat bekle
                        genel_deneme = 0  # Sayacı sıfırla, tekrar dene
            else:
                logla(f"⚠️ Yapay Zeka hatası: {hata[:100]}")
                return None
    return None

def resim_indir(haber_objesi):
    resim_url = None
    try:
        if 'enclosures' in haber_objesi and len(haber_objesi.enclosures) > 0:
            resim_url = haber_objesi.enclosures[0].href
        elif 'media_content' in haber_objesi and len(haber_objesi.media_content) > 0:
            resim_url = haber_objesi.media_content[0]['url']
        if resim_url:
            r = requests.get(resim_url, stream=True, timeout=10)
            if r.status_code == 200:
                with open("tmpphoto.jpg", "wb") as f:
                    f.write(r.content)
                return "tmpphoto.jpg"
    except:
        pass
    return None

def resim_kirp(resim_yolu):
    """Instagram'ın kabul ettiği 4:5 en-boy oranına (veya kareye) uygun şekilde resmi kırpar/düzenler."""
    try:
        img = Image.open(resim_yolu)
        width, height = img.size
        # Instagram aspect ratio limits: 4:5 (0.8) to 1.91:1 (1.91)
        aspect_ratio = width / height

        # Eğer çok ince uzunsa (Genişlik küçük, Yükseklik büyük -> 4:5'ten daha dar)
        if aspect_ratio < 0.8:
            new_height = int(width / 0.8)
            # Üstten kırpma
            top = (height - new_height) // 2
            bottom = top + new_height
            img = img.crop((0, top, width, bottom))
            img.save("tmpphoto_ig.jpg")
            return "tmpphoto_ig.jpg"
        
        # Eğer çok yataysa (Genişlik büyük, Yükseklik küçük -> 1.91:1'den daha geniş)
        elif aspect_ratio > 1.91:
            new_width = int(height * 1.91)
            # Yanlardan kırpma
            left = (width - new_width) // 2
            right = left + new_width
            img = img.crop((left, 0, right, height))
            img.save("tmpphoto_ig.jpg")
            return "tmpphoto_ig.jpg"
            
        return resim_yolu # Zaten uygun oran
    except Exception as e:
        logla(f"⚠️ Resim kırpma hatası: {e}")
        return resim_yolu

def gorsel_uret(baslik, icerik):
    """Haberde kullanılabilir görsel yoksa Gemini ile metinsiz bir kapak görseli üretir. Başarısız olursa None döner.
    NOT: Görsel üretimi Google tarafında faturalandırma (billing) etkin olmayan projelerde ücretsiz tier'da kapalıdır (kota: 0).
    Billing açık değilse bu fonksiyon hata loglayıp None döner, çağıran taraf default.png'ye düşer."""
    try:
        prompt = (
            "Bir haber sitesi için gerçekçi, fotoğrafik tarzda, dikey (4:5) oranlı, sade bir kapak görseli üret. "
            f"Haberin konusu: {baslik}. "
            "Görselde hiçbir yazı, logo veya watermark olmasın."
        )
        cevap = gemini.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
        )
        for part in cevap.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                logla("🖼️ Kapak görseli yapay zeka ile üretildi.")
                return part.inline_data.data
    except Exception as e:
        logla(f"⚠️ Görsel üretim hatası: {str(e)[:150]}")
    return None

def telegram_gonder(metin, resim_yolu=None, kaynak_linki=""):
    telegram_metni = f"{metin}\n\n📰 <b>Haberin tamamını okumak için:</b> {kaynak_linki}"
    try:
        if resim_yolu:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            requests.post(url, data={"chat_id": TELEGRAM_KANAL_ID, "caption": telegram_metni, "parse_mode": "HTML"}, files={"photo": open(resim_yolu, "rb")})
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_KANAL_ID, "text": telegram_metni, "parse_mode": "HTML"})
        logla("✈️ Haberin kopyası TELEGRAM kanalına başarıyla iletildi.")
    except Exception as e:
        logla(f"⚠️ Telegram hatası: {str(e)[:50]}")

def facebook_gonder(metin, site_linki, resim_url=None):
    """Facebook Sayfasına Gönderi Atar"""
    fb_icin_metin = f"{metin}\n\n📰 Detaylar Sitemizde: {site_linki}"
    
    if resim_url:
        url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/photos"
        payload = {"url": resim_url, "caption": fb_icin_metin, "access_token": META_ACCESS_TOKEN}
    else:
        url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/feed"
        payload = {"message": fb_icin_metin, "access_token": META_ACCESS_TOKEN}
    try:
        r = requests.post(url, data=payload)
        sonuc = r.json()
        if "id" in sonuc:
            logla("📘 Facebook sayfasına başarıyla gönderildi.")
        else:
            logla(f"⚠️ Facebook Hatası: {sonuc}")
    except Exception as e:
        logla(f"⚠️ Facebook gönderim hatası: {e}")

def instagram_gonder(metin, resim_url, gercek_resim_yolu=None):
    if not resim_url:
        return
        
    kullanilacak_url = resim_url
    try:
        url_create = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ACCOUNT_ID}/media"
        payload_create = {
            "image_url": kullanilacak_url,
            "caption": metin + "\n\n🔗 Haberin tamamını okumak için profildeki sitemizi ziyaret edin!",
            "access_token": META_ACCESS_TOKEN
        }
        r1 = requests.post(url_create, data=payload_create).json()
        
        if "id" not in r1:
            logla(f"⚠️ Instagram Container Hatası: {r1}")
            return
            
        creation_id = r1["id"]
        time.sleep(10)
        
        url_publish = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        payload_publish = {
            "creation_id": creation_id,
            "access_token": META_ACCESS_TOKEN
        }
        r2 = requests.post(url_publish, data=payload_publish).json()
        
        if "id" in r2:
            logla("📸 Instagram profiline başarıyla gönderildi.")
        else:
            logla(f"⚠️ Instagram Publish Hatası: {r2}")
            
    except Exception as e:
        logla(f"⚠️ Instagram gönderim hatası: {e}")

# ==========================================
# ANA DÖNGÜ
# ==========================================
logla("🤖 Dijital Tamga V9.5 (Tam Otomatik Haber Sitesi Entegreli) Başlatıldı! (GitHub Actions Modu)")
logla("   Tek tur çalışacak ve kapanacak.")

def bot_calistir():
    random.shuffle(rss_linkleri)
    yeni_haber = False

    for rss_url in rss_linkleri:
        try:
            r = requests.get(rss_url, timeout=10)
            feed = feedparser.parse(r.content)

            birlestirilmis_basliklar = ""
            haber_listesi = []
            for i, haber in enumerate(feed.entries[:6]):
                if haber.link not in paylasilan_haberler:
                    birlestirilmis_basliklar += f"[{i}] {haber.title}\n"
                    haber_listesi.append(haber)
            
            if not haber_listesi:
                continue
                
            logla(f"🔍 {len(haber_listesi)} HABER BİRDEN İNCELENİYOR (API Tasarrufu Modu)...")
            puanlar_metni = gemini_sor(f"{toplu_puanlama_talimati}\n\nHaberler:\n{birlestirilmis_basliklar}")

            if puanlar_metni is None:
                # Olası bir kota aşımında devam et
                continue
                
            # Puanları Ayrıştır
            for i, haber in enumerate(haber_listesi):
                try:
                    import re
                    match = re.search(f"\\[{i}\\]\\s+(\\d+)", puanlar_metni)
                    haber_puani = int(match.group(1)) if match else 0
                except:
                    haber_puani = 0

                logla(f"📊 Puanı: {haber_puani}/10 - {haber.title}")

                if haber_puani >= 7:
                    logla("✍️ Tweet ve Makale tek seferde yazdırılıyor...")
                    tam_icerik = gemini_sor(
                        f"{üretim_talimati}\n\nHaber Başlığı: {haber.title}\nHaber Özeti: {haber.description if 'description' in haber else ''}"
                    )
                    
                    if not tam_icerik:
                        paylasilan_haberler.append(haber.link)
                        continue
                        
                    kisa_icerik = ""
                    m_baslik = haber.title
                    m_icerik = ""
                    
                    suanki_bolum = None
                    for satir in tam_icerik.split('\n'):
                        s = satir.strip()
                        if s.startswith("[TWEET]"):
                            suanki_bolum = "T"
                            continue
                        elif s.startswith("[MAKALE_BASLIK]"):
                            suanki_bolum = "B"
                            continue
                        elif s.startswith("[MAKALE_ICERIK]"):
                            suanki_bolum = "I"
                            continue
                            
                        if suanki_bolum == "T":
                            kisa_icerik += satir + "\n"
                        elif suanki_bolum == "B" and s:
                            m_baslik = s
                        elif suanki_bolum == "I":
                            m_icerik += satir + "\n"
                    
                    kisa_icerik = kisa_icerik.strip()
                    m_icerik = m_icerik.strip()

                    resim = resim_indir(haber)
                    resim_gecici_mi = bool(resim)  # tmpphoto.jpg ise turun sonunda silinebilir
                    raw_resim_url = None
                    try:
                        if 'enclosures' in haber and len(haber.enclosures) > 0:
                            raw_resim_url = haber.enclosures[0].href
                        elif 'media_content' in haber and len(haber.media_content) > 0:
                            raw_resim_url = haber.media_content[0]['url']
                    except:
                        pass

                    uretilen_gorsel_bytes = None
                    if not raw_resim_url or not resim:
                        logla("🖼️ Haberde uygun görsel yok, yapay zeka ile kapak görseli üretiliyor...")
                        uretilen_gorsel_bytes = gorsel_uret(m_baslik, m_icerik)

                    # 3. Makaleyi Siteye Ekle ve Yayınla
                    site_linki = haber.link # Yedek (Kendi sitemize yükleyemezsek asıl linki verelim diye)
                    if m_icerik and m_baslik:
                        sonuc = siteye_makale_ekle(m_baslik, m_icerik, raw_resim_url, uretilen_gorsel_bytes)
                        if sonuc:
                            site_linki, uretilen_url, uretilen_yerel_yol = sonuc
                            if uretilen_yerel_yol:
                                # Üretilen görsel artık repo ağacının bir parçası, silinmemeli
                                raw_resim_url = uretilen_url
                                resim = uretilen_yerel_yol
                                resim_gecici_mi = False

                    # Görsel hiçbir şekilde bulunamadıysa (RSS'de yok, üretim de başarısız oldu) yedek görseli kullan
                    yedek_resim = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "default.png")
                    if not raw_resim_url or not resim:
                        if os.path.exists(yedek_resim):
                            resim = yedek_resim
                            raw_resim_url = "https://dijitaltamga.github.io/haber.merkezi/default.png"

                    # Sosyal Medyaya kendi sitemizin linkiyle çıkma
                    if not kisa_icerik: # Eğer tweet kısmı boş gelirse yedeği at
                        kisa_icerik = f"📰 {m_baslik}"
                        
                    sosyal_medya_metni = f"{kisa_icerik}\n\n📰 Okumak İçin: {site_linki}"

                    # Twitter'da karakter sınırı (280) ve Free API kısıtlamaları (resim yüklenememesi) var
                    # Tweet metnini 270 karaktere kadar kesip sonuna ... ekleyelim
                    twitter_kisa_icerik = kisa_icerik
                    if len(twitter_kisa_icerik) > 230:
                        twitter_kisa_icerik = twitter_kisa_icerik[:230] + "..."
                        
                    sosyal_medya_metni = f"{twitter_kisa_icerik}\n\n📰 Okumak İçin: {site_linki}"

                    try:
                        # Free API'de resim yükleme (media_upload) hata verdiği için sadece metin atıyoruz
                        x_cevap = client_x.create_tweet(text=sosyal_medya_metni)

                        logla(f"✅ X(TWITTER)'A ATILDI.")
                    except Exception as e_tw:
                        logla(f"⚠️ X(TWITTER) HATASI: {e_tw}")

                    telegram_gonder(kisa_icerik, resim, site_linki)
                    facebook_gonder(kisa_icerik, site_linki, raw_resim_url)
                    if raw_resim_url:
                        instagram_gonder(kisa_icerik, raw_resim_url)

                    if resim and os.path.exists(resim) and resim != yedek_resim and resim_gecici_mi:
                        os.remove(resim)

                    paylasilan_haberler.append(haber.link)
                    kaydet_paylasilanlar(paylasilan_haberler)
                    yeni_haber = True
                    logla("✅ Makale yazıldı, yayınlandı. İşlem tamam! Bot kapanıyor...")
                    break
                else:
                    if haber.link not in paylasilan_haberler:
                        paylasilan_haberler.append(haber.link)
                        kaydet_paylasilanlar(paylasilan_haberler)

            if yeni_haber:
                break

        except Exception as genel:
            logla(f"⚠️ RSS Hatası: {str(genel)[:50]}")

    if not yeni_haber:
        logla("💤 Yeni haber yok. Bot kapanıyor...")

if __name__ == "__main__":
    bot_calistir()
