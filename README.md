# KAZE

Aplikasi anime pribadi berbasis **Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia + Vue Router**, dengan **FastAPI, SQLAlchemy, SQLite**. Tampilan mengambil referensi struktur layanan streaming seperti Crunchyroll, dengan identitas KAZE sendiri. Tidak memerlukan akun atau pembayaran.

## Menjalankan lokal

Persyaratan: Node.js 22.12+ dan Python 3.12+.

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Terminal pertama, dari root proyek:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal kedua:

```powershell
npm run dev
```

Buka **http://127.0.0.1:5173**. Dokumentasi API: **http://127.0.0.1:8000/docs**.

Linux/macOS: gunakan `.venv/bin/python` sebagai pengganti `.\.venv\Scripts\python.exe`.

`kaze.db` dibuat otomatis pada direktori tempat backend dijalankan. Jalankan dari root yang sama setiap kali. Untuk cadangan, hentikan backend lalu salin file database. Data pribadi tidak disinkronkan ke layanan akun.

## Konfigurasi

Pengaturan opsional tersedia di `.env.example` dan `backend/.env.example`. Salin variabel yang diperlukan ke `.env` di root. Default sudah bekerja dengan dua perintah di atas. Vite meneruskan `/api` ke backend port 8000. Backend hanya diikat ke loopback karena ini aplikasi satu pengguna tanpa autentikasi.

## Yang tersedia

- Beranda: trending, musim berjalan, rilisan terkini, rekomendasi komunitas, lanjut menonton jika ada riwayat.
- Katalog: pencarian Inggris/Romaji/Jepang, debounce, pembatalan permintaan, filter genre/tahun/musim/format/status, pengurutan dan paginasi. Filter disimpan di URL.
- Detail: artwork, sinopsis, studio, karakter, relasi, rekomendasi, tautan penyedia resmi, metadata episode dan status pemutaran.
- Jadwal: episode berikutnya untuk 54 anime paling populer yang sedang tayang, menurut waktu lokal browser. Bukan kalender lengkap seluruh anime.
- Watchlist dengan lima status, sortir, hapus, dan jumlah episode selesai.
- Riwayat dengan resume, penanda selesai, reset per episode, dan hapus semua setelah konfirmasi.
- Preferensi pemutaran dan pengelolaan sumber video melalui Pengaturan.
- Tema gelap, navigasi ponsel, fokus keyboard, reduced motion, skeleton, empty/error states, retry, fallback poster.

## Metadata dan cache

AniList GraphQL menyediakan katalog dan detail. Metadata dinormalisasi sebelum dikirim ke frontend. Respons disimpan di SQLite selama 30 menit, permintaan identik dideduplikasi, dan cache lama dipakai jika penyedia gagal. HTTP memiliki timeout serta retry exponential backoff.

Jikan memberikan metadata episode dengan **`idMal` yang dikirim AniList**, bukan dengan menyamakan ID. Jika detail AniList gagal dan belum ada cache detail, Jikan dapat mengisi detail berdasarkan pemetaan ID terverifikasi dari cache katalog. Bila tidak ada pemetaan, aplikasi menampilkan kegagalan secara jelas. Sinopsis mengikuti bahasa penyedia metadata; tidak diterjemahkan otomatis.

## Menambahkan video

1. Buka detail anime, catat **AniList ID**.
2. Buka **Pengaturan → Sumber video**.
3. Masukkan ID anime, nomor episode, provider, dan sumber yang diizinkan.
4. Untuk YouTube, masukkan **video ID 11 karakter** dari kanal resmi yang mengizinkan embedding.
5. Untuk MP4/HLS, gunakan URL HTTPS atau server lokal `http://127.0.0.1:PORT/...`. File lokal harus disajikan oleh server media dengan CORS yang mengizinkan origin KAZE. URL `file://` tidak didukung browser.
6. Subtitle opsional berupa WebVTT, dengan URL, bahasa, dan label. Server subtitle juga perlu CORS.

Manifest `backend/official_sources.json` menyediakan tautan kanal resmi: Frieren episode 1 dan Cells at Work! episode 1–8 (dubbing Indonesia). Impor semua sekaligus dengan `.\.venv\Scripts\python.exe -m backend.import_official_sources`. Importer aman diulang dan tidak menambah duplikat. Ini daftar tautan terpilih, bukan sinkronisasi otomatis seluruh katalog atau seluruh musim. Tambahkan rekaman pada manifest untuk mengimpor sumber lain sekaligus.

AniList dan Jikan bukan penyedia stream video. Tombol Tonton menunjukkan sumber yang terhubung, bukan jaminan akses. Saat pengujian, embed Frieren ditolak YouTube karena pembatasan negara; pemutaran Cells at Work! belum terverifikasi. Ketersediaan, wilayah, dan izin embed ditentukan kanal/YouTube. Seluruh sumber terhubung tetap muncul di daftar episode saat metadata Jikan gagal; membuka player tidak menunggu metadata episode opsional.

Player YouTube memakai IFrame API resmi. MP4 memakai kontrol HTML5 dan HLS memakai hls.js (atau dukungan native browser). Kualitas hanya muncul bila manifest HLS menyediakan beberapa varian; subtitle hanya bila dikonfigurasi. Kecepatan tersedia di player HTML5 dan kontrol provider yang mendukung. Progres disimpan setiap 10 detik, saat jeda, saat navigasi, dan ketika tab disembunyikan. Penutupan browser secara paksa dapat kehilangan beberapa detik terakhir. Shortcut HTML5 ketika player difokuskan: Spasi/K putar-jeda, panah kiri/kanan 10 detik, M mute, F fullscreen. Shortcut `/` membuka pencarian global.

