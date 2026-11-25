#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kvkk_maske (turkce-kisisel-veri-maskeleme) — Türkçe metinde kişisel veri maskeleme (yerel, ağsız, yalnız stdlib).

Ne yapar:
  TC kimlik no ve vergi no (sağlamalı), IBAN (mod-97), cep ve sabit telefon, e-posta,
  araç plakası, doğum tarihi, adres dizisi, isteğe bağlı esas/karar no ve kişi adlarını
  tutarlı takma adlarla ([KİŞİ-1], [TCKN-1] …) değiştirir.

Ne yapmaz:
  OCR yapmaz; görüntüdeki veriyi görmez. Sözlükte olmayan ve bağlam kelimesi taşımayan adı
  kaçırabilir. Maskelenmiş metni bir insan gözden geçirmeden "temiz" saymayın.

Arayüz:
  maskele(metin, harita=None, kurallar=VARSAYILAN_KURALLAR) -> (yeni_metin, harita, bulgular)
  geri_al(metin, harita) -> metin
  Komut satırı: --dosya, --cikti, --harita, --rapor, --kurallar, --geri, --test

Python 3.9+, yalnız standart kütüphane. Ağ erişimi yok.

Copyright (c) 2026 Av. Cem Sinanoğlu — MIT Lisansı (LICENSE).
"""
import csv
import io
import json
import unicodedata
import os
import random
import re
import sys
import zipfile

SURUM = "0.1.0"

# ───────────────────────── Türkçe harf dönüşümü ─────────────────────────
# Python'un str.upper/str.lower Türkçe i/ı ayrımını bilmez: "Yiğit".upper() -> "YIĞIT" (yanlış),
# "İ".lower() -> "i̇" (iki karakter). Bu iki işlev doğru ve uzunluk koruyan dönüşüm yapar.
_UST = str.maketrans({"i": "İ", "ı": "I"})
_ALT = str.maketrans({"İ": "i", "I": "ı"})


def tr_upper(s):
    return s.translate(_UST).upper()


def tr_lower(s):
    return s.translate(_ALT).lower()


def _katla(s):
    """Ad karşılaştırması için BÜYÜK harf; İ ile I eşit sayılır (yabancı adın ASCII büyük yazımı: ROSSI)."""
    return tr_upper(s).replace("İ", "I")


def tr_title(kelime):
    return tr_upper(kelime[:1]) + tr_lower(kelime[1:]) if kelime else kelime


# ───────────────────────── sağlama algoritmaları ─────────────────────────
def tckn_gecerli(s):
    """TC kimlik no sağlaması (kamuya açık algoritma)."""
    if not re.fullmatch(r"[1-9]\d{10}", s or ""):
        return False
    d = [int(c) for c in s]
    if (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def vkn_gecerli(s):
    """Vergi kimlik no (10 hane) sağlaması (kamuya açık algoritma)."""
    if not re.fullmatch(r"\d{10}", s or ""):
        return False
    d = [int(c) for c in s]
    toplam = 0
    for i in range(9):
        t = (d[i] + 9 - i) % 10
        t2 = (t * 2 ** (9 - i)) % 9
        if t != 0 and t2 == 0:
            t2 = 9
        toplam += t2
    return (10 - toplam % 10) % 10 == d[9]


def iban_gecerli(s):
    """ISO 13616 mod-97. Boşluksuz, büyük harf girdi bekler. TR için uzunluk 26."""
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", s or ""):
        return False
    if s.startswith("TR") and len(s) != 26:
        return False
    r = s[4:] + s[:4]
    sayi = "".join(str(int(c, 36)) for c in r)
    return int(sayi) % 97 == 1


# Sınama için geçerli numara üreticileri (gerçek kişiye ait olması rastlantıdır; --test ve ornek_kullanim.py kullanır).
def tckn_uret(rng):
    d = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(8)]
    d.append((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10)
    d.append(sum(d) % 10)
    return "".join(map(str, d))


def vkn_uret(rng):
    while True:
        s = "".join(str(rng.randint(0, 9)) for _ in range(9))
        for k in range(10):
            if vkn_gecerli(s + str(k)):
                return s + str(k)


def iban_uret(rng):
    bban = "%05d" % rng.randint(1, 99999) + "0" + "".join(str(rng.randint(0, 9)) for _ in range(16))
    sayi = "".join(str(int(c, 36)) for c in bban + "TR00")
    return "TR%02d%s" % (98 - int(sayi) % 97, bban)


# ───────────────────────── sözlükler ─────────────────────────
# Genel Türkçe ad listesi (yaygın adlar; elle derlendi). Yerel ek liste için: KVKK_MASKE_AD_DOSYASI=<yol>
# (satır başına bir ad) ya da maskele(..., ek_adlar=[...]).
_ADLAR = """
Abdullah Adem Adnan Ahmet Akın Alev Ali Alp Alper Altan Arda Arif Arzu Aslı Aslan Atilla Ayhan Aylin Aynur
Aysel Aysun Ayşe Ayşegül Aytaç Aziz Bahar Banu Barış Batuhan Bayram Belgin Berk Berkay Berna Betül Beyza Bilal
Birsen Bora Buket Bülent Burak Burcu Burhan Büşra Cafer Can Canan Cansu Celal Cem Cemal Cemile Cengiz Ceren
Cihan Cüneyt Çağla Çağrı Çiğdem Dilek Dilara Dursun Ebru Ece Ecem Eda Elif Elçin Emel Emin Emine Emir Emre
Ender Engin Enes Erdal Erdem Eren Erhan Erkan Ersin Ertan Ertuğrul Esra Esma Eylül Ezgi Fadime Fahri Faruk
Fatma Fatih Ferhat Feride Fikret Filiz Furkan Gamze Gizem Gökhan Gönül Gül Gülay Gülsüm Gülşen Gürkan Hakan
Halil Halit Hamza Handan Hande Hasan Hatice Haydar Hayriye Hilal Hülya Hüseyin İbrahim İlker İlknur İlyas
İpek İrem İsmail İsmet Kadir Kadriye Kamil Kemal Kenan Kerem Kevser Kübra Leyla Levent Mahmut Melek Melike
Meltem Merve Meryem Mesut Mete Metin Mehmet Melih Mert Mine Murat Musa Mustafa Muhammed Muhammet Mücahit
Nazlı Necati Nergis Nesrin Neslihan Nevin Nihat Nilay Nilüfer Nuri Nurten Oğuz Oğuzhan Okan Oktay Onur Orhan
Osman Ozan Ömer Önder Özge Özgür Özlem Pınar Rabia Ramazan Recep Reşat Rıza Rukiye Sabri Sadık Saffet Sait
Salih Sami Sedat Sefa Selçuk Selim Selin Selma Sema Semra Serap Serdar Serkan Sevda Sevgi Sevil Sevim Seda
Sibel Sinan Sinem Songül Suat Sultan Süleyman Şahin Şenol Şerife Şeyma Şükrü Tamer Taner Tarık Tayfun Tolga
Tuba Tuğba Tuncay Tülay Turgut Tülin Uğur Ufuk Umut Ümit Ünal Vedat Veli Volkan Yakup Yasemin Yasin Yavuz
Yeliz Yılmaz Yiğit Yunus Yusuf Zafer Zehra Zekeriya Zeki Zeynep Ziya Zuhal Zübeyde
"""
AD_SOZLUGU = set(_ADLAR.split())
# Ad olarak da kullanılan yaygın kelime/yer adları: tek başına geçince ad sayılmaz (soyadla birlikteyse sayılır).
BELIRSIZ = {"Bahar", "Barış", "Can", "Gül", "Umut", "Ümit", "Sultan", "Fatih", "Yılmaz", "Aslan", "Arda",
            "Mete", "Ece", "Alp", "Ender", "Eylül", "Ufuk", "Zafer", "Levent", "Nuri", "Seda", "Sevgi", "Melek",
            "Emir", "Kamil", "Gönül", "Bora", "Engin", "Aziz", "Sabri", "Sami", "Arif", "Cem", "Mine", "Ozan",
            "Tuba", "İpek", "Selim", "Sinan", "Yavuz", "Okan", "Altan", "Bayram", "Ramazan", "Kadir", "Rıza"}

# Adın ÖNÜNDE gelen bağlam kelimeleri (küçük harfe çevrilmiş metinde aranır).
BAGLAM_ONCE = ("tanık", "tanığı", "tanıklar", "sanık", "sanıklar", "şüpheli", "müşteki", "mağdur", "katılan",
               "davacı", "davalı", "müvekkil", "müvekkilimiz", "müvekkilim", "borçlu", "alacaklı", "baba adı",
               "anne adı", "babası", "annesi", "eşi", "oğlu", "kızı", "komşu", "komşusu", "sn.", "sayın", "bay",
               "bayan", "muris", "murisi", "müteveffa", "mirasçı", "şikayetçi", "şikâyetçi", "başvurucu",
               "kiracı", "işçi", "ihbar olunan", "ihtar edilen", "muhatap", "şahıs", "şahsı", "kişi")
# Adın ARKASINDAN gelen bağlam kelimeleri.
BAGLAM_SONRA = ("adlı", "isimli", "isminde", "adındaki", "adında")
# Ad dizisini kesen kelimeler (küçük harf).
DUR = {"vekili", "vekilleri", "vekiline", "müdafii", "müdafi", "av", "av.", "adına", "tarafından", "hakim",
       "hâkim", "hakimi", "mahkeme", "mahkemesi", "mahkemesine", "başkan", "başkanı", "savcı", "savcılığı",
       "cumhuriyet", "yargıtay", "danıştay", "tc", "t.c.", "kimlik", "no", "adres", "adresi", "ve", "ile",
       "konu", "açıklamalar", "sonuç", "istem", "hukuki", "deliller", "davacı", "davalı", "sanık", "tanık",
       "müşteki", "şüpheli", "katılan", "bey", "hanım", "beyin", "hanımın", "efendi", "dava", "dosya",
       "esas", "karar", "tarih", "tarihli", "madde", "kanun", "yasa", "türk", "türkiye", "ocak", "şubat",
       "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık",
       "pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar", "dün", "bugün", "olay",
       "bu", "şu", "o", "ancak", "ayrıca", "ilgili", "sayın", "heyet", "huzurdaki", "yukarıda",
       "şirket", "şirketi", "banka", "bankası", "bilirkişi", "bilirkişiler", "beyan", "beyanı", "beyanları",
       "taraf", "tarafı", "taraflar", "vekil", "idare", "idaresi", "kurum", "kurumu", "işveren", "işçi",
       "kooperatif", "belediye", "bakanlık", "müdürlük", "sigorta", "firma", "mahkememiz", "mahkemeniz",
       "dilekçe", "dilekçesi", "cevap", "ifade", "ifadesi", "rapor", "raporu", "kurul", "kurulu", "daire",
       "dairesi", "makam", "makamı", "kuruluş", "personel", "memur", "polis", "jandarma", "doktor", "hekim",
       "noter", "noterlik", "avukat", "avukatı", "kişi", "kişiler", "kişinin", "şahıs", "aile", "ailesi"}
# Ad dizisinin içinde ya da hemen arkasında görülürse dizi kişi değil kurum/yer sayılır.
KURUM = {"a.ş.", "a.ş", "aş", "ltd", "ltd.", "şti", "şti.", "şirketi", "inşaat", "ticaret", "sanayi", "holding",
         "bankası", "bank", "belediyesi", "üniversitesi", "hastanesi", "lisesi", "okulu", "camii", "parkı",
         "köprüsü", "caddesi", "cad.", "mahallesi", "mah.", "sokak", "sokağı", "sok.", "bulvarı", "vakfı",
         "derneği", "odası", "barosu", "kooperatifi", "meclisi", "müdürlüğü", "başkanlığı", "bakanlığı",
         "valiliği", "kaymakamlığı", "noterliği", "mahkemesi", "dairesi", "kurulu", "kurumu", "enstitüsü",
         "merkezi", "sitesi", "apartmanı", "havalimanı", "stadyumu", "paşa", "kışlası", "meydanı", "tic.", "san."}

_BH = "A-ZÇĞİÖŞÜÂÎÛ"
_KH = "a-zçğıöşüâîû"
_HARF = "[^\\W\\d_]"
TOKEN = re.compile(r"[%s][%s]+\.?|[%s]{2,}" % (_BH, _KH, _BH))
DIZI = re.compile(r"(?:[%s][%s]+|[%s]{2,})(?:(?:[ \t]+|-)(?:[%s][%s]+|[%s]{2,})){0,5}" % (_BH, _KH, _BH, _BH, _KH, _BH))
KESME = "'’‘`"
EKLER = ("nin", "nın", "nun", "nün", "in", "ın", "un", "ün", "ye", "ya", "yi", "yı", "yu", "yü", "yle", "yla",
         "den", "dan", "ten", "tan", "de", "da", "te", "ta", "le", "la", "e", "a", "i", "ı", "u", "ü")

ETIKETLER = ("KİŞİ", "TCKN", "VKN", "IBAN", "TEL", "EPOSTA", "PLAKA", "DOĞUM-TARİHİ", "ADRES", "DOSYA-NO", "DEĞER")
TUM_KURALLAR = frozenset({"tckn", "vkn", "iban", "telefon", "eposta", "plaka", "dogum", "adres", "ad",
                          "esas", "av_istisna", "ocr", "tckn_saglamasiz"})
# esas (dosya no) ve tckn_saglamasiz (sağlaması tutmayan her 11 haneyi maskele) varsayılan KAPALI.
VARSAYILAN_KURALLAR = TUM_KURALLAR - {"esas", "tckn_saglamasiz"}
# Dışa giden (ör. bir yapay zekâ hizmeti) metin için sıkı ayar: sağlaması tutmasa da her 11 haneli sayı maskelenir.
SIKI_KURALLAR = VARSAYILAN_KURALLAR | {"tckn_saglamasiz"}

# Öncelik: küçük sayı kazanır. Çakışmada önce öncelik, sonra uzunluk.
_ONCELIK = {"KORUMA": 0, "SABİT": 1, "EPOSTA": 2, "IBAN": 3, "TCKN": 4, "VKN": 5, "TEL": 6, "PLAKA": 7,
            "DOĞUM-TARİHİ": 8, "DOSYA-NO": 9, "ADRES": 10, "KİŞİ": 11}


# ───────────────────────── yardımcılar ─────────────────────────
def _ek_adlar_yukle():
    yol = os.environ.get("KVKK_MASKE_AD_DOSYASI")
    if not yol:
        return set()
    try:
        with open(yol, encoding="utf-8") as f:
            return {tr_title(x.strip()) for x in f if x.strip() and not x.startswith("#")}
    except OSError:
        return set()


def _onizleme(deger):
    d = deger.strip()
    return (d[:1] + "…" + str(len(d))) if d else ""


def _anahtar(tur, deger):
    """Haritadaki karşılaştırma anahtarı: rakamlı türde boşluk/nokta/tire atılır, adda büyük harf + tek boşluk."""
    if tur in ("TCKN", "VKN", "IBAN", "TEL"):
        return re.sub(r"[^0-9A-Za-z]", "", deger).upper()
    if tur == "EPOSTA":
        return deger.lower()
    if tur == "KİŞİ":
        return " ".join(_katla(deger).split())
    return " ".join(tr_upper(deger).split())


class _Harita:
    """gerçek değer -> etiket. Aynı kişi/numara her geçişte aynı etiketi alır.
    Ad araması için ilk-kelime dizini ve yayılma durumu artımlı tutulur (büyük harita + çok hücre hızlı kalır)."""

    def __init__(self, ham, ozel_etiketler=()):
        self.d = {}
        self.ters = {}      # (tur, anahtar) -> etiket
        self.sayac = {}
        self.tur = {}       # gerçek değer -> tür
        self.ad_ilk = {}    # tek kelimelik ad anahtarı (BÜYÜK) -> {anahtar}
        self.ad_cift = {}   # çok kelimeli ad: (1. kelime, 2. kelime) -> {anahtar}
        self.ad_tum = {}    # adın tüm kelimeleri (katlanmış) -> {anahtar}
        self.ad_azami = 0   # en uzun addaki kelime sayısı
        self.ad_yapi = {}   # anahtar -> (kelimeler, ayraçlar, sondaki işaret, özgün yazımlar)
        self.etiketler = set()
        self.sabitler = []  # rakamlı sabit değerler (dosya no vb.)
        self._yayilan = set()
        if isinstance(ham, (list, tuple, set)):
            ham = {k: None for k in ham}
        for k, v in (ham or {}).items():
            if not k or not str(k).strip():
                continue
            k = str(k).strip()
            v = str(v).strip("[] ") if v else ""
            m = re.fullmatch(r"(.+)-(\d+)", v)
            if m and (m.group(1) in ETIKETLER or m.group(1) in ozel_etiketler):
                tur = m.group(1)            # kayıtlı haritadan: tür etiketten okunur
            elif re.fullmatch(r"\d{4}/\d+", k):
                tur = "DOSYA-NO"
            elif re.search(r"\d", k):
                tur = "SABİT"
            else:
                tur = "KİŞİ"                # ad ya da çağıranın özel etiketi ([DAVACI] gibi)
            if v:
                self._say(v)
                self._degere(k, v, tur)
                self._kaydet(tur, _anahtar(tur, k), v, k)
            else:
                self.ver(tur, k)

    def _degere(self, k, v, tur):
        if k not in self.d:
            self.d[k] = v
            self.tur[k] = tur
            if tur in ("SABİT", "DOSYA-NO"):
                self.sabitler.append(k)
        self.etiketler.add(v)

    def _kaydet(self, tur, anahtar, etiket, ozgun=None):
        self.ters[(tur, anahtar)] = etiket
        if tur == "KİŞİ" and anahtar and anahtar not in self.ad_yapi:
            kelimeler = [m for m in _KELIME.finditer(anahtar)]
            if not kelimeler:
                return
            k = [m.group(0) for m in kelimeler]
            ayr = [_ayrac_norm(anahtar[kelimeler[n].end():kelimeler[n + 1].start()]) for n in range(len(k) - 1)]
            son = _ayrac_norm(anahtar[kelimeler[-1].end():]).strip()
            oz = [m.group(0) for m in _KELIME.finditer(ozgun)] if ozgun else []
            self.ad_yapi[anahtar] = (k, ayr, son, oz if len(oz) == len(k) else [])
            self.ad_tum.setdefault(tuple(k), set()).add(anahtar)
            self.ad_azami = max(self.ad_azami, len(k))
            if len(k) == 1:
                self.ad_ilk.setdefault(k[0], set()).add(anahtar)
            else:
                self.ad_cift.setdefault((k[0], k[1]), set()).add(anahtar)

    def _say(self, etiket):
        m = re.fullmatch(r"(.+)-(\d+)", etiket)
        if m:
            self.sayac[m.group(1)] = max(self.sayac.get(m.group(1), 0), int(m.group(2)))

    def bul(self, tur, deger):
        return self.ters.get((tur, _anahtar(tur, deger)))

    def ver(self, tur, deger, etiket=None):
        a = (tur, _anahtar(tur, deger))
        if a in self.ters:
            return self.ters[a]
        if etiket is None:
            self.sayac[tur] = self.sayac.get(tur, 0) + 1
            etiket = "%s-%d" % (tur, self.sayac[tur])
        self._kaydet(tur, a[1], etiket, deger)
        self._degere(deger, etiket, tur)
        return etiket

    def yay(self):
        """Tam adın tek başına geçen ad/soyadı da aynı etiketi alır (yalnız yeni eklenen adlar işlenir)."""
        for k in [x for x in self.d if x not in self._yayilan]:
            self._yayilan.add(k)
            v = self.d[k]
            if self.tur.get(k) != "KİŞİ" or self.bul("KİŞİ", k) != v or len(k.split()) < 2:
                continue
            for p in k.split():
                if len(p) >= 3 and self.bul("KİŞİ", p) is None:
                    self._kaydet("KİŞİ", _anahtar("KİŞİ", p), v, p)


def _kesisir(a, b, c, d):
    return a < d and c < b


# ───────────────────────── kural bulucular ─────────────────────────
_TAG = re.compile(r"\[(?:%s)(?:-\d+)?\]" % "|".join(re.escape(e) for e in ETIKETLER))
_EPOSTA = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_IBAN_BAS = re.compile(r"(?<![0-9])([A-Za-z]{2})[ ]?(\d{2}|[0-9OolI]{2})(?=[ .\r\n-]{0,4}[0-9A-Za-z])")
_TCKN = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
_ON_BIR = re.compile(r"(?<!\d)\d{11}(?!\d)")
_TCKN_OCR = re.compile(r"(?<![\d/])[0-9OolI]{11}(?![\d/])")
_VKN = re.compile(r"(?<![\d/])\d{10}(?![\d/]|[.,]\d)")
_VKN_BAGLAM = re.compile(r"(vergi|vkn|v\.k\.n|v\.no|vergi no)", re.I)
_TEL = re.compile(
    r"(?<![\d/])"
    r"(?:(?P<ulke>(?:\+|00)\s?90|90(?=[\s.-]?5))[\s.-]?)?"
    r"(?:(?P<p00>0)?\((?P<p0>0)?(?P<pa>[2-58]\d{2})\)|(?P<s0>0)?[ ]?(?P<a>[2-58][ .-]?\d[ .-]?\d))"
    r"(?:[\s./-]?\d)(?:[\s.-]?\d){6}(?![\d/]|[.,]\d)")
_TCKN_AYRIK = re.compile(r"(?<![\d])[1-9](?:[ -]?\d){10}(?![\d])|(?<![\d.])[1-9]\d{2}\.\d{3}\.\d{3}\.\d{2}(?![\d]|\.\d)")
_TCKN_BITISIK = re.compile(r"(?<!\d)(?:\d{11}){2,}(?!\d)")
_PLAKA = re.compile(r"(?<!\d)(0[1-9]|[1-7]\d|8[01])[ ]?([A-PR-VYZ]{1,3})[ ]?(\d{2,5})(?![\w/])")
_PLAKA_HARIC = {"HD", "CD", "CGK", "HGK", "BAM", "TL", "KDV", "USD", "EUR", "TCK", "CMK", "HMK", "TMK", "TBK",
                "AYM", "VUK", "SGK", "BK", "MK", "TK", "IK", "KHK", "NO",
                "TTK", "AY", "YIL", "GR", "KG", "KM", "MT", "CM", "MM", "LT", "AB", "AD", "DE", "DA", "VE"}
_AYLAR = "ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık"
_TARIH = r"(?:\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}|\d{1,2}[ \t]+(?:%s)[ \t]+(?:19|20)\d{2})" % _AYLAR
_DOGUM_ONCE = re.compile(r"(doğum tarihi|doğum yeri ve tarihi|doğ\.\s?tar\.|d\.\s?t\.|doğum t\.)\s*[:\-]?\s*"
                         r"(?:[^\d\n]{0,25}?)(?P<t>%s)" % _TARIH)
_DOGUM_SONRA = re.compile(r"(?P<t>%s|(?<!\d)(?:19|20)\d{2})(?:[ \t]*(?:'|’)?[ \t]*)(?:doğumlu|d\.lu)" % _TARIH)
_ESAS = re.compile(r"(?<![\d/])(?:(?:E|K)\.?\s?:?\s?)?(?:19|20)\d{2}\s?/\s?\d{1,6}(?![\d/])(?:\s?(?:E\.|K\.|Esas|Karar|E\b|K\b))?")
_EMSAL_IZI = re.compile(r"(\bhd\b|\bcd\b|\bhgk\b|\bcgk\b|\bbam\b|\bdaire|yargıtay|danıştay|\baym\b|bölge adliye|"
                        r"\bidd?gk\b|\bvddk\b|b\.\s?no|başvuru no|içtihad|emsal)")
_ADRES_PARCA = re.compile(
    r"(?<![\w])(?:mahallesi|mah\.|mh\.|caddesi|cad\.|cd\.|sokağı|sokak|sok\.|sk\.|bulvarı|blv\.|bulvar|"
    r"apartmanı|apt\.|sitesi|blok|kat\s?:?\s?\d+|daire\s?:?\s?\d+|d\s?:\s?\d+|no\s?[:.]?\s?\d+[a-zçğıöşü]?(?:\s?/\s?\d+)?)"
    r"(?![\w])")
_IL_ILCE = re.compile(r"[ \t,]*[%s][%s%s]+[ \t]*/[ \t]*[%s][%s%s]+" % (_BH, _KH, _BH, _BH, _KH, _BH))
_YER_ARKA = re.compile(r"[ \t]*(?:doğumlu|doğumludur|ilinde|ilçesinde|ilçesi|merkezli|şubesi|şubesinde)(?![\w])")
IL_ADLARI = set("""Adana Adıyaman Afyonkarahisar Ağrı Amasya Ankara Antalya Artvin Aydın Balıkesir Bilecik Bingöl Bitlis
Bolu Burdur Bursa Çanakkale Çankırı Çorum Denizli Diyarbakır Edirne Elazığ Erzincan Erzurum Eskişehir Gaziantep Giresun
Gümüşhane Hakkari Hatay Isparta Mersin İstanbul İzmir Kars Kastamonu Kayseri Kırklareli Kırşehir Kocaeli Konya Kütahya
Malatya Manisa Kahramanmaraş Mardin Muğla Muş Nevşehir Niğde Ordu Rize Sakarya Samsun Siirt Sinop Sivas Tekirdağ Tokat
Trabzon Tunceli Şanlıurfa Uşak Van Yozgat Zonguldak Aksaray Bayburt Karaman Kırıkkale Batman Şırnak Bartın Ardahan Iğdır
Yalova Karabük Kilis Osmaniye Düzce""".split())
_ARKA = re.compile(r"[ \t]*([^\s,;:()]+)")
_AV = re.compile(r"(?<![\w])Av\.?[ \t]+(?:[%s][%s]+|[%s]{2,})(?:[ \t]+(?:[%s][%s]+|[%s]{2,})){0,3}"
                 % (_BH, _KH, _BH, _BH, _KH, _BH))


def _iban_bul(metin, ocr, gevsek=False):
    """gevsek=True: boş satırla bölünmüş IBAN'ı da bulur (yalnız korumak için; maskelenmez, şüpheli listesine düşer)."""
    out = []
    for m in _IBAN_BAS.finditer(metin):
        ulke = m.group(1).upper()
        if not (m.group(1).isupper() or ulke == "TR"):
            continue            # küçük harfli başlangıç yalnız "tr" için kabul edilir
        i = m.end(1)
        karakter, konum = [], []
        while i < len(metin) and len(karakter) < 34:
            c = metin[i]
            if c in " -.\n\r" and karakter:   # boşluk, tire, nokta; tek satır sonunda bölünmüş IBAN da (mod-97 doğrular)
                k = i
                while k < len(metin) and metin[k] in " -.\n\r" and k - i < (8 if gevsek else 4):
                    k += 1
                ara = metin[i:k]
                if k < len(metin) and metin[k].isalnum() and ara.count("-") + ara.count(".") <= 1 \
                        and ara.count("\n") <= (2 if gevsek else 1) and ara.count("\r") <= (2 if gevsek else 1) \
                        and ara.count(" ") <= (4 if gevsek else 2):
                    i = k
                    continue
                break
            if c.isalnum() and (c.isdigit() or c.isupper() or (ocr and c in "ol")):
                karakter.append(c)
                konum.append(i)
                i += 1
                continue
            break
        en_iyi = None
        for L in range(min(len(karakter), 32), 12, -1):
            aday = ulke + "".join(karakter[:L])
            if ocr and ulke == "TR":
                aday = aday[:2] + aday[2:].replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
            if iban_gecerli(aday):
                son = konum[L - 1] + 1
                if son < len(metin) and metin[son].isdigit():
                    continue
                en_iyi = (m.start(), son, aday)
                break
        if en_iyi:
            out.append(en_iyi)
    return out


