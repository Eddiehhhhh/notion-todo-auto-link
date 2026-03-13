import os
import requests
from datetime import datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DB_A = os.environ["DATABASE_A"]
DB_B = os.environ["DATABASE_B"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

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
        results.extend(data["results"])
        has_more = data["has_more"]
        next_cursor = data["next_cursor"]
    return results

def get_title(item, field):
    try:
        prop = item["properties"][field]["title"]
        return prop[0]["plain_text"].strip() if prop else ""
    except:
        return ""

def get_start_date(item, field):
    try:
        date_prop = item["properties"][field]["date"]
        if not date_prop:
            return None
        return date_prop["start"]
    except:
        return None

def normalize_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except:
        return None

def get_existing_relations(item, field):
    try:
        rel = item["properties"][field]["relation"]
        return [r["id"] for r in rel]
    except:
        return []

def append_relation(page_id, field, existing_ids, new_id):
    if new_id in existing_ids:
        return
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
        print("更新失败，状态码:", r.status_code)

print("开始执行自动关联...")

a_items = query_database(DB_A)
b_items = query_database(DB_B)

print("A数量:", len(a_items))
print("B数量:", len(b_items))

b_dict = {}
for b in b_items:
    b_title = get_title(b, "标题")
    b_date = normalize_date(get_start_date(b, "开始时间"))
    if not b_title:
        continue
    if b_title not in b_dict:
        b_dict[b_title] = []
    b_dict[b_title].append({"id": b["id"], "date": b_date, "item": b})

match_count = 0

for a in a_items:
    a_name = get_title(a, "名称")
    a_date = normalize_date(get_start_date(a, "日期"))
    if not a_name:
        continue
    if a_name not in b_dict:
        continue
    for b_entry in b_dict[a_name]:
        b_id = b_entry["id"]
        b_date = b_entry["date"]
        b_item = b_entry["item"]
        if a_date and b_date:
            if a_date != b_date:
                continue
        a_relations = get_existing_relations(a, "任务关联")
        b_relations = get_existing_relations(b_item, "任务关联")
        append_relation(a["id"], "任务关联", a_relations, b_id)
        append_relation(b_id, "任务关联", b_relations, a["id"])
        match_count += 1

print("执行结束")
print("成功匹配数量:", match_count)
