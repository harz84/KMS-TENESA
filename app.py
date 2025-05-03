import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# LangChain Imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
# ---- Tambahkan import ini ----
from langchain_openai import ChatOpenAI
# -----------------------------
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Muat variabel lingkungan
load_dotenv()
print("--- START DEBUG ---") # Tambahkan penanda
print(f"load_dotenv() executed. Return value: {load_dotenv()}") # Lihat apakah load_dotenv berhasil

# --- Konfigurasi ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# ---- Muat kunci DeepSeek ----
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# -----------------------------
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24)) # Muat secret key

# ---- Debug Print 2: Lihat nilai yang dibaca ----
print(f"Read GOOGLE_API_KEY: {'Exists' if GOOGLE_API_KEY else 'MISSING!'}")
key_display = f"'{OPENROUTER_API_KEY[:5]}...{OPENROUTER_API_KEY[-4:]}'" if OPENROUTER_API_KEY else "'None' or Empty"
print(f"Read OPENROUTER_API_KEY: '{OPENROUTER_API_KEY}'") # Tampilkan nilai persisnya
print(f"Read FLASK_SECRET_KEY: {'Exists' if FLASK_SECRET_KEY else 'MISSING / Generated fallback!'}")
print("--- END DEBUG ---")  
# -------------------------------------------------

# Cek Kunci API
if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY tidak ditemukan di .env")
if not OPENROUTER_API_KEY: 
    print("ERROR TRACE: Entering 'if not OPENROUTER_API_KEY:' block.") # Pesan debug spesifik
    raise ValueError("OPENROUTER_API_KEY tidak ditemukan di konfigurasi.") # Tetap raise error agar jelas
# -----------------------------


# Konfigurasi Google AI (jika ada kuncinya)
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error konfigurasi Google AI: {e}")

KNOWLEDGE_BASE_DIR = "knowledge_files"
FAISS_INDEX_PATH = "faiss_index"

# --- Inisialisasi Komponen LangChain (Embeddings saja dulu) ---
embeddings = None
if GOOGLE_API_KEY:
    try:
        # Tetap gunakan Google Embeddings untuk konsistensi Vector Store
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    except Exception as e:
        print(f"Error inisialisasi Google Embeddings: {e}")
else:
    print("ERROR: Google API Key diperlukan untuk Embeddings. Aplikasi mungkin tidak berfungsi.")


vectorstore = None

# ... (Fungsi load_vectorstore dan build_vectorstore tetap sama) ...
def load_vectorstore():
    global vectorstore
    if embeddings and os.path.exists(FAISS_INDEX_PATH):
        try:
            vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            print(f"Vector Store FAISS berhasil dimuat dari {FAISS_INDEX_PATH}")
            return True
        except Exception as e:
            print(f"Gagal memuat index FAISS: {e}")
            vectorstore = None
            return False
    return False

def build_vectorstore():
    global vectorstore
    if not embeddings:
        print("ERROR: Model Embeddings tidak terinisialisasi, tidak bisa membangun vector store.")
        return False
    pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"Tidak ada file PDF ditemukan di {KNOWLEDGE_BASE_DIR}. Vector Store tidak dibangun.")
        vectorstore = None
        return False
    print(f"Mulai membangun Vector Store dari {len(pdf_files)} file PDF...")
    documents = []
    for pdf_file in pdf_files:
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, pdf_file)
        try:
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
            print(f"  - Berhasil load: {pdf_file}")
        except Exception as e:
            print(f"  - Gagal load {pdf_file}: {e}")
    if not documents:
        print("Tidak ada dokumen yang berhasil di-load. Vector Store tidak dibangun.")
        vectorstore = None
        return False
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    texts = text_splitter.split_documents(documents)
    print(f"Total dokumen dipecah menjadi {len(texts)} chunks.")
    if not texts:
        print("Tidak ada teks setelah splitting. Vector Store tidak dibangun.")
        vectorstore = None
        return False
    try:
        print("Membuat index FAISS (mungkin perlu waktu)...")
        vectorstore = FAISS.from_documents(texts, embeddings)
        vectorstore.save_local(FAISS_INDEX_PATH)
        print(f"Vector Store FAISS berhasil dibangun dan disimpan di {FAISS_INDEX_PATH}")
        return True
    except Exception as e:
        print(f"Gagal membuat atau menyimpan index FAISS: {e}")
        vectorstore = None
        return False
