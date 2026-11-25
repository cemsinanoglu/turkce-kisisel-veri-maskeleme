# AGENTS.md — instructions for coding assistants

This file tells AI coding assistants (Claude Code, Cursor, Copilot, Codex and similar) how to install and use this tool for a user. Human documentation: [README.md](README.md) (English), [README.tr.md](README.tr.md) (Turkish).

## What this is

Offline masking of personal data in Turkish text: TC kimlik no, VKN, IBAN, phone, e-mail, plate, birth date, address, person names. Pure Python 3.9+, standard library only, no network access. Masked values become consistent labels such as `[KİŞİ-1]`, `[TCKN-1]`; a map file (JSON) lets you restore them later.

## Install

```bash
python3 -m pip install git+https://github.com/cemsinanoglu/turkce-kisisel-veri-maskeleme
```

No Git or no install rights: download the repository and run `python3 kvkk_maske.py …` directly; the single file is enough. On Windows use `py` instead of `python3` and set `PYTHONUTF8=1` first.

## Verify

```bash
python3 kvkk_maske.py --test      # must print "193/193" (or N/N); exit code 0
python3 pano_maskele.py --test    # clipboard helper self-test
```

If installed via pip, `turkce-maske --test` does the same. If the command is not on PATH, use `python3 -m kvkk_maske --test`.

## Typical tasks

```bash
# Mask a file and keep the map (needed to restore later)
turkce-maske --dosya input.txt --harita map.json --cikti masked.txt --supheli

# Add an instruction for the AI to keep labels unchanged
turkce-maske --dosya input.txt --harita map.json --yz --cikti masked.txt

# Restore an AI answer with the same map
turkce-maske --dosya answer.txt --harita map.json --geri --cikti answer_restored.txt

# CSV / simple .xlsx (first sheet; output is CSV)
turkce-maske --csv list.csv --sutun "Ad Soyad,Telefon" --harita map.json --cikti masked.csv
```

Python API:

```python
from kvkk_maske import maskele, geri_al, SIKI_KURALLAR
masked, mapping, findings = maskele(text, kurallar=SIKI_KURALLAR)
restored = geri_al(answer, mapping)
```

Other flags: `--kurallar +esas,-plaka` · `--haric "Name A,Company B"` · `--haric-dosya` · `--kural-dosya` (`LABEL<TAB>regex`) · `--rapor` · `--harita`. Full list: `turkce-maske --help`.

Exit codes: `0` success · `2` input/argument error (e.g. input and output are the same file, broken map file).

## Rules for assistants

1. **Never send, upload, paste or print the map file (`--harita` / `~/.turkce_maske/harita.json`).** It contains the real values. Do not commit it; do not put it next to the masked text.
2. **Do not show the original text** in chat or logs once the user has asked for masking. Work with the masked output.
3. **Run `--supheli` and show the user the list** of possible misses. Tell the user that a person must read the masked text before it leaves the computer; masking is not guaranteed and is pseudonymization, not anonymization.
4. **Use the same map for all parts** of one job (draft + attachments), otherwise the same person gets different labels.
5. If the text will go to an external service, prefer `SIKI_KURALLAR` (Python) so every 11-digit number is masked.
6. The tool does not read PDF, Word, UDF or scanned images. Convert to plain text first and tell the user that conversion errors can affect masking.
7. Do not modify `kvkk_maske.py` to "fix" a miss silently; report it (see [SECURITY.md](SECURITY.md)) with a synthetic example, never real personal data.
