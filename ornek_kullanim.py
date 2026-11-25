#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kvkk_maske örnek kullanım. Tüm adlar ve numaralar uydurmadır."""
import random

from kvkk_maske import geri_al, iban_uret, maskele, tckn_uret

rng = random.Random(7)
tc, iban = tckn_uret(rng), iban_uret(rng)   # sağlaması geçerli, uydurma numaralar

metin = ("DAVACI : Yiğit Karaca\n"
         "Tanık Okyay Tezcanlı (T.C. %s) 0555 010 20 30 numarasından aradı.\n"
         "Ödeme %s hesabına yapıldı. KARACA'NIN aracı 34 ABC 123 plakalıdır.\n"
         "Adres: Çınar Mah. Lale Sok. No: 5 D: 3 Kadıköy/İstanbul\n"
         "Yargıtay 9. HD 2018/99999 E. 2019/99999 K. sayılı karar emsaldir." % (tc, iban))

# 1) Taraf adı dışarıdan, kendi etiketiyle verilir; gerisi kendiliğinden bulunur.
maskeli, harita, bulgular = maskele(metin, harita={"Yiğit Karaca": "DAVACI"})
print(maskeli)
print()
for b in bulgular:
    print(b["tur"], b["etiket"], b["onizleme"])

# 2) İkinci belge aynı haritayla: aynı kişi aynı etiketi alır.
ikinci, harita, _ = maskele("Tezcanlı'nın ikinci ifadesi alındı.", harita)
print()
print(ikinci)

# 3) Geri dönüş (harita gerçek değer taşır; paylaşmayın).
print()
print(geri_al(maskeli, harita))
