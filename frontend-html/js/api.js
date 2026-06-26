/* ══════════════════════════════════════════
   PPT 智造 — API 层
   REST + WebSocket 客户端
   ══════════════════════════════════════════ */

const API = {
  base: 'http://localhost:3000/api',

  async getTemplates() {
    const res = await fetch(`${this.base}/templates`);
    return res.json();
  },

  async recommendPages(content) {
    const fd = new FormData();
    fd.append('content', content);
    const res = await fetch(`${this.base}/recommend-pages`, {
      method: 'POST',
      body: fd,
    });
    return res.json();
  },

  async generateWithFiles(formData) {
    const res = await fetch(`${this.base}/generate/upload`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async confirmOutline(taskId, pages) {
    const res = await fetch(`${this.base}/generate/outline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId, pages }),
    });
    return res.json();
  },

  async modifyPpt(taskId, newText, modifyScope) {
    const res = await fetch(`${this.base}/modify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId, new_text: newText, modify_scope: modifyScope }),
    });
    return res.json();
  },

  async restylePpt(taskId, templateId, customStyleDesc) {
    const res = await fetch(`${this.base}/restyle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId, template_id: templateId, custom_style_desc: customStyleDesc }),
    });
    return res.json();
  },

  getDownloadUrl(taskId) {
    return `http://localhost:3000/api/download/${taskId}`;
  },

  async getTaskStatus(taskId) {
    const res = await fetch(`${this.base}/task/${taskId}`);
    return res.json();
  },

  async cancelTask(taskId) {
    const res = await fetch(`${this.base}/cancel/${taskId}`, { method: 'POST' });
    return res.json();
  },

  createWebSocket(taskId, handlers) {
    const ws = new WebSocket(`ws://localhost:3000/ws/task/${taskId}`);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (handlers.onMessage) handlers.onMessage(msg);
      } catch (e) {
        // ignore parse errors
      }
    };
    ws.onerror = () => {
      if (handlers.onError) handlers.onError();
    };
    ws.onclose = () => {
      if (handlers.onClose) handlers.onClose();
    };

    return ws;
  }
};
