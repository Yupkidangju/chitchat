#!/usr/bin/env python3
"""ko.json + en.json 기준으로 ja/zh_tw/zh_cn 번역 사전을 생성한다."""
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent / "src/chitchat/i18n/locales"
ko = json.loads((BASE / "ko.json").read_text("utf-8"))
en = json.loads((BASE / "en.json").read_text("utf-8"))

# 번역 매핑 (키 → ja/zh_tw/zh_cn)
# 이미 번역된 키는 기존 파일에서 가져옴
for lang in ["ja", "zh_tw", "zh_cn"]:
    existing = json.loads((BASE / f"{lang}.json").read_text("utf-8"))
    result = {}
    for key in ko:
        if key in existing:
            result[key] = existing[key]
        else:
            # en.json 값을 폴백으로 사용 (번역 키가 없으면)
            result[key] = en.get(key, ko[key])
    (BASE / f"{lang}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(f"{lang}.json: {len(result)} keys written")
