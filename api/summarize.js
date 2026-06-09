export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    if (req.method === 'OPTIONS') {
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        return res.status(200).end();
    }

    // ===== GET: 获取B站字幕 =====
    if (req.method === 'GET') {
        const url = new URL(req.url, 'http://localhost').searchParams.get('url');
        if (!url) return res.status(400).json({ error: '缺少url参数' });
        
        try {
            const bv = url.match(/BV[a-zA-Z0-9]{10}/)[0];
            const headers = { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com/' };
            
            // 获取视频信息
            const info = await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${bv}`, { headers }).then(r => r.json());
            if (info.code !== 0) throw new Error(info.message);
            const cid = info.data.cid || info.data.pages[0].cid;
            const title = info.data.title;
            
            // 获取字幕列表
            const player = await fetch(`https://api.bilibili.com/x/player/v2?bvid=${bv}&cid=${cid}`, { headers }).then(r => r.json());
            const subs = player.data?.subtitle?.subtitles || [];
            if (!subs.length) throw new Error('该视频没有字幕');
            
            // 选最优字幕
            let target = subs[0];
            for (const s of subs) { if (s.ai_type === 1 && ['zh-Hans','zh-CN','zh'].includes(s.lan)) { target = s; break; } }
            for (const s of subs) { if (['zh-Hans','zh-CN','zh'].includes(s.lan)) { target = s; break; } }
            
            let su = target.subtitle_url;
            if (su.startsWith('//')) su = 'https:' + su;
            const data = await fetch(su, { headers }).then(r => r.json());
            const lines = data.body.filter(i => i.content?.trim()).map(i => i.content);
            const text = lines.join('\n');
            
            return res.json({ title, text, chars: text.length });
        } catch (e) {
            return res.status(500).json({ error: e.message });
        }
    }

    // ===== POST: DeepSeek总结 =====
    if (req.method === 'POST') {
        const { title, text } = req.body;
        if (!text) return res.status(400).json({ error: 'no text' });
        
        const key = process.env.DEEPSEEK_API_KEY;
        if (!key) return res.status(500).json({ error: 'API key not set' });
        
        const prompt = `你是严谨的科普作家。根据以下B站视频字幕写一篇科普短文（Markdown，800-1200字）。\n\n标题：${title}\n\n字幕：${text.slice(0, 6000)}\n\n结构：\n## 核心内容 - 按原文逻辑解释概念和原理，用通俗中文，保留案例和数据\n## 关键要点 - 列出3-5个最重要知识点（-列表）\n## 总结 - 100字总结+1个延伸思考问题\n\n规则：严格基于字幕不编造，术语首次出现括号解释。结尾附原文链接。`;
        
        try {
            const resp = await fetch('https://api.deepseek.com/chat/completions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
                body: JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], temperature: 0.3, max_tokens: 1800 })
            });
            const data = await resp.json();
            return res.json({ article: data.choices[0].message.content, chars: text.length, title, prompt });
        } catch (e) {
            return res.status(500).json({ error: e.message });
        }
    }

    return res.status(404).json({ error: 'not found' });
}
