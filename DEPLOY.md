# Panduan Deployment Sinabung Monitoring di Ubuntu VPS

Berikut adalah langkah-langkah untuk mendeploy aplikasi ini ke server produksi Ubuntu.

## 1. Persiapan Server & Git
1. Pastikan Anda sudah masuk ke VPS Ubuntu Anda (via SSH).
2. Clone atau transfer direktori `sinabung-monitoring` ini ke server Anda. 
   Disarankan diletakkan di direktori seperti `/var/www/asetpedia/sinabung-monitoring` atau `/home/ubuntu/sinabung-monitoring`.

## 2. Install Python dan Virtual Environment
Jalankan perintah berikut di VPS Anda:
```bash
sudo apt update
sudo apt install python3-pip python3-venv
```

Masuk ke folder aplikasi dan buat virtual environment:
```bash
cd /path/ke/folder/sinabung-monitoring
python3 -m venv venv
source venv/bin/activate
```

Install semua dependencies dari `requirements.txt`:
```bash
pip install -r requirements.txt
```

## 3. Konfigurasi Environment (`.env`)
Salin template konfigurasi:
```bash
cp .env.example .env
nano .env
```
Isi konfigurasi Anda (seperti kredensial DB dan Token Telegram) di dalam file `.env` tersebut.
Pastikan file `.env` tidak terunggah ke Git.

## 4. Setup Systemd Service (Gunicorn)
Agar aplikasi dapat berjalan di latar belakang (background) dan otomatis *restart* apabila server VPS di-*reboot*, kita menggunakan `systemd` dan `gunicorn`.

1. Buka file `sinabung-monitoring.service` yang telah disiapkan.
2. Sesuaikan **User**, **Group**, **WorkingDirectory**, dan **ExecStart** (pastikan path-nya benar sesuai dengan lokasi folder di VPS Anda).
3. Salin file service tersebut ke direktori systemd:
   ```bash
   sudo cp sinabung-monitoring.service /etc/systemd/system/
   ```

## 5. Menjalankan dan Mengaktifkan Service
Reload *daemon* systemd dan aktifkan aplikasi Anda:
```bash
sudo systemctl daemon-reload
sudo systemctl start sinabung-monitoring
sudo systemctl enable sinabung-monitoring
```

Cek status apakah aplikasi sudah berjalan dengan normal:
```bash
sudo systemctl status sinabung-monitoring
```

## 6. Selesai
Monitoring aplikasi kini bisa diakses melalui IP VPS Anda (misal `http://IP-VPS-ANDA:9000`).
*Catatan*: Jika Anda ingin menghubungkannya dengan domain menggunakan SSL, Anda bisa melakukan *Reverse Proxy* menggunakan Nginx.
