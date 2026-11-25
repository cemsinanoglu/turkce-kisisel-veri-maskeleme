[English](README.md) · **Türkçe**

# turkce-kisisel-veri-maskeleme

[![Lisans: MIT](https://img.shields.io/badge/Lisans-MIT-blue.svg)](LICENSE)
[![Sınamalar](https://github.com/cemsinanoglu/turkce-kisisel-veri-maskeleme/actions/workflows/test.yml/badge.svg)](https://github.com/cemsinanoglu/turkce-kisisel-veri-maskeleme/actions/workflows/test.yml)

**Türkçe metindeki kişisel verileri (TC kimlik ve vergi no, IBAN, telefon, adres, kişi adı) kendi bilgisayarınızda maskeler. Hiçbir yere bir şey gönderilmez.**

Avukat, muhasebeci, İK çalışanı, geliştirici ve bir belgeyi yapay zekâya sormak isteyen ama gerçek ad ve numaraları yapıştırmak istemeyen herkes için.

Yazar: Av. Cem Sinanoğlu · Saf Python 3.9+, yalnız standart kütüphane, ağ erişimi yok.

> Bu araç **takma adlandırma (pseudonymization) yapar, anonimleştirme yapmaz** ve **bir uyum belgesi değildir**. Harita dosyası maskeyi geri açabildiği için kendisi de kişisel veridir. Maskeli metin bilgisayarınızdan çıkmadan önce bir insan tarafından okunmalıdır.

## Neye ihtiyacınız var

- **Python 3.9 veya üstü.** Hesap, API anahtarı ya da internet bağlantısı gerekmez; ek paket kurulmaz.
  - **macOS:** Terminal'i açıp `python3 --version` yazın. Python yoksa macOS geliştirici araçlarını kurmayı önerir; "Yükle" deyin.
  - **Windows:** Python'u [python.org](https://www.python.org/downloads/) adresinden kurun ve kurulumda "Add python.exe to PATH" kutusunu işaretleyin. Aşağıdaki komutlarda `python3` yerine `py` yazın. Türkçe harflerin bozulmaması için PowerShell'de önce `$env:PYTHONUTF8=1` çalıştırın.
  - **Linux:** Python çoğu dağıtımda kuruludur.
- `pip install git+…` komutu **Git** ister. Git yoksa kurulum yapmadan da kullanabilirsiniz: bu sayfada **Code → Download ZIP** ile indirin, klasörü açın, `python3 kvkk_maske.py --dosya metin.txt` çalıştırın. Tek dosya yeter.
- Kurulumdan sonra `turkce-maske` komutu bulunamazsa (Python'un komut klasörü PATH'te değilse) aynı işi `python3 -m kvkk_maske` yapar.

## Hangi yapay zekâyla çalışır

Araç hiçbir yapay zekâya bağlanmaz; yalnız metni hazırlar ve cevabı geri çevirir. Bu yüzden hepsinde aynı çalışır.

- **ChatGPT, Claude, Grok, Gemini, Copilot gibi bulut hizmetleri:** Maskeli metni hangisine yapıştırırsanız ona verin, cevabı `--geri` ile çevirin. Ayar ya da anahtar gerekmez. Asıl yarar buradadır: gerçek ad ve numaralar hizmetin sunucusuna hiç gitmez.
- **Bilgisayarınızda çalışan yerel modeller (Ollama, LM Studio vb.):** Araç burada da çalışır, ama metin zaten bilgisayardan çıkmadığı için gereği azalır. Model sohbet kaydı tutuyorsa ya da çıktı başkasıyla paylaşılacaksa yine yararlıdır.

## Kod asistanıyla kurulum

Claude Code, Cursor, Copilot ya da Codex gibi bir kod asistanı kullanıyorsanız şunu yazmanız yeter:

> github.com/cemsinanoglu/turkce-kisisel-veri-maskeleme deposunu kur, AGENTS.md dosyasını oku ve metin.txt dosyasını maskele.

Asistanlar için kurulum, doğrulama, komutlar ve uyulacak kurallar [AGENTS.md](AGENTS.md) dosyasındadır.

## 30 saniyede başlangıç

```bash
python3 -m pip install git+https://github.com/cemsinanoglu/turkce-kisisel-veri-maskeleme
echo "Tanık Okyay Tezcanlı'ya göre müvekkil Ahmet Doğrusöz'den 0555 010 20 30 numarasıyla arandı." | turkce-maske
```

```text
Tanık [KİŞİ-1]'ya göre müvekkil [KİŞİ-2]'den [TEL-1] numarasıyla arandı.
```

Türkçe ekler etiketin arkasında kalır (`Doğrusöz'den` → `[KİŞİ-2]'den`), cümle bozulmaz. Aynı kişi her yerde aynı etiketi alır. `Yargıtay 9. HD 2018/99999 E.` gibi karar künyelerine dokunulmaz.

Bu belgedeki ad, numara ve plakalar uydurmadır; gerçek bir kişiyle rastlantısal eşleşme kastî değildir. Sınamalardaki kimlik numaraları sağlama algoritmasıyla üretilir.

## Maskele → yapay zekâya ver → cevabı geri çevir

```bash
turkce-maske --dosya dilekce.txt --harita harita.json --yz --cikti maskeli.txt   # 1. maskele, haritayı sakla
#   2. maskeli.txt'yi oku, sonra yapay zekâya ver (harita.json'u ASLA verme)
turkce-maske --dosya cevap.txt --harita harita.json --geri --cikti cevap_acik.txt  # 3. geri çevir
```

`--yz`, metnin başına tek paragraflık bir talimat ekler: `[KİŞİ-1]` gibi etiketleri harfi harfine koru.

**Model etiketi değiştirirse:**
- `[Kişi-1]` ya da `[KİŞİ 1]` (köşeli parantez duruyor, harf ya da boşluk değişmiş) yine geri çevrilir.
- `KİŞİ-1` (parantez düşmüş) ya da `[KİŞİ-9]` (haritada yok) geri çevrilmez; `--geri` uyarı yazar.
- Modelin etiketi sözcüğe çevirmesi ("birinci kişi" gibi) fark edilemez. Geri çevrilmiş cevabı okuyun.

### Pano komutu

```bash
turkce-maske-pano --yz        # kopyaladığınızı maskeler; panoda artık maskeli metin var
turkce-maske-pano --geri      # yapay zekânın cevabını kopyalayın, bunu çalıştırın, geri çevrilmişi yapıştırın
turkce-maske-pano --sifirla   # haritayı boşalt (yeni konuşma)
```

- Harita `~/.turkce_maske/harita.json` dosyasında durur (dizin 0700, dosya 0600; POSIX). Başka yol için `TURKCE_MASKE_HARITA`.
- Kullanılan pano araçları: macOS'ta `pbpaste`/`pbcopy`, Linux'ta `wl-paste`/`wl-copy` ya da `xclip`, Windows'ta PowerShell `Get-Clipboard`/`Set-Clipboard`.
- **Panodaki önceki içerik maskeli metinle değişir.** Pano geçmişi tutan araçlar özgün metni saklamaya devam eder; onları siz temizleyin.
- Pano betiği (`pano_maskele.py`) modülden ayrıdır. Alt süreç başlatan tek parça odur.

## Neyi maskeler

| Veri | Nasıl bulunur | Etiket |
|---|---|---|
| TC kimlik no | 11 hane ve resmî sağlama algoritması | `[TCKN-1]` |
| Vergi kimlik no | 10 hane, sağlama ve yakında "vergi/VKN" kelimesi (CSV'de sütun başlığı da sayılır) | `[VKN-1]` |
| IBAN | TR ve yabancı IBAN; boşluklu ya da bitişik; mod-97 sağlaması | `[IBAN-1]` |
| Telefon | Cep (5xx) ve sabit hat; +90, 0 ve parantezli yazım | `[TEL-1]` |
| E-posta | Standart biçim; serbest bırakılacak adresler verilebilir | `[EPOSTA-1]` |
| Araç plakası | İl kodu + harf + rakam; künye kısaltmaları (HD, CD, TL…) hariç | `[PLAKA-1]` |
| Doğum tarihi | Yalnız bağlamla: "doğum tarihi", "D.T.", "… doğumlu" | `[DOĞUM-TARİHİ-1]` |
| Adres | En az iki adres parçası yan yanaysa (Mah., Sok., No, Daire…) | `[ADRES-1]` |
| Esas/karar no | İsteğe bağlı (`+esas`). Yargıtay/BAM/Daire künyeleri serbest kalır | `[DOSYA-NO-1]` |
| Kişi adı | Bağlam kelimesi (tanık, sanık, baba adı…), ad sözlüğü ya da sizin verdiğiniz liste | `[KİŞİ-1]` |
| Kendi kalıplarınız | `--kural-dosya`, satır başına `ETİKET<TAB>regex` | `[FATURA-1]` |

Ayrıca:
- **Türkçe büyük/küçük harf** doğru çevrilir: "Yiğit" büyük harfle "YİĞİT" olur. Python'un `str.upper()` işlevi "YIĞIT" verir.
- **Ekler** korunur: `Ahmet'in` → `[KİŞİ-1]'in`, `AHMET'İN` → `[KİŞİ-1]'İN`, `Doğrusözden` → `[KİŞİ-1]'den`.
- **OCR hatalı numaralar** (dar kapsam): TCKN ve TR IBAN'da `O→0`, `l/I→1` düzeltilip sağlama denenir.
- **Unicode:** metin önce NFC biçimine getirilir; ayrışık yazılmış harfler (ör. `o` + birleşen işaret olarak yazılmış `ö`) de tanınır.
- **Noktalama taşıyan adlar** (`Mehmet A. Öz`, `O'Brien`, `Jean-Luc`, `Ayşe-Nur`) haritadaki yazımıyla eşleşir; tire ile boşluk aynı sayılır (`Ayşe-Nur` = `Ayşe Nur`), yabancı adların ASCII büyük yazımı (`O'BRIEN`, `ROSSI`) da tanınır.
- **"Av."** ile başlayan meslektaş adları varsayılan olarak maskelenmez. Bu kural kapatılabilir.

## Diğer seçenekler

```bash
turkce-maske --test                                            # öz sınama
turkce-maske --dosya girdi.txt --harita harita.json --rapor rapor.json --cikti maskeli.txt
turkce-maske --dosya girdi.txt --kurallar +esas,-plaka         # kural aç/kapat
turkce-maske --dosya girdi.txt --haric "Örnek Yazılım A.Ş.,Proje Örnek"   # bunları hiç maskeleme
turkce-maske --dosya girdi.txt --haric-dosya haric.txt         # satır başına bir ifade
turkce-maske --dosya girdi.txt --kural-dosya kurallar.txt      # ör. FATURA<TAB>FTR-\d{6}
turkce-maske --dosya girdi.txt --supheli                       # kaçırılmış olabilecekleri listele
turkce-maske --csv liste.csv --sutun "Ad Soyad,Telefon" --harita harita.json --cikti maskeli.csv
turkce-maske --csv liste.xlsx --cikti maskeli.csv              # basit Excel: ilk sayfa, çıktı CSV
```

```python
from kvkk_maske import maskele, geri_al, supheli_izler, SIKI_KURALLAR

metin, harita, bulgular = maskele("Tanık Okyay Tezcanlı 0555 010 20 30 numarasından aradı.")
# metin   -> "Tanık [KİŞİ-1] [TEL-1] numarasından aradı."
metin2, harita, _ = maskele("Yiğit Karaca dava açtı.", harita={"Yiğit Karaca": "DAVACI"})
# metin2  -> "[DAVACI] dava açtı."
```

- Kurallar: `tckn, vkn, iban, telefon, eposta, plaka, dogum, adres, ad, esas, av_istisna, ocr, tckn_saglamasiz`. `esas` ve `tckn_saglamasiz` varsayılan olarak kapalıdır.
- Metin dışarıdaki bir hizmete gidecekse `kurallar=SIKI_KURALLAR` kullanın: sağlaması tutmasa da her 11 haneli sayı maskelenir.
- Birden çok parça (ör. taslak + ek belge) birlikte gönderilecekse **tek harita** kullanın: önce birleşik metinden haritayı kurun, sonra her parçayı o haritayla maskeleyin. Aksi hâlde aynı kişi farklı etiket alır.
- Ek ad listesi: `KVKK_MASKE_AD_DOSYASI=/yol/adlar.txt` (satır başına bir ad).

### Hariç listesi ve özel kurallar
- `--haric` / `haric=[...]`: hiçbir kuralda maskelenmeyecek ifadeler (büyük/küçük harf duyarsız). Şirket unvanı, proje adı ya da görünür kalması gereken bir kişi için. Hariç ifade yalnız kendisi kadar ya da daha kısa veriyi serbest bırakır: `0` ya da `Tezcanlı` hariç tutulunca telefon numarası ya da `Okyay Tezcanlı` tam adı açılmaz.
- `--kural-dosya` / `ozel_kurallar=[("FATURA", r"FTR-\d{6}")]`: kendi kalıplarınız tutarlı etiket alır. Etiket büyük harftir ve hazır etiket adlarından biri olamaz. Çakışmada hazır kurallar önce gelir; özel kural bir kimlik numarasını bölemez. Hatalı regex anlaşılır bir hata iletisiyle durur.
- **ReDoS uyarısı:** özel regex yazıldığı gibi çalışır. `(a+)+` gibi iç içe tekrarlar bazı girdilerde çok uzun sürebilir. Kalıpları basit ve sınırlı tutun.

### "Kaçırılmış olabilecekler" listesi
`--supheli` (ya da `--rapor` dosyasındaki `supheli` alanı) maskelemeden **sonra** kalan izleri listeler: 10–11 haneli rakam dizileri, `@` içeren kelimeler, sözlükte olmayan büyük harfli iki kelime, "Mah." gibi tek adres izi, IBAN gibi başlayan dizi. Yalnız satır, tür ve önizleme (ilk karakter + uzunluk) gösterir, değeri göstermez. Bu bir "şunlara bir de siz bakın" listesidir. Puan değildir, uyum raporu değildir.

### CSV ve Excel
- `--sutun "Ad Soyad,Telefon"`: yalnız bu sütunlar işlenir. Ad sütununda (Ad, Soyad, İsim, Unvan…) rakam içermeyen hücre tek kişi olarak maskelenir; "Soyad, Ad" sırası ve `'`, `-`, `.` taşıyan adlar da dahil. Rakam içeren hücre kurallarla işlenir. Diğer sütunlarda kural bir şey bulamazsa hücrenin **tamamı** tutarlı etiket alır (`[DEĞER-n]`).
- `--sutun` verilmezse tüm hücreler kurallarla taranır. Başlığında "vergi" ya da "VKN" geçen sütunda sağlaması geçerli 10 haneli numara, hücrede bu kelime olmasa da `[VKN-n]` olur.
- İlk satır başlıktır ve değişmez. Ayraç kendiliğinden bulunur (`;` `,` sekme `|`). Kodlama: UTF-8 (BOM'lu/BOM'suz), olmazsa cp1254.
- **Excel (.xlsx)** yalnız okunur, çıktı CSV'dir. Standart kütüphaneyle yalnız ilk sayfanın hücre değerleri alınır. Biçim, formül ve birleştirilmiş hücre taşınmaz; tarihler Excel seri sayısı olarak gelir; baştaki sıfırlar Excel'de zaten silinmiş olabilir. Karmaşık dosyalarda Excel'den **"CSV UTF-8"** olarak kaydedip onu verin.

## Bilinen sınırlar

- **Taranmış belgeyi okumaz.** OCR yoktur. Önce metne çevirin.
- **Her adı bulamaz.** Sözlükte olmayan ve yanında bağlam kelimesi bulunmayan ad kaçabilir. Bağlam kelimesi yoksa, üç kelimeli adın aynı zamanda ad olarak da kullanılan soyadı (`Mehmet Ali Yılmaz`, `… Aslan`, `… Can`) açık kalabilir.
- **Fazla maskeleyebilir.** Ad olarak da kullanılan kelimeler (ör. "Deniz", "Yıldız") büyük harfle yazılmışsa maskelenebilir.
- **Garanti vermez.** Maskelenmiş metni dışarı vermeden önce bir insan gözden geçirmelidir. Bu araç tek başına hukuki uyumu sağlamaz.
- Düz metin, CSV ve basit .xlsx işler. PDF, Word ya da UDF dosyalarını okumaz.
- **Geri alma yaklaşıktır:** tek geçen soyad tam ada, BÜYÜK harfli yazım haritadaki yazıma döner.
- **İki harfli soyad** (`Ak`, `Öz`) tam adın içinde maskelenir ama tek başına geçince açık kalır; iki harfli kelimeler yayılamayacak kadar yaygındır.
- **Tireli soyad:** `Arıkanlı-Kaya` tek ad olarak maskelenir. Tirenin çevresinde boşluk varsa (`Arıkanlı - Kaya`), uzun tire (`–`) kullanılmışsa ya da ad satır sonunda bölünmüşse ikinci parça açık kalabilir. İkinci soyad bir il adıysa (`Yılmaz-Aydın`, `Ekinci-Tokat`) yer sayılır ve açık kalır; bu kişileri haritaya elle ekleyin.
- **Tireyle yazılmış ad–yer:** `Ekinci-Kadıköy/İstanbul`, `Arıkanlı-Ankara Üniversitesi` ve tireden sonra il adı gelen yazımlarda ad tirede biter. Bu biçimde yazılmış başka yer adları (`Ekinci-Bakırköy`) adla birlikte maskelenebilir (fazla maskeleme).
- **Sağlama çakışması (güvenli yönde):** sağlaması tesadüfen tutan 11 haneli bir sayı, örneğin TL'li bir tutarın içinde, `[TCKN-n]` olarak maskelenebilir.
- **Büyük dosya:** bir Mac'te ölçüldü (25.11.2026): 200 KB metin 0,2–0,9 sn sürdü; adlarla dolu metin, aynı ada binlerce farklı soyadın eşlik ettiği durum ve aynı ilk iki adı paylaşan binlerce kişi dahil. 10.000 satırlık CSV yaklaşık 3–6 sn. Daha yavaş makinelerde birkaç kat uzun sürebilir. Çok büyük dosyaları parçalara bölün; parçalar arasında aynı haritayı kullanın. Açılmış boyutu 50 MB'ı aşan `.xlsx` sayfası reddedilir.

## Bilinen riskler (kullanmadan önce okuyun)

1. **Kaçırma riski.** Sözlükte olmayan, yanında bağlam kelimesi bulunmayan ad (özellikle yabancı ya da nadir adlar), küçük harfle yazılmış ad, tek parça adres ya da alışılmadık yazılmış numara maskelenmeden kalabilir. Bilinen örnekler: yazıyla yazılmış numara, satır sonunda bölünmüş numara (`--supheli` listeler, maskelemez), numara içinde `O/l/I` dışında harf, küçük harfle yazılmış ad. `--supheli` listesine bakın; maskeli metin dışarı verilmeden önce bir insan tarafından okunmalıdır.
2. **Kurallar herkese açıktır.** Aracın neyi yakalamadığı kaynak koddan görülebilir. Araç bir savunma katmanıdır; tek başına güvenlik önlemi olarak kullanılmamalıdır.
3. **Harita dosyası gerçek değerleri içerir.** Harita sızarsa maske anlamını yitirir. Haritayı maskeli metinle aynı yere koymayın, paylaşmayın.
4. **Fazla maskeleme.** Ad olarak da kullanılan kelimeler ve bazı sayı dizileri gereksiz yere maskelenebilir; metnin anlamını kontrol edin.
5. **Kapsam dışı biçimler.** Taranmış belge, görsel, PDF, Word ve UDF dosyaları doğrudan işlenmez; önce düz metne çevrilmeleri gerekir. Çeviri sırasında oluşan hatalar maskelemeyi etkileyebilir.
6. **Hukuki uyum garantisi yoktur.** Maskeleme, kişisel verilerin korunmasına ilişkin yükümlülükleri tek başına yerine getirmez; anonimleştirme sayılıp sayılmayacağı somut olaya göre değerlendirilir.

## SSS

- **Harita dosyası kişisel veri midir?** Evet. Etiketleri gerçek değerlere bağlar. Gizli tutun; maskeli metinle birlikte asla göndermeyin.
- **Emsal künye maskelenir mi?** Hayır. Yargıtay, BAM, Daire ve benzeri künyeler kalır. İsteğe bağlı `esas` kuralı diğer dosya numaralarını maskeler, künyelere dokunmaz.
- **Tamamen çevrimdışı mı?** Evet. Modül ağa çıkmaz, alt süreç başlatmaz. Ayrı pano betiği yalnız sistemin pano araçlarını çağırır.
- **Tarayıcı sürümü var mı?** Planlanıyor (yol haritasına bakın).

## Benzer araçlar

Bilgiler 25.11.2026'da her projenin kendi deposundan ya da paket sayfasından kontrol edildi. Burada performans karşılaştırması yapılmaz.

| Araç | Lisans | Dil / teknoloji |
|---|---|---|
| [Süzgeç](https://github.com/hukukca-cloud/suzgec) | PolyForm Noncommercial 1.0.0 | Tek HTML dosyası, JavaScript |
| [Katip](https://github.com/fikrifirat/katip) | AGPL-3.0 | Tarayıcı uygulaması ve Türkçe NER modelleri (depo dili: Python) |
| [kalkan](https://github.com/CelkMehmett/kalkan) | MIT ya da Apache-2.0 | Rust (PyPI'de Python paketi) |
| [anadolushield](https://github.com/Voxyfy/anadolushield) | MIT | TypeScript |
| [Presidio](https://github.com/data-privacy-stack/presidio) | MIT | Python, genel amaçlı (Türkçeye özgü değil) |

Bu aracın özellikleri: bağımlılıksız saf Python, Türkçe eki koruyan etiketler, yapay zekâ cevabını aynı haritayla geri çevirme.

## Güvenlik notları

- Harita ve rapor dosyaları yalnız sahibi tarafından okunabilir (0600) yazılır (POSIX; Windows'ta 0600 uygulanmaz).
- Rapor tam değeri içermez; tür, konum ve önizleme olarak yalnız ilk karakter + uzunluk içerir.
- Girdi, `--cikti`, `--harita` ve `--rapor` birbirinin aynı olamaz (sembolik ve sabit bağlar dahil); çakışmada çıkış kodu 2.
- Bozuk harita dosyası hata iletisiyle durur (çıkış 2).
- `kvkk_maske.py` ağ, alt süreç ya da dış paket kullanmaz.

## Yol haritası

- Tarayıcıda çalışan sürüm (sonraki aşama).

## Lisans

MIT — [LICENSE](LICENSE) dosyasına bakın. Copyright (c) 2026 Av. Cem Sinanoğlu.

Bu araç hukuki danışmanlık değildir; kendi sorumluluğunuzda kullanın.