def _baglam_var(metin, bas, desen, geri=40):
    return bool(desen.search(metin[max(0, bas - geri):bas]))


def _adres_bul(metin, low):
    parcalar = []
    for m in _ADRES_PARCA.finditer(low):
        bas = m.start()
        # sola doğru en çok 3 büyük harfli kelime ya da sayı ("Lale Sok.", "1234. Sokak", "Atatürk Cad.")
        pb = max(0, bas - 120)
        sol = metin[pb:bas]
        g = re.search(r"((?:(?:[%s][\w]*|\d+\.?)[ \t]+){1,3})$" % _BH, sol)
        if g and not re.match(r"(?i)no|kat|daire|d\s?:", m.group(0)):
            bas = pb + g.start(1)
        parcalar.append([bas, m.end(), 1])
    birlesik = []
    for p in sorted(parcalar):
        if birlesik and re.fullmatch(r"[\s,.:/-]{0,4}", metin[birlesik[-1][1]:p[0]] if p[0] >= birlesik[-1][1] else ""):
            birlesik[-1][1] = max(birlesik[-1][1], p[1])
            birlesik[-1][2] += 1
        elif birlesik and p[0] < birlesik[-1][1]:
            birlesik[-1][1] = max(birlesik[-1][1], p[1])
            birlesik[-1][2] += 1
        else:
            birlesik.append(p)
    out = []
    for bas, son, n in birlesik:
        if n < 2:
            continue
        k = re.compile(r"[ \t,]*\d{5}\b").match(metin, son)
        if k:
            son = k.end()
        k = _IL_ILCE.match(metin, son)
        if k:
            son = k.end()
        out.append((bas, son))
    return out