Cloudflare Stream adalah adapter opsional dengan player hosted; **progres otomatis belum didukung untuk adapter ini**. Kontrol dan ketersediaan YouTube/Cloudflare tetap mengikuti pembatasan penyedia.

## Pengujian dan build

### Integrasi Wajik

Halaman detail dan player utama sekarang juga memakai Zen (`https://api.anizen.tr`). Anime dicocokkan dengan AniList ID, atau MyAnimeList ID dari metadata AniList jika Zen tidak menyediakan AniList ID. Daftar episode berasal dari provider; jumlah total katalog tidak digunakan untuk membuat episode palsu. Player Zen memakai embed HTTPS dari host provider tanpa sandbox sesuai pilihan pengguna untuk pemakaian pribadi. URL embed tetap divalidasi backend ke https://api.anizen.tr/player/. Progres otomatis dan auto-next iframe Zen belum didukung; tombol sebelumnya/berikutnya tersedia. Bahasa SUB/DUB mengikuti provider dan tidak menjamin subtitle Indonesia. Jika Zen tidak tersedia, sumber lokal dan metadata Jikan digunakan sebagai fallback.

Menu **Nonton** membuka pencarian Wajik (sumber Otakudesu). Pada detail AniList, **Cari episode di Wajik** membawa judul ke pencarian; pilih season secara eksplisit agar ID AniList tidak tertukar dengan ID provider. Halaman detail memuat seluruh `episodeList` dari respons, lalu halaman episode menampilkan embed, pilihan server, serta navigasi sebelumnya/berikutnya.

Backend mengakses JSON dari `KAZE_WAJIK_BASE_URL` (default `https://wajik-anime-api.vercel.app`). Tidak ada proxy video, pengunduhan, atau bypass akses. Iframe HTTPS dibatasi sandbox tanpa popup dan navigasi halaman induk. Riwayat/progres otomatis dan auto-next belum didukung pada iframe Wajik. Sumber ini pihak ketiga, tidak ditandai sebagai penyedia resmi. Ketersediaannya mengikuti API dan host video.

Verifikasi langsung: pencarian Frieren berhasil; detail `sousou-frieren-sub-indo` mengembalikan 403 dari provider. Karena itu daftar episode aktual dan playback belum terverifikasi. UI menampilkan kegagalan tersebut, bukan menandai pemutaran berhasil. Jangan menganggap semua judul/episode pasti dapat diputar.

## Perintah pengujian

Pembaruan 20 Oktober 2026: pencarian Zen memeriksa hingga tiga judul alternatif dan dua belas kandidat per judul dalam batas waktu 35 detik, tetap memverifikasi ID AniList/MAL, dan melewati kandidat yang gagal. Episode lokal yang tidak ada di daftar Zen tetap ditampilkan. Player menyediakan muat ulang sumber, perpindahan sumber ketika adapter melaporkan error, dan tautan membuka player langsung untuk server yang menolak iframe sandbox. Error di dalam iframe pihak ketiga tidak dapat dideteksi otomatis; pilih server lain secara manual.

Verifikasi API lokal menemukan 28 episode Frieren, 1.180 One Piece, dan 25 Attack on Titan dengan URL sumber. Ini bukan verifikasi playback semua episode. Pemeriksaan browser Frieren episode 1 menemukan HD-1 menolak sandbox dan VidCloud-1 mengembalikan 404. Setelah persetujuan pengguna, sandbox khusus Zen dilepas. Verifikasi browser berikutnya berhasil memutar Frieren episode 1 di dalam WINNIME melalui HD-1. Sandbox Wajik tetap aktif; tombol buka player langsung tetap tersedia sebagai alternatif.

Player langsung HD-1 untuk Frieren episode 1 berhasil memuat durasi 25:59 dan menampilkan video dalam pengujian browser. Hasil ini hanya berlaku untuk sampel tersebut; subtitle Indonesia dan pemutaran seluruh katalog belum terverifikasi.

```powershell
npm test
npm run build
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Tes backend memakai database SQLite terisolasi dan mencakup watchlist, history, validasi sumber, preferensi, pemetaan AniList/MAL, cache saat provider gagal. Tes frontend menguji kegagalan simpan, deduplikasi watchlist, progres, dan kegagalan hapus. Fixture tes tidak digunakan sebagai dataset aplikasi.

Build frontend ada di `dist/`. Untuk deployment, gunakan host SPA yang mengembalikan `index.html` untuk route frontend dan reverse proxy `/api` ke FastAPI; backend Python dan database tetap perlu dijalankan. Menyajikan `dist/` saja tidak menyediakan backend. Aplikasi ini disiapkan untuk penggunaan lokal, belum untuk layanan publik multi-pengguna.

## Struktur

```text
src/
  components/       Kartu, koleksi, loading/error, adapter player
  pages/            Beranda, katalog, detail, player, koleksi, jadwal, pengaturan
  services/         Axios dan normalisasi pesan error
  stores/           Pinia: watchlist, riwayat, preferensi
backend/app/
  core/             Konfigurasi dan database
  services/         HTTP metadata, cache, normalisasi, fallback
  api.py            Route API
  models.py         Model SQLAlchemy
  schemas.py        Validasi Pydantic
  repositories.py   Akses/serialisasi database
backend/tests/      Tes API dan metadata
```

Koneksi internet diperlukan untuk metadata, artwork, font eksternal, dan video hosted. Metadata yang pernah dimuat tetap tersedia saat penyedia gagal; artwork tidak dicache oleh backend.
