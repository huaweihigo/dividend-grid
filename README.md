# 股息率网格 · A股收息观察器

一个可以部署在 GitHub Pages 的个人 A 股收息观察工具。它把你**人工确认的每股年度分红**和**自动更新的最近有效股价**放在一起，计算当前股息率，并为每只股票生成连续的股息率价格网格。

> 本工具仅用于个人股票估值与股息率数据整理，不构成任何投资建议。分红数据可能由用户人工维护，请以公司公告为准。

## 网站地址

发布后访问：[https://huaweihigo.github.io/dividend-grid/](https://huaweihigo.github.io/dividend-grid/)

如果刚完成首次发布，GitHub Pages 通常需要一两分钟才会显示网站。

## 它会做什么

- 展示关注股票的现价、人工维护的年度分红和当前股息率。
- 按“深入击球区 / 已进入 / 接近 / 等待”排序观察；这是估值状态，**不是买卖建议**。
- 点击任意股票，查看 0.1% 步长的股息率对应价格网格。
- 每个工作日北京时间约 15:30 自动更新行情；也可以在 GitHub 手动刷新。
- 行情源依次尝试 AKShare/东方财富与东方财富公开接口；更新失败时，绝不会用 0、空值或错误数据覆盖上一份有效行情。

## 我如何增加一只股票

1. 打开本仓库网页。
2. 打开 `data` 文件夹，再点开 `stocks.json`。
3. 点击右上方铅笔图标 **Edit**。
4. 在最外层 `[` 和 `]` 中加入一项。除最后一项外，每项末尾需要一个英文逗号 `,`。
5. 滚动到底部，点击 **Commit changes** 保存。网站会自动重新发布。

例如，添加云铝股份可复制下面这一项（注意与前一项之间要有逗号）：

```json
{
  "code": "000807",
  "exchange": "SZ",
  "name": "云铝股份",
  "category": "有色金属",
  "annual_dividend": 1.0,
  "dividend_note": "人工维护",
  "target_low": 24,
  "target_high": 25,
  "target_price": null,
  "grid_min": 3.0,
  "grid_max": 7.0,
  "grid_step": 0.1,
  "notes": ""
}
```

股票代码必须保留在双引号中，例如 `"000807"`，这样前面的 0 不会丢失。

### 每个字段是什么意思

| 字段 | 含义 |
|---|---|
| `code` / `exchange` | 六位股票代码与交易所：上海是 `SH`，深圳是 `SZ`。|
| `name` / `category` | 网站显示的名称与分类。|
| `annual_dividend` | **人工确认的每股年度分红**。未知时填写 `null`，不要猜。|
| `dividend_note` | 分红数据的来源或维护说明。|
| `target_low` / `target_high` | 击球区下沿、上沿；不设置就都填 `null`。|
| `target_price` | 只有一个参考价格时使用；它不会被伪装成击球区。|
| `grid_min` / `grid_max` / `grid_step` | 详情页网格的最小股息率、最大股息率和步长，单位都是百分比。|
| `notes` | 其他提醒。|

## 我如何修改分红或击球区

还是打开 `data/stocks.json` 并点击 **Edit**：

- 分红变为 2.10 元：把对应股票的 `"annual_dividend": 2.02` 改成 `"annual_dividend": 2.10`。
- 修改击球区：改 `target_low` 和 `target_high`。例如 `36～37` 就是 `"target_low": 36, "target_high": 37`。
- 不确定分红时请填 `null`。网页会显示“分红待维护”，不会把它算成 0%。

保存后等待 Pages 自动发布即可。

## 我如何手动刷新行情

在仓库网页依次点击：

`Actions` → `Update Market Data` → `Run workflow` → `Run workflow`

流程会读取股票池、抓取并校验价格、写入 `data/market.json`，再自动提交。周一到周五也会在**北京时间约 15:30**自动运行；GitHub 的定时任务可能因排队而稍晚执行。

## 如果行情更新失败怎么办

不用紧张：页面会明确显示数据状态，且脚本会保留上次已确认有效的价格。它不会把价格变成 0，也不会清空整个 `market.json`。稍后在 Actions 再运行一次即可。若某只股票一直缺失，请检查 `code` 和 `exchange` 是否正确。

## 计算口径

```
当前股息率 = 每股年度分红 ÷ 当前股价 × 100%
对应价格 = 每股年度分红 ÷ (目标股息率 ÷ 100)
```

例如年度分红为 2.02 元、目标股息率为 5%，对应价格是 `2.02 ÷ 0.05 = 40.40` 元。

## 项目目录

```text
├── index.html / style.css / app.js   # 无构建步骤的静态网站
├── data/
│   ├── stocks.json                   # 你维护的股票池和分红（唯一配置来源）
│   └── market.json                   # 自动更新的行情快照
├── scripts/
│   ├── market_utils.py               # 公式与安全合并规则
│   └── update_market.py              # 免费行情更新脚本
├── tests/                            # 关键计算与失败保护测试
└── .github/workflows/
    ├── test.yml                      # 推送后运行测试
    ├── update-market.yml             # 定时/手动刷新行情
    └── deploy-pages.yml              # 发布 GitHub Pages
```

## 本地检查（可选）

安装 Python 3.10+ 后，在项目目录运行：

```powershell
python -m unittest discover -s tests -v
python scripts/update_market.py --dry-run
```

第二条会联网尝试获取行情但不会改写文件。没有安装 AKShare 时，会自动回退到东方财富公开行情接口。