def _ad_adaylari(metin, low, dolu, sozluk, kurallar):
    """Bağlam kelimesi ya da ad sözlüğüyle bilinmeyen kişi adlarını bulur -> [(ad metni, baş, son)]."""
    bulunan = []

    import bisect
    dolu_s = sorted(dolu)
    dolu_bas = [x for x, _ in dolu_s]
    en_uzun = max([y - x for x, y in dolu_s] or [0])

    def bos(a, b):
        # yalnız a'dan en uzun aralık kadar önce başlayan ve b'den önce başlayan aralıklara bakılır
        i = bisect.bisect_left(dolu_bas, a - en_uzun)
        k = bisect.bisect_left(dolu_bas, b)
        return not any(_kesisir(a, b, x, y) for x, y in dolu_s[i:k])

    def kes(tokenler, sozluk_kurali):
        """Kişi adını seç. Tireyle bağlı ikinci parça yer/kurum ise ("Ekinci-Kadıköy/İstanbul",
        "Arıkanlı-Ankara Üniversitesi", "Ekinci-İstanbul doğumlu") ad tireden önce biter."""
        for i in range(1, len(tokenler)):
            if metin[tokenler[i - 1][2]:tokenler[i][1]] != "-":
                continue
            sec = _kes0(tokenler, sozluk_kurali)
            yer = tr_title(tokenler[i][0]) in IL_ADLARI or not sec or (
                sec and sec[-1][2] >= tokenler[i][2] and _YER_ARKA.match(metin, sec[-1][2]))
            if yer:
                return _kes0(tokenler[:i], sozluk_kurali)
            return sec
        return _kes0(tokenler, sozluk_kurali)

    def _kes0(tokenler, sozluk_kurali):
        """Token listesinden kişi adını seç; kurum/durak kelimelerinde kes."""
        secilen = []
        for i, (t, a, b) in enumerate(tokenler):
            tl = tr_lower(t)
            if tl in DUR or tl.rstrip(".") in DUR:
                break
            if tl in KURUM or tl.rstrip(".") in KURUM:
                return []
            if sozluk_kurali and i >= 2 and tr_title(t) in sozluk:
                break       # yeni kişi başlıyor ("Ahmet Kaya Mehmet Demir")
            secilen.append((t, a, b))
            if len(secilen) == 3:
                break
        if not secilen:
            return []
        # dizinin hemen arkasındaki kelime kurum/yer ise kişi değildir ("Mehmet Akif Ersoy Üniversitesi")
        son = secilen[-1][2]
        arka = _ARKA.match(metin, son)
        if arka and (tr_lower(arka.group(1)) in KURUM or tr_lower(arka.group(1)).rstrip(".,") in KURUM):
            return []
        if metin[son:son + 1] == "/" or (secilen[0][1] > 0 and metin[secilen[0][1] - 1] == "/"):
            return []
        return secilen

    def tokenle(bas, son=None):
        parca = metin[bas:son] if son else metin[bas:bas + 200]
        out = []
        for m in TOKEN.finditer(parca):
            if out and not re.fullmatch(r"[ \t]+|-", parca[out[-1][2] - bas:m.start()]):
                break
            if not out and m.start() != 0:
                break
            t = m.group(0).rstrip(".") if not m.group(0).endswith("..") else m.group(0)
            out.append((t, bas + m.start(), bas + m.start() + len(t)))
            if len(out) == 6:
                break
        return out

    # (1) önde bağlam kelimesi
    desen = re.compile(r"(?<![\w])(%s)(?![\w])[ \t]*[:\-–]?[ \t]*" % "|".join(re.escape(b) for b in
                                                                       sorted(BAGLAM_ONCE, key=len, reverse=True)))
    for m in desen.finditer(low):
        sec = kes(tokenle(m.end()), False)
        if sec and bos(sec[0][1], sec[-1][2]):
            bulunan.append((metin[sec[0][1]:sec[-1][2]], sec[0][1], sec[-1][2]))
    # (2) arkada bağlam kelimesi ("Ahmet Kaya adlı")
    desen2 = re.compile(r"(?<![ \t])[ \t]+(%s)(?![\w])" % "|".join(BAGLAM_SONRA))
    for m in desen2.finditer(low):
        pb = max(0, m.start() - 200)
        sol = metin[pb:m.start()]
        g = re.search(r"((?:[%s][%s]+|[%s]{2,})(?:[ \t]+(?:[%s][%s]+|[%s]{2,})){0,2})$" % (_BH, _KH, _BH, _BH, _KH, _BH), sol)
        if not g:
            continue
        tok = [(x.group(0), pb + g.start(1) + x.start(), pb + g.start(1) + x.end()) for x in TOKEN.finditer(g.group(1))]
        while tok and (tr_lower(tok[0][0]) in DUR or (len(tok) > 2 and tr_title(tok[0][0]) not in sozluk)):
            tok = tok[1:]
        if any(tr_lower(t) in DUR or tr_lower(t) in KURUM for t, _, _ in tok):
            continue
        if tok and bos(tok[0][1], tok[-1][2]):
            bulunan.append((metin[tok[0][1]:tok[-1][2]], tok[0][1], tok[-1][2]))
    # (3) sözlükteki ad (+ büyük harfli soyad)
    for m in DIZI.finditer(metin):
        tok = [(x.group(0), m.start() + x.start(), m.start() + x.end()) for x in TOKEN.finditer(m.group(0))]
        i = 0
        while i < len(tok):
            t = tok[i][0].rstrip(".")
            if tr_title(t) in sozluk:
                if i > 0 and tr_lower(tok[i - 1][0]) == "av" and "av_istisna" in kurallar:
                    i += 1
                    continue
                sec = kes(tok[i:], True)
                if sec and (len(sec) >= 2 or tr_title(sec[0][0]) not in BELIRSIZ) and bos(sec[0][1], sec[-1][2]):
                    bulunan.append((metin[sec[0][1]:sec[-1][2]], sec[0][1], sec[-1][2]))
                    i += len(sec)
                    continue
            i += 1
    return bulunan


_KELIME = re.compile(r"[^\W\d_]+")
_EKLER_UST = {_katla(e): e for e in EKLER}
_EK_KUME = set(EKLER) | set(_EKLER_UST)


def _yazim_uygun(parca, kok):
    """Metindeki kelime haritadaki kelimenin Başlık ya da BÜYÜK yazımı mı? (küçük harfli sıradan kelime değil)
    kok katlanmış (İ=I) BÜYÜK yazımdır; ASCII büyük yazım (ROSSI) ve Türkçe büyük yazım (YİĞİT) ikisi de kabul."""
    if not parca or not parca[0].isupper() or _katla(parca) != kok:
        return False
    govde = parca[1:]
    return govde == "" or govde.islower() or govde.isupper() or not any(c.isalpha() for c in govde)


def _ayrac_norm(x):
    """Ad içindeki ayraç: boşluk tekleşir, noktalama çevresindeki boşluk atılır, kıvrık kesme düz olur."""
    x = re.sub(r"[’‘`]", "'", x)
    x = re.sub(r"\s*-\s*", " ", x)            # tireli ad boşluklu yazılmış olabilir (Ayşe-Nur / Ayşe Nur)
    x = re.sub(r"\s*([^\w\s])\s*", r"\1", x)
    return re.sub(r"\s+", " ", x)


def _ek_kokleri(W, w):
    """'DOĞRUSÖZDEN' -> [('DOĞRUSÖZDEN', ''), ('DOĞRUSÖZ', 'den')] (kesmesiz ek, kök 4+ harf)."""
    out = [(W, "")]
    for eu in _EKLER_UST:
        if W.endswith(eu) and len(W) - len(eu) >= 4 and w[len(w) - len(eu):] in _EK_KUME:
            out.append((W[:-len(eu)], w[len(w) - len(eu):]))
    return out


def _ad_eslesmeleri(metin, H):
    """Haritadaki tüm adların (tam ad + parçaları) geçişleri -> [(baş, son, harita anahtarı)].
    Metin bir kez kelimelere bölünür; her konumda 1..en uzun ad kadar kelime dizisi tek sözlük aramasıyla denenir
    (aynı ilk adları paylaşan binlerce kişi olsa da hızlı). Ad içindeki nokta, kesme, tire korunarak karşılaştırılır
    (Mehmet A. Öz, O'Brien, Jean-Luc). Kesmesiz ek yalnız 4+ harfli son kelimede kabul edilir."""
    if not H.ad_tum:
        return []
    tok = [(m.start(), m.end(), m.group(0)) for m in _KELIME.finditer(metin)]
    out = []

    def uygun(parca, kelime, ozgun):
        return _yazim_uygun(parca, kelime) or (ozgun and parca == ozgun)

    def dogrula(i, anahtar, ilk_ek):
        k, ayr, son_isaret, oz = H.ad_yapi[anahtar]
        a, b, w = tok[i]
        if not uygun(w[:len(w) - len(ilk_ek)] if ilk_ek else w, k[0], oz[0] if oz else None):
            return None
        son = b - len(ilk_ek)
        for n in range(1, len(k)):
            j = i + n
            if j >= len(tok):
                return None
            ara = metin[tok[j - 1][1]:tok[j][0]]
            if "\n" in ara or _ayrac_norm(ara) != ayr[n - 1]:
                return None
            a2, b2, w2 = tok[j]
            W2, t, ozg = _katla(w2), k[n], (oz[n] if oz else None)
            if W2 == t and uygun(w2, t, ozg):
                son = b2
            elif n == len(k) - 1 and not son_isaret and len(t) >= 4 and W2.startswith(t) \
                    and W2[len(t):] in _EKLER_UST and w2[len(t):] in _EK_KUME and uygun(w2[:len(t)], t, ozg):
                son = b2 - (len(w2) - len(t))
            else:
                return None
        if son_isaret and metin.startswith(son_isaret, son):
            son += len(son_isaret)          # "Ali Rıza K." sondaki nokta da adın parçası
        return son

    katli = [None] * len(tok)
    for i, (a, b, w) in enumerate(tok):
        if not w[0].isupper():
            continue
        kelimeler = []
        for L in range(1, min(H.ad_azami, len(tok) - i) + 1):
            j = i + L - 1
            if L > 1:
                ara = metin[tok[j - 1][1]:tok[j][0]]
                if len(ara) > 3 or "\n" in ara:
                    break           # ad kelimeleri arasında en çok kısa bir ayraç olur
            if katli[j] is None:
                katli[j] = _katla(tok[j][2])
            kelimeler.append(katli[j])
            # adın tüm kelimeleri tek sözlük aramasıyla bulunur; son kelimede kesmesiz ek denenir
            for kok, ek in _ek_kokleri(kelimeler[-1], tok[j][2]):
                for anahtar in H.ad_tum.get(tuple(kelimeler[:-1]) + (kok,), ()):
                    if L == 1 and ek and H.ad_yapi[anahtar][2]:
                        continue
                    son = dogrula(i, anahtar, ek if L == 1 else "")
                    if son:
                        out.append((a, son, anahtar))
    return out


# ───────────────────────── ana işlev ─────────────────────────
def maskele(metin, harita=None, kurallar=VARSAYILAN_KURALLAR, ek_adlar=None, serbest_epostalar=(),
            haric=(), ozel_kurallar=()):
    """-> (maskeli_metin, harita {gerçek: etiket}, bulgular [{tur, etiket, bas, son, onizleme}])

    harita: dışarıdan verilen ad/değer listesi ya da {gerçek: etiket|None}. None ise etiket kendiliğinden
    verilir (KİŞİ-n). Dönen haritayı bir sonraki çağrıya verirsen aynı kişi aynı etiketi alır.
    haric: hiçbir kuralda maskelenmeyecek ifadeler (büyük/küçük harf duyarsız; ör. şirket unvanı, proje adı).
    ozel_kurallar: [(ETİKET, regex)] ya da ozel_kural_derle() çıktısı; eşleşen değer [ETİKET-n] olur.
    """
    if not metin:
        return metin, dict(harita or {}) if isinstance(harita, dict) else {}, []
    metin = unicodedata.normalize("NFC", metin)     # ayrışık (NFD) harfler birleşik biçime
    if isinstance(harita, dict):
        harita = {unicodedata.normalize("NFC", str(k)): v for k, v in harita.items()}
    elif harita:
        harita = [unicodedata.normalize("NFC", str(k)) for k in harita]
    ozel = ozel_kural_derle(ozel_kurallar)
    H = _Harita(harita, {e for e, _ in ozel})
    out, bulgular = _maskele_ic(metin, H, set(kurallar), ek_adlar, serbest_epostalar, haric, ozel)
    return out, dict(H.d), bulgular


