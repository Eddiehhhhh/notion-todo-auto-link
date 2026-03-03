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

def query_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    r = requests.post(url, headers=headers)
    data = r.json()
    return data.get("results", [])

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
        # date_prop 可以有 start/end
        return date_prop.get("start")
    except:
        return None

def update_relation(page_id, related_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "任务关联": {
                "relation": [{"id": related_id}]
            }
        }
    }
    r = requests.patch(url, headers=headers, json=data)
    if r.status_code != 200:
        print("更新失败:", r.text)

print("开始执行自动关联...")

a_items = query_database(DB_A)
b_items = query_database(DB_B)

print("A数量:", len(a_items), "B数量:", len(b_items))

# 构建 B 的字典：标题 → 列表
b_dict = {}
for b in b_items:
    b_title = get_title(b, "标题")
    b_date = get_start_date(b, "开始时间")
    if b_title not in b_dict:
        b_dict[b_title] = []
    b_dict[b_title].append({"id": b["id"], "date": b_date})

# 遍历 A
for a in a_items:
    a_name = get_title(a, "名称")
    a_date = get_start_date(a, "日期")
    print("A项:", repr(a_name), a_date)

    if a_name in b_dict:
        # 名称匹配的 B 列表
        for b_entry in b_dict[a_name]:
            b_id = b_entry["id"]
            b_date = b_entry["date"]
            # 比较日期，统一取 YYYY-MM-DD
            if a_date and b_date and a_date[:10] == b_date[:10]:
                print("匹配成功:", a_name)
                update_relation(a["id"], b_id)
                update_relation(b_id, a["id"])

print("执行结束")
