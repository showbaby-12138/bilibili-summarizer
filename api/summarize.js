export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    if (req.method === 'OPTIONS') {
        res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        return res.status(200).end();
    }
    if (req.method !== 'POST') return res.status(404).json({ error: 'use POST' });

    const { title, text } = req.body;
    if (!text) return res.status(400).json({ error: 'no text' });
    
    const key = process.env.DEEPSEEK_API_KEY;
    const prompt = `你是严谨的科普作家。根据以下B站视频字幕写一篇科普短文（Markdown，800-1200字）。\n\n标题：${title}\n\n字幕：${text.slice(0, 6000)}\n\n结构：\n## 核心内容 - 按原文逻辑解释概念和原理，用通俗中文，保留案例和数据\n## 关键要点 - 列出3-5个最重要知识点（-列表）\n## 总结 - 100字总结+1个延伸思考问题\n\n规则：严格基于字幕不编造，术语首次出现括号解释。结尾附原文链接。`;
    
    try {
        const resp = await fetch('https://api.deepseek.com/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
            body: JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], temperature: 0.3, max_tokens: 1800 })
        });
        const data = await resp.json();
        if (data.error) return res.status(500).json({ error: data.error.message });
        return res.json({ article: data.choices[0].message.content, chars: text.length, title, prompt });
    } catch (e) {
        return res.status(500).json({ error: e.message });
    }
}