# -----------------------------------------------------------

if not load_vectorstore():
    build_vectorstore()

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY # Gunakan secret key yang dimuat

# ... (Rute /login, /, /logout tetap sama) ...
VALID_USERS = { # ... (definisi user) ...
    "admin_kms": {"password": "TenesaAdmin!24", "role": "admin"},
    "agent001": {"password": "PasswordAgent#1", "role": "agent"}
}
@app.route('/login', methods=['GET', 'POST']) # ... (kode login) ...
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

@app.route('/') # ... (kode index) ...
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user_role = session.get('role', 'agent')
    return render_template('index.html', user_role=user_role)

@app.route('/logout') # ... (kode logout) ...
def logout():
    session.pop('username', None)
    session.pop('role', None)
    print("User logged out.")
    return redirect(url_for('login'))
# ---------------------------------------------


# --- Rute /ask dengan Logika Pemilihan Platform AI ---
@app.route('/ask', methods=['POST'])
def ask_ai():
    # 1. Cek otentikasi
    if 'username' not in session:
        return jsonify({"error": "Unauthorized - Silakan login kembali"}), 401

    # 2. Pastikan Vector Store sudah siap
    global vectorstore
    if vectorstore is None:
         if not load_vectorstore():
             if not build_vectorstore():
                 print("ERROR: Vector Store tidak tersedia dan tidak bisa dibangun.")
                 return jsonify({"error": "Knowledge base belum siap atau tidak ditemukan."}), 503

    # 3. Dapatkan pertanyaan dan pilihan platform dari request
    try:
        data = request.get_json()
        question = data.get('question')
        # ---- Ambil pilihan platform ----
        platform_choice = data.get('platform', 'gemini') # Default ke 'gemini' jika tidak dikirim
        # -------------------------------
        if not question:
             return jsonify({"error": "Pertanyaan tidak boleh kosong"}), 400
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({"error": "Format request tidak valid (JSON expected)"}), 400

    print(f"User '{session['username']}' bertanya: '{question}' menggunakan platform: '{platform_choice}'")

    # 4. Inisialisasi LLM berdasarkan pilihan platform
    llm = None
    try:
        if platform_choice == 'deepseek':
            if not OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY tidak ditemukan di konfigurasi.")
            # Gunakan ChatOpenAI tapi arahkan ke DeepSeek
            llm = ChatOpenAI(
                model="deepseek/deepseek-chat", # Model umum DeepSeek, cek dokumentasi DeepSeek jika perlu model spesifik
                api_key=OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1", # Pastikan URL base ini benar
                temperature=0.5, # Sesuaikan suhu sesuai keinginan
                default_headers={
                    "HTTP-Referer": request.url_root if request else "http://localhost:5000/",
                    "X-Title": "KMS TENESA"
                }
            )
            print("Menggunakan LLM: OpenRouter DeepSeek")

        elif platform_choice == 'gemini':
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY tidak ditemukan di konfigurasi.")
            # Gunakan model Gemini yang sudah berhasil sebelumnya
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5)
            print("Menggunakan LLM: Google Gemini")

        # --- Tambahkan blok elif untuk 'openai' jika diperlukan nanti ---
        # elif platform_choice == 'openai':
        #     OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        #     if not OPENAI_API_KEY:
        #          raise ValueError("OPENAI_API_KEY tidak ditemukan.")
        #     llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=OPENAI_API_KEY, temperature=0.5) # Contoh
        #     print("Menggunakan LLM: OpenAI GPT")
        # ---------------------------------------------------------------

        else:
            # Platform tidak dikenal
            return jsonify({"error": f"Platform AI tidak dikenal: {platform_choice}"}), 400

        if llm is None: # Jika karena alasan lain llm gagal diinisialisasi
            raise ValueError("Gagal menginisialisasi model LLM yang dipilih.")

    except Exception as e:
        print(f"Error saat inisialisasi LLM platform '{platform_choice}': {e}")
        return jsonify({"error": f"Gagal memuat model AI untuk platform {platform_choice}. Periksa konfigurasi API Key atau nama model."}), 500


    # 5. Implementasi RAG Chain (menggunakan LLM yang sudah dipilih)
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # Template prompt bisa tetap sama atau disesuaikan per model jika perlu
        template = """
        Anda adalah asisten AI untuk agent Customer Care TENESA.
        Jawab pertanyaan berikut HANYA berdasarkan konteks yang diberikan di bawah.
        JAWAB DENGAN RINGKAS DAN JELAS.
        Jika informasi tidak ada dalam konteks, katakan 'Maaf, informasi tersebut tidak ditemukan dalam knowledge base yang saya miliki saat ini.'
        Jangan mengarang jawaban.

        Konteks:
        {context}

        Pertanyaan: {question}

        Jawaban:
        """
        prompt = PromptTemplate.from_template(template)

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm # --> Gunakan LLM yang sudah dipilih (Gemini atau DeepSeek)
            | StrOutputParser()
        )

        print("Memulai proses RAG chain...")
        answer = rag_chain.invoke(question)
        print(f"Jawaban dari RAG Chain ({platform_choice}): {answer}")

        # 6. Kirim jawaban kembali
        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Error selama proses RAG dengan platform '{platform_choice}': {e}")
        return jsonify({"error": f"Terjadi kesalahan saat memproses pertanyaan dengan {platform_choice}: {e}. Coba beberapa saat lagi."}), 500


