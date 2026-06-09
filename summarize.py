from http.server import BaseHTTPRequestHandler
import json, os, re, urllib.request, urllib.error, urllib.parse
from openai import OpenAI

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch_bili_subs(video_url):
    bv = re.search(r"BV[a-zA-Z0-9]{10}", video_url).group(0)
    h = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
    def api(path):
        r = urllib.request.Request("https://api.bilibili.com" + path, headers=h)
        with urllib.request.urlopen(r, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    info = api("/x/web-interface/view?bvid=" + bv)
    if info["code"] != 0: raise Exception(info.get("message", "B站API错误"))
    cid = info["data"]["cid"] or info["data"]["pages"][0]["cid"]
    title = info["data"]["title"]
    player = api("/x/player/v2?bvid=" + bv + "&cid=" + str(cid))
    subs = player.get("data", {}).get("subtitle", {}).get("subtitles", [])
    if not subs: raise Exception("该视频没有字幕")
    target = subs[0]
    for s in subs:
        if s.get("ai_type") == 1 and s.get("lan", "") in ("zh-Hans", "zh-CN", "zh"): target = s; break
    for s in subs:
        if s.get("lan", "") in ("zh-Hans", "zh-CN", "zh"): target = s; break
    su = target.get("subtitle_url", "")
    if su.startswith("//"): su = "https:" + su
    req = urllib.request.Request(su, headers=h)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    lines = [item["content"] for item in data.get("body", []) if item.get("content", "").strip()]
    return {"title": title, "text": "\n".join(lines), "chars": len("\n".join(lines))}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        url = params.get("url", [""])[0]
        if not url:
            self._json(400, {"error": "缺少url参数"})
            return
        try:
            result = fetch_bili_subs(url)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": str(e)})
    
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
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=90)
            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], temperature=0.3, max_tokens=1800, stream=False)
            self._json(200, {"article": resp.choices[0].message.content, "chars": len(text), "title": title, "prompt": prompt})
        except Exception as e:
            self._json(500, {"error": str(e)})
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
