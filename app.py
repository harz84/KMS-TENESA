import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

# Muat variabel dari file .env (untuk API Key)
load_dotenv()

app = Flask(__name__)
# Perlu secret key untuk menggunakan session (ganti dengan key acak Anda nanti)
app.secret_key = os.urandom(24)

# --- Simulasi Data User (HARUS diganti Database nanti) ---
VALID_USERS = {
    "admin_kms": {"password": "TenesaAdmin!24", "role": "admin"},
    "agent001": {"password": "PasswordAgent#1", "role": "agent"}
}
# --------------------------------------------------------

# Rute untuk Halaman Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # --- Validasi User (Simulasi) ---
        user_data = VALID_USERS.get(username)
        if user_data and user_data['password'] == password:
            # Simpan info user di session
            session['username'] = username
            session['role'] = user_data['role']
            print(f"Login berhasil: {username}, Role: {session['role']}") # Log Sederhana
            return redirect(url_for('index')) # Arahkan ke halaman utama
        else:
            error = "Username atau password salah."
            return render_template('login.html', error=error)
        # ---------------------------------

    # Jika metode GET, tampilkan halaman login
    # Jika sudah login, redirect ke index
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# Rute untuk Halaman Utama Aplikasi (setelah login)
@app.route('/')
def index():
    # Cek apakah user sudah login (ada session)
    if 'username' not in session:
        return redirect(url_for('login')) # Belum login, paksa ke login

    # Jika sudah login, tampilkan halaman utama
    # Kirim peran user ke template agar bisa atur privilege di frontend (misal sembunyikan tombol upload)
    user_role = session.get('role', 'agent') # Default ke agent jika role tidak ada
    return render_template('index.html', user_role=user_role)

# Rute untuk Logout
@app.route('/logout')
def logout():
    session.pop('username', None) # Hapus username dari session
    session.pop('role', None)     # Hapus role dari session
    return redirect(url_for('login')) # Arahkan kembali ke login

# --- Rute untuk Fungsi Inti (akan ditambahkan nanti) ---
@app.route('/ask', methods=['POST'])
def ask_ai():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    question = request.json.get('question')
    # TODO:
    # 1. Ambil AI platform choice dari request (jika diimplementasikan)
    # 2. Proses pertanyaan menggunakan RAG (cari di vector store, panggil LLM)
    # 3. Dapatkan jawaban dari AI
    print(f"Menerima pertanyaan: {question}") # Log Sederhana

    # --- Jawaban Dummy ---
    ai_response = f"Ini jawaban dummy dari backend untuk: '{question}'. Logika AI belum diimplementasikan."
    # --------------------

    return jsonify({"answer": ai_response})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
         return jsonify({"error": "Unauthorized"}), 401
    if session.get('role') != 'admin': # Hanya admin yang boleh upload
        return jsonify({"error": "Forbidden - Admin access required"}), 403

    if 'pdf-file' not in request.files:
         return jsonify({"error": "No file part"}), 400
    file = request.files['pdf-file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.pdf'):
        # TODO:
        # 1. Simpan file PDF ke folder 'knowledge_files'
        # 2. Proses file PDF (baca, pecah, embed, simpan ke vector store)
        filename = file.filename # Ambil nama file asli
        print(f"Menerima file PDF: {filename}") # Log Sederhana
        # Contoh simpan (perlu pastikan folder 'knowledge_files' ada):
        # file_path = os.path.join('knowledge_files', filename)
        # file.save(file_path)
        # print(f"File disimpan di: {file_path}")
        # Lanjutkan dengan proses ingestion...

         # --- Respon Dummy ---
        return jsonify({"message": f"File '{filename}' diterima. Proses Ingestion perlu diimplementasikan."})
         # --------------------
    else:
         return jsonify({"error": "Invalid file type, only PDF allowed"}), 400


# Menjalankan Aplikasi Flask
if __name__ == '__main__':
    # Pastikan folder knowledge_files ada
    if not os.path.exists('knowledge_files'):
        os.makedirs('knowledge_files')
    # Jalankan dalam mode debug untuk pengembangan
    app.run(debug=True)