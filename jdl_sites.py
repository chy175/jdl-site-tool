#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京东物流网点查询 → 奥维地图标注工具
================================================
用法示例：
    python jdl_sites.py --city 惠州市
    python jdl_sites.py --city 惠州市 --district 惠城区
    python jdl_sites.py --city 北京 --district 东城区 --source demo   # 离线验证输出格式

输入城市名后：
  1) 解析出省市区 ID（内置表 / 接口解析 / 手动指定，三选一）
  2) 调用京东物流官网公开接口获取该地区全部网点
  3) 生成两个文件：
     - output/京东物流网点-<城市>.kml   奥维互动地图可直接导入
     - output/京东物流网点-<城市>.csv   表格版，便于存档/汇报

数据源：京东物流官网「网点查询」公开页面（https://www.jdl.com/network/）
合规提示：仅查询官方公开数据，控制请求频率，输出文件注明数据来源与抓取日期。
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------- 常量

API_URL = "https://api.jdl.com/site/getSiteListByAddressInfo"

# 请求头：从浏览器实际观察到的字段（curl 裸调会 401，需要这套头 + 浏览器会话上下文）
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Origin": "https://www.jdl.com",
    "Referer": "https://www.jdl.com/network/",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
}

# 内置省市区 ID 表（仅收录"已实测验证"的城市；新城市请用 --region-json 或补充此表）
# 字段：provinceId / cityId / countyId / 展示名
KNOWN_REGIONS = {
    # 北京（东城区）—— 接口实测：provinceId=1, cityId=2802, countyId=54744
    "北京": {"provinceId": 1, "cityId": 2802, "countyId": 54744,
            "label": "北京市-东城区"},
}

# 奥维地图导入用的 KML 模板（标准 KML 2.2，奥维互动地图可直接识别）
KML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{title}</name>
  <description>{desc}</description>
{placemarks}
</Document>
</kml>
"""

KML_PLACEMARK = """  <Placemark>
    <name>{name}</name>
    <description>{desc}</description>
    <Point>
      <coordinates>{lon},{lat},0</coordinates>
    </Point>
  </Placemark>
"""


# ---------------------------------------------------------------- 数据获取

def fetch_sites_api(region: dict, pause: float = 1.0) -> list:
    """
    调用京东物流公开接口获取网点列表（主数据源）。
    region: {"provinceId":.., "cityId":.., "countyId":..}
    返回：[{siteName,address,latitude,longitude,telephone,siteCode,...}]
    """
    try:
        import requests  # 延迟导入，demo 模式可离线运行
    except ImportError:
        sys.exit("缺少依赖：请先运行  pip install -r requirements.txt")

    payload = [{
        "provinceId": region["provinceId"],
        "cityId": region["cityId"],
        "countyId": region["countyId"],
        "searchSiteName": "",
    }]
    time.sleep(pause)  # 限速：避免高频请求
    resp = requests.post(API_URL, json=payload, headers=API_HEADERS, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 1:
        sys.exit(f"接口返回异常: code={body.get('code')}, msg={body.get('msg')}")
    return body.get("data") or []


def fetch_sites_browser(region_label: str) -> list:
    """
    备选数据源：Playwright 无头浏览器驱动官网页面（任何城市都能跑，无需维护 ID 表）。
    TODO(联调项)：地区选择器的 DOM 结构在真实环境需确认选择器；
                  步骤已按实测页面流程编写，首次运行请打开 headless=False 观察。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("缺少依赖：请先运行  pip install -r requirements.txt  （含 playwright 及其浏览器）")

    province = region_label.split("省")[0] if "省" in region_label else region_label

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.jdl.com/network/", timeout=30000)
        page.wait_for_load_state("networkidle")

        # 1) 打开地区选择器（主查询输入框，默认值如"北京 东城区"）
        # TODO: 以下为骨架步骤，选择器需在真实页面联调：
        #   page.click('input[placeholder="请输入省份/城市/区县搜索"]')
        #   page.fill('input[placeholder="请输入省份/城市/区县搜索"]', province)
        #   page.click(f'text={province}')
        #   page.fill('input[placeholder="请输入省份/城市/区县搜索"]', city)
        #   page.click(f'text={city}')
        #   page.click('text=查询')
        #   page.wait_for_timeout(3000)
        #   # 解析结果区文本（每站：名称 / 地址 / 联系电话 / 网点编码）
        #   text = page.inner_text("body")
        #   ... 用正则按块拆分站点信息 ...
        browser.close()
    raise NotImplementedError("browser 数据源为骨架，需按 TODO 完成联调；当前请用 --source api 或 --source demo")


