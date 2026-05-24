import os
import sys
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DB_A = os.environ.get("DB_A")  # 任务中心数据库ID
DB_B = os.environ.get("DB_B")  # 任务数据库ID

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


def query_database(database_id):
    """查询数据库所有数据"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    results = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        r = requests.post(url, headers=headers, json=payload)

        # 检查 API 是否返回了错误响应
        if r.status_code != 200:
            print(f"Notion API error: status={r.status_code}, body={r.text[:500]}")
            break

        data = r.json()

        # 检查响应结构合法性
        if "results" not in data:
            print(f"Notion API unexpected response: keys={list(data.keys())}")
            break

        results.extend(data["results"])
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return results


def get_title(item, field):
    """获取标题字段值"""
    try:
        prop = item["properties"][field]["title"]
        return prop[0]["plain_text"].strip() if prop else ""
    except (KeyError, IndexError, TypeError):
        return ""


def get_start_date(item, field):
    """获取日期字段值"""
    try:
        date_prop = item["properties"][field]["date"]
        if not date_prop:
            return None
        return date_prop["start"]
    except (KeyError, TypeError):
        return None


def normalize_date(date_str):
    """将日期字符串标准化为 date 对象（转换到 GMT+8 时区）"""
    if not date_str:
        return None
    try:
        # 处理带时区的时间字符串 (如 2026-04-06T16:00:00.000+00:00 或 ...Z)
        if "T" in date_str and ("Z" in date_str or "+" in date_str or date_str.count("-") > 2):
            # 解析 ISO 格式时间
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # 如果是 UTC 时间，转换到 Asia/Shanghai (GMT+8)
            if dt.tzinfo is not None:
                shanghai_tz = ZoneInfo("Asia/Shanghai")
                dt_local = dt.astimezone(shanghai_tz)
                return dt_local.date()
            return dt.date()
        # 纯日期格式 (如 2026-04-07)
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError):
        return None


def get_existing_relations(item, field):
    """获取已有的关联"""
    try:
        rel = item["properties"][field]["relation"]
        return [r["id"] for r in rel]
    except (KeyError, TypeError):
        return []


def append_relation(item_id, field, existing_ids, target_id):
    """添加关联（不重复）"""
    if target_id in existing_ids:
        return False

    url = f"https://api.notion.com/v1/pages/{item_id}"
    payload = {
        "properties": {
            field: {
                "relation": [{"id": target_id}] + [{"id": rid} for rid in existing_ids]
            }
        }
    }
    r = requests.patch(url, headers=headers, json=payload)
    return r.status_code == 200


def main():
    print("开始自动关联任务...")

    # 查询两个数据库
    a_items = query_database(DB_A)
    b_items = query_database(DB_B)

    print(f"任务中心(A): {len(a_items)} 条")
    print(f"任务(B): {len(b_items)} 条")

    # 检查数据是否有效（防止 API 错误导致空数据）
    if not a_items or not b_items:
        if not a_items:
            print("ERROR: 任务中心(A) 查询为空，可能是 Token 或数据库 ID 配置错误")
        if not b_items:
            print("ERROR: 任务(B) 查询为空，可能是 Token 或数据库 ID 配置错误")
        sys.exit(1)

    # 构建 B 的索引: 标题 -> [{id, date, item}]
    b_dict = {}
    for b in b_items:
        b_title = get_title(b, "标题")
        b_date = normalize_date(get_start_date(b, "开始时间"))
        if not b_title:
            continue
        if b_title not in b_dict:
            b_dict[b_title] = []
        b_dict[b_title].append({"id": b["id"], "date": b_date, "item": b})

    print(f"任务(B) 按「标题」去重后有 {len(b_dict)} 个唯一标题")

    # 遍历 A，找到同名同日期的 B，建立双向关联
    linked_count = 0
    skipped_count = 0
    no_match_count = 0

    for a in a_items:
        a_name = get_title(a, "名称")
        a_date = normalize_date(get_start_date(a, "日期"))

        if not a_name:
            continue

        if a_name not in b_dict:
            no_match_count += 1
            continue

        # 找到同名的 B 条目
        for b_entry in b_dict[a_name]:
            b_id = b_entry["id"]
            b_date = b_entry["date"]

            # 日期匹配规则:
            # - 如果两边都有日期，必须相等才关联
            # - 如果任意一边没有日期，仍然关联（宽松匹配）
            if a_date and b_date:
                if a_date != b_date:
                    continue  # 都有日期但不相等，跳过

            # 检查是否已关联
            a_relations = get_existing_relations(a, "任务关联")
            b_relations = get_existing_relations(b_entry["item"], "任务关联")

            if b_id in a_relations:
                skipped_count += 1
                continue  # 已关联，跳过

            # 建立双向关联
            success_a = append_relation(a["id"], "任务关联", a_relations, b_id)
            success_b = append_relation(b_id, "任务关联", b_relations, a["id"])

            if success_a and success_b:
                linked_count += 1
                print(f"✅ 关联成功: {a_name}")
            else:
                print(f"❌ 关联失败: {a_name}")

    print(f"\n完成！新增关联: {linked_count} 条, 跳过已关联: {skipped_count} 条, 无匹配: {no_match_count} 条")


if __name__ == "__main__":
    main()
