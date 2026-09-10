#!/usr/bin/env python3
"""天気ブロック生成

render_news.py から使う。data.json の "weather" キーに、気象庁の
2つのJSONをそのまま入れておく。

{
  "weather": {
    "forecast": [ ... forecast/130000.json の中身 ... ],
    "warning":  { ... warning/130000.json の中身 ... }
  }
}

render_weather() は (html, notes) を返す。notes は空リストのことも
ある。中身があるときは日報末尾の注記に足す。
仕様は weather-block.md を参照。
"""

import html as _html
from datetime import date, timedelta

AREA_FORECAST = "東京地方"
AREA_TEMP = "東京"
CODE_FORECAST = "130010"

WARNING_NAMES = {
    "02": "暴風雪警報", "03": "大雨警報", "04": "洪水警報", "05": "暴風警報",
    "06": "大雪警報", "07": "波浪警報", "08": "高潮警報", "09": "土砂災害警報",
    "32": "暴風雪特別警報", "33": "大雨特別警報", "35": "暴風特別警報",
    "36": "大雪特別警報", "37": "波浪特別警報", "38": "高潮特別警報",
    "39": "土砂災害特別警報",
    "43": "大雨危険警報", "48": "高潮危険警報", "49": "土砂災害危険警報",
}

_CLOUD = "M7 15.5a4.4 4.2 0 0 1 0-8.6 4.8 4.3 0 0 1 10.5 1.9h1a3.35 3.35 0 0 1 0 6.7z"

ICONS = {
    "sun": (
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 3v1.5M12 19.5V21M3 12h1.5M19.5 12H21'
        'M5.6 5.6l1.1 1.1M17.3 17.3l1.1 1.1M18.4 5.6l-1.1 1.1M6.7 17.3l-1.1 1.1"/>'
    ),
    "cloud": f'<path d="{_CLOUD}"/>',
    "rain": f'<path d="{_CLOUD}"/><path d="M10 18l-1 3M14 18l-1 3M18 18l-1 3"/>',
    "storm": f'<path d="{_CLOUD}"/><path d="M13 17.5l-2.5 4h3.5l-2.5 4"/>',
    "snow": f'<path d="{_CLOUD}"/><path d="M10 19h.01M14 19h.01M12 21.5h.01M17 19h.01"/>',
    "fog": f'<path d="{_CLOUD}"/><path d="M5 18.5h6M13 18.5h6M7 21.5h11"/>',
}

ICON_COLORS = {
    "sun": "var(--no)",
    "cloud": "var(--muted)",
    "rain": "var(--accent-2)",
    "storm": "var(--down)",
    "snow": "var(--accent-2)",
    "fog": "var(--muted)",
}


def esc(s):
    return _html.escape(str(s), quote=True)


def _day(iso):
    return str(iso)[:10]


def _hour(iso):
    return int(str(iso)[11:13])


def _label(iso):
    return "%d/%d %d時発表" % (int(iso[5:7]), int(iso[8:10]), _hour(iso))


def _tidy(text):
    return " ".join(str(text).replace("\u3000", " ").split())


def _pick_icon(code, text):
    if "雷" in text:
        return "storm"
    if "霧" in text:
        return "fog"
    head = str(code)[:1]
    return {"1": "sun", "2": "cloud", "3": "rain", "4": "snow"}.get(head, "cloud")


def _pop_fill(pop):
    if pop < 20:
        return "var(--paper-2)"
    n = 10
    if pop >= 40:
        n = 24
    if pop >= 60:
        n = 38
    if pop >= 80:
        n = 48
    return "color-mix(in srgb, var(--accent-2) %d%%, transparent)" % n


def _find_area(series, name):
    for a in series.get("areas", []):
        if a.get("area", {}).get("name") == name:
            return a
    return None


def _svg(kind):
    return (
        '<svg class="w-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="%s" stroke-width="1.5" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">%s</svg>'
        % (ICON_COLORS[kind], ICONS[kind])
    )