# ---------------------------------------------------------------- 输出生成

def build_kml(sites: list, title: str, source_desc: str) -> str:
    """生成奥维地图可导入的 KML 文本。"""
    places = []
    for s in sites:
        name = s.get("siteName", "未命名站点")
        desc_parts = [
            s.get("address", ""),
            "电话：" + str(s.get("telephone", "")),
            "网点编码：" + str(s.get("siteCode", "")),
            "服务：" + str(s.get("siteBusinessName", "")),
        ]
        if s.get("businessHoursStart"):
            desc_parts.append("营业：" + s["businessHoursStart"] + "~" + s.get("businessHoursEnd", ""))
        places.append(KML_PLACEMARK.format(
            name=_escape_xml(name),
            desc=_escape_xml("；".join(p for p in desc_parts if p)),
            lon=s.get("longitude", 0),
            lat=s.get("latitude", 0),
        ))
    return KML_TEMPLATE.format(title=_escape_xml(title), desc=_escape_xml(source_desc),
                               placemarks="\n".join(places))


def build_csv(sites: list) -> str:
    """生成带表头的 CSV 文本（UTF-8 带 BOM，Excel 直接打开不乱码）。"""
    out = ["站名,地址,经度,纬度,联系电话,网点编码,服务类型,营业时间"]
    for s in sites:
        hours = ""
        if s.get("businessHoursStart"):
            hours = f'{s["businessHoursStart"]}~{s.get("businessHoursEnd", "")}'
        out.append(",".join([
            _csv_cell(s.get("siteName", "")),
            _csv_cell(s.get("address", "")),
            str(s.get("longitude", "")),
            str(s.get("latitude", "")),
            _csv_cell(s.get("telephone", "")),
            str(s.get("siteCode", "")),
            _csv_cell(s.get("siteBusinessName", "")),
            _csv_cell(hours),
        ]))
    return "\ufeff" + "\n".join(out) + "\n"


def _csv_cell(v: str) -> str:
    v = str(v).replace('"', '""')
    return f'"{v}"' if ("," in v or '"' in v) else v


def _escape_xml(v: str) -> str:
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def write_outputs(sites: list, region: dict, out_dir: str, source_desc: str) -> list:
    """写出 KML + CSV，返回生成的文件路径列表。"""
    os.makedirs(out_dir, exist_ok=True)
    city_label = region.get("label", region.get("city", "未知名"))
    stamp = datetime.now().strftime("%Y-%m-%d")
    title = f"京东物流网点-{city_label}"
    desc = f"数据来源：京东物流官网网点查询（公开接口）｜抓取日期：{stamp}｜共 {len(sites)} 个站点"

    kml_path = os.path.join(out_dir, f"{title}.kml")
    csv_path = os.path.join(out_dir, f"{title}.csv")
    with open(kml_path, "w", encoding="utf-8") as f:
        f.write(build_kml(sites, title, desc))
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(build_csv(sites))
    return [kml_path, csv_path]


# ---------------------------------------------------------------- 区域解析

