#!/usr/bin/env python3
"""Kemas kini fail data untuk halaman Kualiti Udara Ulu Tiram.

Mengambil bacaan IPU sejam dari portal APIMS (Jabatan Alam Sekitar) dan
ramalan cuaca MET Malaysia melalui portal data terbuka kerajaan, kemudian
menulis semula fail JSON dalam data/.

Ulu Tiram tiada stesen pemantauan sendiri. Stesen rujukan ialah Larkin
(CA33J), 14.3 km dari pusat pekan — stesen APIMS paling hampir.

Hanya pustaka standard Python digunakan. Dijalankan setiap jam oleh
.github/workflows/kemaskini.yml pada pelari GitHub.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

MYT = timezone(timedelta(hours=8))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(AKAR, "data")

NEGERI_JOHOR = 1
STESEN_RUJUKAN = "CA33J"     # Larkin — stesen terdekat Ulu Tiram
JAM_DISIMPAN = 168           # tetingkap bergolek tujuh hari
AMBANG_BASI_JAM = 3          # bacaan lebih lama daripada ini dikira basi

APIMS = "https://eqms.doe.gov.my/api3/publicportalapims/apitablehourly"

# Dua lokasi di portal data.gov.my berkongsi nama "Johor Bahru": Ds090
# (daerah) dan Tn139 (bandar). Ulu Tiram terletak dalam daerah Johor
# Bahru, jadi rekod ditapis mengikut location_id, bukan nama sahaja.
CUACA = ("https://api.data.gov.my/weather/forecast?"
         + urllib.parse.urlencode({"contains": "Johor Bahru@location__location_name",
                                   "limit": 20}))
CUACA_LOKASI = "Ds090"

# Jarak garis lurus dari pusat pekan Ulu Tiram (1.5944 N, 103.8167 E) ke
# koordinat stesen JAS, dalam kilometer. Dikira sekali dengan formula
# haversine dan disimpan sebagai pemalar supaya halaman tidak bergantung
# pada pengiraan setiap larian.
JARAK_KM = {
    "CA33J": 14.3,    # Larkin
    "CA34J": 16.3,    # Pasir Gudang
    "CA35J": 43.4,    # Pengerang
    "CA36J": 45.5,    # Kota Tinggi
    "CA32J": 74.6,    # Kluang
    "CA31J": 111.7,   # Batu Pahat
    "CA29J": 145.7,   # Segamat
    "CA66J": 158.9,   # Tangkak
}

HARI_MELAYU = ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"]

SIMBOL_PENCEMAR = {
    "**": "PM2.5",
    "*": "PM10",
    "a": "SO2",
    "b": "NO2",
    "c": "O3",
    "d": "CO",
    "&": "2 pencemar atau lebih",
}


def kategori(ipu):
    if ipu <= 50:
        return "Baik"
    if ipu <= 100:
        return "Sederhana"
    if ipu <= 200:
        return "Tidak Sihat"
    if ipu <= 300:
        return "Sangat Tidak Sihat"
    return "Berbahaya"


def ayat_biasa(teks):
    teks = (teks or "").strip()
    return teks[:1].upper() + teks[1:].lower() if teks else teks


def ambil_json(url, cubaan=3):
    """Ambil JSON dengan beberapa cubaan. Mengembalikan None jika gagal."""
    for i in range(cubaan):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "ipu-ulu-tiram/1.0 (+github actions)",
                              "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as res:
                return json.loads(res.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, TimeoutError, OSError) as e:
            print(f"  cubaan {i + 1}/{cubaan} gagal: {e}", file=sys.stderr)
            if i + 1 < cubaan:
                time.sleep(5 * (i + 1))
    return None


def muat(nama, lalai):
    laluan = os.path.join(DATA, nama)
    try:
        with open(laluan, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return lalai


def simpan(nama, isi):
    laluan = os.path.join(DATA, nama)
    os.makedirs(DATA, exist_ok=True)
    with open(laluan, "w", encoding="utf-8") as f:
        json.dump(isi, f, ensure_ascii=False, indent=1)
        f.write("\n")


def ambil_apims(sekarang):
    """Tingkap 25 jam bagi semua stesen Johor, sehingga jam hadapan.

    Jam dibundarkan ke atas supaya tetingkap merangkumi bacaan terbaharu
    yang baru diterbitkan, dan `_r` menghalang jawapan lama daripada
    cache dihidangkan semula.
    """
    sehingga = (sekarang.replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")
    url = (f"{APIMS}?stateid={NEGERI_JOHOR}&datetime={sehingga}"
           f"&stn=all&_r={int(time.time())}")
    print(f"APIMS: {url}")
    jawapan = ambil_json(url)
    if not jawapan:
        return None
    baris = jawapan.get("api_table_hourly") if isinstance(jawapan, dict) else jawapan
    if not baris:
        return None
    bersih = []
    for r in baris:
        try:
            ipu = int(r["API"])
        except (KeyError, TypeError, ValueError):
            continue  # bacaan tiada atau rosak — langkau
        masa = str(r.get("DATETIME", ""))[:19]
        if len(masa) != 19:
            continue
        bersih.append({
            "id": r.get("STATION_ID"),
            "lokasi": str(r.get("STATION_LOCATION", "")).split(",")[0].strip(),
            "masa": masa,
            "ipu": ipu,
            "pencemar": SIMBOL_PENCEMAR.get(str(r.get("PARAM_SYMBOL", "")).strip(), "PM2.5"),
        })
    return bersih or None


def tulis_ipu(baris, sekarang):
    rujukan = sorted([b for b in baris if b["id"] == STESEN_RUJUKAN],
                     key=lambda b: b["masa"])
    if not rujukan:
        print(f"Tiada baris {STESEN_RUJUKAN} dalam jawapan APIMS.", file=sys.stderr)
        return None

    terbaharu = rujukan[-1]
    umur = sekarang - datetime.strptime(terbaharu["masa"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=MYT)
    if umur > timedelta(hours=AMBANG_BASI_JAM):
        print(f"DATA BASI: bacaan terbaharu {terbaharu['masa']} "
              f"({umur.total_seconds() / 3600:.1f} jam lalu).", file=sys.stderr)
        return None

    sedia = muat("ipu.json", {"bacaan": []})
    simpanan = {b["masa"]: b for b in sedia.get("bacaan", [])}
    baharu = 0
    for b in rujukan:
        if b["masa"] not in simpanan:
            simpanan[b["masa"]] = {
                "masa": b["masa"], "ipu": b["ipu"],
                "kategori": kategori(b["ipu"]), "pencemar": b["pencemar"],
            }
            baharu += 1

    bacaan = [simpanan[m] for m in sorted(simpanan)][-JAM_DISIMPAN:]
    simpan("ipu.json", {
        "kawasan": "Ulu Tiram",
        "stesen": terbaharu["lokasi"],
        "id_stesen": STESEN_RUJUKAN,
        "jarak_km": JARAK_KM.get(STESEN_RUJUKAN),
        "negeri": "Johor",
        "dikemaskini": terbaharu["masa"] + "+08:00",
        "sumber": "APIMS, Jabatan Alam Sekitar",
        "bacaan": bacaan,
    })
    print(f"ipu.json: {baharu} bacaan baharu, {len(bacaan)} jam disimpan, "
          f"terkini {terbaharu['masa']} = {terbaharu['ipu']}")
    return terbaharu


def tulis_johor(baris):
    terkini = {}
    for b in baris:
        ada = terkini.get(b["id"])
        if ada is None or b["masa"] > ada["masa"]:
            terkini[b["id"]] = b
    if not terkini:
        return
    # Disusun mengikut jarak dari Ulu Tiram, yang paling hampir dahulu.
    stesen = sorted(terkini.values(),
                    key=lambda b: JARAK_KM.get(b["id"], 9999))
    simpan("johor.json", {
        "dikemaskini": max(b["masa"] for b in stesen) + "+08:00",
        "sumber": "APIMS, Jabatan Alam Sekitar",
        "stesen": [{
            "nama": b["lokasi"], "id": b["id"], "ipu": b["ipu"],
            "jarak_km": JARAK_KM.get(b["id"]),
            "kategori": kategori(b["ipu"]), "pencemar": b["pencemar"],
        } for b in stesen],
    })
    print(f"johor.json: {len(stesen)} stesen")


def tulis_cuaca(sekarang):
    print(f"Cuaca: {CUACA}")
    rekod = ambil_json(CUACA)
    if not rekod:
        print("  gagal — fail cuaca dibiarkan seperti sedia ada.", file=sys.stderr)
        return
    hari_ini = sekarang.strftime("%Y-%m-%d")
    ikut_tarikh = {}
    for r in rekod:
        lokasi = r.get("location") or {}
        if lokasi.get("location_id") != CUACA_LOKASI:
            continue  # nama yang sama dikongsi beberapa lokasi
        tarikh = str(r.get("date", ""))[:10]
        if len(tarikh) != 10 or tarikh < hari_ini:
            continue
        try:
            d = datetime.strptime(tarikh, "%Y-%m-%d")
        except ValueError:
            continue
        ikut_tarikh[tarikh] = {
            "tarikh": tarikh,
            "hari": HARI_MELAYU[d.weekday()],
            "ringkasan": ayat_biasa(r.get("summary_forecast") or r.get("summary")),
            "ringkasan_bila": ayat_biasa(r.get("summary_when")),
            "pagi": ayat_biasa(r.get("morning_forecast")),
            "petang": ayat_biasa(r.get("afternoon_forecast")),
            "malam": ayat_biasa(r.get("night_forecast")),
            "suhu_min": int(r.get("min_temp", 0)),
            "suhu_maks": int(r.get("max_temp", 0)),
        }
    if not ikut_tarikh:
        print("  tiada rekod Johor Bahru — fail cuaca dibiarkan.", file=sys.stderr)
        return
    ramalan = [ikut_tarikh[t] for t in sorted(ikut_tarikh)]
    simpan("cuaca.json", {
        "lokasi": "Johor Bahru",
        "dikemaskini": sekarang.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "sumber": "MET Malaysia melalui data.gov.my",
        "ramalan": ramalan,
    })
    print(f"cuaca.json: {len(ramalan)} hari")


def main():
    sekarang = datetime.now(MYT)
    print(f"Masa Malaysia: {sekarang:%Y-%m-%d %H:%M:%S}")

    baris = ambil_apims(sekarang)
    if baris is None:
        print("APIMS tidak dapat dibaca. Tiada fail ditulis.", file=sys.stderr)
        return 1

    terbaharu = tulis_ipu(baris, sekarang)
    if terbaharu is None:
        return 1
    tulis_johor(baris)
    tulis_cuaca(sekarang)

    nama = terbaharu["lokasi"]
    if terbaharu["ipu"] > 200:
        print(f"::warning::AMARAN: IPU {nama} {terbaharu['ipu']} — sangat tidak sihat")
    elif terbaharu["ipu"] > 150:
        print(f"::warning::AMARAN: IPU {nama} {terbaharu['ipu']} — melepasi ambang 150")
    return 0


if __name__ == "__main__":
    sys.exit(main())
