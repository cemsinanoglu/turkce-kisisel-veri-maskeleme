#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pano_maskele — panodaki (kopyala-yapıştır) metni maskeler ya da geri çevirir.

Kullanım:
  python3 pano_maskele.py            # panodaki metni maskele, maskeli hâli panoya yaz
  python3 pano_maskele.py --yz       # ayrıca başına "etiketleri aynen koru" talimatı ekle
  python3 pano_maskele.py --geri     # panodaki (yapay zekâ) cevabı aynı haritayla geri çevir
  python3 pano_maskele.py --sifirla  # haritayı boşalt (yeni konuşma)
  python3 pano_maskele.py --test     # öz sınama (gerçek panoya ve ev dizinine dokunmaz)

Harita: ~/.turkce_maske/harita.json (dizin 0700, dosya 0600; Windows'ta bu izinler uygulanmaz).
Harita dosyası GERÇEK değerleri taşır, yani kişisel veridir: paylaşmayın.
Başka yol için: TURKCE_MASKE_HARITA=<yol>.
Pano araçları: macOS pbpaste/pbcopy · Linux wl-paste/wl-copy ya da xclip · Windows PowerShell Get/Set-Clipboard.
Alt süreç YALNIZ bu betikte kullanılır; kvkk_maske.py modülü alt süreç kullanmaz.

Copyright (c) 2026 Av. Cem Sinanoğlu — MIT Lisansı.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvkk_maske as KM  # noqa: E402


def harita_yolu():
    return os.environ.get("TURKCE_MASKE_HARITA") or os.path.join(os.path.expanduser("~"), ".turkce_maske", "harita.json")


def _komutlar():
    """-> (okuma komutu, yazma komutu)"""
    if sys.platform == "darwin":
        return ["pbpaste"], ["pbcopy"]
    if sys.platform.startswith("win"):
        ps = ["powershell", "-NoProfile", "-Command"]
        return (ps + ["[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                ps + ["[Console]::InputEncoding=[Text.Encoding]::UTF8; [Console]::In.ReadToEnd() | Set-Clipboard"])
    if os.environ.get("WAYLAND_DISPLAY"):
        return ["wl-paste", "--no-newline"], ["wl-copy"]
    return ["xclip", "-selection", "clipboard", "-o"], ["xclip", "-selection", "clipboard", "-i"]


def pano_oku():
    oku, _ = _komutlar()
    r = subprocess.run(oku, capture_output=True, timeout=15)
    if r.returncode != 0:
        raise SystemExit("hata: pano okunamadı (%s)" % " ".join(oku[:1]))
    return r.stdout.decode("utf-8", errors="replace")


def pano_yaz(metin):
    _, yaz = _komutlar()
    r = subprocess.run(yaz, input=metin.encode("utf-8"), capture_output=True, timeout=15)
    if r.returncode != 0:
        raise SystemExit("hata: panoya yazılamadı (%s)" % " ".join(yaz[:1]))


def harita_oku(yol):
    if not os.path.exists(yol):
        return {}
    try:
        with open(yol, encoding="utf-8") as f:
            h = json.load(f).get("harita", {})
        if not isinstance(h, dict):
            raise ValueError("'harita' sözlük değil")
        return h
    except (ValueError, OSError, AttributeError) as e:
        raise SystemExit("hata: harita okunamadı (%s): %s" % (yol, e))


def harita_yaz(yol, h):
    d = os.path.dirname(yol)
    if d and not os.path.isdir(d):
        os.makedirs(d, mode=0o700, exist_ok=True)
    elif d and os.name != "nt" and os.path.basename(d) == ".turkce_maske" and os.stat(d).st_mode & 0o077:
        os.chmod(d, 0o700)      # önceden geniş izinle açılmış harita dizinini sıkılaştır
    KM._gizli_yaz(yol, json.dumps({"surum": KM.SURUM, "harita": h}, ensure_ascii=False, indent=1))


def calistir(arglar, oku=pano_oku, yaz=pano_yaz, yol=None, hata=sys.stderr):
    """Pano işlevleri dışarıdan verilebilir (sınama için)."""
    yol = yol or harita_yolu()
    if "--sifirla" in arglar:
        harita_yaz(yol, {})
        print("harita boşaltıldı: %s" % yol, file=hata)
        return 0
    metin = oku()
    if not metin.strip():
        print("pano boş", file=hata)
        return 1
    h = harita_oku(yol)
    if "--geri" in arglar:
        if not h:
            print("hata: harita boş; önce maskeleyin", file=hata)
            return 2
        out = KM.geri_al(metin, h)
        bozuk = KM.bozuk_etiketler(out, h)
        for _, iz in bozuk[:10]:
            print("uyarı: geri çevrilemeyen etiket izi: %s" % iz, file=hata)
        yaz(out)
        print("geri çevrildi%s" % (" (%d uyarı)" % len(bozuk) if bozuk else ""), file=hata)
        return 0
    out, h, bulgular = KM.maskele(metin, h, KM.SIKI_KURALLAR)
    if "--yz" in arglar:
        out = KM.YZ_TALIMATI + out
    harita_yaz(yol, h)
    yaz(out)
    print("maskelendi: %d bulgu · harita: %s" % (len([b for b in bulgular if b["etiket"]]), yol), file=hata)
    return 0


def _oz_sinama():
    import io
    import tempfile
    pano = {"m": ""}

    def oku():
        return pano["m"]

    def yaz(m):
        pano["m"] = m

    d = tempfile.mkdtemp(prefix="pano_maskele_sinama_")
    yol = os.path.join(d, "alt", "harita.json")
    sessiz = io.StringIO()
    ok, top = 0, 0

    def k(ad, kosul):
        nonlocal ok, top
        top += 1
        ok += bool(kosul)
        if not kosul:
            print("  ✗ " + ad)

    pano["m"] = "Tanık Okyay Tezcanlı 0555 010 20 30 numarasından aradı."
    k("maskele: çıkış 0", calistir([], oku, yaz, yol, sessiz) == 0)
    k("maskele: panoda maskeli metin", pano["m"] == "Tanık [KİŞİ-1] [TEL-1] numarasından aradı.")
    k("harita 0600 ve dizin 0700", os.name == "nt" or (oct(os.stat(yol).st_mode & 0o777) == "0o600"
                                                         and oct(os.stat(os.path.dirname(yol)).st_mode & 0o777) == "0o700"))
    pano["m"] = "[KİŞİ-1]'in [TEL-1] numarası doğrulandı. [Kişi-1] tekrar aradı."
    k("geri: çıkış 0", calistir(["--geri"], oku, yaz, yol, sessiz) == 0)
    k("geri: yapay zekâ cevabı çevrildi", pano["m"] == "Okyay Tezcanlı'in 0555 010 20 30 numarası doğrulandı. "
                                                     "Okyay Tezcanlı tekrar aradı.")
    pano["m"] = "ikinci metin: Okyay Tezcanlı ve tanık Vural Pekdemir"
    calistir(["--yz"], oku, yaz, yol, sessiz)
    k("ikinci maskeleme aynı etiketi korur + YZ talimatı", pano["m"].startswith(KM.YZ_TALIMATI)
      and "[KİŞİ-1] ve tanık [KİŞİ-2]" in pano["m"])
    e = io.StringIO()
    pano["m"] = "KİŞİ-2 aradı"
    calistir(["--geri"], oku, yaz, yol, e)
    k("geri: bozuk etiket uyarısı", "uyarı" in e.getvalue())
    k("sıfırla", calistir(["--sifirla"], oku, yaz, yol, sessiz) == 0 and harita_oku(yol) == {})
    if os.name != "nt":
        gd = os.path.join(d, ".turkce_maske")
        os.makedirs(gd)
        os.chmod(gd, 0o755)
        harita_yaz(os.path.join(gd, "harita.json"), {})
        k("geniş izinli harita dizini 0700'e sıkılaşır", oct(os.stat(gd).st_mode & 0o777) == "0o700")
    pano["m"] = "   "
    k("boş pano çıkış 1", calistir([], oku, yaz, yol, sessiz) == 1)
    k("komut seçimi platforma göre", _komutlar()[0][0] in ("pbpaste", "powershell", "wl-paste", "xclip"))
    print("pano_maskele öz sınama: %d/%d geçti" % (ok, top))
    return 0 if ok == top else 1


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if "--test" in a:
        return _oz_sinama()
    if "-h" in a or "--help" in a:
        print(__doc__)
        return 0
    try:
        return calistir(a)
    except KM._YazmaHatasi as e:
        print("hata: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
