"""从 gov.cn 抓取政策文件并保存为 Markdown"""

import urllib.request
import re
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

# 选定的政策文件 URL（涵盖不同领域：消费、能源、养老、交通、医药）
DOCS = [
    ("https://www.gov.cn/zhengce/zhengceku/202602/content_7056817.htm", "2026乐购新春春节特别活动方案"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056676.htm", "完善发电侧容量电价机制通知"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056416.htm", "自然资源要素保障支持养老服务改革"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056084.htm", "推进城际铁路健康可持续发展意见"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7055835.htm", "促进药品零售行业高质量发展意见"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7055567.htm", "实施中小微企业贷款贴息政策"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7056040.htm", "国家产业技术工程化中心管理办法"),
    ("https://www.gov.cn/zhengce/zhengceku/202601/content_7055963.htm", "可能影响未成年人身心健康的网络信息分类办法"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "test_docs_new")


def fetch_and_parse(url, title_hint):
    """抓取页面并提取正文"""
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

    # 提取正文区域（通常在 class="pages_content" 或 id="UCAP-CONTENT" 内）
    content_match = re.search(
        r'<div[^>]*(?:class="pages_content"|id="UCAP-CONTENT"|class="article-content")[^>]*>(.*?)</div>\s*(?:<div|</article|</main)',
        html, re.DOTALL
    )
    if not content_match:
        # fallback: 找最大的 <p> 集合区域
        content_match = re.search(r'<div[^>]*>(\s*<p>.*?</p>\s*){3,}</div>', html, re.DOTALL)

    if content_match:
        raw = content_match.group(1) if '<p>' in content_match.group(0) else content_match.group(1)
    else:
        raw = html

    # 清理 HTML 标签，保留段落结构
    # 先把 <p>、<br>、标题标签转为换行
    text = raw
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'<h(\d)[^>]*>(.*?)</h\1>', lambda m: '\n' + '#' * int(m.group(1)) + ' ' + m.group(2) + '\n', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)  # 去除剩余标签
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return title, doc_num, text


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    success = 0

    for url, hint in DOCS:
        try:
            print(f"抓取: {hint} ...", end=" ", flush=True)
            title, doc_num, text = fetch_and_parse(url, hint)

            if len(text) < 100:
                print(f"内容太短 ({len(text)} 字符)，跳过")
                continue

            # 构建 Markdown
            md = f"# {title}\n\n"
            if doc_num:
                md += f"**文号**: {doc_num}\n\n"
            md += f"**来源**: 中国政府网 (gov.cn)\n\n"
            md += f"**链接**: {url}\n\n---\n\n"
            md += text

            # 保存
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', hint)
            filepath = os.path.join(OUT_DIR, f"{safe_name}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)

            print(f"OK ({len(text)} 字符)")
            success += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"失败: {e}")

    print(f"\n完成: 成功 {success}/{len(DOCS)} 个文件")
    print(f"保存目录: {OUT_DIR}")

    # 列出文件
    if os.path.exists(OUT_DIR):
        for f in sorted(os.listdir(OUT_DIR)):
            fp = os.path.join(OUT_DIR, f)
            size = os.path.getsize(fp)
            print(f"  {f} ({size:,} bytes)")


if __name__ == "__main__":
    main()