def _render_alert(warning, today):
    notes = []
    if not warning or not warning.get("reportDatetime"):
        return "", ["天気：警報JSONを取得できなかったため、警報の有無は未確認です。"]
    day = _day(warning["reportDatetime"])
    if day not in (today, str(date.fromisoformat(today) - timedelta(days=1))):
        return "", ["天気：警報JSONの発表日時が%sで古いため、警報の有無は未確認です。" % day]
    area = None
    for a in warning.get("areaTypes", [{}])[0].get("areas", []):
        if a.get("code") == CODE_FORECAST:
            area = a
            break
    if area is None:
        return "", ["天気：警報JSONに東京地方(130010)が見当たりませんでした。"]
    names = [
        WARNING_NAMES[w["code"]]
        for w in area.get("warnings", [])
        if w.get("code") in WARNING_NAMES and w.get("status") != "解除"
    ]
    if not names:
        return "", notes
    return (
        '    <div class="w-alert">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 4.5l9 15.5H3z"/><path d="M12 10v4M12 17h.01"/></svg>'
        '<span class="w-alert-name">%s</span>'
        '<span class="w-alert-area">東京地方</span></div>\n' % esc("・".join(names)),
        notes,
    )


def render_weather(weather, today=None, now_hour=7):
    """(html, notes) を返す。表示しない場合 html は空文字。"""
    notes = []
    if not weather:
        return "", []
    forecast = weather.get("forecast")
    warning = weather.get("warning")
    if today is None:
        today = date.today().isoformat()

    if not forecast or not forecast[0].get("reportDatetime"):
        return "", ["天気：予報JSONを取得できなかったため、天気ブロックを省略しました。"]

    report = forecast[0]["reportDatetime"]
    report_day = _day(report)
    yesterday = str(date.fromisoformat(today) - timedelta(days=1))
    if report_day not in (today, yesterday):
        return "", ["天気：予報JSONの発表日時が%sで古いため、天気ブロックを省略しました。" % report_day]
    if report_day != today:
        notes.append("天気：%sの内容です（当日発表分は未反映）。" % _label(report))

    ts = forecast[0]["timeSeries"]
    idx = next((i for i, t in enumerate(ts[0]["timeDefines"]) if _day(t) == today), None)
    if idx is None:
        return "", ["天気：予報JSONに当日ぶんが含まれていないため、天気ブロックを省略しました。"]

    f_area = _find_area(ts[0], AREA_FORECAST)
    text = _tidy(f_area["weathers"][idx])
    kind = _pick_icon(f_area["weatherCodes"][idx], text)

    t_area = _find_area(ts[2], AREA_TEMP)
    tmin = tmax = None
    for i, t in enumerate(ts[2]["timeDefines"]):
        if _day(t) != today:
            continue
        if _hour(t) == 0:
            tmin = t_area["temps"][i]
        if _hour(t) == 9:
            tmax = t_area["temps"][i]

    p_area = _find_area(ts[1], AREA_FORECAST)
    pops = []
    for i, t in enumerate(ts[1]["timeDefines"]):
        if _day(t) != today:
            continue
        h = _hour(t)
        if h + 6 <= now_hour:
            continue
        try:
            v = int(p_area["pops"][i])
        except (ValueError, TypeError):
            continue
        pops.append((("%d-%d" % (h, h + 6)), v))

    sub = ""
    avg = None
    if len(forecast) > 1:
        for a in forecast[1].get("tempAverage", {}).get("areas", []):
            if a.get("area", {}).get("name") == AREA_TEMP:
                avg = a
    if avg and tmax is not None:
        diff = float(tmax) - float(avg["max"])
        if diff >= 3:
            sub = "平年より高め"
        elif diff <= -3:
            sub = "平年より低め"

    alert_html, alert_notes = _render_alert(warning, today)
    notes.extend(alert_notes)

    pop_html = ""
    if pops:
        cells = "".join(
            '<li style="background:%s"><span>%s</span><b>%d%%</b></li>' % (_pop_fill(v), esc(l), v)
            for l, v in pops
        )
        pop_html = '    <ul class="w-pops">%s</ul>\n' % cells

    body = (
        '  <section class="weather" aria-label="天気">\n'
        '    <div class="w-head"><span class="label">Weather</span>'
        '<span class="sub">気象庁 %s</span></div>\n' % esc(_label(report))
        + alert_html
        + '    <div class="w-main">%s\n' % _svg(kind)
        + '      <div class="w-text"><div class="w-desc">%s</div>%s</div>\n'
        % (esc(text), ('<div class="w-sub">%s</div>' % esc(sub)) if sub else "")
        + '      <div class="w-temp"><span class="w-max">%s°</span>'
        '<span class="w-min">/ %s°</span></div>\n'
        % (esc(tmax) if tmax is not None else "—", esc(tmin) if tmin is not None else "—")
        + '    </div>\n'
        + pop_html
        + '  </section>'
    )
    return body, notes
