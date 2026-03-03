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
    data = res.json()
    if "results" not in data:
        print("数据库查询失败：", data)
        return []
    return data["results"]

def get_title(item, field):
    try:
        prop = item["properties"][field]["title"]
        return prop[0]["plain_text"] if prop else ""
    except:
        print("读取 title 失败：", field)
        return ""

def get_date(item, field):
    try:
        date = item["properties"][field]["date"]
        return date["start"] if date else None
    except:
        print("读取 date 失败：", field)
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
        print("更新失败：", r.text)

print("开始查询数据库...")

a_items = query_database(DB_A)
b_items = query_database(DB_B)

print("数据库A数量：", len(a_items))
print("数据库B数量：", len(b_items))

for a in a_items:
    a_name = get_title(a, "名称")
    a_date = get_date(a, "日期")

    print("A项：", a_name, a_date)

    for b in b_items:
        b_title = get_title(b, "标题")
        b_date = get_date(b, "开始时间")

        print("  对比B项：", b_title, b_date)

        # 只比较日期部分 YYYY-MM-DD
        if (
            a_name == b_title
            and a_date
            and b_date
            and a_date[:10] == b_date[:10]
        ):
            print("匹配成功：", a_name)
            update_relation(a["id"], b["id"])
            update_relation(b["id"], a["id"])

print("执行结束")
