import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env (untuk API Key dll)
load_dotenv()

app = Flask(__name__)

# Konfigurasi Secret Key untuk Session
# Penting: Ganti dengan key yang kuat dan acak di production, bisa dari environment variable
# os.urandom(24) baik untuk development tapi akan berubah setiap restart server
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Simulasi Data User (Ganti dengan Database di production) ---
VALID_USERS = {
    "admin_kms": {"password": "TenesaAdmin!24", "role": "admin"},
    "agent001": {"password": "PasswordAgent#1", "role": "agent"}
}
# ---------------------------------------------------------------

# Rute untuk Halaman Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None # Inisialisasi pesan error

    # Jika user sudah login, langsung redirect ke halaman utama
    if 'username' in session:
        return redirect(url_for('index'))

    # Tangani jika metode POST (pengiriman form)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validasi user (contoh sederhana)
        user_data = VALID_USERS.get(username)
        if user_data and user_data['password'] == password:
            # Simpan informasi user ke session
            session['username'] = username
            session['role'] = user_data['role']
            # session.permanent = True # Uncomment jika ingin sesi lebih tahan lama
            print(f"Login berhasil: User '{username}', Role: '{session['role']}'") # Log server
            return redirect(url_for('index')) # Redirect ke halaman utama setelah login sukses
        else:
            error = "Username atau password salah. Silakan coba lagi."
            print(f"Login gagal untuk user: '{username}'") # Log server

    # Jika metode GET atau login POST gagal, tampilkan halaman login
    # Kirim variabel error ke template (akan None jika GET atau login sukses)
    return render_template('login.html', error=error)

# Rute untuk Halaman Utama Aplikasi ('/')
@app.route('/')
def index():
    # Cek apakah user sudah login (ada session 'username')
    if 'username' not in session:
        # Jika belum login, redirect ke halaman login
        return redirect(url_for('login'))

    # Jika sudah login, tampilkan halaman utama
    # Ambil peran user dari session untuk mengatur tampilan di frontend
    user_role = session.get('role', 'agent') # Default ke 'agent' jika role tidak ada
    return render_template('index.html', user_role=user_role)

# Rute untuk Logout
@app.route('/logout')
def logout():
    # Hapus informasi user dari session
    session.pop('username', None)
    session.pop('role', None)
    print("User logged out.") # Log server
    # Redirect kembali ke halaman login
    return redirect(url_for('login'))

# --- Rute Placeholder untuk Fitur Inti ---

@app.route('/ask', methods=['POST'])
def ask_ai():
    # 1. Cek otentikasi (apakah user sudah login?)
    if 'username' not in session:
        return jsonify({"error": "Unauthorized - Silakan login kembali"}), 401

    # 2. Dapatkan data dari request
    try:
        data = request.get_json()
        question = data.get('question')
        if not question:
             return jsonify({"error": "Pertanyaan tidak boleh kosong"}), 400
        # ai_platform = data.get('ai_platform', 'gemini') # Contoh ambil pilihan AI
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({"error": "Format request tidak valid (JSON expected)"}), 400

    print(f"User '{session['username']}' bertanya: '{question}'") # Log server

    # 3. TODO: Implementasikan logika RAG (Retrieval-Augmented Generation) di sini
    #    - Load vector store (FAISS)
    #    - Cari dokumen relevan berdasarkan `question`
    #    - Buat prompt untuk LLM (misal: Gemini) dengan konteks
    #    - Panggil API LLM
    #    - Dapatkan jawaban

    # --- Jawaban Dummy (Ganti dengan jawaban AI asli) ---
    ai_response = f"Ini jawaban dari KMS TENESA (sementara): Untuk pertanyaan '{question}', informasi detail akan segera diimplementasikan menggunakan knowledge base."
    # ----------------------------------------------------

    # 4. Kirim jawaban kembali ke frontend
    return jsonify({"answer": ai_response})

@app.route('/upload', methods=['POST'])
def upload_file():
    # 1. Cek otentikasi
    if 'username' not in session:
         return jsonify({"error": "Unauthorized - Silakan login kembali"}), 401

    # 2. Cek otorisasi (hanya admin yang boleh upload)
    if session.get('role') != 'admin':
        print(f"Upload ditolak: User '{session['username']}' (role: {session.get('role')}) bukan admin.") # Log server
        return jsonify({"error": "Akses ditolak - Hanya admin yang dapat mengunggah file"}), 403

    # 3. Proses file upload
    if 'pdf-upload-input' not in request.files: # Pastikan 'name' input file di HTML sesuai
         print("Upload gagal: 'pdf-upload-input' tidak ditemukan dalam request.files")
         return jsonify({"error": "Bagian file tidak ditemukan dalam request"}), 400

    file = request.files['pdf-upload-input'] # Gunakan 'name' dari input file HTML

    if file.filename == '':
        print("Upload gagal: Tidak ada file yang dipilih.")
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if file and file.filename.endswith('.pdf'):
        # Amankan nama file (contoh sederhana, bisa gunakan Werkzeug)
        filename = file.filename.replace('/','_').replace('\\','_') # Hindari path traversal dasar
        upload_folder = 'knowledge_files'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, filename)

        try:
            file.save(file_path)
            print(f"Admin '{session['username']}' mengunggah file: {filename}") # Log server
            print(f"File disimpan di: {file_path}")

            # 4. TODO: Implementasikan proses INGESTION (baca, pecah, embed, simpan ke vector store)
            #    - Panggil fungsi khusus untuk memproses file PDF di `file_path`

            # --- Respon Dummy (Ganti dengan status ingestion) ---
            return jsonify({"message": f"File '{filename}' berhasil diunggah. Proses analisis konten perlu diimplementasikan."})
            # ----------------------------------------------------

        except Exception as e:
            print(f"Error saat menyimpan atau memproses file {filename}: {e}")
            return jsonify({"error": f"Terjadi kesalahan saat memproses file: {e}"}), 500

    else:
        print(f"Upload gagal: Tipe file tidak valid ({file.filename}). Hanya PDF yang diizinkan.")
        return jsonify({"error": "Tipe file tidak valid, hanya file PDF yang diizinkan"}), 400


# Menjalankan Aplikasi Flask
if __name__ == '__main__':
    # Pastikan folder knowledge_files ada saat startup
    if not os.path.exists('knowledge_files'):
        try:
            os.makedirs('knowledge_files')
            print("Folder 'knowledge_files' dibuat.")
        except OSError as e:
            print(f"Error membuat folder 'knowledge_files': {e}")

    # Jalankan dalam mode debug untuk pengembangan (aktifkan auto-reload dan debugger)
    # Host '0.0.0.0' agar bisa diakses dari IP lain di jaringan lokal (opsional)
    app.run(debug=True, host='0.0.0.0')