import json
import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SOURCE = "https://event.rakuten.co.jp/campaign/point-up/marathon/"
FILE = Path("calendar-events.json")


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def collect_rakuten():
    request = Request(
        SOURCE,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = PageText()
    parser.feed(html)

    text = re.sub(r"\s+", " ", " ".join(parser.parts))

    date_pattern = (
        r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日"
        r"(?:\s*[\(（][月火水木金土日][\)）])?"
        r"\s*(\d{1,2}):(\d{2})"
    )

    pattern = re.compile(
        date_pattern + r"\s*[～〜~]\s*" + date_pattern
    )

    for label in re.finditer("ポイントアップ期間", text):
        nearby = text[label.end():label.end() + 300]
        match = pattern.search(nearby)

        if not match:
            continue

        values = [int(v) for v in match.groups()]

        try:
            start = datetime(*values[:5])
            end = datetime(*values[5:])
        except ValueError:
            continue

        today = datetime.now(ZoneInfo("Asia/Tokyo")).date()

        if not (
            today - timedelta(days=14)
            <= start.date()
            <= today + timedelta(days=60)
        ):
            continue

        if not (start < end <= start + timedelta(days=14)):
            continue

        start_date = start.date().isoformat()
        return {
            "id": f"rakuten-marathon-{start_date}",
            "category": "rakuten",
            "name": "楽天お買い物マラソン",
            "shortName": "楽天マラソン",
            "startDate": start_date,
            "endDate": end.date().isoformat(),
            "startTime": start.strftime("%H:%M"),
            "endTime": end.strftime("%H:%M"),
            "sourceUrl": SOURCE,
        }

    return None


def main():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    events = data["events"]

    event = collect_rakuten()

    if event is None:
        print("開催日時を確認できませんでした。既存データを維持します。")
        return

    for existing in events:
        if existing.get("id") == event["id"]:
            print("登録済みのイベントです。変更なし。")
            return

    events.append(event)
    events.sort(key=lambda item: item["startDate"])

    data["updatedAt"] = date.today().isoformat()

    FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print("追加しました:", event["name"], event["startDate"])


if __name__ == "__main__":
    main()
