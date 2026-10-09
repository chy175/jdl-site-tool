# 京东物流网点查询 → 奥维地图标注工具

把「查询某城市京东物流站点 → 生成奥维地图标注文件」的重复劳动，做成一条命令行搞定。

## 它能做什么

输入城市名，自动完成：

1. 解析省市区 ID
2. 调用京东物流官网公开接口，获取该地区全部网点（站名 / 地址 / 经纬度 / 电话 / 网点编码 / 服务类型 / 营业时间）
3. 一键生成两个文件：
   - `京东物流网点-<城市>.kml` —— 奥维互动地图直接导入（标注点带名称和详情）
   - `京东物流网点-<城市>.csv` —— 表格版，Excel 直接打开，便于存档/汇报

## 快速开始

```bash
pip install -r requirements.txt

# 方式A：内置城市（当前内置：北京东城区，用于验证链路）
python jdl_sites.py --city 北京 --district 东城区

# 方式B：新城市手动指定省市区 ID（推荐，ID 来源见下）
python jdl_sites.py --city 惠州市 --region-json "{\"provinceId\":..,\"cityId\":..,\"countyId\":..}"

# 方式C：离线验证输出格式（不联网，用内置示例数据）
python jdl_sites.py --city 北京 --district 东城区 --source demo
```

## 如何拿到新城市的省市区 ID

打开 [京东物流网点查询页](https://www.jdl.com/network/)，按 F12 打开开发者工具 →「网络」标签 → 筛选 `getSiteListByAddressInfo` → 在页面上选好省市区并点查询 → 查看该请求的请求载荷（Payload），里面就是：

```json
[{"provinceId": 1, "cityId": 2802, "countyId": 54744, "searchSiteName": ""}]
```

把这三个 ID 填进 `--region-json` 即可。用得多的话，也可以直接把它们写进 `jdl_sites.py` 的 `KNOWN_REGIONS` 表，一劳永逸。

## 数据源与合规说明

- 数据来源：京东物流官网「网点查询」公开页面（jdl.com/network）背后的公开接口
  `POST https://api.jdl.com/site/getSiteListByAddressInfo`
- 该页面公开可访问、无需登录；接口返回的站点数据**直接含经纬度**，无需地址转坐标
- 本工具默认在请求间加 1 秒间隔（`--pause` 可调），请勿高频抓取
- 每个输出文件都会注明数据来源与抓取日期，站点信息可能随时间更新，使用时注意时效

## 目录结构

```
jdl-site-tool/
├── jdl_sites.py       # 主程序（CLI）
├── requirements.txt   # 依赖清单
├── README.md          # 本文件
├── examples/          # 示例输出（KML / CSV）
└── output/            # 生成的 KML / CSV（运行时自动创建）
```

## 数据源实现状态

| 数据源 | 状态 | 说明 |
|---|---|---|
| `api`（默认） | ✅ 主路径 | 直接调公开接口，curl 裸调会 401，代码内已带浏览器请求头，仍需在真实环境确认会话要求 |
| `demo` | ✅ 可用 | 内置实测示例数据，离线验证 KML/CSV 输出格式 |
| `browser` | 🔧 骨架 | Playwright 无头浏览器驱动页面，任何城市免配 ID；地区选择器 DOM 需按 TODO 联调 |

## 后续待办（Roadmap）

- [ ] 逆向地址树接口，实现「城市名 → 省市区 ID」自动解析
- [ ] 完成 browser 数据源的地区选择器联调
- [ ] 支持一次查询多区县合并输出
- [ ] 输出奥维「线路/标签」样式定制（图标、颜色、分组）
