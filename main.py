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
    res = requests.post(url, headers=headers)
    return res.json()["results"]

def get_title(item, field):
    prop = item["properties"][field]["title"]
    return prop[0]["plain_text"] if prop else ""

def get_date(item, field):
    date = item["properties"][field]["date"]
    return date["start"] if date else None

def update_relation(page_id, related_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "任务关联": {
                "relation": [{"id": related_id}]
            }
        }
    }
    requests.patch(url, headers=headers, json=data)

a_items = query_database(DB_A)
b_items = query_database(DB_B)

for a in a_items:
    a_name = get_title(a, "名称")
    a_date = get_date(a, "日期")

    for b in b_items:
        b_title = get_title(b, "标题")
        b_date = get_date(b, "开始时间")

        if a_name == b_title and a_date == b_date:
            update_relation(a["id"], b["id"])
            update_relation(b["id"], a["id"])
            print("匹配成功:", a_name)
