# Crawler Project — 数据工程管线

多源数据采集、清洗、存储、分析一体化管线。当前支持 GitHub Trending 和 SegmentFault。

## 架构

```
crawl.py                     # 统一入口
├── spider/                  # 爬虫层
│   ├── base_spider.py       #   请求引擎（UA池、重试、Session复用）
│   ├── github_spider.py     #   GitHub Trending 爬虫
│   └── sf_spider.py         #   SegmentFault 爬虫
├── parsers/                 # 解析器
│   ├── github_parser.py     #   BeautifulSoup HTML 解析
│   ├── sf_parser.py         #   文章列表解析
│   └── sf_detail_parser.py  #   文章详情解析
├── core/                    # 核心算法
│   ├── bloom_filter.py      #   布隆过滤器（bit数组 + k哈希）
│   ├── simhash.py           #   SimHash 文本指纹（2-gram + 64位指纹）
│   ├── logger.py            #   分层日志 + 监控指标
│   └── alerts.py            #   异常告警
├── storage/                 # 存储层
│   ├── github_db.py         #   SQLite（WAL模式、upsert、历史趋势）
│   └── sf_db.py             #   SQLite + 爬取日志
├── scripts/                 # 运行脚本
│   ├── github_runner.py     #   GitHub 爬取/导出/统计
│   ├── sf_runner.py         #   SegmentFault 爬取/详情/统计
│   ├── analysis.py          #   数据分析 + Matplotlib 5 维图表
│   └── daily_crawl.py       #   每日全流程管线
├── tests/                   # 测试
│   ├── run_all.py           #   3 组 9 项测试入口
│   ├── test_bloom_filter.py
│   ├── test_simhash.py
│   └── test_db.py
└── data/                    # 数据目录（不提交 Git）
```

## 去重架构

两级去重保证数据质量：

| 层级 | 算法 | 作用 |
|------|------|------|
| 第 0 层 | `repo_full_name` 精确匹配 | 跳过数据库中已有的仓库 |
| 第 1 层 | 布隆过滤器 | 单次爬取内的 ID 去重，O(k) 时间 |
| 指纹存储 | SimHash | 内容指纹存储，用于后续分析 |

布隆过滤器参数自选：根据预期容量和误判率自动计算最优 bit 数组大小（m）和哈希函数数（k）。实际误判率与理论值一致（测试验证 < 1.24%）。

## 可观测体系

- **分层日志**：按模块拆分，按 T 轮转保留 7 天
- **监控指标**：爬取次数、失败率、去重统计、入库量
- **异常告警**：失败率 >20% 告警、连续空数据告警、数据量骤降告警

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 爬取 GitHub Trending
python crawl.py github

# 查看统计
python crawl.py github --stats

# 导出数据
python crawl.py github --export --format csv

# 生成分析图表
python crawl.py github --analysis

# 跑完全流程
python scripts/daily_crawl.py

# 运行测试
python tests/run_all.py
```

## 数据

GitHub Trending 表结构（`data/github/github_trending.db`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| repo_full_name | TEXT | owner/repo |
| description | TEXT | 仓库描述 |
| language | TEXT | 编程语言 |
| stars | INTEGER | 总星数 |
| stars_today | INTEGER | 今日新增星数 |
| simhash | TEXT | 内容指纹 |

配套 `trending_history` 表记录每日趋势变化。

## 定时调度

通过 Hermes cronjob 每天 9:00 自动执行全流程：

```bash
# 脚本路径：scripts/daily_crawl.py
# 操作：爬取 → 去重入库 → 分析 → 报告 → 告警检查
```

## License

MIT
