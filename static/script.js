// Tunggu hingga seluruh konten HTML dimuat sebelum menjalankan script
document.addEventListener('DOMContentLoaded', () => {

    // Referensi ke elemen-elemen penting di HTML
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');

    // --- Referensi untuk Fitur Upload (akan digunakan nanti) ---
    const uploadInput = document.getElementById('pdf-upload'); // Pastikan ID ini ada di index.html
    const uploadButton = document.querySelector('.btn-upload'); // Tombol 'Unggah Sekarang'
    const fileNameDisplay = document.getElementById('file-name');
    const uploadSection = document.getElementById('upload'); // Sidebar section untuk upload

    if (!messageInput || !sendButton || !chatMessages) {
        console.error("Error: Elemen chat penting tidak ditemukan!");
        return; // Hentikan script jika elemen dasar tidak ada
    }

    // Fungsi untuk menambahkan pesan ke area chat
    function addMessage(text, sender, messageId = null, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
        if (messageId) {
            messageDiv.id = messageId; // Beri ID jika perlu (misal: untuk pesan 'thinking')
        }
        if (isError) {
            messageDiv.classList.add('error-message-chat'); // Tambahkan kelas untuk styling error
        }


        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('message-bubble');

        // Jika ini pesan error dari AI, beri indikasi
        if (isError && sender === 'ai') {
            bubbleDiv.innerHTML = `<i class="fas fa-exclamation-triangle error-icon"></i> <p>${text}</p>`; // Tambahkan ikon error
        } else {
            const paragraph = document.createElement('p');
            paragraph.textContent = text; // Gunakan textContent agar aman dari XSS
            bubbleDiv.appendChild(paragraph);
        }


        messageDiv.appendChild(bubbleDiv);
        chatMessages.appendChild(messageDiv);

        // Auto-scroll ke pesan terbaru
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return messageDiv; // Kembalikan elemen pesan jika perlu dimanipulasi
    }

    // Fungsi utama untuk mengirim pesan ke backend
    async function sendMessage() {
        const messageText = messageInput.value.trim();

        if (messageText === '') {
            return; // Jangan kirim pesan kosong
        }

        // 1. Tampilkan pesan pengguna segera
        addMessage(messageText, 'user');

        // 2. Kosongkan input dan beri fokus kembali
        messageInput.value = '';
        messageInput.focus(); // Fokus kembali ke input setelah kirim

        // 3. Tampilkan indikator 'berpikir...' & disable input/button
        const thinkingMessageId = 'thinking-' + Date.now(); // ID unik
        const thinkingElement = addMessage('KMS TENESA sedang memproses...', 'ai', thinkingMessageId);
        messageInput.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Ganti ikon jadi loading

        try {
            // 4. Kirim request ke backend '/ask'
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: messageText }), // Kirim pertanyaan dalam format JSON
            });

            // 5. Hapus pesan 'berpikir...'
            const thinkingMsgElement = document.getElementById(thinkingMessageId);
            if (thinkingMsgElement) {
                thinkingMsgElement.remove();
            }

            // 6. Tangani response dari backend
            if (response.ok) {
                const data = await response.json();
                if (data.answer) {
                    // Tampilkan jawaban AI jika sukses
                    addMessage(data.answer, 'ai');
                } else if (data.error) {
                    // Tampilkan pesan error dari backend (jika ada)
                    console.error('Backend error:', data.error);
                    addMessage(`Error dari server: ${data.error}`, 'ai', null, true);
                } else {
                    // Kasus aneh jika tidak ada jawaban atau error
                     addMessage("Menerima respons kosong dari server.", 'ai', null, true);
                }
            } else {
                // Tangani error HTTP (misal: 401 Unauthorized, 403 Forbidden, 500 Internal Server Error)
                let errorText = `Error ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json(); // Coba dapatkan detail error dari body JSON
                    errorText = `Error ${response.status}: ${errorData.error || response.statusText}`;
                } catch (e) {
                    // Biarkan errorText seperti semula jika body bukan JSON atau kosong
                }
                console.error('HTTP error:', errorText);
                addMessage(errorText, 'ai', null, true); // Tampilkan pesan error HTTP
            }

        } catch (error) {
            // Tangani error network atau error lainnya saat fetch
            console.error('Fetch error:', error);
             // Hapus pesan 'berpikir...' jika masih ada saat error network
            const thinkingMsgElement = document.getElementById(thinkingMessageId);
            if (thinkingMsgElement) {
                thinkingMsgElement.remove();
            }
            addMessage(`Tidak dapat terhubung ke server atau terjadi kesalahan jaringan. (${error.message})`, 'ai', null, true);
        } finally {
            // 7. Aktifkan kembali input dan tombol, apapun hasilnya
            messageInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>'; // Kembalikan ikon kirim
             messageInput.focus(); // Fokus kembali
        }
    }

    // --- Event Listeners ---

    // Klik tombol kirim
    sendButton.addEventListener('click', sendMessage);

    // Tekan Enter di input field
    messageInput.addEventListener('keypress', (event) => {
        // Pastikan tombol Shift tidak sedang ditekan (untuk multiline jika diimplementasikan)
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Mencegah baris baru default di beberapa browser
            sendMessage();
        }
    });


    // --- Logika Upload (Placeholder - Akan diimplementasikan lebih lanjut) ---
    if (uploadInput && uploadButton && fileNameDisplay && uploadSection) {
        // Menampilkan nama file saat dipilih
        uploadInput.addEventListener('change', function() {
            if (uploadInput.files.length > 0) {
                fileNameDisplay.textContent = uploadInput.files[0].name;
            } else {
                fileNameDisplay.textContent = 'Belum ada file dipilih';
            }
        });

        // Menangani klik tombol 'Unggah Sekarang'
        uploadButton.addEventListener('click', async () => {
            if (uploadInput.files.length === 0) {
                alert('Silakan pilih file PDF terlebih dahulu.');
                return;
            }

            const file = uploadInput.files[0];
            const formData = new FormData();
            // Penting: Nama field ('pdf-upload') harus cocok dengan yang diharapkan backend di request.files[...]
            formData.append('pdf-upload', file);

            // Tambahkan indikator loading di tombol upload
            uploadButton.disabled = true;
            uploadButton.textContent = 'Mengunggah...';

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData, // Kirim sebagai FormData, bukan JSON
                    // Headers tidak perlu Content-Type, browser akan set otomatis untuk FormData
                });

                const data = await response.json(); // Tanggapan backend diharapkan JSON

                if (response.ok) {
                    alert(`Sukses: ${data.message}`); // Tampilkan pesan sukses dari backend
                    fileNameDisplay.textContent = 'Belum ada file dipilih'; // Reset tampilan nama file
                    uploadInput.value = ''; // Reset input file
                } else {
                     alert(`Error: ${data.error || response.statusText}`); // Tampilkan pesan error
                }

            } catch (error) {
                console.error('Upload fetch error:', error);
                alert(`Gagal mengunggah file: Terjadi kesalahan jaringan. (${error.message})`);
            } finally {
                // Kembalikan state tombol upload
                 uploadButton.disabled = false;
                 uploadButton.textContent = 'Unggah Sekarang';
            }
        });
    } else {
         console.warn("Elemen untuk fitur upload tidak ditemukan sepenuhnya.");
    }

    // --- Logika Tambahan (misal: navigasi menu, penyesuaian UI berdasarkan role) ---
    // Anda bisa menambahkan logika untuk menyembunyikan tombol upload jika user_role bukan 'admin'
    // (Perlu meneruskan user_role dari template Jinja2 ke JavaScript, misal via data attribute)

    console.log("KMS TENESA Frontend Script Loaded.");

}); // Akhir dari DOMContentLoaded