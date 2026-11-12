import json
import os
import re
import sys
import unicodedata
from pathlib import Path


DIRECTORY = re.compile(r"^window\.BOOTH_DIRECTORY = (\[\n[\s\S]*?\n\]);", re.MULTILINE)
BOOTH = re.compile(r"[A-F](?:[1-9]|[12][0-9]|3[0-4])")
NAME_SEPARATORS = re.compile(r"[\s()\[\]【】·•・.,、\-—_\u200b]")


def name_key(name):
    return NAME_SEPARATORS.sub("", unicodedata.normalize("NFKC", name).lower())


def add_exhibitor(page, booth_input, company_input):
    booth = unicodedata.normalize("NFKC", booth_input).strip().upper()
    company = company_input.strip()
    if not BOOTH.fullmatch(booth):
        raise ValueError("展位号须为 A1–F34 范围内的编号，每区 1–34 号。")
    if (
        not name_key(company)
        or len(company) > 100
        or any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in company)
    ):
        raise ValueError("请填写 1–100 个字符的单行单位名称。")

    match = DIRECTORY.search(page)
    if match is None:
        raise ValueError("网页中的展位表无法识别。")
    rows = json.loads(match.group(1))
    by_booth = dict(rows)
    if len(rows) != len(by_booth):
        raise ValueError("现有展位表包含重复展位号，请先核对。")

    if booth in by_booth:
        if name_key(by_booth[booth]) == name_key(company):
            return page
        raise ValueError("该展位已分配给其他单位。")
    if any(name_key(name) == name_key(company) for name in by_booth.values()):
        raise ValueError("该单位已有展位。")

    rows.append([booth, company])
    rows.sort(key=lambda row: (row[0][0], int(row[0][1:])))
    # Escape the HTML tag opener so names remain data inside the script element.
    lines = ["  " + json.dumps(row, ensure_ascii=False) for row in rows]
    encoded = ("[\n" + ",\n".join(lines) + "\n]").replace("<", r"\u003c")
    return page[:match.start(1)] + encoded + page[match.end(1):]


def main():
    page_file = Path(sys.argv[1])
    previous = page_file.read_text(encoding="utf-8")
    try:
        current = add_exhibitor(previous, os.environ["BOOTH_CODE"], os.environ["COMPANY_NAME"])
    except ValueError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    if current != previous:
        page_file.write_text(current, encoding="utf-8")
        print("单位已加入展位表。")
    else:
        print("该单位与展位已对应，继续发布当前展位表。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
