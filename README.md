# 3D Rotating Planet with Orbit

## Judul Proyek

3D Rotating Planet with Orbit

## Sumber Proyek

Dikembangkan berdasarkan inspirasi dari dokumentasi resmi ModernGL (https://moderngl.readthedocs.io) dan contoh-contoh komunitas OpenGL Python (mis. rotating sphere example di GitHub).

## Hasil Program

Setelah dijalankan, akan muncul jendela 3D berisi:

- Sebuah matahari kecil di tengah (sphere statis).
- Sebuah planet bertekstur bumi yang:
  - Berotasi pada porosnya.
  - Bergerak mengelilingi matahari secara halus (orbit).
- Kamera menampilkan pandangan orbit dari sudut miring (perspektif).

Efek 3D terlihat karena proyeksi perspektif dan rotasi kontinu.

## Berkas Utama

- `program.py` — kode aplikasi ModernGL yang menampilkan sun + textured planet.

## Dependensi

Proyek ini menggunakan paket Python berikut:

- modernGL / `moderngl`
- modernGL-window / `moderngl-window`
- `pyrr`
- `Pillow` (PIL)
- `numpy`

Untuk kemudahan instalasi, gunakan `requirements.txt` yang disertakan.

## Menjalankan (Windows PowerShell)

1. Buat virtual environment (opsional tetapi disarankan):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Pasang dependensi:

```powershell
python -m pip install -r requirements.txt
```

3. Pastikan file tekstur tersedia. Program saat ini membuka tekstur dengan:

```python
img = Image.open(mglw.resources.data_dir / "earthmap1k2.jpg")
```

Jika mengalami error karena tidak menemukan tekstur, lakukan salah satu dari dua opsi berikut:

- Unduh `earthmap1k2.jpg` (contoh: dari repositori contoh ModernGL) dan letakkan di folder project yang sama, lalu ubah baris tersebut menjadi:

```python
img = Image.open("earthmap1k2.jpg").transpose(Image.FLIP_TOP_BOTTOM)
```

- Atau salin `earthmap1k2.jpg` ke direktori data ModernGL Window resources (tidak umum untuk pemula).

4. Jalankan program:

```powershell
python program.py
```

Jendela OpenGL akan muncul menampilkan matahari dan planet yang mengorbit.

## Catatan

- Jika jendela tidak muncul atau ada error terkait OpenGL, pastikan driver GPU Anda sudah terpasang/terupdate dan sistem mendukung OpenGL 3.3.
- Jika menggunakan WSL, GUI OpenGL harus di-forward ke host; lebih mudah menjalankan di Windows native.