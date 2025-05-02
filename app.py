import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import google.generativeai as genai # Import library Google AI

# LangChain Imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA # Cara klasik untuk RAG
from langchain.prompts import PromptTemplate # Untuk kustomisasi prompt
# Alternatif modern menggunakan LCEL (LangChain Expression Language)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Muat variabel lingkungan dari file .env
load_dotenv()

# --- Konfigurasi ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY tidak ditemukan di .env")
    # exit() # Sebaiknya hentikan aplikasi jika kunci API tidak ada

# Konfigurasi Google AI
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error konfigurasi Google AI: {e}")
    # Mungkin ingin menangani ini lebih lanjut

KNOWLEDGE_BASE_DIR = "knowledge_files"
FAISS_INDEX_PATH = "faiss_index" # Nama folder untuk menyimpan index FAISS

# --- Inisialisasi Komponen LangChain (Global) ---
# Sebaiknya inisialisasi sekali saja untuk efisiensi
try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001") # Atau model embedding lain yang sesuai
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, convert_system_message_to_human=True)
except Exception as e:
    print(f"Error inisialisasi model Google AI (Embeddings/LLM): {e}")
    embeddings = None
    llm = None

vectorstore = None # Akan di-load atau dibuat nanti

# --- Fungsi Helper untuk Vector Store ---

def load_vectorstore():
    """Mencoba memuat Vector Store FAISS dari disk."""
    global vectorstore
    if embeddings and os.path.exists(FAISS_INDEX_PATH):
        try:
            # Penting: allow_dangerous_deserialization=True sering dibutuhkan saat load index dengan embeddings custom/API
            vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            print(f"Vector Store FAISS berhasil dimuat dari {FAISS_INDEX_PATH}")
            return True
        except Exception as e:
            print(f"Gagal memuat index FAISS: {e}")
            vectorstore = None
            return False
    return False

def build_vectorstore():
    """Membangun Vector Store FAISS dari PDF di KNOWLEDGE_BASE_DIR."""
    global vectorstore
    if not embeddings:
        print("ERROR: Model Embeddings tidak terinisialisasi, tidak bisa membangun vector store.")
        return False

    pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"Tidak ada file PDF ditemukan di {KNOWLEDGE_BASE_DIR}. Vector Store tidak dibangun.")
        vectorstore = None # Pastikan vectorstore kosong jika tidak ada file
        return False

    print(f"Mulai membangun Vector Store dari {len(pdf_files)} file PDF...")
    documents = []
    for pdf_file in pdf_files:
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, pdf_file)
        try:
            loader = PyPDFLoader(file_path)
            # Load dan pecah dokumen menjadi halaman
            # Untuk file besar, pertimbangkan load_and_split() atau cara lain
            documents.extend(loader.load())
            print(f"  - Berhasil load: {pdf_file}")
        except Exception as e:
            print(f"  - Gagal load {pdf_file}: {e}")

    if not documents:
        print("Tidak ada dokumen yang berhasil di-load. Vector Store tidak dibangun.")
        vectorstore = None
        return False

    # Pecah teks dokumen menjadi chunks yang lebih kecil
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    texts = text_splitter.split_documents(documents)
    print(f"Total dokumen dipecah menjadi {len(texts)} chunks.")

    if not texts:
        print("Tidak ada teks setelah splitting. Vector Store tidak dibangun.")
        vectorstore = None
        return False

    try:
        # Buat index FAISS dari chunks dan model embeddings
        print("Membuat index FAISS (mungkin perlu waktu)...")
        vectorstore = FAISS.from_documents(texts, embeddings)

        # Simpan index ke disk untuk penggunaan selanjutnya
        vectorstore.save_local(FAISS_INDEX_PATH)
        print(f"Vector Store FAISS berhasil dibangun dan disimpan di {FAISS_INDEX_PATH}")
        return True
    except Exception as e:
        print(f"Gagal membuat atau menyimpan index FAISS: {e}")
        vectorstore = None
        return False