def _maskele_ic(metin, H, kurallar, ek_adlar=None, serbest_epostalar=(), haric=(), ozel=()):
    """maskele'nin gövdesi; harita nesnesi (H) çağrılar arasında paylaşılabilir (CSV hücreleri)."""
    if not metin:
        return metin, []
    metin = unicodedata.normalize("NFC", metin)
    low = tr_lower(metin)
    assert len(low) == len(metin)
    sozluk = AD_SOZLUGU | _ek_adlar_yukle() | {tr_title(a) for a in (ek_adlar or ())}
    adaylar = []        # (bas, son, tur, deger)
    uyarilar = []

    ozel_adlar = {e for e, _ in ozel}
    for m in re.finditer(r"\[([^\[\]\n]{1,40})\]", metin):
        ic = m.group(1)
        if ic in H.etiketler or _TAG.fullmatch(m.group(0)) or re.sub(r"-\d+$", "", ic) in ozel_adlar:
            adaylar.append((m.start(), m.end(), "KORUMA", None))
            if _TAG.fullmatch(m.group(0)) and ic not in H.etiketler:
                H._say(ic)      # metinde zaten olan etiket numarası yeniden verilmez
    # Hariç ifadeler: yalnız TAMAMEN içlerinde kalan bulgu serbest kalır (daha uzun veri yine maskelenir)
    haric_araliklar = []
    for ifade in haric:
        ifade = tr_lower(ifade.strip())
        if not ifade:
            continue
        for m in re.finditer(r"(?<![\w])%s(?![\w])" % re.escape(ifade), low):
            haric_araliklar.append((m.start(), m.end()))
    for etiket, desen in ozel:
        for m in desen.finditer(metin):
            if m.end() > m.start():
                adaylar.append((m.start(), m.end(), etiket, m.group(0)))
    if "av_istisna" in kurallar:
        for m in _AV.finditer(metin):
            adaylar.append((m.start(), m.end(), "KORUMA", None))
    # dışarıdan verilen rakamlı sabit değerler (dosya no vb.)
    for k in H.sabitler:
        if k in metin:
            for m in re.finditer(r"(?<![\w/])%s(?![\w/])" % re.escape(k), metin):
                adaylar.append((m.start(), m.end(), "SABİT", k))
    if "eposta" in kurallar:
        serbest = {e.lower() for e in serbest_epostalar}
        for m in _EPOSTA.finditer(metin):
            if m.group(0).lower() not in serbest:
                adaylar.append((m.start(), m.end(), "EPOSTA", m.group(0)))
    if "iban" in kurallar:
        bulunan_iban = _iban_bul(metin, "ocr" in kurallar)
        for a, b, deger in bulunan_iban:
            adaylar.append((a, b, "IBAN", metin[a:b]))      # haritada yazıldığı biçim; anahtar boşluksuz
        for a, b, _ in _iban_bul(metin, "ocr" in kurallar, gevsek=True):
            if not any(_kesisir(a, b, x, y) for x, y, _ in bulunan_iban):
                adaylar.append((a, b, "KORUMA", None))      # boş satırla bölünmüş IBAN: yarım maske olmasın
    if "tckn" in kurallar:
        for m in _TCKN.finditer(metin):
            if tckn_gecerli(m.group(0)):
                adaylar.append((m.start(), m.end(), "TCKN", m.group(0)))
        for m in _TCKN_AYRIK.finditer(metin):          # 123 456 789 01 / 123-456-789-01 (sağlamalı)
            sade = re.sub(r"[ .-]", "", m.group(0))
            if sade != m.group(0) and tckn_gecerli(sade):
                adaylar.append((m.start(), m.end(), "TCKN", sade))
        for m in _TCKN_BITISIK.finditer(metin):        # iki TCKN bitişik yazılmış
            g = m.group(0)
            parca = [g[k:k + 11] for k in range(0, len(g), 11)]
            if all(tckn_gecerli(x) for x in parca):
                for n, x in enumerate(parca):
                    adaylar.append((m.start() + 11 * n, m.start() + 11 * n + 11, "TCKN", x))
        for m in _ON_BIR.finditer(metin):
            if tckn_gecerli(m.group(0)):
                continue
            if re.match(r"0[2-58]", m.group(0)) and "telefon" in kurallar:   # 0 5xx… telefondur
                adaylar.append((m.start(), m.end(), "TEL", m.group(0)))
            elif "tckn_saglamasiz" in kurallar:
                adaylar.append((m.start(), m.end(), "TCKN", m.group(0)))
            else:
                uyarilar.append((m.start(), m.end()))
        if "ocr" in kurallar:
            for m in _TCKN_OCR.finditer(metin):
                g = m.group(0)
                if g.isdigit() or sum(c.isdigit() for c in g) < 8:
                    continue
                n = g.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
                if tckn_gecerli(n):
                    adaylar.append((m.start(), m.end(), "TCKN", n))
    if "vkn" in kurallar:
        for m in _VKN.finditer(metin):
            if vkn_gecerli(m.group(0)) and _baglam_var(metin, m.start(), _VKN_BAGLAM):
                adaylar.append((m.start(), m.end(), "VKN", m.group(0)))
    if "telefon" in kurallar:
        for m in _TEL.finditer(metin):
            alan = m.group("pa") or m.group("a")
            cep = alan.startswith("5")
            onek = m.group("ulke") or m.group("p00") or m.group("p0") or m.group("s0") or m.group("pa")
            if cep or onek:       # sabit hat için 0, +90 ya da parantez şart
                adaylar.append((m.start(), m.end(), "TEL", m.group(0)))
    if "plaka" in kurallar:
        for m in _PLAKA.finditer(metin):
            harf, rakam = m.group(2), m.group(3)
            if harf in _PLAKA_HARIC:
                continue
            gecerli = (len(harf) == 1 and len(rakam) in (4, 5)) or (len(harf) == 2 and len(rakam) in (3, 4)) \
                or (len(harf) == 3 and len(rakam) in (2, 3))
            if gecerli:
                adaylar.append((m.start(), m.end(), "PLAKA", m.group(0)))
    if "dogum" in kurallar:
        for m in _DOGUM_ONCE.finditer(low):
            adaylar.append((m.start("t"), m.end("t"), "DOĞUM-TARİHİ", metin[m.start("t"):m.end("t")]))
        for m in _DOGUM_SONRA.finditer(low):
            adaylar.append((m.start("t"), m.end("t"), "DOĞUM-TARİHİ", metin[m.start("t"):m.end("t")]))
    if "esas" in kurallar:
        for m in _ESAS.finditer(metin):
            satir_bas = metin.rfind("\n", 0, m.start()) + 1
            if _EMSAL_IZI.search(low[max(satir_bas, m.start() - 60):m.start()]):
                continue
            no = re.search(r"(?:19|20)\d{2}\s?/\s?\d{1,6}", m.group(0)).group(0).replace(" ", "")
            adaylar.append((m.start(), m.end(), "DOSYA-NO", no))
    if "adres" in kurallar:
        for a, b in _adres_bul(metin, low):
            adaylar.append((a, b, "ADRES", metin[a:b]))

    # ad dışı adayları çöz; adlar bunların içinde aranmaz
    def coz(liste):
        # çakışmayan aralıklar başlangıca göre sıralı tutulur; her aday için yalnız komşuya bakılır (n log n)
        import bisect
        secilen, baslar, sonlar = [], [], []
        for a in sorted(liste, key=lambda x: (_ONCELIK.get(x[2], 10.5), -(x[1] - x[0]), x[0])):
            if a[2] != "KORUMA" and any(h0 <= a[0] and a[1] <= h1 for h0, h1 in haric_araliklar):
                continue
            i = bisect.bisect_left(baslar, a[1])
            if i > 0 and sonlar[i - 1] > a[0]:
                continue
            if i < len(baslar) and baslar[i] < a[1]:
                continue
            baslar.insert(i, a[0])
            sonlar.insert(i, a[1])
            secilen.append(a)
        return secilen

    secili = coz(adaylar)

    H.yay()
    if "ad" in kurallar:
        dolu = [(s[0], s[1]) for s in secili]
        # haritada zaten olan adların geçişleri de dolu sayılır: "Ayşe-Nur" içindeki "Ayşe" yeni kişi olmaz
        dolu += [(x[0], x[1]) for x in _ad_eslesmeleri(metin, H)]
        # uzun (tam) adlar önce: "Koray Selvitop" etiketi sonra tek geçen "Selvitop"ye de yayılsın
        bulunan = [x for x in _ad_adaylari(metin, low, dolu, sozluk, kurallar)
                   if not any(h0 <= x[1] and x[2] <= h1 for h0, h1 in haric_araliklar)]
        ilk_sira = {}
        for n, x in enumerate(bulunan):
            ilk_sira.setdefault(x[0], n)
        for ad in sorted(ilk_sira, key=lambda x: (-len(x.split()), ilk_sira[x])):
            if H.bul("KİŞİ", ad) is None:
                H.ver("KİŞİ", ad)
                H.yay()
    for a, b, deger in _ad_eslesmeleri(metin, H):
        adaylar.append((a, b, "KİŞİ", deger))
    secili = coz(adaylar)

    bulgular = []
    parcalar = []
    for bas, son, tur, deger in sorted(secili, key=lambda x: x[0]):
        if tur == "KORUMA":
            continue
        if tur == "SABİT":
            etiket = H.d[deger]
            tur = H.tur.get(deger, "SABİT")
        elif tur == "KİŞİ":
            etiket = H.bul("KİŞİ", deger)
        else:
            etiket = H.ver(tur, deger)
        bulgular.append({"tur": tur, "etiket": etiket, "bas": bas, "son": son, "onizleme": _onizleme(metin[bas:son])})
        parcalar.append((bas, son, etiket))
    for bas, son in uyarilar:
        if not any(_kesisir(bas, son, b, s) for b, s, _ in parcalar):
            bulgular.append({"tur": "UYARI-11-HANE", "etiket": None, "bas": bas, "son": son,
                             "onizleme": _onizleme(metin[bas:son]), "not": "sağlaması tutmayan 11 hane; maskelenmedi"})
    parca_listesi, onceki = [], 0
    for bas, son, etiket in sorted(parcalar):
        yeni = "[%s]" % etiket
        if son < len(metin) and metin[son].isalpha():
            yeni += "'"
        parca_listesi += [metin[onceki:bas], yeni]
        onceki = son
    parca_listesi.append(metin[onceki:])
    return "".join(parca_listesi), bulgular


# Yapay zekâya maskeli metinle birlikte verilecek talimat (etiketlerin bozulmaması için).
YZ_TALIMATI = ("[Not: Bu metindeki [KİŞİ-1], [TEL-1] gibi köşeli parantezli etiketler gizlenmiş kişisel verilerdir. "
               "Cevabında bu etiketleri köşeli parantezleri ve tireleriyle HARFİ HARFİNE aynen kullan; çevirme, "
               "değiştirme, birleştirme, açmaya ya da tahmin etmeye çalışma. Etiketin arkasına ek getirebilirsin "
               "([KİŞİ-1]'in gibi).]\n\n")

_ETIKET_KOK = "|".join(re.escape(e) for e in sorted(ETIKETLER, key=len, reverse=True))


def geri_al(metin, harita):
    """[ETİKET] -> gerçek değer. Aynı etikete birden çok yazım bağlıysa en uzunu (tam ad) kullanılır.
    Köşeli parantezli ama harfi/boşluğu bozulmuş etiket ([Kişi-1], [KİŞİ 1]) de çevrilir."""
    metin = unicodedata.normalize("NFC", metin)
    ters = {}
    for k, v in (harita or {}).items():
        if v and (v not in ters or len(k) > len(ters[v])):
            ters[v] = k
    for v in sorted(ters, key=len, reverse=True):
        metin = metin.replace("[%s]" % v, ters[v])
    # bozulmuş ama köşeli parantezli biçimler: büyük/küçük harf, tire yerine boşluk ya da alt çizgi
    norm = {_etiket_norm(v): k for v, k in ters.items()}

    def _onar(m):
        return norm.get(_etiket_norm(m.group(1)), m.group(0))
    return re.sub(r"\[([^\[\]\n]{1,40})\]", _onar, metin)


def _etiket_norm(e):
    return re.sub(r"[\s_\-]+", "-", tr_upper(e.strip()))


def bozuk_etiketler(metin, harita=None):
    """Geri çevrilemeyecek etiket izlerini bulur (köşeli parantezi düşmüş 'KİŞİ-1' ya da haritada olmayan etiket).
    Dönüş: [(konum, görülen metin)]. Cevabı geri çevirdikten SONRA çağırın."""
    bilinen = {_etiket_norm(v) for v in (harita or {}).values() if v}
    ust = tr_upper(metin)
    out = []
    for m in re.finditer(r"(?<![\w])\[?(%s)[\s_\-]?(\d+)\]?" % _ETIKET_KOK, ust):
        out.append((m.start(), metin[m.start():m.end()]))
    return [x for x in out if x[1].startswith("[") is False or _etiket_norm(x[1].strip("[]")) not in bilinen]


_ETIKET_ADI = re.compile(r"[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9_]*(?:-[A-ZÇĞİÖŞÜ_][A-ZÇĞİÖŞÜ0-9_]*)*")


def ozel_kural_derle(kurallar):
    """[(ETİKET, regex)] -> [(ETİKET, derlenmiş)]. Hatalı etiket ya da regex -> ValueError (anlaşılır ileti).
    Uyarı: regex kullanıcınındır; iç içe tekrar (ör. (a+)+) çok yavaş çalışabilir (ReDoS)."""
    out = []
    for i, (etiket, desen) in enumerate(kurallar or (), 1):
        if hasattr(desen, "finditer"):
            out.append((etiket, desen))
            continue
        etiket = str(etiket).strip()
        if not _ETIKET_ADI.fullmatch(etiket) or etiket in ETIKETLER:
            raise ValueError("özel kural %d: etiket '%s' geçersiz (BÜYÜK harf, rakam, tire; hazır etiket adı olamaz)"
                             % (i, etiket))
        try:
            out.append((etiket, re.compile(desen)))
        except re.error as e:
            raise ValueError("özel kural %d (%s): regex derlenemedi: %s" % (i, etiket, e))
    return out


def ozel_kural_dosyasi(yol):
    """Her satır: ETİKET<TAB>regex. Boş ve # ile başlayan satırlar atlanır."""
    kurallar = []
    with open(yol, encoding="utf-8-sig") as f:
        for n, satir in enumerate(f, 1):
            satir = satir.rstrip("\r\n")
            if not satir.strip() or satir.lstrip().startswith("#"):
                continue
            if "\t" not in satir:
                raise ValueError("%s satır %d: ETİKET ile regex arasında SEKME yok" % (yol, n))
            etiket, desen = satir.split("\t", 1)
            kurallar.append((etiket.strip(), desen))
    ozel_kural_derle(kurallar)
    return kurallar


def haric_dosyasi(yol):
    with open(yol, encoding="utf-8-sig") as f:
        return [x.strip() for x in f if x.strip() and not x.lstrip().startswith("#")]


_SUPHE_SAYI = re.compile(r"(?<!\d)\d{10,11}(?!\d)|(?<!\d)\d{3}[ .-]\d{3}[ .-]\d{2}[ .-]\d{2}(?!\d)")
_SUPHE_BOLUNMUS = re.compile(r"(?<![\d])(\d[\d .-]{1,14}?)[ \t]*\n[ \t]*([\d .-]{1,14}\d)(?![\d])")
_SUPHE_UZUN = re.compile(r"(?<![\d])\d(?:[ .-]?\d){11,}(?![\d])")
_SUPHE_AT = re.compile(r"[^\s\[\]]*@[^\s\[\]]+")
_SUPHE_ADRES = re.compile(r"(?<![\w])(mahallesi|mah\.|mh\.|caddesi|cad\.|sokağı|sokak|sok\.|sk\.|bulvarı|apt\.|apartmanı)(?![\w])")
_SUPHE_IBAN = re.compile(r"(?<![A-Za-z0-9])TR\s?\d{2}")
_SUPHE_IKILI = re.compile(r"(?<![\w\[])([%s][%s]{2,})(?=([ \t]+)([%s][%s]{2,})(?![\w\]]))" % (_BH, _KH, _BH, _KH))


