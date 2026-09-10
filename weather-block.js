'use strict';

const AREA_FORECAST = '東京地方';
const AREA_TEMP = '東京';
const CODE_FORECAST = '130010';

const WARNING_NAMES = {
  '02': '暴風雪警報', '03': '大雨警報', '04': '洪水警報', '05': '暴風警報',
  '06': '大雪警報', '07': '波浪警報', '08': '高潮警報', '09': '土砂災害警報',
  '32': '暴風雪特別警報', '33': '大雨特別警報', '35': '暴風特別警報',
  '36': '大雪特別警報', '37': '波浪特別警報', '38': '高潮特別警報',
  '39': '土砂災害特別警報',
  '43': '大雨危険警報', '48': '高潮危険警報', '49': '土砂災害危険警報'
};

const ICONS = {
  sun:   { icon: 'ti-sun',         color: 'var(--text-warning)' },
  cloud: { icon: 'ti-cloud',       color: 'var(--text-secondary)' },
  rain:  { icon: 'ti-cloud-rain',  color: 'var(--text-accent)' },
  storm: { icon: 'ti-cloud-storm', color: 'var(--text-pro)' },
  snow:  { icon: 'ti-cloud-snow',  color: 'var(--text-accent)' },
  fog:   { icon: 'ti-cloud-fog',   color: 'var(--text-secondary)' }
};

function jstDate(iso) {
  return String(iso).slice(0, 10);
}

function jstHour(iso) {
  return parseInt(String(iso).slice(11, 13), 10);
}

