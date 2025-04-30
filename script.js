// Referensi ke elemen-elemen penting di HTML
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const chatMessages = document.getElementById('chat-messages');
const pdfUpload = document.getElementById('pdf-upload');
const fileNameDisplay = document.getElementById('file-name');

// Fungsi untuk menambahkan pesan ke area chat
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');

    const bubbleDiv = document.createElement('div');
    bubbleDiv.classList.add('message-bubble');

    const paragraph = document.createElement('p');
    paragraph.textContent = text;

    bubbleDiv.appendChild(paragraph);
    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);

    // Auto-scroll ke pesan terbaru
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Fungsi untuk 'mengirim' pesan (saat ini hanya menampilkan & dummy AI response)
function sendMessage() {
    const messageText = messageInput.value.trim();

    if (messageText !== '') {
        // 1. Tampilkan pesan pengguna
        addMessage(messageText, 'user');

        // 2. Kosongkan input
        messageInput.value = '';

        // 3. (Placeholder) Tampilkan pesan loading/thinking AI
        const thinkingMessage = addMessage('KMS TENESA sedang berpikir...', 'ai');

        // 4. (Placeholder) Simulasikan jawaban AI setelah beberapa saat
        setTimeout(() => {
            // Hapus pesan "berpikir" (opsional)
             if(thinkingMessage) thinkingMessage.remove(); // Perlu cara menandai pesan ini

            // Ganti dengan logika pemanggilan API AI sebenarnya nanti
            const aiResponse = `Ini adalah contoh jawaban dari AI untuk pertanyaan: "${messageText}". Informasi detail akan diambil dari knowledge base PDF yang relevan.`;
            addMessage(aiResponse, 'ai');
        }, 1500); // Tunggu 1.5 detik
    }
}

// Event listener untuk tombol kirim
sendButton.addEventListener('click', sendMessage);

// Event listener untuk menekan Enter di input field
messageInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// Event listener untuk menampilkan nama file yang dipilih (sederhana)
pdfUpload.addEventListener('change', function() {
    if (pdfUpload.files.length > 0) {
        fileNameDisplay.textContent = pdfUpload.files[0].name;
    } else {
        fileNameDisplay.textContent = 'Belum ada file dipilih';
    }
});


// --- Navigasi Menu Sederhana (opsional, bisa disempurnakan) ---
// Ini hanya contoh sederhana, mungkin perlu logika lebih kompleks nanti
const menuItems = document.querySelectorAll('.menu-item');
const sidebarSections = document.querySelectorAll('.sidebar-section'); // Asumsikan section punya ID yg sama dgn href

menuItems.forEach(item => {
    item.addEventListener('click', function(e) {
        e.preventDefault(); // Mencegah pindah halaman standar

        // Hapus kelas active dari semua item
        menuItems.forEach(i => i.classList.remove('active'));
        // Tambahkan kelas active ke item yang diklik
        this.classList.add('active');

        // Dapatkan target section (misal dari href="#upload")
        const targetId = this.getAttribute('href');

        // Fokus ke area chat jika menu chat diklik
        if (targetId === '#chat') {
           document.getElementById('chat').scrollIntoView({ behavior: 'smooth' }); // atau fokus ke input
           messageInput.focus();
        } else {
            // Fokus ke section di sidebar (jika ada)
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                 targetSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    });
});


console.log("Frontend KMS TENESA siap (tampilan awal).");