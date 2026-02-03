/* static/js/clauwbot.js */
class ClauwbotUI {
    constructor() {
        this.isOpen = false;
        this.container = null;
        this.messagesContainer = null;
        this.input = null;
        this.init();
    }

    init() {
        // Create toggle button
        const toggle = document.createElement('div');
        toggle.className = 'clauwbot-toggle';
        toggle.innerHTML = '<i class="fa-solid fa-robot"></i>';
        toggle.onclick = () => this.toggle();
        document.body.appendChild(toggle);

        // Create chat container
        this.container = document.createElement('div');
        this.container.className = 'clauwbot-container hidden';
        this.container.innerHTML = `
            <div class="clauwbot-header">
                <div class="clauwbot-title">
                    <i class="fa-solid fa-bolt"></i>
                    <span>Clauwbot AI</span>
                </div>
                <div onclick="clauwbot.toggle()" style="cursor:pointer opacity:0.7">
                    <i class="fa-solid fa-xmark"></i>
                </div>
            </div>
            <div class="clauwbot-messages" id="clauwbot-msgs">
                <div class="message bot">Chào bạn! Tôi là Clauwbot. Tôi có thể giúp gì cho bạn hôm nay? Bạn có thể yêu cầu tôi tìm kiếm phim hoặc thông tin bất kỳ trên mạng.</div>
            </div>
            <div class="clauwbot-input-area">
                <input type="text" class="clauwbot-input" placeholder="Hỏi tôi bất cứ điều gì..." id="clauwbot-input">
                <div class="clauwbot-send" onclick="clauwbot.sendMessage()">
                    <i class="fa-solid fa-paper-plane"></i>
                </div>
            </div>
        `;
        document.body.appendChild(this.container);
        this.messagesContainer = document.getElementById('clauwbot-msgs');
        this.input = document.getElementById('clauwbot-input');

        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    toggle() {
        this.isOpen = !this.isOpen;
        this.container.classList.toggle('hidden', !this.isOpen);
        if (this.isOpen) this.input.focus();
    }

    addMessage(text, isUser = false) {
        const msg = document.createElement('div');
        msg.className = `message ${isUser ? 'user' : 'bot'}`;
        msg.textContent = text;
        this.messagesContainer.appendChild(msg);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        return msg;
    }

    showThinking() {
        const thinking = document.createElement('div');
        thinking.className = 'message bot thinking-container';
        thinking.innerHTML = `
            <div class="thinking">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        this.messagesContainer.appendChild(thinking);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        return thinking;
    }

    async sendMessage() {
        const text = this.input.value.trim();
        if (!text) return;

        this.input.value = '';
        this.addMessage(text, true);

        const thinking = this.showThinking();

        try {
            const resp = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await resp.json();

            thinking.remove();
            if (data.status === 'ok') {
                this.addMessage(data.answer);
            } else {
                this.addMessage("Có lỗi xảy ra: " + (data.msg || "Không xác định"));
            }
        } catch (err) {
            thinking.remove();
            this.addMessage("Không thể kết nối với máy chủ AI.");
        }
    }
}

const clauwbot = new ClauwbotUI();
window.clauwbot = clauwbot;
