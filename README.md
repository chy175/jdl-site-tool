# 京东物流网点查询 → 奥维地图标注工具

把「查询某城市京东物流站点 → 生成奥维地图标注文件」的重复劳动，做成一条命令行搞定。

## 它能做什么

输入城市名，自动完成：

1. 解析省市区 ID（从 `regions.json` 读取，新增城市不用改代码）
2. 调用京东物流官网公开接口，获取该地区全部网点（站名 / 地址 / 经纬度 / 电话 / 网点编码 / 服务类型 / 营业时间）
3. 一键生成两个文件：
   - `京东物流网点-<城市>.kml` —— 奥维互动地图直接导入（标注点带名称和详情）
   - `京东物流网点-<城市>.csv` —— 表格版，Excel 直接打开，便于存档/汇报

## 快速开始

```bash
pip install -r requirements.txt

# 方式A：内置城市（当前内置：北京东城区、惠州惠城区）
python jdl_sites.py --city 惠州

# 方式B：任意城市，用浏览器自动操作官网（无需手动配 ID，推荐）
python jdl_sites.py --city 惠州市 --district 惠城区 --source browser --province 广东

# 方式C：新城市手动指定省市区 ID
python jdl_sites.py --city 惠州市 --region-json "{\"provinceId\":..,\"cityId\":..,\"countyId\":..}"

# 方式D：离线验证输出格式（不联网，用内置示例数据）
python jdl_sites.py --city 北京 --district 东城区 --source demo
```

## 新增城市（两种方式）

### 方式一：加进 regions.json（推荐）

打开 `regions.json`，复制一个已有条目改成新城市即可。省市区 ID 获取方法：

打开 [京东物流网点查询页](https://www.jdl.com/network/)，F12 →「网络」→ 筛选 `getSiteListByAddressInfo` → 页面上选好省市区并点查询 → 看该请求的请求载荷（Payload）：

```json
[{"provinceId": 19, "cityId": 1643, "countyId": 36176, "searchSiteName": ""}]
```

把三个 ID 填进 `regions.json`，之后 `python jdl_sites.py --city <城市名>` 即可。

### 方式二：浏览器模式（不用配 ID）

```bash
python jdl_sites.py --city 某城市 --source browser --province 所在省
```

工具会自动打开京东物流官网，按省份→城市→区县逐级选择并查询（基于实测页面结构编写，若官网改版需微调选择器）。

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
├── regions.json       # 省市区 ID 表（新增城市改这里）
├── requirements.txt   # 依赖清单
├── README.md          # 本文件
├── examples/          # 示例输出（北京 / 惠州，KML + CSV）
└── output/            # 生成的 KML / CSV（运行时自动创建）
```

## 数据源实现状态

| 数据源 | 状态 | 说明 |
|---|---|---|
| `api`（默认） | ✅ 主路径 | 直接调公开接口，curl 裸调会 401，代码内已带浏览器请求头，仍需在真实环境确认会话要求 |
| `browser` | 🔧 已实现待联调 | Playwright 无头浏览器驱动页面，任何城市免配 ID；流程按实测页面结构编写，官网改版需微调 |
| `demo` | ✅ 可用 | 内置实测示例数据，离线验证 KML/CSV 输出格式 |

## 后续待办（Roadmap）

- [ ] 逆向地址树接口，实现「城市名 → 省市区 ID」自动解析（api 模式免配 ID）
- [ ] 在真实环境完成 browser 数据源联调（Playwright）
- [ ] 支持一次查询多区县合并输出
- [ ] 输出奥维「线路/标签」样式定制（图标、颜色、分组）
