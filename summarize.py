from http.server import BaseHTTPRequestHandler
import json, os
from openai import OpenAI

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            title = body.get("title", "")
            text = body.get("text", "")
            if not text:
                self._json(400, {"error": "no subtitle text"})
                return
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not key:
                self._json(500, {"error": "DEEPSEEK_API_KEY not set"})
                return
            prompt = "你是严谨的科普作家。根据以下B站视频字幕写一篇科普短文（Markdown，800-1200字）。\n\n标题：" + title + "\n\n字幕：" + text[:6000] + "\n\n结构：\n## 核心内容 - 按原文逻辑解释概念和原理，用通俗中文，保留案例和数据\n## 关键要点 - 列出3-5个最重要知识点（-列表）\n## 总结 - 100字总结+1个延伸思考问题\n\n规则：严格基于字幕不编造，术语首次出现括号解释。结尾附原文链接。"
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=60)
            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], temperature=0.3, max_tokens=1800, stream=False)
            self._json(200, {"article": resp.choices[0].message.content, "chars": len(text), "title": title, "prompt": prompt})
        except Exception as e:
            self._json(500, {"error": str(e)})
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