def supheli_izler(metin, sozluk=None):
    """MASKELEMEDEN SONRA kalan, gözle bakılması gereken izler. Değer göstermez: satır, tür, önizleme (ilk karakter
    + uzunluk). Puan ya da uyum raporu DEĞİLDİR; "şunlara bir de sen bak" listesidir."""
    sozluk = sozluk or AD_SOZLUGU
    low = tr_lower(metin)
    out = []

    def ekle(bas, son, tur):
        out.append({"satir": metin.count("\n", 0, bas) + 1, "tur": tur, "onizleme": _onizleme(metin[bas:son])})

    for m in _SUPHE_SAYI.finditer(metin):
        ekle(m.start(), m.end(), "rakam dizisi (10-11 hane / telefon biçimi)")
    for m in _SUPHE_BOLUNMUS.finditer(metin):
        if 10 <= len(re.sub(r"\D", "", m.group(1) + m.group(2))) <= 12:
            ekle(m.start(), m.end(), "satır sonunda bölünmüş rakam dizisi")
    for m in _SUPHE_UZUN.finditer(metin):
        ekle(m.start(), m.end(), "uzun rakam dizisi (12+ hane; bölünmüş IBAN/numara olabilir)")
    for m in _SUPHE_AT.finditer(metin):
        ekle(m.start(), m.end(), "@ içeren kelime")
    for m in _SUPHE_IBAN.finditer(metin):
        ekle(m.start(), m.end(), "IBAN başlangıcına benzer")
    for m in _SUPHE_ADRES.finditer(low):
        ekle(m.start(), m.end(), "tek adres izi")
    for m in _SUPHE_IKILI.finditer(metin):
        a, b = m.group(1), m.group(3)
        if {tr_lower(a), tr_lower(b)} & (DUR | KURUM) or tr_title(a) in sozluk:
            continue
        satir_bas = metin.rfind("\n", 0, m.start()) + 1
        if not metin[satir_bas:m.start()].strip() or re.search(r"[.!?:]\s*$", metin[max(0, m.start() - 3):m.start()]):
            continue        # cümle/satır başı: büyük harf olağan
        ekle(m.start(), m.end(1) + len(m.group(2)) + len(b), "ad benzeri iki kelime (sözlükte yok)")
    return sorted(out, key=lambda x: x["satir"])


# ───────────────────────── CSV / XLSX ─────────────────────────
_AD_KELIME = re.compile(r"[^\W\d_]+(?:['’\-.][^\W\d_]*)*\.?")
_AD_SUTUNU = {"ad", "adı", "adi", "soyad", "soyadı", "soyadi", "isim", "ismi", "adsoyad", "unvan", "unvanı",
              "müvekkil", "kişi", "name", "surname", "danışan", "taraf"}