# ... (Rute /upload tetap sama) ...
@app.route('/upload', methods=['POST']) # ... (kode upload) ...
def upload_file():
    if 'username' not in session:
         return jsonify({"error": "Unauthorized - Silakan login kembali"}), 401
    if session.get('role') != 'admin':
        print(f"Upload ditolak: User '{session['username']}' (role: {session.get('role')}) bukan admin.")
        return jsonify({"error": "Akses ditolak - Hanya admin yang dapat mengunggah file"}), 403

    input_file_name = 'pdf-upload' # Sesuaikan jika nama di <input type="file" name="..."> berbeda
    if input_file_name not in request.files:
         print(f"Upload gagal: '{input_file_name}' tidak ditemukan dalam request.files")
         return jsonify({"error": f"Bagian file ('{input_file_name}') tidak ditemukan dalam request"}), 400

    file = request.files[input_file_name]

    if file.filename == '':
        print("Upload gagal: Tidak ada file yang dipilih.")
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if file and file.filename.endswith('.pdf'):
        filename = file.filename.replace('/','_').replace('\\','_')
        upload_folder = KNOWLEDGE_BASE_DIR
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, filename)

        try:
            file.save(file_path)
            print(f"Admin '{session['username']}' mengunggah file: {filename}")
            print(f"File disimpan di: {file_path}")

            print("Memulai pembangunan ulang Vector Store setelah upload...")
            if build_vectorstore():
                 message = f"File '{filename}' berhasil diunggah dan Knowledge Base telah diperbarui."
            else:
                 message = f"File '{filename}' berhasil diunggah, tetapi terjadi masalah saat memperbarui Knowledge Base. Coba lagi nanti atau periksa log."

            return jsonify({"message": message})

        except Exception as e:
            print(f"Error saat menyimpan atau memproses file {filename}: {e}")
            return jsonify({"error": f"Terjadi kesalahan saat memproses file: {e}"}), 500
    else:
        print(f"Upload gagal: Tipe file tidak valid ({file.filename}). Hanya PDF yang diizinkan.")
        return jsonify({"error": "Tipe file tidak valid, hanya file PDF yang diizinkan"}), 400
# ---------------------------------------------

# Menjalankan Aplikasi Flask
if __name__ == '__main__':
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        try:
            os.makedirs(KNOWLEDGE_BASE_DIR)
            print(f"Folder '{KNOWLEDGE_BASE_DIR}' dibuat.")
        except OSError as e:
            print(f"Error membuat folder '{KNOWLEDGE_BASE_DIR}': {e}")

    app.run(debug=True, host='0.0.0.0', port=5000)