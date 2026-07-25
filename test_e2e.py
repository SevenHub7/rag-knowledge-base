"""端到端测试脚本：创建知识库 → 上传文档 → 等待处理 → 提问测试"""

import httpx
import time
import os
import sys
import json

BASE = "http://localhost:8000"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "data", "test_docs")


def main():
    client = httpx.Client(base_url=BASE, timeout=60)

    # 1. 创建知识库
    print("=" * 50)
    print("[1/4] 创建知识库...")
    res = client.post("/api/knowledge/", json={
        "name": "国务院政策文件知识库",
        "description": "包含2025-2026年国务院及各部委发布的公开政策文件"
    })
    if res.status_code != 200:
        print(f"  失败: {res.text}")
        return
    kb = res.json()
    kb_id = kb["id"]
    print(f"  知识库 ID: {kb_id}")
    print(f"  名称: {kb['name']}")

    # 2. 上传文档
    print("\n" + "=" * 50)
    print("[2/4] 上传文档...")
    doc_files = [
        "2026乐购新春春节特别活动方案.md",
        "促进药品零售行业高质量发展意见.md",
        "加快培育交通物流领军企业行动方案.md",
        "可能影响未成年人身心健康的网络信息分类办法.md",
        "完善发电侧容量电价机制通知.md",
        "实施中小微企业贷款贴息政策.md",
        "教育部做好2026年普通高校招生工作通知.md",
        "进一步健全完善临时救助制度意见.md",
    ]
    doc_ids = []
    for fname in doc_files:
        fpath = os.path.join(DOCS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  跳过（文件不存在）: {fname}")
            continue
        with open(fpath, "rb") as f:
            res = client.post(
                f"/api/documents/upload/{kb_id}",
                files={"file": (fname, f, "application/octet-stream")}
            )
        if res.status_code == 200:
            data = res.json()
            doc_ids.append(data["doc_id"])
            print(f"  上传成功: {fname} (doc_id: {data['doc_id']})")
        else:
            print(f"  上传失败: {fname} -> {res.text}")

    if not doc_ids:
        print("  没有文档上传成功，退出")
        return

    # 3. 等待处理完成
    print("\n" + "=" * 50)
    print("[3/4] 等待文档处理（向量化）...")
    all_done = False
    for attempt in range(30):
        time.sleep(3)
        statuses = []
        for did in doc_ids:
            res = client.get(f"/api/documents/status/{did}")
            if res.status_code == 200:
                statuses.append(res.json())

        done = sum(1 for s in statuses if s["status"] == "completed")
        failed = sum(1 for s in statuses if s["status"] == "failed")
        processing = sum(1 for s in statuses if s["status"] == "processing")

        print(f"  [{attempt+1}] 完成: {done}, 处理中: {processing}, 失败: {failed}", end="")

        for s in statuses:
            if s["status"] == "failed":
                print(f"  !! {s['filename']} 失败: {s['error_message']}")

        if done == len(doc_ids):
            print("\n  全部处理完成!")
            all_done = True
            break
        elif failed > 0 and done + failed == len(doc_ids):
            print("\n  部分文档处理失败")
            break
        else:
            print()

    # 显示知识库统计
    res = client.get(f"/api/knowledge/{kb_id}")
    kb_info = res.json()
    print(f"\n  知识库统计: {kb_info['doc_count']} 个文档, {kb_info['chunk_count']} 个分块")

    # 显示系统统计
    res = client.get("/api/chat/stats")
    stats = res.json()
    print(f"  系统统计: {json.dumps(stats, ensure_ascii=False)}")

    if not all_done:
        print("\n  文档处理未完成，跳过问答测试")
        return

    # 4. 问答测试
    print("\n" + "=" * 50)
    print("[4/4] 问答测试...")

    questions = [
        "发电侧容量电价机制涵盖哪些类型的电源？",
        "中小微企业贷款贴息政策的贴息标准是什么？",
        "网络信息分类办法中，哪些信息属于可能影响未成年人身心健康的信息？",
        "促进药品零售行业高质量发展有哪些具体措施？",
        "2026年春节乐购新春活动包括哪些重点领域？",
        "临时救助制度主要救助哪些对象？",
        "2026年高校招生工作有哪些新要求？",
        "交通物流领军企业的培育目标是什么？",
    ]

    conv_id = None
    for i, q in enumerate(questions):
        print(f"\n--- 问题 {i+1}: {q}")
        res = client.post("/api/chat/", json={
            "message": q,
            "conversation_id": conv_id,
            "kb_ids": [kb_id],
        })
        if res.status_code == 200:
            data = res.json()
            conv_id = data["conversation_id"]
            answer = data["answer"]
            sources = data["sources"]
            # 截取回答前200字
            preview = answer[:200] + ("..." if len(answer) > 200 else "")
            print(f"  回答: {preview}")
            if sources:
                src_names = [f"{s['filename']}({s['score']:.2f})" for s in sources[:3]]
                print(f"  来源: {', '.join(src_names)}")
            else:
                print("  来源: 无")
        else:
            print(f"  请求失败: {res.status_code} {res.text}")

    # 最终统计
    print("\n" + "=" * 50)
    print("测试完成!")
    res = client.get("/api/chat/stats")
    print(f"最终统计: {json.dumps(res.json(), ensure_ascii=False)}")

    # 显示对话历史
    res = client.get("/api/chat/conversations")
    convs = res.json()
    print(f"对话数: {len(convs)}")
    for c in convs:
        print(f"  - {c['title']} ({c['message_count']} 条消息)")


if __name__ == "__main__":
    main()
