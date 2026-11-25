# Sürüm notları

## 0.1.0 — 2026-11-25
İlk herkese açık sürüm.
- TCKN, VKN, IBAN (sağlamalı), telefon, e-posta, plaka, doğum tarihi, adres, isteğe bağlı dosya no ve kişi adı maskeleme.
- Türkçe büyük/küçük harf ve ek koruma ("Ahmet'in" → "[KİŞİ-1]'in").
- Harita ile geri çevirme; yapay zekâ akışı (`--yz`).
- Pano betiği (`pano_maskele.py`).
- Kod asistanları için `AGENTS.md` (kurulum, doğrulama, komutlar, harita dosyası kuralları).
- CSV sütun maskeleme; basit `.xlsx` okuma.
- Hariç listesi: `--haric`, `--haric-dosya`, API'de `haric=` (şirket unvanı, proje adı vb. hiç maskelenmez).
- Özel kurallar: `--kural-dosya` (`ETİKET<TAB>regex`), API'de `ozel_kurallar=`; hatalı regex anlaşılır hata verir.
- "Kaçırılmış olabilecekler" listesi: `--supheli` ve rapordaki `supheli` alanı (değer göstermez; puan/uyum raporu değildir).
- Yapışık yazılmış TCKN/telefon/IBAN da yakalanır (`TC12345…`, `tel.0555…`).
- Girdi/çıktı/harita/rapor aynı dosya olamaz (sembolik ve sabit bağ dahil); bozuk harita düzgün hata verir.
- Büyük metinde hız: çakışma çözümü n log n.
- Komutlar: `turkce-maske`, `turkce-maske-pano`.
- README İngilizce (`README.md`) ve Türkçe (`README.tr.md`).
- Hariç ifade yalnız kendisi kadar ya da daha kısa veriyi serbest bırakır; özel kural hazır kuralları bölemez.
- Ad araması kelime dizinine dayanır (tek kelimelik ad: kelime; çok kelimeli ad: ilk iki kelime), harita CSV'de bir kez kurulur. Bir Mac'te ölçüm: 200 KB metin 0,2–0,9 sn, 10.000 satırlık CSV yaklaşık 3–6 sn.
- Ek yazımlar: boşluklu/tireli TCKN, bitişik iki TCKN, küçük harfli `tr` IBAN, tireli/çift boşluklu IBAN, `90555…`, `0(555)…`, `0555 01 02 030`.
- CSV ad sütununda "Soyad, Ad" sırası tanınır.
- `--csv` ile `--dosya` birlikte verilemez; `--haric-dosya`/`--kural-dosya` da çakışma denetimine girer; bozuk xlsx ve cp1254 metin düzgün hata/okuma; xlsx 50 MB sınırı.
- Pano harita dizini 0700'e sıkılaştırılır.
- CI eylemleri SHA ile sabitlendi.
- Noktalama taşıyan adlar (`Mehmet A. Öz`, `O'Brien`, `Jean-Luc`) ve CSV'de `D'Angelo`, `Ayşe-Nur` hücreleri.
- Girdi NFC'ye normalize edilir (ayrışık Unicode).
- Ek yazımlar: noktalı yazımda TCKN (yalnız 3-3-3-2 gruplu) ve IBAN, `0555/010 20 30`, `05 55 01 02 03 0`, harfe/noktaya/eğik çizgiye yapışık plaka ve OCR-bozuk TCKN.
- `--supheli`: satır sonunda bölünmüş rakam dizisi.
- Bağlam ya da sözlükle bulunan tireli ad ve çift soyad bütün maskelenir (`Ayşe-Nur Kaya`, `Arıkanlı-Kaya`); tire ile boşluk ad içinde eşit sayılır; yabancı adların ASCII büyük yazımı (`ROSSI`) eşleşir.
- Ad araması tüm kelime dizisiyle tek sözlük aramasına geçti: aynı ilk iki adı paylaşan binlerce kişi de hızlı.
- Tek satır sonunda (`\n` ya da `\r\n`) bölünmüş IBAN bütünüyle maskelenir (mod-97 doğrular). Boş satırla bölünmüşse maskelenmez, yarım maske de oluşmaz; `--supheli` listeler.
- Tireyle bağlı ad–yer yazımında (`Ekinci-Kadıköy/İstanbul`, `Arıkanlı-Ankara Üniversitesi`, tireden sonra il adı) ad tirede biter.
- `--supheli`: 12+ haneli uzun rakam dizisi.
- `--rapor`/`--harita` yazılamazsa (ör. `/dev/stdout`) hata iletisi, çıkış 2.
