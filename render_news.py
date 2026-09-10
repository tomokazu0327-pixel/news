#!/usr/bin/env python3
"""ニュース日報レンダラ

使い方:
    python3 render_news.py data.json news_template.html out.html

data.json の形:
{
  "dateline": "2026.08.26 WED",
  "mmdd": "8/26",
  "isodate": "2026-08-26",
  "period": "8月25日（火）7時 〜 8月26日（水）7時（日本時間）",
  "market": {
    "rows": [
      {"name":"日経平均株価","when":"8/25（火）大引け","close":"65,528.09",
       "chg":"−488.27（−0.74%）","dir":"down"}
    ],
    "note": "..."
  },
  "genres": [
    {"mark":"①","name":"国内・政治・社会","genre_key":"国内・政治・社会",
     "items":[{"title":"...","body":"...","why":"...","src":"NHK（8/25）"}]},
    {"mark":"③","name":"健康・医療","genre_key":"健康・医療","items":[],
     "empty_note":"本日は該当なし。"}
  ],
  "skipped": "...",
  "note": "..."
}

dir は "up" / "down" / "flat" のいずれか。通し番号とジャンル見出しの
番号レンジは自動で振るので data.json に書かなくてよい。
items が空のジャンルは、見出しだけ残して empty_note（無ければ既定文言）
を表示する。
"""

import html
import json
import sys

from weather_block import render_weather


def esc(s):
    return html.escape(str(s), quote=True)


def render_market(market):
    rows = []
    for r in market.get("rows", []):
        cls = ' class="own"' if r.get("kind") == "own" else ""
        rows.append(
            f'      <li{cls}>\n'
            '        <div>\n'
            f'          <div class="m-name">{esc(r["name"])}</div>\n'
            f'          <span class="m-when">{esc(r["when"])}</span>\n'
            '        </div>\n'
            '        <div class="m-vals">\n'
            f'          <span class="m-close">{esc(r["close"])}</span>\n'
            f'          <span class="m-chg {esc(r.get("dir", "flat"))}">{esc(r["chg"])}</span>\n'
            '        </div>\n'
            '      </li>'
        )
    return "\n".join(rows)


def render_sections(genres):
    out = []
    n = 0
    for g in genres:
        items = g.get("items", [])
        if not items:
            empty_note = g.get("empty_note", "本日は該当なし。")
            out.append(
                '  <section class="genre">\n'
                '    <div class="genre-head">\n'
                f'      <h2>{esc(g["mark"])} {esc(g["name"])}</h2>\n'
                '    </div>\n'
                f'    <p style="margin:0;font-size:0.875rem;line-height:1.7;color:var(--muted);">{esc(empty_note)}</p>\n'
                '  </section>'
            )
            continue
        start = n + 1
        arts = []
        genre_key = g.get("genre_key", g.get("name", ""))
        for it in items:
            n += 1
            title = it["title"]
            arts.append(
                '    <article class="art">\n'
                f'      <div class="num">{n}</div>\n'
                f'      <h3>{esc(title)}</h3>\n'
                f'      <p class="body">{esc(it["body"])}</p>\n'
                '      <div class="why"><span class="label">なぜ重要か</span>'
                f'<p>{esc(it["why"])}</p></div>\n'
                '      <div class="foot">'
                f'<span class="src">{esc(it["src"])}</span>'
                f'<button type="button" class="dig" data-n="{n}" data-t="{esc(title)}">深掘り</button>'
                '</div>\n'
                f'      <div class="rate" data-n="{n}" data-t="{esc(title)}" data-g="{esc(genre_key)}">'
                '<span class="rl">評価</span>'
                '<button type="button" class="rb" data-v="yes" aria-pressed="false">興味あり</button>'
                '<button type="button" class="rb" data-v="no" aria-pressed="false">興味なし</button>'
                '</div>\n'
                '    </article>'
            )
        rng = f"{start}–{n}" if n > start else f"{n}"
        out.append(
            '  <section class="genre">\n'
            '    <div class="genre-head">\n'
            f'      <h2>{esc(g["mark"])} {esc(g["name"])}</h2>\n'
            f'      <span class="range">{rng}</span>\n'
            '    </div>\n\n'
            + "\n\n".join(arts) + "\n  </section>"
        )
    return "\n\n".join(out)


def main():
    data_path, tpl_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(data_path, encoding="utf-8") as f:
        d = json.load(f)
    with open(tpl_path, encoding="utf-8") as f:
        tpl = f.read()

    market = d.get("market", {})
    weather_html, weather_notes = render_weather(
        d.get("weather"), d.get("isodate"), 7)
    note = d.get("note", "")
    if weather_notes:
        note = (note + " " if note else "") + " ".join(weather_notes)
    page = (
        tpl.replace("{{DATELINE}}", esc(d["dateline"]))
        .replace("{{PERIOD}}", esc(d["period"]))
        .replace("{{WEATHER}}", weather_html)
        .replace("{{MARKET_ROWS}}", render_market(market))
        .replace("{{MARKET_NOTE}}", esc(market.get("note", "")))
        .replace("{{SECTIONS}}", render_sections(d.get("genres", [])))
        .replace("{{SKIPPED}}", esc(d.get("skipped", "")))
        .replace("{{NOTE}}", esc(note))
        .replace("{{MMDD}}", esc(d["mmdd"]))
        .replace("{{ISODATE}}", esc(d["isodate"]))
    )

    leftover = [m for m in ("{{DATELINE}}", "{{PERIOD}}", "{{WEATHER}}", "{{MARKET_ROWS}}",
                            "{{MARKET_NOTE}}", "{{SECTIONS}}", "{{SKIPPED}}",
                            "{{NOTE}}", "{{MMDD}}", "{{ISODATE}}") if m in page]
    if leftover:
        sys.exit("未置換のプレースホルダが残っています: " + ", ".join(leftover))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)

    total = sum(len(g.get("items", [])) for g in d.get("genres", []))
    print(f"OK {out_path}  記事{total}本  {len(page)}バイト")


if __name__ == "__main__":
    main()
