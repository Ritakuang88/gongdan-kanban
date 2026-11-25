# -*- coding: utf-8 -*-
"""
地区对接人速查 —— 一键同步脚本
用法（手动触发）：python sync.py
流程：企微CLI读智能表[地区对接人名单] → 清洗为 data.json → 生成 index.html → 自检
"""
import json, re, subprocess, sys, io, os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DOCID = "s3_ASwAVQYIACQCNhuImXhpBR8uzclV3"
SHEET_MAIN = "对接人名单-一维表"
SHEET_POS = "人员职位"

# 角色字段 → 页面显示名 → 搜索关键词
ROLES = [
    ("合同接口人", "合同接口人", ["合同"]),
    ("结算接口人", "结算接口人", ["结算"]),
    ("费用修改接口人", "费用修改", ["费用"]),
    ("客情接口人（含商品调价）", "客情+商品调价", ["客情", "调价"]),
    ("采购接口人", "采购接口人", ["采购"]),
    ("撤架接口人", "撤架接口人", ["撤架"]),
    ("补货接口人", "补货接口人", ["补货"]),
    ("商品效期接口人", "商品效期接口人", ["效期"]),
    ("货损接口人", "货损接口人", ["货损"]),
    ("设备运维接口人", "设备运维接口人", ["设备", "运维"]),
    ("物流接口人（搬迁/换架→物流接口人）", "物流接口人（搬迁换架催审）", ["物流", "搬迁", "换架", "催审"]),
    ("清洁客诉-新装（激活后两周内）反馈物流接口人", "清洁新装（激活两周内由司机清洁）", ["清洁新装", "新装"]),
    ("清洁客诉（留存）", "清洁留存（店主）", ["清洁留存", "留存", "店主"]),
    ("商品质量接口人", "商品质量接口人", ["质量"]),
    ("挪点商机申报", "挪点商机", ["挪点"]),
    ("企业福利接口人", "企业福利", ["福利"]),
    ("管家接口人", "管家接口人", ["管家"]),
    ("客诉工单总接口人", "客诉工单总接口人", ["客诉", "工单总"]),
    ("运营经理/城市总", "地区运营经理", ["运营经理", "城市总"]),
    ("AI群内管家账号", "AI群内管家账号", ["AI管家", "AI群内"]),
    ("管家账号（非AI群）", "管家账号（非AI群）", ["管家账号"]),
]

# 优先直接运行本地原生程序，避免 npx / cmd 在 Windows 上反复弹出黑窗
WECOM_PKG = "@wecom/cli@1.3.4"
WECOM_NATIVE = os.path.join(HERE, ".wecom-cli", "node_modules", "@wecom",
                            "cli-win32-x64", "bin", "wecom-cli.exe")

def run_cli(args):
    use_native = os.path.isfile(WECOM_NATIVE)
    cmd = ([WECOM_NATIVE] if use_native else ["npx", "-y", WECOM_PKG]) + args
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       shell=(os.name == "nt" and not use_native), startupinfo=startupinfo,
                       creationflags=creationflags)
    if p.returncode != 0:
        raise RuntimeError("wecom-cli 失败: " + p.stderr[:500])
    m = re.search(r"\{.*\}", p.stdout, re.S)
    if not m:
        raise RuntimeError("wecom-cli 无 JSON 输出: " + p.stdout[:300])
    d = json.loads(m.group(0))
    if d.get("errcode") not in (0, None):
        raise RuntimeError(f"errcode={d.get('errcode')} errmsg={d.get('errmsg')}")
    return d

def list_records(sheet_title, limit):
    """分页拉取整个子表，直到 has_more 为 False"""
    recs, cursor = [], None
    while True:
        payload = {"docid": DOCID, "sheet_title": sheet_title, "limit": limit}
        if cursor:
            payload["cursor"] = cursor
        d = run_cli(["smartsheet", "records", "list", "--json",
                     json.dumps(payload, ensure_ascii=False)])
        recs.extend(d.get("records", []))
        if not d.get("has_more"):
            break
        cursor = d.get("next_cursor")
        if not cursor:
            break
    return recs

def cell(values, field):
    v = values.get(field)
    if not v:
        return None
    if isinstance(v, list):
        if not v:
            return None
        # 多段文本（单元格内换行/多条目）按段拼接，段尾一般自带 \n
        return "".join(x.get("text", "") for x in v if isinstance(x, dict))
    return v

def clean_person(name):
    """去掉姓名后的（备注）后缀"""
    if not name:
        return None
    return re.sub(r"（.*?）$", "", name.strip()).strip()