function shiftDate(ymd, days) {
  const d = new Date(ymd + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function labelReport(iso) {
  const m = parseInt(iso.slice(5, 7), 10);
  const d = parseInt(iso.slice(8, 10), 10);
  const h = jstHour(iso);
  return `${m}/${d} ${h}時発表`;
}

function pickIcon(code, text) {
  if (/雷/.test(text)) return ICONS.storm;
  if (/霧/.test(text)) return ICONS.fog;
  const head = String(code).charAt(0);
  if (head === '1') return ICONS.sun;
  if (head === '2') return ICONS.cloud;
  if (head === '3') return ICONS.rain;
  if (head === '4') return ICONS.snow;
  return ICONS.cloud;
}

function tidy(text) {
  return String(text).replace(/\u3000+/g, ' ').replace(/\s+/g, ' ').trim();
}

function popFill(pop) {
  if (pop < 20) return 'var(--surface-1)';
  let n = 10;
  if (pop >= 40) n = 24;
  if (pop >= 60) n = 38;
  if (pop >= 80) n = 48;
  return `color-mix(in srgb, var(--fill-accent) ${n}%, transparent)`;
}

function findArea(series, key, value) {
  return series.areas.find((a) => a.area[key] === value);
}

function buildWarning(warning, today) {
  const notes = [];
  if (!warning || !warning.reportDatetime) {
    notes.push('警報JSONを取得できませんでした（警報の有無は未確認）。');
    return { html: '', notes };
  }
  const day = jstDate(warning.reportDatetime);
  if (day !== today && day !== shiftDate(today, -1)) {
    notes.push(`警報JSONの発表日時が${day}で古いため、警報の有無は未確認として表示を省略しました。`);
    return { html: '', notes };
  }
  const area = (warning.areaTypes[0].areas || []).find((a) => a.code === CODE_FORECAST);
  if (!area) {
    notes.push('警報JSONに東京地方(130010)が見当たりませんでした。');
    return { html: '', notes };
  }
  const names = (area.warnings || [])
    .filter((w) => w.code && w.status !== '解除' && WARNING_NAMES[w.code])
    .map((w) => WARNING_NAMES[w.code]);
  if (names.length === 0) return { html: '', notes };

  const html = `<div style="display:flex; align-items:center; gap:8px; background:var(--bg-danger); color:var(--text-danger); border-radius:var(--radius); padding:8px 12px; margin-bottom:14px;">`
    + `<i class="ti ti-alert-triangle" style="font-size:18px;" aria-hidden="true"></i>`
    + `<span style="font-size:14px; font-weight:500;">${names.join('・')}</span>`
    + `<span style="font-size:12px; margin-left:auto;">東京地方</span></div>`;
  return { html, notes };
}

function renderWeatherBlock(forecast, warning, todayYmd, nowHour) {
  const notes = [];
  const today = todayYmd;
  const hour = typeof nowHour === 'number' ? nowHour : 7;

  if (!forecast || !forecast[0] || !forecast[0].reportDatetime) {
    return { html: '', notes: ['予報JSONを取得できませんでした。天気ブロックは省略しました。'] };
  }
  const report = forecast[0].reportDatetime;
  const reportDay = jstDate(report);
  if (reportDay !== today && reportDay !== shiftDate(today, -1)) {
    return { html: '', notes: [`予報JSONの発表日時が${reportDay}で古いため、天気ブロックを省略しました。`] };
  }
  if (reportDay !== today) {
    notes.push(`予報は${labelReport(report)}の内容です（当日発表分は未反映）。`);
  }

  const ts0 = forecast[0].timeSeries[0];
  const ts1 = forecast[0].timeSeries[1];
  const ts2 = forecast[0].timeSeries[2];

  const idx = ts0.timeDefines.findIndex((t) => jstDate(t) === today);
  if (idx < 0) return { html: '', notes: ['予報JSONに当日ぶんの天気が含まれていません。天気ブロックを省略しました。'] };

  const fArea = findArea(ts0, 'name', AREA_FORECAST);
  const weatherText = tidy(fArea.weathers[idx]);
  const icon = pickIcon(fArea.weatherCodes[idx], weatherText);

  const tArea = findArea(ts2, 'name', AREA_TEMP);
  let tmin = null;
  let tmax = null;
  ts2.timeDefines.forEach((t, i) => {
    if (jstDate(t) !== today) return;
    if (jstHour(t) === 0) tmin = tArea.temps[i];
    if (jstHour(t) === 9) tmax = tArea.temps[i];
  });

  const pArea = findArea(ts1, 'name', AREA_FORECAST);
  const pops = [];
  ts1.timeDefines.forEach((t, i) => {
    if (jstDate(t) !== today) return;
    const h = jstHour(t);
    if (h + 6 <= hour) return;
    const v = parseInt(pArea.pops[i], 10);
    if (Number.isNaN(v)) return;
    pops.push({ label: `${h}-${h + 6}`, value: v });
  });

  let normal = '';
  const avg = forecast[1] && forecast[1].tempAverage
    ? forecast[1].tempAverage.areas.find((a) => a.area.name === AREA_TEMP)
    : null;
  if (avg && tmax !== null) {
    const diff = Number(tmax) - Number(avg.max);
    if (diff >= 3) normal = '平年より高め';
    else if (diff <= -3) normal = '平年より低め';
  }

  const warn = buildWarning(warning, today);
  notes.push(...warn.notes);

  const popCells = pops.map((p) =>
    `<div style="flex:1; text-align:center; background:${popFill(p.value)}; border-radius:var(--radius); padding:6px 0;">`
    + `<div style="font-size:11px; color:var(--text-secondary);">${p.label}</div>`
    + `<div style="font-size:14px; font-weight:500;">${p.value}%</div></div>`
  ).join('');

  const html = `<div style="background:var(--surface-2); border:0.5px solid var(--border); border-radius:12px; padding:1rem 1.25rem;">`
    + warn.html
    + `<div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:10px;">`
    + `<span style="font-size:13px; color:var(--text-secondary); letter-spacing:0.04em;">東京地方</span>`
    + `<span style="font-size:11px; color:var(--text-muted);">気象庁 ${labelReport(report)}</span></div>`
    + `<div style="display:flex; align-items:center; gap:14px;">`
    + `<i class="ti ${icon.icon}" style="font-size:28px; color:${icon.color};" aria-hidden="true"></i>`
    + `<div style="flex:1; min-width:0;"><p style="margin:0; font-size:16px; font-weight:500;">${weatherText}</p>`
    + (normal ? `<p style="margin:2px 0 0; font-size:13px; color:var(--text-secondary);">${normal}</p>` : '')
    + `</div><div style="display:flex; align-items:baseline; gap:6px;">`
    + `<span style="font-size:24px; font-weight:500;">${tmax === null ? '—' : tmax}°</span>`
    + `<span style="font-size:16px; color:var(--text-secondary);">/ ${tmin === null ? '—' : tmin}°</span></div></div>`
    + (popCells
      ? `<div style="display:flex; gap:6px; margin-top:12px; padding-top:12px; border-top:0.5px solid var(--border);">${popCells}</div>`
      : '')
    + `</div>`;

  return { html, notes };
}

module.exports = { renderWeatherBlock, WARNING_NAMES, popFill, pickIcon };
