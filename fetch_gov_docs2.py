"""补充抓取：重新获取短文档 + 新增文档"""

import urllib.request
import re
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

# 重新抓取短文档 + 新增文档
DOCS = [
    # 重新抓取（之前内容太短）
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056084.htm", "推进城际铁路健康可持续发展意见"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056416.htm", "自然资源要素保障支持养老服务改革"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056040.htm", "国家产业技术工程化中心管理办法"),
    # 新增文档
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056035.htm", "加快培育交通物流领军企业行动方案"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7055769.htm", "教育部做好2026年普通高校招生工作通知"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056020.htm", "中央预算内投资计划管理办法"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "test_docs_new")


def fetch_and_parse(url, title_hint):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # 提取标题
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else title_hint

    # 提取文号
    doc_num_match = re.search(r'([^\s<]*〔\d{4}〕[^\s<]*|[^\s<]*\[\d{4}\][^\s<]*)', html)
    doc_num = doc_num_match.group(1).strip() if doc_num_match else ""
    doc_num = re.sub(r'^[^〔\[]*', '', doc_num)  # 去掉前缀杂质

    # 改进的正文提取：尝试多种模式
    text = ""
    patterns = [
        r'<div[^>]*class="pages_content"[^>]*>(.*?)</div>\s*<div',
        r'<div[^>]*id="UCAP-CONTENT"[^>]*>(.*?)</div>\s*(?:<div|</)',
        r'<div[^>]*class="article-content"[^>]*>(.*?)</div>\s*(?:<div|</)',
        r'<div[^>]*id="zoom"[^>]*>(.*?)</div>\s*(?:<div|</)',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL)
        if m:
            text = m.group(1)
            break

    if not text:
        # fallback: 提取所有 <p> 标签内容
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        if paragraphs:
            text = '\n'.join(paragraphs)
        else:
            text = html

    # 清理 HTML
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'<h(\d)[^>]*>(.*?)</h\1>', lambda m: '\n' + '#' * int(m.group(1)) + ' ' + m.group(2) + '\n', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\u200b', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return title, doc_num, text


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for url, hint in DOCS:
        try:
            print(f"抓取: {hint} ...", end=" ", flush=True)
            title, doc_num, text = fetch_and_parse(url, hint)

            if len(text) < 100:
                print(f"内容太短 ({len(text)} 字符)，跳过")
                continue

            md = f"# {title}\n\n"
            if doc_num:
                md += f"**文号**: {doc_num}\n\n"
            md += f"**来源**: 中国政府网 (gov.cn)\n\n"
            md += f"**链接**: {url}\n\n---\n\n"
            md += text

            safe_name = re.sub(r'[\\/:*?"<>|]', '_', hint)
            filepath = os.path.join(OUT_DIR, f"{safe_name}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)

            print(f"OK ({len(text):,} 字符)")
            time.sleep(0.5)

        except Exception as e:
            print(f"失败: {e}")

    # 列出最终文件
    print(f"\n=== 最终文件列表 ===")
    total = 0
    for f in sorted(os.listdir(OUT_DIR)):
        if not f.endswith('.md'): continue
        fp = os.path.join(OUT_DIR, f)
        size = os.path.getsize(fp)
        total += 1
        print(f"  {f} ({size:,} bytes)")
    print(f"共 {total} 个文件")


if __name__ == "__main__":
    main()