# --- Coba muat atau bangun Vector Store saat aplikasi dimulai ---
if not load_vectorstore():
    build_vectorstore()

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# ... (Kode VALID_USERS, /login, /logout tetap sama) ...
VALID_USERS = {
    "admin_kms": {"password": "TenesaAdmin!24", "role": "admin"},
    "agent001": {"password": "PasswordAgent#1", "role": "agent"}
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = VALID_USERS.get(username)
        if user_data and user_data['password'] == password:
            session['username'] = username
            session['role'] = user_data['role']
            print(f"Login berhasil: User '{username}', Role: '{session['role']}'")
            return redirect(url_for('index'))
        else:
            error = "Username atau password salah. Silakan coba lagi."
            print(f"Login gagal untuk user: '{username}'")
    return render_template('login.html', error=error)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user_role = session.get('role', 'agent')
    return render_template('index.html', user_role=user_role)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    print("User logged out.")
    return redirect(url_for('login'))


# --- Rute /ask dengan Logika RAG ---
@app.route('/ask', methods=['POST'])
def ask_ai():
    # 1. Cek otentikasi
    if 'username' not in session:
        return jsonify({"error": "Unauthorized - Silakan login kembali"}), 401

    # 2. Pastikan Vector Store sudah siap
    global vectorstore
    if vectorstore is None:
         # Coba load/build lagi jika belum ada (misalnya jika build awal gagal)
         if not load_vectorstore():
             if not build_vectorstore():
                 print("ERROR: Vector Store tidak tersedia dan tidak bisa dibangun.")
                 return jsonify({"error": "Knowledge base belum siap atau tidak ditemukan. Silakan upload dokumen PDF."}), 503 # 503 Service Unavailable

    # 3. Dapatkan pertanyaan dari request
    try:
        data = request.get_json()
        question = data.get('question')
        if not question:
             return jsonify({"error": "Pertanyaan tidak boleh kosong"}), 400
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({"error": "Format request tidak valid (JSON expected)"}), 400

    print(f"User '{session['username']}' bertanya: '{question}'")

    # 4. Implementasi RAG Chain menggunakan LCEL (Lebih modern)
    try:
        if not llm:
             raise ValueError("Model LLM (Gemini) tidak terinisialisasi.")

        # Buat retriever dari vector store
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # Ambil 3 dokumen teratas

        # Definisikan template prompt
        template = """
        Anda adalah asisten AI untuk agent Customer Care TENESA.
        Jawab pertanyaan berikut HANYA berdasarkan konteks yang diberikan di bawah.
        Jika informasi tidak ada dalam konteks, katakan 'Maaf, informasi tersebut tidak ditemukan dalam knowledge base yang saya miliki saat ini.'
        Jangan mencoba mengarang jawaban.

        Konteks:
        {context}

        Pertanyaan: {question}

        Jawaban:
        """
        prompt = PromptTemplate.from_template(template)

        # Helper function untuk format dokumen yang diambil retriever
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Bangun RAG chain menggunakan LCEL
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        print("Memulai proses RAG chain...")
        # Invoke chain untuk mendapatkan jawaban
        answer = rag_chain.invoke(question)
        print(f"Jawaban dari RAG Chain: {answer}")

        # 5. Kirim jawaban kembali ke frontend
        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Error selama proses RAG: {e}")
        # Mengirim pesan error yang lebih umum ke pengguna
        return jsonify({"error": f"Terjadi kesalahan saat memproses pertanyaan: {e}. Coba beberapa saat lagi."}), 500


# ... (Rute /upload tetap sama untuk saat ini, fokus di /ask dulu) ...
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
         return jsonify({"error": "Unauthorized - Silakan login kembali"}), 401
    if session.get('role') != 'admin':
        print(f"Upload ditolak: User '{session['username']}' (role: {session.get('role')}) bukan admin.")
        return jsonify({"error": "Akses ditolak - Hanya admin yang dapat mengunggah file"}), 403

    # Gunakan nama input file yang konsisten dengan HTML Anda
    input_file_name = 'pdf-upload' # Sesuaikan jika nama di <input type="file" name="..."> berbeda
    if input_file_name not in request.files:
         print(f"Upload gagal: '{input_file_name}' tidak ditemukan dalam request.files")
         return jsonify({"error": "Bagian file ('pdf-upload') tidak ditemukan dalam request"}), 400

    file = request.files[input_file_name]

    if file.filename == '':
        print("Upload gagal: Tidak ada file yang dipilih.")
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if file and file.filename.endswith('.pdf'):
        filename = file.filename.replace('/','_').replace('\\','_')
        upload_folder = KNOWLEDGE_BASE_DIR # Gunakan konstanta
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, filename)

        try:
            file.save(file_path)
            print(f"Admin '{session['username']}' mengunggah file: {filename}")
            print(f"File disimpan di: {file_path}")

            # --- TRIGGER PEMBANGUNAN ULANG VECTOR STORE SETELAH UPLOAD ---
            print("Memulai pembangunan ulang Vector Store setelah upload...")
            if build_vectorstore():
                 message = f"File '{filename}' berhasil diunggah dan Knowledge Base telah diperbarui."
            else:
                 message = f"File '{filename}' berhasil diunggah, tetapi terjadi masalah saat memperbarui Knowledge Base. Coba lagi nanti atau periksa log."
            # -------------------------------------------------------------

            return jsonify({"message": message})

        except Exception as e:
            print(f"Error saat menyimpan atau memproses file {filename}: {e}")
            return jsonify({"error": f"Terjadi kesalahan saat memproses file: {e}"}), 500

    else:
        print(f"Upload gagal: Tipe file tidak valid ({file.filename}). Hanya PDF yang diizinkan.")
        return jsonify({"error": "Tipe file tidak valid, hanya file PDF yang diizinkan"}), 400


# Menjalankan Aplikasi Flask
if __name__ == '__main__':
    # Pastikan folder knowledge_files ada saat startup
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        try:
            os.makedirs(KNOWLEDGE_BASE_DIR)
            print(f"Folder '{KNOWLEDGE_BASE_DIR}' dibuat.")
        except OSError as e:
            print(f"Error membuat folder '{KNOWLEDGE_BASE_DIR}': {e}")

    app.run(debug=True, host='0.0.0.0', port=5000) # Tentukan port jika perlu