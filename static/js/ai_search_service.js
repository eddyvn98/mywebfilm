import { state } from './state.js';
import { renderGrid } from './render_service.js';

export async function runAiSearch() {
    const searchInput = document.getElementById('search');
    const query = searchInput.value.trim();
    if (!query) return;

    // Show loading state
    const grid = document.getElementById('video-grid');
    const oldHtml = grid.innerHTML;
    grid.innerHTML = `
        <div class="col-span-full py-40 flex flex-col items-center justify-center space-y-4 animate-pulse">
            <div class="w-16 h-16 rounded-full bg-blue-600/20 flex items-center justify-center">
                <i class="fa-solid fa-robot text-blue-500 text-3xl animate-bounce"></i>
            </div>
            <p class="text-blue-500 font-black text-xs uppercase tracking-[0.2em]">AI đang phân tích yêu cầu...</p>
            <p class="text-slate-500 text-[10px] italic">"${query}"</p>
        </div>
    `;

    try {
        const res = await fetch('/api/ai/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();

        if (data.status === 'ok') {
            // Hiển thị thông tin Intent cho người dùng
            const intent = data.intent;
            let intentMsg = `AI hiểu: ${intent.intent_summary || 'Đang tìm kiếm...'}`;

            // Re-render grid with results
            state.currentGridVideos = data.results;
            renderGrid(data.results);

            // Thêm banner thông báo kết quả AI
            const banner = document.createElement('div');
            banner.className = 'col-span-full mb-6 bg-blue-600/10 border border-blue-500/20 rounded-2xl p-4 flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-500';
            banner.innerHTML = `
                <div class="flex items-center gap-3">
                    <i class="fa-solid fa-wand-magic-sparkles text-blue-500"></i>
                    <div>
                        <p class="text-blue-400 font-bold text-[10px] uppercase tracking-wider">KẾT QUẢ TÌM KIẾM AI</p>
                        <p class="text-white text-xs">${intentMsg}</p>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" class="text-slate-500 hover:text-white transition">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            `;
            grid.prepend(banner);

        } else {
            alert('AI Search lỗi: ' + (data.msg || 'Không rõ'));
            grid.innerHTML = oldHtml;
        }
    } catch (err) {
        console.error(err);
        alert('Lỗi kết nối AI');
        grid.innerHTML = oldHtml;
    }
}

window.runAiSearch = runAiSearch;