def csv_metni_oku(yol):
    """UTF-8 (BOM'lu ya da BOM'suz), olmazsa cp1254 (Türkçe Windows/Excel) ile okur."""
    ham = open(yol, "rb").read()
    for kod in ("utf-8-sig", "cp1254"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            continue
    return ham.decode("utf-8", errors="replace")


def _ayrac_bul(metin):
    ornek = "\n".join(metin.splitlines()[:20])
    try:
        return csv.Sniffer().sniff(ornek, delimiters=";,\t|").delimiter
    except csv.Error:
        say = {d: ornek.count(d) for d in ";,\t|"}
        return max(say, key=say.get) if any(say.values()) else ","


def csv_maskele(metin, sutunlar=None, harita=None, kurallar=VARSAYILAN_KURALLAR, haric=(), ozel_kurallar=()):
    """CSV metnini maskeler; ilk satır başlıktır ve değişmez. -> (csv_metin, harita, ayraç)
    sutunlar verilirse yalnız o sütunlar işlenir ve hücrede kural tutmazsa hücrenin TAMAMI tutarlı etiket alır
    (ad sütununda [KİŞİ-n], diğerlerinde [DEĞER-n]). Verilmezse tüm hücreler kurallarla taranır.
    Harita bir kez kurulur ve tüm hücrelerde paylaşılır (binlerce satırda da hızlı)."""
    metin = unicodedata.normalize("NFC", metin)
    ayrac = _ayrac_bul(metin)
    satirlar = list(csv.reader(io.StringIO(metin), delimiter=ayrac))
    if not satirlar:
        return metin, dict(harita or {}), ayrac
    baslik = satirlar[0]
    ozel = ozel_kural_derle(ozel_kurallar)
    H = _Harita(harita, {e for e, _ in ozel})
    kurallar = set(kurallar)
    haric_kume = {tr_lower(x.strip()) for x in haric if x.strip()}
    if sutunlar:
        istenen = {tr_lower(x.strip()) for x in sutunlar if x.strip()}
        secili = [i for i, b in enumerate(baslik) if tr_lower(b.strip()) in istenen]
        eksik = istenen - {tr_lower(baslik[i].strip()) for i in secili}
        if eksik:
            raise ValueError("başlıkta olmayan sütun: %s" % ", ".join(sorted(eksik)))
    else:
        secili = list(range(len(baslik)))
    ad_sutunu = {i: bool(set(re.split(r"[^\wçğıöşüÇĞİÖŞÜ]+", tr_lower(baslik[i]))) & _AD_SUTUNU) for i in secili}
    for satir in satirlar[1:]:
        for i in secili:
            if i >= len(satir) or not satir[i].strip():
                continue
            hucre = satir[i]
            deger = hucre.strip()
            serbest = tr_lower(deger) in haric_kume
            if sutunlar and ad_sutunu[i] and not serbest and not re.search(r"\d", deger):
                # ad sütunu: hücredeki ad bütünüyle kişi sayılır; "Ekinci, Hilal" → "Hilal Ekinci"
                parca = [x.strip() for x in deger.split(",") if x.strip()]
                ad = " ".join(reversed(parca)) if len(parca) == 2 else " ".join(parca)
                ad = " ".join(w for w in re.split(r"[\s]+", ad) if _AD_KELIME.fullmatch(w))
                if ad and ad[0].isupper():
                    if H.bul("KİŞİ", ad) is None:
                        H.ver("KİŞİ", ad)
                    if deger != ad and H.bul("KİŞİ", deger) is None:
                        H.ver("KİŞİ", deger, H.bul("KİŞİ", ad))     # hücrenin yazıldığı biçim de aynı kişi
                    H.yay()
            yeni, _ = _maskele_ic(hucre, H, kurallar, haric=haric, ozel=ozel)
            if yeni == hucre and sutunlar and not serbest:
                etiket = H.bul("DEĞER", deger) or H.ver("DEĞER", deger)
                yeni = hucre.replace(deger, "[%s]" % etiket)
            satir[i] = yeni
    cikti = io.StringIO()
    csv.writer(cikti, delimiter=ayrac, lineterminator="\n").writerows(satirlar)
    return cikti.getvalue(), dict(H.d), ayrac


XLSX_AZAMI = 50 * 2 ** 20    # açılmış sayfa/dize dosyası üst sınırı (zip bombasına karşı)


def xlsx_csv(yol, sayfa=1, ayrac=","):
    """Basit .xlsx okuyucu (yalnız stdlib zipfile): N. sayfanın hücre DEĞERLERİNİ CSV metnine çevirir.
    Biçim, formül, birleştirilmiş hücre ve tarih biçimi taşınmaz (tarih Excel seri sayısı olarak gelir)."""
    import xml.etree.ElementTree as ET
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(yol) as z:
        for bilgi in z.infolist():
            if bilgi.filename.startswith("xl/") and bilgi.file_size > XLSX_AZAMI:
                raise ValueError("%s çok büyük (%d MB > %d MB); CSV olarak kaydedip deneyin"
                                 % (bilgi.filename, bilgi.file_size // 2 ** 20, XLSX_AZAMI // 2 ** 20))
        ortak = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(ns + "si"):
                ortak.append("".join(t.text or "" for t in si.iter(ns + "t")))
        ad = "xl/worksheets/sheet%d.xml" % sayfa
        if ad not in z.namelist():
            raise ValueError("sayfa yok: %s" % ad)
        kok = ET.fromstring(z.read(ad))
    tablo = []
    for row in kok.iter(ns + "row"):
        satir = {}
        for c in row.iter(ns + "c"):
            ref, tip = c.get("r", ""), c.get("t")
            sutun = 0
            for ch in re.match(r"[A-Z]*", ref).group(0):
                sutun = sutun * 26 + ord(ch) - 64
            v = c.find(ns + "v")
            if tip == "s" and v is not None:
                deger = ortak[int(v.text)]
            elif tip == "inlineStr":
                deger = "".join(t.text or "" for t in c.iter(ns + "t"))
            elif v is not None:
                deger = v.text or ""
                if re.fullmatch(r"-?\d+\.0", deger):
                    deger = deger[:-2]
            else:
                deger = ""
            satir[max(sutun - 1, len(satir)) if sutun else len(satir)] = deger
        if satir:
            tablo.append([satir.get(i, "") for i in range(max(satir) + 1)])
    genislik = max((len(r) for r in tablo), default=0)
    cikti = io.StringIO()
    csv.writer(cikti, delimiter=ayrac, lineterminator="\n").writerows([r + [""] * (genislik - len(r)) for r in tablo])
    return cikti.getvalue()


class _YazmaHatasi(Exception):
    pass


def _gizli_yaz(yol, icerik):
    """Harita/rapor gerçek değer taşır: yalnız sahibi okuyabilir (0600)."""
    try:
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except OSError as e:
        raise _YazmaHatasi("%s yazılamadı (sembolik bağ, aygıt ya da izin): %s" % (yol, e.strerror or e))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(icerik)
    os.chmod(yol, 0o600)


def _ayni_dosya(a, b):
    """Sembolik ve sabit bağları da yakalar: ikisi de varsa samefile, yoksa gerçek yol karşılaştırılır."""
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a) == os.path.realpath(b)


def kurallari_coz(s):
    """'+esas,-plaka' ya da 'tckn,iban' -> küme."""
    if not s:
        return set(VARSAYILAN_KURALLAR)
    parca = [x.strip() for x in s.split(",") if x.strip()]
    if all(p[0] in "+-" for p in parca):
        k = set(VARSAYILAN_KURALLAR)
        for p in parca:
            (k.add if p[0] == "+" else k.discard)(p[1:])
    else:
        k = set(parca)
    bilinmeyen = {x.lstrip("+-") for x in parca} - TUM_KURALLAR
    if bilinmeyen:
        raise SystemExit("bilinmeyen kural: %s" % ", ".join(sorted(bilinmeyen)))
    return k


# ───────────────────────── öz sınama ─────────────────────────
def _gecici_dosya(ad, veri):
    import tempfile
    d = tempfile.mkdtemp(prefix="kvkk_maske_sinama_")
    yol = os.path.join(d, ad)
    with open(yol, "wb") as f:
        f.write(veri)
    return yol


def _cp1254_sinama():
    yol = _gecici_dosya("t.csv", "Ad Soyad;Şehir\nAyşe Işıkçı;Iğdır\n".encode("cp1254"))
    return csv_metni_oku(yol).startswith("Ad Soyad;Şehir\nAyşe Işıkçı")


def _xlsx_sinama(tc):
    ss = ('<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<si><t>Ad Soyad</t></si><si><t>TC</t></si><si><r><t>Okyay </t></r><r><t>Tezcanlı</t></r></si></sst>')
    sh = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
          '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="s"><v>1</v></c></row>'
          '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="C2"><v>%s</v></c></row>'
          '<row r="3"><c r="A3" t="inlineStr"><is><t>Vural Pekdemir</t></is></c></row>'
          '</sheetData></worksheet>' % tc)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", ss)
        z.writestr("xl/worksheets/sheet1.xml", sh)
    yol = _gecici_dosya("t.xlsx", buf.getvalue())
    c = xlsx_csv(yol)
    m, _, _ = csv_maskele(c, ["Ad Soyad", "TC"])
    return c.splitlines() == ["Ad Soyad,,TC", "Okyay Tezcanlı,,%s" % tc, "Vural Pekdemir,,"] \
        and m.splitlines()[1] == "[KİŞİ-1],,[TCKN-1]"


def _cli_sinama():
    import tempfile
    d = tempfile.mkdtemp(prefix="kvkk_maske_cli_")
    g = os.path.join(d, "girdi.txt")
    with open(g, "w", encoding="utf-8") as f:
        f.write("tanık Okyay Tezcanlı")
    bag = os.path.join(d, "bag.txt")
    sabit = os.path.join(d, "sabit.txt")
    try:
        os.symlink(g, bag)
    except (OSError, NotImplementedError):
        bag = g        # Windows'ta sembolik bağ izni yoksa aynı dosya yolu sınanır
    os.link(g, sabit)
    bozuk = os.path.join(d, "bozuk.json")
    with open(bozuk, "w") as f:
        f.write("{bozuk")
    bozuk_xlsx = os.path.join(d, "bozuk.xlsx")
    with open(bozuk_xlsx, "wb") as f:
        f.write(b"PK\x03\x04bozuk")
    cp = os.path.join(d, "cp.txt")
    with open(cp, "wb") as f:
        f.write("tanık Okyay Tezcanlı, Iğdır".encode("cp1254"))
    eski = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = io.StringIO()
    try:
        kodlar = [main(["--dosya", g, "--rapor", g]), main(["--dosya", g, "--rapor", bag]),
                  main(["--dosya", g, "--cikti", sabit]), main(["--dosya", g, "--harita", g]),
                  main(["--dosya", g, "--cikti", os.path.join(d, "c.txt"), "--rapor", os.path.join(d, "c.txt")]),
                  main(["--dosya", g, "--harita", bozuk]),
                  main(["--dosya", g, "--csv", g]),
                  main(["--dosya", g, "--cikti", os.path.join(d, "h.txt"), "--haric-dosya", os.path.join(d, "h.txt")]),
                  main(["--dosya", g, "--kural-dosya", g]),
                  main(["--csv", bozuk_xlsx])]
        kod_cp = main(["--dosya", cp, "--cikti", os.path.join(d, "cp_out.txt")])
    finally:
        sys.stdout, sys.stderr = eski
    with open(g, encoding="utf-8") as f:
        saglam = f.read() == "tanık Okyay Tezcanlı"
    with open(os.path.join(d, "cp_out.txt"), encoding="utf-8") as f:
        cp_ok = f.read() == "tanık [KİŞİ-1], Iğdır"
    return kodlar == [2] * 10 and saglam and kod_cp == 0 and cp_ok


def _hiz_sinama():
    import time
    r = random.Random(3)
    adlar = sorted(AD_SOZLUGU)
    soy = ["Tezcan", "Arıkan", "Pekdemir", "Selvitop", "Karaca", "Doğrusöz", "Baysal", "Ekinci", "Oralkan", "Ilgaz"]

    def kisi():
        return r.choice(adlar) + " " + r.choice(soy) + r.choice(["", "lı", "oğlu", "gil", "er"])
    satirlar = ["Ad Soyad;Telefon;TC;Not"] + ["%s;0555 0%02d %02d %02d;%s;%s ile görüştü"
                                             % (kisi(), i % 100, i % 97, i % 89, tckn_uret(r), kisi())
                                             for i in range(2000)]
    t = time.time()
    csv_maskele("\n".join(satirlar) + "\n", ["Ad Soyad", "Telefon", "TC"])
    t_csv = time.time() - t
    harf = "abcçdefgğhıijklmnoöprsştuüvyz"

    def soyad():
        return r.choice("ABCÇDEFGHIİKLMNOÖPRSŞTUÜVYZ") + "".join(r.choice(harf) for _ in range(r.randint(4, 8)))
    kotu = " ".join("tanık Ahmet %s geldi." % soyad() for _ in range(9000))[:200000]
    t = time.time()
    maskele(kotu, None, SIKI_KURALLAR)
    t_kotu = time.time() - t
    ortak_iki = " ".join("tanık Ahmet Ali %s geldi." % soyad() for _ in range(2000))
    t = time.time()
    maskele(ortak_iki)
    t_kotu = max(t_kotu, time.time() - t)
    ozel_ad = ["O'Brien", "Jean-Luc Picard", "D'Angelo", "Ayşe-Nur Demir", "Mehmet A. Öz", "Ali Rıza K."]
    on_bin = ["Ad Soyad;Telefon;Not"] + ["%s;0555 0%02d %02d %02d;not" % (
        r.choice(ozel_ad + ["%s %s" % (r.choice(adlar), soyad())]), i % 100, i % 97, i % 89) for i in range(10000)]
    t = time.time()
    csv_maskele("\n".join(on_bin) + "\n", ["Ad Soyad", "Telefon"])
    t_on_bin = time.time() - t
    yogun = " ".join("tanık %s ve %s dinlendi." % (kisi(), kisi()) for _ in range(4000))[:200000]
    t = time.time()
    maskele(yogun, None, SIKI_KURALLAR)
    t_ad = time.time() - t
    parca = ("Tanık Okyay Tezcanlı 0555 010 20 30 numarasından aradı. Çınar Mah. Lale Sok. No: 5 adresinde "
             "Vural Pekdemir adlı kişi vardı. Tutar 12.500,00 TL. " + " " * 40 + "\n")
    metin = parca * (200000 // len(parca))
    t = time.time()
    maskele(metin, None, SIKI_KURALLAR)
    t1 = time.time() - t
    t = time.time()
    maskele(" " * 100000)
    return max(t1, time.time() - t, t_csv, t_ad, t_kotu, t_on_bin)


def _oz_sinama():
    rng = random.Random(20261125)
    tc1, tc2 = tckn_uret(rng), tckn_uret(rng)
    vkn = vkn_uret(rng)
    ib = iban_uret(rng)
    ib_bosluklu = " ".join([ib[i:i + 4] for i in range(0, 26, 4)])
    tc_bozuk = tc1[:10] + str((int(tc1[10]) + 1) % 10)
    tc_ocr = tc2[:3] + "O" + tc2[4:] if tc2[3] == "0" else None
    if tc_ocr is None:
        while True:
            t = tckn_uret(rng)
            if "0" in t[1:] and "1" in t[1:]:
                break
        tc_ocr = t.replace("0", "O", 1).replace("1", "l", 1) if t[0] != "1" else t[0] + t[1:].replace("0", "O", 1)
    ES = VARSAYILAN_KURALLAR | {"esas"}

    V = []   # (ad, metin, içermeli, içermemeli, kurallar, harita)

    def v(ad, metin, var=(), yok=(), kurallar=VARSAYILAN_KURALLAR, harita=None):
        V.append((ad, metin, var, yok, kurallar, harita))

    # sayılar
    v("TCKN sağlamalı", "kimlik no %s olan" % tc1, ["[TCKN-1]"], [tc1])
    v("TCKN sağlaması tutmayan maskelenmez", "sayı %s yazıldı" % tc_bozuk, [tc_bozuk], ["[TCKN"])
    v("TCKN sağlamasız kural açıkken maskelenir", "sayı %s" % tc_bozuk, ["[TCKN-1]"], [tc_bozuk],
      VARSAYILAN_KURALLAR | {"tckn_saglamasiz"})
    v("sıkı ayar: sağlamasız 11 hane maskelenir", "evrak %s ve 01%s" % (tc_bozuk, tc_bozuk[2:]),
      ["[TCKN-1]", "[TCKN-2]"], [tc_bozuk[2:]], SIKI_KURALLAR)
    v("sıkı ayar: 11 haneli cep telefonu TEL kalır", "tel 05550102030 ara", ["[TEL-1]"], ["TCKN"], SIKI_KURALLAR)
    v("sıkı ayar: emsal künyesi ve tutar serbest", "Y. 9. HD 2018/99999 E. · 12.500,00 TL", ["2018/99999 E.", "12.500,00 TL"],
      ["["], SIKI_KURALLAR)
    v("TCKN OCR bozuk (O/l)", "T.C. no: %s" % tc_ocr, ["[TCKN-1]"], [tc_ocr])
    v("aynı TCKN iki kez aynı etiket", "%s ve yine %s" % (tc1, tc1), ["[TCKN-1] ve yine [TCKN-1]"], ["TCKN-2"])
    v("iki TCKN iki etiket", "%s, %s" % (tc1, tc2), ["[TCKN-1]", "[TCKN-2]"])
    v("VKN bağlamla", "vergi no: %s" % vkn, ["[VKN-1]"], [vkn])
    v("VKN bağlamsız 10 hane serbest", "sipariş %s kaydı" % vkn, [vkn], ["[VKN"])
    v("IBAN bitişik", "hesap %s'ye" % ib, ["[IBAN-1]'ye"], [ib])
    v("IBAN boşluklu", "IBAN: %s gönder" % ib_bosluklu, ["[IBAN-1] gönder"], [ib_bosluklu[5:15]])
    v("IBAN sağlaması bozuk serbest", "TR00 1234 5678 9012 3456 7890 12", ["TR00 1234"], ["[IBAN"])
    v("yabancı IBAN (mod-97)", "DE89 3704 0044 0532 0130 00 hesabı", ["[IBAN-1] hesabı"])
    # telefon
    v("cep 0'lı boşluklu", "tel 0555 010 20 30 ara", ["[TEL-1] ara"], ["010 20"])
    v("cep +90", "+90 555 040 50 60", ["[TEL-1]"], ["040 50"])
    v("cep bitişik", "05550708090'dan", ["[TEL-1]'dan"])
    v("sabit hat parantezli", "(0216) 999 00 01 nolu", ["[TEL-1]"], ["999 00"])
    v("sabit hat 0'lı", "0312 999 00 02 dahili", ["[TEL-1]"])
    v("sabit hat öneksiz serbest (tutar/sayı olabilir)", "kod 312 999 00 02", ["312 999"], ["[TEL"])
    # e-posta, plaka, doğum
    v("e-posta", "yaz: deneme.kisi@ornek.test bugün", ["[EPOSTA-1] bugün"], ["@ornek"])
    v("serbest e-posta listesi", "bilgi@buro.test", ["bilgi@buro.test"], [], VARSAYILAN_KURALLAR)
    v("plaka boşluklu", "34 ABC 123 plakalı araç", ["[PLAKA-1] plakalı"], ["ABC 123"])
    v("plaka tek harf", "06 K 4521 plakalı", ["[PLAKA-1]"])
    v("plaka değil: künye", "Y. 2. CD 12 HD 345 sayılı", ["HD 345"], ["[PLAKA"])
    v("plaka değil: tutar", "34 TL 500 ödendi, 12 KDV 18", ["34 TL 500"], ["[PLAKA"])
    v("doğum tarihi bağlamlı", "Doğum tarihi: 03.04.1988, İstanbul", ["[DOĞUM-TARİHİ-1]"], ["1988"])
    v("doğumlu", "1979 doğumlu sanık", ["[DOĞUM-TARİHİ-1] doğumlu"])
    v("sıradan tarih serbest", "12.03.2024 tarihli duruşma", ["12.03.2024 tarihli"], ["[DOĞUM"])
    # adres
    v("adres dizisi", "Çınar Mah. Lale Sok. No: 5 D: 3 Kadıköy/İstanbul adresinde",
      ["[ADRES-1] adresinde"], ["Lale", "Kadıköy"])
    v("tek adres izi serbest", "Cumhuriyet Mah. yakınında", ["Cumhuriyet Mah."], ["[ADRES"])
    # esas no
    v("esas no varsayılan kapalı", "Mahkemenizin 2021/905 E. sayılı dosyası", ["2021/905 E."], ["[DOSYA"])
    v("esas no açıkken maskelenir", "Mahkemenizin 2021/905 E. sayılı dosyası", ["[DOSYA-NO-1] sayılı"],
      ["2021/905"], ES)
    v("emsal künyesi serbest kalır", "Yargıtay 9. HD 2018/99999 E. 2019/99999 K. sayılı karar",
      ["2018/99999 E.", "2019/99999 K."], ["[DOSYA"], ES)
    v("harita ile verilen dosya no", "dosya 2025/412 hakkında", ["[DOSYA-NO-1]"], ["2025/412"],
      VARSAYILAN_KURALLAR, {"2025/412": None})
    # yanlış pozitif
    v("Madde 12 serbest", "TMK Madde 12 ve m. 2/1 uyarınca", ["Madde 12", "m. 2/1"], ["["])
    v("tutar serbest", "1.250.000,00 TL ve 45.000 TL", ["1.250.000,00 TL", "45.000 TL"], ["["])
    v("sıradan büyük harfli kelime serbest", "Dosya Kapsamı ve Hukuki Değerlendirme", ["Dosya Kapsamı"], ["["])
    v("küçük harfli ortak kelime serbest", "yıldız haritası ve deniz kenarı", ["yıldız", "deniz"], ["["],
      VARSAYILAN_KURALLAR, {"Deniz Yıldız": None})
    # adlar
    v("bağlam: tanık", "tanık Okyay Tezcanlı dinlendi", ["tanık [KİŞİ-1] dinlendi"], ["Okyay", "Tezcanlı"])
    v("bağlam: baba adı", "Baba adı: Rüstem, anne adı: Güllü", ["[KİŞİ-1]", "[KİŞİ-2]"], ["Rüstem", "Güllü"])
    v("bağlam: SANIK büyük harf", "SANIK : TUNÇ ALAGÖZ", ["[KİŞİ-1]"], ["ALAGÖZ"])
    v("bağlam sonra: adlı", "olay yerinde Vural Pekdemir adlı kişi vardı", ["[KİŞİ-1] adlı"], ["Pekdemir"])
    v("sözlük adı + soyad", "toplantıya Zeynep Arıkanlı katıldı", ["[KİŞİ-1] katıldı"], ["Arıkanlı"])
    v("soyad yayılır", "Zeynep Arıkanlı geldi. Arıkanlı ayrıca", ["[KİŞİ-1] ayrıca"], ["Arıkanlı"])
    v("kesmeli ek", "Ahmet Doğrusöz'ün beyanı", ["[KİŞİ-1]'ün"], ["Doğrusöz"])
    v("büyük harf + kesmeli ek AHMET'İN", "AHMET'İN dilekçesi", ["[KİŞİ-1]'İN"], ["AHMET"],
      VARSAYILAN_KURALLAR, {"Ahmet Doğrusöz": None})
    v("YİĞİT (Türkçe büyük harf)", "YİĞİT KARACA hazır", ["[KİŞİ-1] hazır"], ["YİĞİT", "YIĞIT", "KARACA"],
      VARSAYILAN_KURALLAR, {"Yiğit Karaca": None})
    v("kesmesiz ek", "Karacanın aracı", ["[KİŞİ-1]'nın"], ["Karacanın"], VARSAYILAN_KURALLAR, {"Yiğit Karaca": None})
    v("harita etiketi kullanılır", "Selin Oralkan dava açtı", ["[DAVACI] dava"], ["Oralkan"],
      VARSAYILAN_KURALLAR, {"Selin Oralkan": "DAVACI"})
    v("Av. meslektaş adı korunur", "Av. Mehmet Tarlakaya geldi", ["Av. Mehmet Tarlakaya"], ["[KİŞİ"])
    v("Av. istisnası kapatılabilir", "Av. Mehmet Tarlakaya geldi", ["[KİŞİ-1]"], ["Tarlakaya"],
      VARSAYILAN_KURALLAR - {"av_istisna"})
    v("kurum adı kişi sayılmaz", "Mehmet Akif Ersoy Üniversitesi rektörlüğü", ["Mehmet Akif Ersoy"], ["[KİŞİ"])
    v("ilçe/il kişi sayılmaz", "Fatih/İSTANBUL adresinde", ["Fatih/İSTANBUL"], ["[KİŞİ"])
    v("davacı vekili Av. serbest", "Davacı vekili Av. Kemal Sözer", ["Av. Kemal Sözer"], ["[KİŞİ"])
    v("tek soyad önceki tam ada bağlanır", "Sanık Selvitop ve SANIK : KORAY SELVİTOP", ["Sanık [KİŞİ-1] ve"],
      ["KİŞİ-2", "Selvitop"])
    for yp in ("Davalı Şirket'in itirazı", "Davalı Banka cevap verdi", "Sayın Bilirkişi raporunda",
               "TANIK BEYANLARI incelendi", "DAVACI TARAF bildirdi", "Müvekkil Şirket'in kaydı"):
        v("rol + ortak isim kişi sayılmaz: " + yp, yp, [yp.split()[1]], ["[KİŞİ"])
    v("iki kişi ayrı etiket", "müşteki Hilal Ekinci ile şüpheli Doruk Baysal", ["[KİŞİ-1]", "[KİŞİ-2]"],
      ["Ekinci", "Baysal"])

    gecti, toplam, hatalar = 0, 0, []
    for ad, metin, var, yok, kurallar, harita in V:
        toplam += 1
        out, _, _ = maskele(metin, harita, kurallar, serbest_epostalar=("bilgi@buro.test",))
        hata = [x for x in var if x not in out] + ["(kalmamalı) " + x for x in yok if x in out]
        if hata:
            hatalar.append("%s\n    girdi: %s\n    çıktı: %s\n    eksik: %s" % (ad, metin, out, hata))
        else:
            gecti += 1

    def ozel(ad, kosul):
        nonlocal gecti, toplam
        toplam += 1
        if kosul:
            gecti += 1
        else:
            hatalar.append(ad)

    ozel("tr_upper Yiğit -> YİĞİT", tr_upper("Yiğit") == "YİĞİT")
    ozel("tr_lower IŞIK -> ışık", tr_lower("IŞIK") == "ışık")
    ozel("tr_lower uzunluk korur", len(tr_lower("İİİ")) == 3)
    ozel("üretilen numaralar geçerli", tckn_gecerli(tc1) and vkn_gecerli(vkn) and iban_gecerli(ib))
    ornek = ("tanık Okyay Tezcanlı (%s) 0555 010 20 30 numaralı telefondan, Çınar Mah. Lale Sok. No: 5 "
             "adresinden aradı. Tezcanlı'nın e-postası ok.tz@ornek.test" % tc1)
    m1, h1, b1 = maskele(ornek)
    m2, h2, b2 = maskele(m1)
    ozel("idempotent: ikinci geçiş değiştirmez", m2 == m1)
    ozel("bulgu raporunda ham değer yok", all(tc1 not in json.dumps(b, ensure_ascii=False) for b in b1))
    m3, h3, _ = maskele("ikinci belge: Okyay Tezcanlı ve şüpheli Doruk Baysal", h1)
    ozel("harita devri: aynı kişi aynı etiket", "[KİŞİ-1]" in m3 and "[KİŞİ-2]" in m3)
    ikinci = "e-posta ok.tz@ornek.test, %s; Cumhuriyet Mah. Şirinler Sok. No: 4; 1991 doğumlu" % ib_bosluklu
    n1, hk, _ = maskele(ikinci)
    hk = json.loads(json.dumps(hk, ensure_ascii=False))      # dosyaya yazılıp okunmuş gibi
    n2, hk2, _ = maskele(ikinci + "\nCumhuriyet Bayramı 12.03.1991 tarihinde", hk)
    ozel("kayıtlı harita: e-posta/IBAN/adres aynı etiket", n2.split("\n")[0] == n1)
    ozel("kayıtlı harita: adres parçası kişi sayılmaz", "Cumhuriyet Bayramı" in n2)
    ozel("kayıtlı harita: doğum yılı başka tarihe yayılmaz", "12.03.1991" in n2)
    ozel("kayıtlı harita: geri dönüş", geri_al(n2, hk2).split("\n")[0] == ikinci)
    ozel("geri dönüş", geri_al(m1, h1) == ornek.replace("Tezcanlı'nın", "Okyay Tezcanlı'nın"))
    ozel("boş metin", maskele("")[0] == "")
    # başka karaktere yapışık yazılmış numaralar
    for on, arka in (("TC", ""), ("T.C.", ""), ("no,", ""), ("x/", ""), ("", "/2"), ("", ".5"), ("A", "b")):
        for kur in (VARSAYILAN_KURALLAR, SIKI_KURALLAR):
            ozel("yapışık TCKN %r…%r" % (on, arka), tc1 not in maskele("%s%s%s" % (on, tc1, arka), None, kur)[0])
    for on in ("tel.", "gsm,", "A", "dosya/", "tel:"):
        ozel("yapışık telefon %r (sıkı)" % on, "0102030" not in maskele(on + "05550102030", None, SIKI_KURALLAR)[0])
    ozel("harfe yapışık IBAN", ib not in maskele("x" + ib + "abc")[0] and ib not in maskele("IBAN:" + ib)[0])
    # S-4: metinde önceden olan etiketle çakışma yok
    mt, _, _ = maskele("[KİŞİ-1] daha önce maskelenmişti; tanık Okyay Tezcanlı geldi")
    ozel("önceden var olan [KİŞİ-1] ile yeni etiket çakışmaz", "[KİŞİ-2] geldi" in mt)
    ozel("CLI: girdi/çıktı/harita/rapor çakışması ve bozuk harita çıkış 2", _cli_sinama())
    # v1.2 hariç listesi
    mh, _, _ = maskele("Müvekkil Şirket Örnek Yazılım A.Ş. ile tanık Ali Veli ve tanık Okyay Tezcanlı görüştü",
                       haric=["Ali Veli", "örnek yazılım a.ş."])
    ozel("hariç: listedeki ad ve unvan kalır, diğeri maskelenir", "Ali Veli" in mh and "Örnek Yazılım A.Ş." in mh
         and "Tezcanlı" not in mh)
    ozel("hariç: numara da serbest bırakılabilir", "0555 010 20 30" in maskele("tel 0555 010 20 30",
                                                                               haric=["0555 010 20 30"])[0])
    # hariç listesi kendisinden uzun veriyi serbest bırakmaz
    for har, gir, kalmamali in ((["0"], "tel 0555 010 20 30 ve %s" % ib, ["010 20", ib]),
                                (["Lale", "No"], "Çınar Mah. Lale Sok. No: 5 Kadıköy/İstanbul", ["Lale Sok"]),
                                (["Tezcanlı"], "tanık Okyay Tezcanlı geldi", ["Okyay"]),
                                (["5"], "TC %s" % tc1, [tc1]), (["a"], "e-posta ok.tz@ornek.test", ["ok.tz@"])):
        ozel("hariç %r daha uzun veriyi açmaz" % har, all(x not in maskele(gir, haric=har)[0] for x in kalmamali))
    mo3, _, _ = maskele("TC %s yılı 1987" % tc1, ozel_kurallar=[("YIL", r"(?:19|20)\d{2}")])
    ozel("özel kural TCKN'yi bölmez", "[TCKN-1]" in mo3 and "[YIL-1]" in mo3 and tc1 not in mo3)
    ozel("özel kural her şeyi kapsasa da hazır etiket korunur", "[TCKN-1]" in
         maskele("TC %s" % tc1, ozel_kurallar=[("HEPSI", r".+")])[0] or tc1 not in maskele("TC %s" % tc1,
         ozel_kurallar=[("HEPSI", r".+")])[0])
    # ek yazım biçimleri
    tcb = tc2
    for ad_, yaz in (("boşluklu TCKN", "%s %s %s %s" % (tc1[:3], tc1[3:6], tc1[6:9], tc1[9:])),
                     ("tireli TCKN", "%s-%s-%s" % (tc1[:3], tc1[3:6], tc1[6:])), ("bitişik iki TCKN", tc1 + tcb),
                     ("küçük harf tr IBAN", ib.lower()), ("tireli IBAN", "-".join(ib[k:k + 4] for k in range(0, 26, 4))),
                     ("çift boşluklu IBAN", "  ".join(ib[k:k + 4] for k in range(0, 26, 4))),
                     ("90555 telefon", "905550102030"), ("0(555) telefon", "0(555) 010 20 30"),
                     ("0555 01 02 030 telefon", "0555 01 02 030")):
        cikti_ = maskele("x " + yaz + " y", None, SIKI_KURALLAR)[0]
        ozel("yazım: %s" % ad_, cikti_.startswith("x [") and not re.search(r"\d{2}", cikti_.replace("-1]", "").replace("-2]", "")))
    # harf dışı karakter taşıyan adlar (nokta, kesme, tire)
    for har, gir, beklenen in ((["Mehmet A. Öz"], "Mehmet A. Öz geldi, MEHMET A. ÖZ'ün; Mehmet A.Öz", "[KİŞİ-1] geldi, [KİŞİ-1]'ün; [KİŞİ-1]"),
                               (["Ali Rıza K."], "Ali Rıza K. dedi ki", "[KİŞİ-1] dedi ki"),
                               (["O'Brien"], "O'Brien ve O’Brien'in", "[KİŞİ-1] ve [KİŞİ-1]'in"),
                               (["Jean-Luc Picard"], "Jean-Luc Picard ve Jean-Luc", "[KİŞİ-1] ve [KİŞİ-1]"),
                               (["Ayşe-Nur Demir"], "Ayşe-Nur Demir'e", "[KİŞİ-1]'e")):
        ozel("harf dışı karakterli ad: %s" % har[0], maskele(gir, har)[0] == beklenen)
    c5, _, _ = csv_maskele("Ad Soyad;x\nD'Angelo;1\nAyşe-Nur Demir;2\nAhmet Kaya (vekil);3\n", ["Ad Soyad"])
    ozel("CSV: D'Angelo, Ayşe-Nur ve parantezli hücre bütünüyle maskelenir",
         c5.splitlines()[1:] == ["[KİŞİ-1];1", "[KİŞİ-2];2", "[KİŞİ-3];3"])
    # ayrışık (NFD) Unicode
    import unicodedata as _ud
    nfd = _ud.normalize("NFD", "tanık Gökçe Özgüleş ve tanık Şükrü Çağlayan'ın")
    mn, hn, _ = maskele(nfd)
    ozel("NFD yazılmış ad maskelenir", mn == "tanık [KİŞİ-1] ve tanık [KİŞİ-2]'ın")
    ozel("NFD: geri dönüş NFC verir", geri_al(mn, hn) == _ud.normalize("NFC", nfd))
    # noktalı / eğik çizgili / yapışık ek biçimler
    tc_o = tc1.replace("0", "O", 1) if "0" in tc1[1:] else None
    for ad_, yaz in (("noktalı TCKN", "%s.%s.%s.%s" % (tc1[:3], tc1[3:6], tc1[6:9], tc1[9:])),
                     ("noktalı IBAN", ".".join(ib[k:k + 4] for k in range(0, 26, 4))),
                     ("0555/010 20 30", "0555/010 20 30"), ("05 55 01 02 03 0", "05 55 01 02 03 0")):
        ozel("yazım: %s" % ad_, maskele("x " + yaz + " y", None, SIKI_KURALLAR)[0].startswith("x ["))
    for ad_, yaz in (("plaka.34 ABC 123", "plaka.34 ABC 123"), ("x/34 ABC 123", "x/34 ABC 123")):
        ozel("yazım: %s" % ad_, "[PLAKA-1]" in maskele(yaz)[0])
    if tc_o:
        ozel("yapışık OCR-bozuk TCKN", "[TCKN-1]" in maskele("TC" + tc_o)[0])
    for serbest in ("12.345.678.901 TL", "1.234.567,89 TL", "05.12.2024 10:30", "12.03.2024 tarihli",
                    "Y. 9. HD 2018/99999 E. 2019/99999 K.", "34 TL 500", "Madde 34 ve 12"):
        ozel("yanlış pozitif yok: %s" % serbest, maskele(serbest, None, SIKI_KURALLAR)[0] == serbest)
    ozel("şüpheli: satır sonunda bölünmüş numara listelenir",
         any(x["tur"] == "satır sonunda bölünmüş rakam dizisi" for x in supheli_izler("TC no 1234\n5678901 olan")))
    # tireli ad ve çift soyad; tire/boşluk yazım farkı; yabancı adın ASCII büyük yazımı
    for gir, har, beklenen in (("tanık Ayşe-Nur Kaya geldi", None, "tanık [KİŞİ-1] geldi"),
                               ("tanık Zeynep Arıkanlı-Kaya geldi", None, "tanık [KİŞİ-1] geldi"),
                               ("toplantıya Zeynep Arıkanlı-Kaya katıldı", None, "toplantıya [KİŞİ-1] katıldı"),
                               ("davacı - Hilal Ekinci dedi", None, "davacı - [KİŞİ-1] dedi"),
                               ("Ayşe Nur Kaya ve Ayşe-Nur Kaya", ["Ayşe-Nur Kaya"], "[KİŞİ-1] ve [KİŞİ-1]"),
                               ("Ayşe-Nur Kaya ve Ayşe Nur Kaya", ["Ayşe Nur Kaya"], "[KİŞİ-1] ve [KİŞİ-1]"),
                               ("O'BRIEN ve Mario ROSSI", ["O'Brien", "Mario Rossi"], "[KİŞİ-1] ve [KİŞİ-2]"),
                               ("Ankara-İstanbul hattı 2024-2025 döneminde", None, "Ankara-İstanbul hattı 2024-2025 döneminde")):
        ozel("tire/yazım: %s" % gir, maskele(gir, har)[0] == beklenen)
    for gir, beklenen in (("tanık Hilal Ekinci-Kadıköy/İstanbul", "tanık [KİŞİ-1]-Kadıköy/İstanbul"),
                          ("tanık Hilal Ekinci-Atatürk Caddesi No: 5", "tanık [KİŞİ-1]-"),
                          ("toplantıya Zeynep Arıkanlı-Ankara Üniversitesi katıldı", "toplantıya [KİŞİ-1]-Ankara Üniversitesi"),
                          ("toplantıya Zeynep Arıkanlı-Kadıköy Belediyesi katıldı", "toplantıya [KİŞİ-1]-Kadıköy Belediyesi"),
                          ("toplantıya Zeynep Arıkanlı-Holding toplantısı", "toplantıya [KİŞİ-1]-Holding"),
                          ("tanık Hilal Ekinci-İstanbul doğumlu", "tanık [KİŞİ-1]-İstanbul doğumlu"),
                          ("Fatih-İstanbul adresinde", "Fatih-İstanbul adresinde")):
        ozel("ad-yer tireli yazım: %s" % gir, maskele(gir)[0].startswith(beklenen))
    ozel("ad-yer: yer adı haritaya kişi diye girmez",
         not any("İstanbul" in k or "Kadıköy" in k for k in maskele("tanık Hilal Ekinci-İstanbul doğumlu")[1]))
    ibg = " ".join(ib[k:k + 4] for k in range(0, 26, 4))
    ozel("\\r\\n ile bölünmüş IBAN da bütün maskelenir",
         maskele("IBAN: %s\r\n%s gönderildi" % (ibg[:14], ibg[15:]), None, SIKI_KURALLAR)[0] == "IBAN: [IBAN-1] gönderildi")
    mb = maskele("IBAN: %s\n\n%s gönderildi" % (ibg[:14], ibg[15:]), None, SIKI_KURALLAR)[0]
    ozel("boş satırla bölünmüş IBAN: yarım maske yok, kalan kısım şüpheli listesinde",
         "[" not in mb and any(x["tur"].startswith("uzun rakam") for x in supheli_izler(mb)))
    mi = maskele("IBAN: %s\n%s gönderildi" % (ibg[:14], ibg[15:]), None, SIKI_KURALLAR)[0]
    ozel("satır sonunda bölünmüş IBAN bütünüyle maskelenir (yarım maske yok)",
         mi == "IBAN: [IBAN-1] gönderildi")
    # CSV: "Soyad, Ad" hücresi
    c4, _, _ = csv_maskele("Ad Soyad;Not\nEkinci, Hilal;x\n", ["Ad Soyad"])
    ozel("CSV: 'Ekinci, Hilal' hücresinde soyad da maskelenir", "Ekinci" not in c4 and "Hilal" not in c4)
    # xlsx boyut sınırı
    global XLSX_AZAMI
    eski_azami, XLSX_AZAMI = XLSX_AZAMI, 50
    try:
        try:
            _xlsx_sinama(tc1); sinir = False
        except ValueError:
            sinir = True
    finally:
        XLSX_AZAMI = eski_azami
    ozel("XLSX: boyut sınırı aşılınca ValueError", sinir)
    # v1.2 özel kural
    mo, ho, _ = maskele("Fatura FTR-123456 ve FTR-123456, sonra FTR-654321.", ozel_kurallar=[("FATURA", r"FTR-\d{6}")])
    ozel("özel kural: tutarlı etiket", mo == "Fatura [FATURA-1] ve [FATURA-1], sonra [FATURA-2].")
    mo2, _, _ = maskele("yine FTR-654321 ve FTR-777777", ho, ozel_kurallar=[("FATURA", r"FTR-\d{6}")])
    ozel("özel kural: kayıtlı haritayla numara sürer", mo2 == "yine [FATURA-2] ve [FATURA-3]")
    ozel("özel kural: geri dönüş", geri_al(mo, ho) == "Fatura FTR-123456 ve FTR-123456, sonra FTR-654321.")
    for kotu in ((("FATURA", "FTR-(\\d")), (("fatura", "x"),), (("KİŞİ", "x"),)):
        try:
            ozel_kural_derle(kotu if isinstance(kotu[0], tuple) else [kotu]); oldu = False
        except ValueError:
            oldu = True
        ozel("özel kural: hatalı girdi anlaşılır hata %r" % (kotu,), oldu)
    # v1.2 şüpheli izler
    sm, _, _ = maskele("Görüşmeye Doruk Baysal da katıldı. Not: 1234567890 ve x@y Cumhuriyet Mah. yakını")
    sz = supheli_izler(sm)
    turler = {x["tur"] for x in sz}
    ozel("şüpheli: ad benzeri, rakam, @, tek adres izi listelenir", {"ad benzeri iki kelime (sözlükte yok)",
         "rakam dizisi (10-11 hane / telefon biçimi)", "@ içeren kelime", "tek adres izi"} <= turler)
    ozel("şüpheli: değer göstermez", all("Baysal" not in x["onizleme"] and "1234567890" not in x["onizleme"] for x in sz))
    ozel("şüpheli: temiz maskeli metinde yanlış alarm yok",
         supheli_izler(maskele("Tanık Okyay Tezcanlı 0555 010 20 30 aradı. Dosya Kapsamı incelendi.")[0]) == [])
    # ek koruma vitrini: iyelik, yönelme, bulunma, ayrılma, büyük harf, kıvrık kesme
    hk = {"Ahmet Doğrusöz": None}
    for girdi_, beklenen in (("Ahmet'in dosyası", "[KİŞİ-1]'in"), ("Doğrusöz'e yazıldı", "[KİŞİ-1]'e"),
                             ("Doğrusöz'de kaldı", "[KİŞİ-1]'de"), ("Doğrusöz'den alındı", "[KİŞİ-1]'den"),
                             ("DOĞRUSÖZ'DEN ALINDI", "[KİŞİ-1]'DEN"), ("AHMET DOĞRUSÖZ'ÜN", "[KİŞİ-1]'ÜN"),
                             ("Doğrusöz’ün (kıvrık kesme)", "[KİŞİ-1]’ün"), ("Doğrusözden kesmesiz", "[KİŞİ-1]'den")):
        ozel("ek koruma: %s" % girdi_, beklenen in maskele(girdi_, hk)[0])
    esik = float(os.environ.get("KVKK_MASKE_HIZ_ESIK", "10"))
    ozel("hız: 200 KB karışık / ad yoğun / aynı ad + farklı soyad / aynı ilk iki ad, 2.000 ve 10.000 satır CSV — her biri %g sn altında"
         % esik, _hiz_sinama() < esik)
    # yapay zekâ akışı: maskele -> (model cevabı taklidi) -> geri çevir
    soru = "Tanık Okyay Tezcanlı 0555 010 20 30 numarasından Doruk'u aradı mı? Tezcanlı'nın beyanını özetle."
    ms, hs, _ = maskele(soru, None, SIKI_KURALLAR)
    cevap = ("[KİŞİ-1]'in beyanına göre [TEL-1] numarasından arama yapılmıştır. [Kişi-1] bunu ikinci "
             "ifadesinde de tekrarlamıştır.")
    geri = geri_al(cevap, hs)
    ozel("YZ akışı: cevaptaki etiket ve bozuk büyük/küçük harfli etiket geri çevrilir",
         geri == ("Okyay Tezcanlı'in beyanına göre 0555 010 20 30 numarasından arama yapılmıştır. Okyay Tezcanlı "
                  "bunu ikinci ifadesinde de tekrarlamıştır.") and "[TEL-1]" in ms)
    bozuk = geri_al("KİŞİ-1 ve [KİŞİ-9] aradı", hs)
    ozel("YZ akışı: parantezi düşmüş / haritada olmayan etiket uyarı verir", len(bozuk_etiketler(bozuk, hs)) == 2)
    ozel("YZ akışı: temiz cevapta uyarı yok", bozuk_etiketler(geri, hs) == [])
    ozel("YZ talimatı etiketi aynen koru der", "HARFİ HARFİNE" in YZ_TALIMATI)
    # CSV
    tcx = tckn_uret(rng)
    csv1 = "Ad Soyad;Telefon;TC;Not\nOkyay Tezcanlı;0555 010 20 30;%s;arandı\nVural Pekdemir;0555 010 40 50;;Okyay Tezcanlı ile\n" \
        "Okyay Tezcanlı;0555 010 20 30;;tekrar\n" % tcx
    c1, ch, ay = csv_maskele(csv1, ["Ad Soyad", "Telefon"])
    s1 = c1.splitlines()
    ozel("CSV: ayraç ';' algılandı, başlık korundu", ay == ";" and s1[0] == "Ad Soyad;Telefon;TC;Not")
    ozel("CSV: seçili sütun tutarlı etiket (aynı kişi aynı etiket)", s1[1].split(";")[:2] == ["[KİŞİ-1]", "[TEL-1]"]
         and s1[3].split(";")[:2] == ["[KİŞİ-1]", "[TEL-1]"] and s1[2].split(";")[0] == "[KİŞİ-2]")
    ozel("CSV: seçilmeyen sütun dokunulmadan kalır", tcx in c1 and "Okyay Tezcanlı ile" in c1)
    c2, _, _ = csv_maskele(csv1)
    ozel("CSV: sütun verilmezse tüm hücreler taranır", tcx not in c2 and "[TCKN-1]" in c2)
    c3, _, ay3 = csv_maskele('Müşteri,Şehir\n"Bilgin, Ayşe",Kadıköy\n', ["Şehir"])
    ozel("CSV: virgül ayraç + tırnaklı hücre + DEĞER etiketi", ay3 == "," and "[DEĞER-1]" in c3 and '"Bilgin, Ayşe"' in c3)
    ozel("CSV: geri dönüş", geri_al(c1, ch) == csv1)
    try:
        csv_maskele(csv1, ["Yok Sütun"]); hata_var = False
    except ValueError:
        hata_var = True
    ozel("CSV: başlıkta olmayan sütun hata verir", hata_var)
    ozel("CSV: cp1254 kodlu dosya okunur", _cp1254_sinama())
    ozel("XLSX: zipfile ile okunur (ortak dize, sayı, satır içi dize, boş hücre)", _xlsx_sinama(tcx))
    ozel("uyarı: sağlamasız 11 hane bulguya düşer",
         any(b["tur"] == "UYARI-11-HANE" for b in maskele("no %s" % tc_bozuk)[2]))

    for h in hatalar:
        print("  ✗ " + h)
    print("kvkk_maske öz sınama: %d/%d geçti" % (gecti, toplam))
    return 0 if gecti == toplam else 1


# ───────────────────────── komut satırı ─────────────────────────
def main(argv=None):
    try:
        return _main(argv)
    except _YazmaHatasi as e:
        print("hata: %s" % e, file=sys.stderr)
        return 2


def _main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Türkçe metinde kişisel veri maskeleme (yerel, ağsız).")
    p.add_argument("--dosya", help="girdi dosyası (yoksa standart girdi)")
    p.add_argument("--cikti", help="maskeli çıktı dosyası (yoksa standart çıktı); girdi dosyasının üstüne yazılmaz")
    p.add_argument("--harita", help="harita JSON: varsa okunur, sonra güncellenip yazılır (0600)")
    p.add_argument("--rapor", help="bulgu raporu JSON (ham değer içermez; 0600)")
    p.add_argument("--kurallar", help="ör. '+esas,-plaka' ya da 'tckn,iban,ad'")
    p.add_argument("--geri", action="store_true", help="haritayla maskeyi geri al")
    p.add_argument("--csv", help="CSV dosyası (ayraç ve kodlama kendiliğinden; .xlsx de olur: ilk sayfa okunur)")
    p.add_argument("--sutun", help="CSV'de yalnız bu sütunlar: 'Ad Soyad,Telefon' (yoksa tüm hücreler taranır)")
    p.add_argument("--haric", help="hiç maskelenmeyecek ifadeler: 'Ali Veli,Proje Örnek'")
    p.add_argument("--haric-dosya", help="hariç ifadeler dosyası (satır başına bir ifade)")
    p.add_argument("--kural-dosya", help="özel kurallar: her satır ETİKET<TAB>regex (ör. FATURA<TAB>FTR-\\d{6})")
    p.add_argument("--supheli", action="store_true", help="maskeden sonra kalan şüpheli izleri standart hataya yaz")
    p.add_argument("--yz", action="store_true", help="maskeli metnin başına yapay zekâya 'etiketi aynen koru' talimatı ekle")
    p.add_argument("--test", action="store_true", help="öz sınama (uydurma örneklerle)")
    a = p.parse_args(argv)
    if a.test:
        return _oz_sinama()
    if a.csv and a.dosya:
        print("hata: --csv ile --dosya birlikte verilemez", file=sys.stderr)
        return 2
    girdi = a.csv or a.dosya
    yollar = [("girdi", girdi), ("--cikti", a.cikti), ("--harita", a.harita), ("--rapor", a.rapor),
              ("--haric-dosya", a.haric_dosya), ("--kural-dosya", a.kural_dosya)]
    for i in range(len(yollar)):
        for j in range(i + 1, len(yollar)):
            if yollar[i][1] and yollar[j][1] and _ayni_dosya(yollar[i][1], yollar[j][1]):
                print("hata: %s ile %s aynı dosya olamaz (üzerine yazılırdı)" % (yollar[i][0], yollar[j][0]),
                      file=sys.stderr)
                return 2
    harita = None
    if a.harita and os.path.exists(a.harita):
        try:
            with open(a.harita, encoding="utf-8") as f:
                harita = json.load(f).get("harita", {})
            if not isinstance(harita, dict):
                raise ValueError("'harita' bir sözlük değil")
        except (ValueError, OSError, AttributeError) as e:
            print("hata: harita dosyası okunamadı (%s): %s" % (a.harita, e), file=sys.stderr)
            return 2
    haric = [x.strip() for x in (a.haric or "").split(",") if x.strip()]
    try:
        if a.haric_dosya:
            haric += haric_dosyasi(a.haric_dosya)
        ozel = ozel_kural_dosyasi(a.kural_dosya) if a.kural_dosya else []
    except (ValueError, OSError) as e:
        print("hata: %s" % e, file=sys.stderr)
        return 2
    secenek = {"haric": haric, "ozel_kurallar": ozel}
    try:
        if a.csv:
            ham = xlsx_csv(a.csv) if a.csv.lower().endswith(".xlsx") else csv_metni_oku(a.csv)
        else:
            ham = csv_metni_oku(a.dosya) if a.dosya else sys.stdin.read()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
        print("hata: girdi okunamadı (%s): %s" % (girdi or "stdin", e), file=sys.stderr)
        return 2
    except Exception as e:      # bozuk xlsx içindeki XML vb.
        print("hata: girdi okunamadı (%s): %s" % (girdi or "stdin", e.__class__.__name__), file=sys.stderr)
        return 2
    if a.csv and not a.geri:
        sutunlar = a.sutun.split(",") if a.sutun else None
        try:
            out, harita, _ = csv_maskele(ham, sutunlar, harita, kurallari_coz(a.kurallar), **secenek)
        except ValueError as e:
            print("hata: %s" % e, file=sys.stderr)
            return 2
        bulgular = []
        if a.harita:
            _gizli_yaz(a.harita, json.dumps({"surum": SURUM, "harita": harita}, ensure_ascii=False, indent=1))
    elif a.geri:
        metin = ham
        if not harita:
            print("hata: --geri için --harita gerekli", file=sys.stderr)
            return 2
        out, bulgular = geri_al(metin, harita), []
        for _, iz in bozuk_etiketler(out, harita)[:10]:
            print("uyarı: geri çevrilemeyen etiket izi: %s" % iz, file=sys.stderr)
    else:
        metin = ham
        out, harita, bulgular = maskele(metin, harita, kurallari_coz(a.kurallar), **secenek)
        if a.harita:
            _gizli_yaz(a.harita, json.dumps({"surum": SURUM, "harita": harita}, ensure_ascii=False, indent=1))
        if a.yz:
            out = YZ_TALIMATI + out
    supheli = supheli_izler(out) if not a.geri else []
    if a.supheli:
        for x in supheli:
            print("şüpheli (satır %d): %s · %s" % (x["satir"], x["tur"], x["onizleme"]), file=sys.stderr)
        if not supheli:
            print("şüpheli iz bulunmadı (bu, kaçırma olmadığı anlamına gelmez)", file=sys.stderr)
    if a.rapor:
        ozet = {}
        for b in bulgular:
            ozet[b["tur"]] = ozet.get(b["tur"], 0) + 1
        _gizli_yaz(a.rapor, json.dumps({"surum": SURUM, "ozet": ozet, "bulgular": bulgular, "supheli": supheli},
                                       ensure_ascii=False, indent=1))
    if a.cikti:
        with open(a.cikti, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
