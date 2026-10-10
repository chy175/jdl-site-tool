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

# 方式A：内置城市（当前内置：北京东城区、惠州惠城区、惠州惠东县）
python jdl_sites.py --city 惠州-惠东县

# 方式B：任意城市，用浏览器自动操作官网（无需手动配 ID，推荐）
python jdl_sites.py --city 惠州市 --district 惠东县 --source browser --province 广东

# 方式C：新城市手动指定省市区 ID
python jdl_sites.py --city 惠州市 --region-json "{\"provinceId\":..,\"cityId\":..,\"countyId\":..}"

# 方式D：离线验证输出格式（不联网，用内置示例数据）
python jdl_sites.py --city 北京 --district 东城区 --source demo
```

> **提示**：默认 `--source api` 在纯 requests 环境下会被京东 WAF 按 TLS 指纹拦截（返回 401 Invalid Host），不是请求头问题。跨机器/服务器部署时优先用 `--source browser`（Playwright 无头浏览器），或自行换 `curl_cffi` 模拟 Chrome TLS 指纹。

## 新增城市（两种方式）

### 方式一：加进 regions.json（推荐）

打开 `regions.json`，复制一个已有条目改成新城市即可。省市区 ID 获取方法：

打开 [京东物流网点查询页](https://www.jdl.com/network/)，F12 →「网络」→ 筛选 `getSiteListByAddressInfo` → 页面上选好省市区并点查询 → 看该请求的请求载荷（Payload）：

```json
[{"provinceId": 19, "cityId": 1643, "countyId": 36177, "searchSiteName": ""}]
```

把三个 ID 填进 `regions.json`，之后 `python jdl_sites.py --city <key>` 即可。

### 方式二：浏览器模式（不用配 ID）

```bash
python jdl_sites.py --city 某城市 --source browser --province 所在省 --district 区县
```

工具会自动打开京东物流官网，按省份→城市→区县逐级选择并查询（基于 2026-10 实测页面结构编写，若官网改版需微调选择器）。

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
| `api` | ⚠️ 受限 | 接口本身可用，但 requests 裸调会被 WAF 按 TLS 指纹拦截（401 Invalid Host: api.jdl.com 未注册）；代码内请求头已齐，缺的是浏览器 TLS 指纹。服务器部署请换 curl_cffi 或走 browser 模式 |
| `browser` | ✅ 已联调 | Playwright 无头浏览器驱动页面，任何城市免配 ID；选择器按 2026-10 实测页面结构编写（`.cascade-address .tab-item` / `.option-item` / `button.el-button--primary`），官网改版需微调 |
| `demo` | ✅ 可用 | 内置实测示例数据，离线验证 KML/CSV 输出格式 |

## 实测踩坑记录（2026-10）

- **api 模式 401 不是请求头问题**：最初以为缺 Origin/Referer，补全后仍 401，错误体是 `Invalid Host: api.jdl.com 未注册`，实际是 WAF 校验 TLS 指纹（JA3），纯 requests/curl 过不去。
- **级联选择器第一级 tab**：不是 `.tab-list li:first-child`，而是 `.tab-list .tab-item >> nth=0`；选项要加 `.cascade-address` 前缀，否则会误中页面其他 `li`。
- **选完区县弹层会自动关闭**：不需要再点遮罩或关闭按钮，直接等 ~1s 即可。
- **查询按钮别用 `text=查询`**：页面上整个搜索列表区都含「查询」字样，`text=查询` 会误点到列表区域而不触发请求；要点具体的 `button.el-button--primary:has-text("查询")`。
- **expect_response 要限定 POST**：页面加载时可能有其他 GET 请求命中同 URL 片段，限定 `request.method == "POST"` 才稳。

## 后续待办（Roadmap）

- [ ] 逆向地址树接口，实现「城市名 → 省市区 ID」自动解析（api 模式免配 ID）
- [x] 在真实环境完成 browser 数据源联调（Playwright）
- [ ] 支持一次查询多区县合并输出
- [ ] 输出奥维「线路/标签」样式定制（图标、颜色、分组）
- [ ] api 模式接入 curl_cffi 绕过 TLS 指纹校验