def resolve_region(city: str, district: str, region_json: str) -> dict:
    """
    把城市名解析为省市区 ID，优先级：
      1) --region-json 手动指定（最可靠，新城市推荐）
      2) 内置 KNOWN_REGIONS 表
      3) 接口解析（TODO：地址树接口参数待逆向，命中失败会明确提示）
    """
    if region_json:
        cfg = json.loads(region_json)
        cfg.setdefault("label", f"{city}-{district or ''}")
        return cfg

    if city in KNOWN_REGIONS:
        r = dict(KNOWN_REGIONS[city])
        r.setdefault("label", f"{city}-{district or '全部'}")
        return r

    # TODO(联调项)：调用京东地址树接口按城市名解析 ID
    #   候选接口：POST /address/getAddressInfoByParentIdFilterGAT（参数格式待确认）
    #   未确认前不编造 ID，明确提示用户两种可行做法。
    sys.exit(
        f"未内置「{city}」的省市区 ID，请任选一种方式：\n"
        "  1) 用 --region-json 手动指定：\n"
        "     python jdl_sites.py --city 惠州市 --region-json "
        '{"provinceId":..,"cityId":..,"countyId":..}\n'
        "     （ID 获取方法：打开 jdl.com/network，F12 → 网络 → 筛选 getSiteListByAddressInfo，"
        "看请求参数里的 provinceId/cityId/countyId）\n"
        "  2) 把城市加入 jdl_sites.py 里的 KNOWN_REGIONS 表后重跑"
    )


# ---------------------------------------------------------------- 主流程

def main():
    parser = argparse.ArgumentParser(description="京东物流网点查询 → 奥维 KML/CSV 标注工具")
    parser.add_argument("--city", required=True, help="城市名，如：惠州市")
    parser.add_argument("--district", default="", help="区县名（可选），如：惠城区")
    parser.add_argument("--source", choices=["api", "browser", "demo"], default="api",
                        help="数据源：api=接口(默认) / browser=无头浏览器 / demo=内置示例数据(离线验证输出)")
    parser.add_argument("--out", default="output", help="输出目录（默认 output/）")
    parser.add_argument("--region-json", default="", help="手动指定省市区 ID 的 JSON 字符串")
    parser.add_argument("--pause", type=float, default=1.0, help="接口请求间隔秒数（限速，默认1秒）")
    args = parser.parse_args()

    # 示例数据源：离线验证 KML/CSV 生成逻辑（数据来自接口实测，非编造）
    if args.source == "demo":
        demo_sites = [
            {"siteName": "北京市-东四-雍和宫项目接驳点", "address": "北京市东城区北新桥歌华大厦(青龙胡同北)",
             "latitude": 39.948864, "longitude": 116.424217, "telephone": "18730726288",
             "siteCode": 2904839, "siteBusinessName": "京配配送服务"},
            {"siteName": "北京市-东四-条子胡同项目接驳点", "address": "北京市东城区北新桥秋果酒店(北京东直门雍和宫簋街店)南",
             "latitude": 39.947816, "longitude": 116.424795, "telephone": "18618564934",
             "siteCode": 2904699, "siteBusinessName": "京配配送服务"},
            {"siteName": "北京新仓站", "address": "北京市东城区豆瓣胡同2号楼底商",
             "latitude": 39.928558, "longitude": 116.432304, "telephone": "19233014680",
             "siteCode": 689804, "siteBusinessName": "京配配送、自提服务"},
        ]
        region = {"label": f"{args.city}-{args.district or '示例'}"}
        source_desc = "示例数据（接口实测样本，离线验证用）"
    else:
        region = resolve_region(args.city, args.district, args.region_json)
        if args.source == "api":
            sites_raw = fetch_sites_api(region, pause=args.pause)
            # 接口可能返回 dict（单条）或 list，统一成 list
            demo_sites = sites_raw if isinstance(sites_raw, list) else [sites_raw]
            source_desc = f"京东物流官网公开接口（{datetime.now():%Y-%m-%d}）"
        else:
            demo_sites = fetch_sites_browser(region.get("label", args.city))
            source_desc = f"京东物流官网页面（{datetime.now():%Y-%m-%d}）"

    if not demo_sites:
        sys.exit("未查询到站点数据（可能该地区暂无网点，或 ID 配置有误）。")

    files = write_outputs(demo_sites, region, args.out, source_desc)
    print(f"查询成功：共 {len(demo_sites)} 个站点")
    for f in files:
        print("已生成:", f)


if __name__ == "__main__":
    main()