def fetch_and_clean():
    main_recs = list_records(SHEET_MAIN, 200)   # 列多，limit*列数须 <10000
    pos_recs = list_records(SHEET_POS, 1000)
    positions = {}
    for r in pos_recs:
        n = cell(r["values"], "姓名")
        t = cell(r["values"], "职位")
        if n:
            positions[n.strip()] = t or ""
    # 职位表漏录时的兜底；一旦表内有刘依晴，以智能表为准。
    positions.setdefault("刘依晴", "高级经营分析专员")
    rows, notes = [], []
    for r in main_recs:
        v = r["values"]
        region, area = cell(v, "大区"), cell(v, "地区")
        if not region or not area:
            continue
        role_map = {}
        for field, disp, _kw in ROLES:
            role_map[disp] = cell(v, field)
        rows.append({"region": region, "area": area, "roles": role_map})
        nb = cell(v, "临时备注")
        if nb:
            notes.append({"region": region, "area": area, "text": nb.strip()})
    # 大区排序：按首次出现顺序
    region_order = []
    for r in rows:
        if r["region"] not in region_order:
            region_order.append(r["region"])
    rows.sort(key=lambda r: (region_order.index(r["region"]), r["area"]))
    data = {
        "meta": {
            "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "企微智能表格 [地区对接人名单]",
            "n_regions": len(region_order),
            "n_areas": len(rows),
            "n_roles": len(ROLES),
        },
        "region_order": region_order,
        "roles": [d for _f, d, _k in ROLES],
        "role_keywords": {d: k for _f, d, k in ROLES},
        "rows": rows,
        "positions": positions,
        "notes": notes,
    }
    return data

# 页面模板独立为 page-template.html（交互增强后模板变大，内嵌会撑爆推送体积上限）
TEMPLATE_FILE = os.path.join(HERE, "page-template.html")

def build(data):
    # 页面运行时 fetch 加载 data.json + rows-N.json，模板不含数据
    with open(TEMPLATE_FILE, encoding="utf-8") as f:
        return f.read()

def selfcheck(data, html):
    errs = []
    m = data["meta"]
    if m["n_areas"] != len(data["rows"]):
        errs.append("片区数不一致")
    if m["n_regions"] != len(data["region_order"]):
        errs.append("大区数不一致")
    # PII 扫描：手机号 / 银行卡 / 内部userId（页面模板 + 全部数据负载）
    payload = json.dumps({k: data[k] for k in ("rows", "positions", "notes")}, ensure_ascii=False)
    for pat, name in [(r"1[3-9]\d{9}", "手机号"), (r"\d{16,19}", "银行卡号"), (r"userId", "内部userId"), (r"woNaUWDw", "内部userid")]:
        if re.search(pat, html) or re.search(pat, payload):
            errs.append(f"PII残留: {name}")
    # 渲染完整性
    for kw in ["地区对接人速查", "全部大区", "临时备注", "单击任意人名"]:
        if kw not in html:
            errs.append(f"页面缺元素: {kw}")
    print(f"[自检] 大区{m['n_regions']} 片区{m['n_areas']} 角色{m['n_roles']} 备注{len(data['notes'])} 职位表{len(data['positions'])} 同步时间{m['synced_at']}")
    if errs:
        print("[自检] 发现问题:", errs)
        return False
    print("[自检] 通过：条数核对一致、无手机号/银行卡/内部ID残留、页面元素齐全")
    return True

# rows 分块：按大区分组写入 rows-1..N.json，页面端按 meta.n_chunks 逐个拉取合并
# （单文件全量内嵌超过 100KB，无法走 API 稳定推送；新大区自动并入最后一块）
ROW_GROUPS = [("东北大区", "东南大区"), ("华南大区", "华西大区"), ("华北大区",), ("华中大区",), ("华东大区", "浙江大区")]

def write_outputs(data):
    chunks = [[] for _ in ROW_GROUPS]
    for r in data["rows"]:
        for i, g in enumerate(ROW_GROUPS):
            if r["region"] in g:
                chunks[i].append(r)
                break
        else:
            chunks[-1].append(r)
    meta = dict(data["meta"])
    meta["n_chunks"] = len(chunks)
    base = {"meta": meta, "region_order": data["region_order"], "roles": data["roles"],
            "role_keywords": data["role_keywords"], "positions": data["positions"], "notes": data["notes"]}
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=1)
    for i, ch in enumerate(chunks, 1):
        with open(os.path.join(HERE, f"rows-{i}.json"), "w", encoding="utf-8") as f:
            json.dump({"rows": ch}, f, ensure_ascii=False, indent=1)

def load_old():
    """读取上次发布的 data.json + rows-N.json 并合并为完整数据"""
    old = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    old["rows"] = []
    for i in range(1, old["meta"].get("n_chunks", 0) + 1):
        old["rows"] += json.load(open(os.path.join(HERE, f"rows-{i}.json"), encoding="utf-8"))["rows"]
    return old

def main():
    print("[1/4] 读取企微智能表 ...")
    data = fetch_and_clean()
    keys = ("region_order", "roles", "role_keywords", "rows", "positions", "notes")
    if os.path.exists(os.path.join(HERE, "data.json")):
        try:
            old = load_old()
            if json.dumps({k: old[k] for k in keys}, ensure_ascii=False, sort_keys=True) == \
               json.dumps({k: data[k] for k in keys}, ensure_ascii=False, sort_keys=True):
                print("[同步] 智能表自上次同步（" + old["meta"]["synced_at"] + "）后无变化，无需重新发布")
                sys.exit(0)
        except Exception:
            pass
    print("[2/4] 写 data.json + rows 分块 ...")
    write_outputs(data)
    print("[3/4] 生成 index.html ...")
    html = build(data)
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("[4/4] 自检 ...")
    ok = selfcheck(data, html)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
