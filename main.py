import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DB_A = os.environ["DATABASE_A"]
DB_B = os.environ["DATABASE_B"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# -----------------------------
# 分页查询数据库
# -----------------------------
def query_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    results = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        r = requests.post(url, headers=headers, json=payload)
        data = r.json()

        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return results


# -----------------------------
# 获取标题
# -----------------------------
def get_title(item, field):
    try:
        prop = item["properties"][field]["title"]
        return prop[0]["plain_text"].strip() if prop else ""
    except:
        return ""


# -----------------------------
# 获取开始日期（兼容单日期/范围）
# -----------------------------
def get_start_date(item, field):
    try:
        date_prop = item["properties"].get(field, {}).get("date")
        if not date_prop:
            return None
        return date_prop.get("start")
    except:
        return None


# -----------------------------
# 获取已有 relation
# -----------------------------
def get_existing_relations(item, field):
    try:
        rel = item["properties"][field]["relation"]
        return [r["id"] for r in rel]
    except:
        return []


# -----------------------------
# 更新 relation（追加，不覆盖）
# -----------------------------
def append_relation(page_id, field, existing_ids, new_id):
    if new_id in existing_ids:
        return  # 已经关联过

    all_ids = existing_ids + [new_id]

    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            field: {
                "relation": [{"id": i} for i in all_ids]
            }
        }
    }

    r = requests.patch(url, headers=headers, json=data)
    if r.status_code != 200:
        print("更新失败:", r.text)


# -----------------------------
# 主逻辑
# -----------------------------
print("开始执行自动关联...")

a_items = query_database(DB_A)
b_items = query_database(DB_B)

print("A数量:", len(a_items), "B数量:", len(b_items))

# 构建 B 字典：标题 -> 列表
b_dict = {}
for b in b_items:
    b_title = get_title(b, "标题")
    b_date = get_start_date(b, "开始时间")

    if b_title not in b_dict:
        b_dict[b_title] = []

    b_dict[b_title].append({
        "id": b["id"],
        "date": b_date,
        "item": b
    })


match_count = 0

for a in a_items:
    a_name = get_title(a, "名称")
    a_date = get_start_date(a, "日期")
    a_relations = get_existing_relations(a, "任务关联")

    if not a_name:
        continue

    if a_name in b_dict:

        for b_entry in b_dict[a_name]:
            b_id = b_entry["id"]
            b_date = b_entry["date"]
            b_item = b_entry["item"]
            b_relations = get_existing_relations(b_item, "任务关联")

            # 如果两边都有日期 -> 必须日期一致
            if a_date and b_date:
                if a_date[:10] != b_date[:10]:
                    continue

            print("匹配成功:", a_name)

            # 双向追加
            append_relation(a["id"], "任务关联", a_relations, b_id)
            append_relation(b_id, "任务关联", b_relations, a["id"])

            match_count += 1

print("执行结束")
print("成功匹配数量:", match_count)
