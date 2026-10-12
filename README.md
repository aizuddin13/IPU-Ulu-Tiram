# Kualiti Udara Ulu Tiram

Halaman awam yang memaparkan bacaan Indeks Pencemar Udara (IPU) bagi kawasan
**Ulu Tiram, Johor**, bersama ramalan cuaca MET Malaysia dan bandingan dengan
stesen-stesen lain di Johor.

Halaman: https://aizuddin13.github.io/IPU-Ulu-Tiram/

## Stesen rujukan

Ulu Tiram tiada stesen pemantauan APIMS sendiri. Halaman ini menggunakan
**CA33J, Larkin** sebagai stesen rujukan — stesen APIMS paling hampir, 14.3 km
dari pusat pekan. **CA34J, Pasir Gudang** (16.3 km) hampir sama dekat dan
sering mencatat bacaan lebih tinggi kerana kawasan perindustrian di sana, jadi
kedua-duanya ditonjolkan dalam carta bandingan.

Jarak dikira dengan formula haversine dari pusat pekan Ulu Tiram
(1.5944 N, 103.8167 E) ke koordinat stesen yang diterbitkan JAS, dan disimpan
sebagai pemalar dalam `scripts/kemaskini.py`.

| Stesen | Kod | Jarak |
| --- | --- | --- |
| Larkin | CA33J | 14.3 km |
| Pasir Gudang | CA34J | 16.3 km |
| Pengerang | CA35J | 43.4 km |
| Kota Tinggi | CA36J | 45.5 km |
| Kluang | CA32J | 74.6 km |
| Batu Pahat | CA31J | 111.7 km |
| Segamat | CA29J | 145.7 km |
| Tangkak | CA66J | 158.9 km |

## Kandungan

| Fail | Keterangan |
| --- | --- |
| `index.html` | Halaman itu sendiri. Tiada kebergantungan luar — semua carta dilukis sendiri sebagai SVG. |
| `data/ipu.json` | Bacaan IPU sejam bagi stesen rujukan, tetingkap bergolek tujuh hari (168 bacaan). |
| `data/johor.json` | Bacaan semasa kelapan stesen di Johor, disusun mengikut jarak dari Ulu Tiram. |
| `data/cuaca.json` | Ramalan cuaca tujuh hari bagi daerah Johor Bahru. |

## Kemas kini

Fail data dalam `data/` ditulis semula setiap jam oleh
`.github/workflows/kemaskini.yml`, yang berjalan pada pelari GitHub dan
memanggil API APIMS serta data.gov.my terus dengan Python pustaka standard.
Alur kerja yang sama menerbitkan halaman ini ke GitHub Pages, jadi tiada
langkah manual dan tiada perkhidmatan luar yang terlibat.

Dua perlindungan terbina:

- **Semakan kesegaran.** Jika bacaan terbaharu yang diterima lebih lama
  daripada tiga jam, skrip itu berhenti tanpa menulis apa-apa dan larian itu
  gagal dengan nyata dalam tab Actions. Data beku tidak akan berlalu secara
  senyap sebagai "tiada bacaan baharu".
- **Gabungan, bukan tambahan.** Setiap larian menerima tetingkap 25 jam dan
  mengisi mana-mana jam yang tiada dalam fail. Larian yang terlepas ditampal
  sendiri oleh larian berikutnya.

Dua perincian kecil yang menjadikan larian itu boleh dipercayai: jam diminta
dibundarkan ke atas supaya tetingkap merangkumi bacaan terbaharu yang baru
diterbitkan, dan setiap URL membawa parameter `_r` supaya jawapan lama dari
cache tidak dihidangkan semula.

Larian boleh dicetuskan secara manual dari tab Actions (Run workflow).

## Sumber

- Bacaan IPU: Sistem Pengurusan Indeks Pencemar Udara (APIMS), Jabatan Alam
  Sekitar — https://eqms.doe.gov.my/APIMS/main
- Ramalan cuaca: MET Malaysia, melalui portal data terbuka kerajaan
  (`api.data.gov.my/weather/forecast`, lokasi `Ds090` — daerah Johor Bahru)

Kedua-duanya data awam kerajaan Malaysia. Halaman ini bukan terbitan rasmi
mana-mana agensi. Untuk keputusan kesihatan yang penting, rujuk portal APIMS
atau nasihat Kementerian Kesihatan.
