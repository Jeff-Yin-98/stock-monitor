# 🦞 A股量化监控系统

A股实时行情查询和监控工具，支持技术指标分析和交易建议。

## 功能

- **实时行情**: 查询股票价格、涨跌幅
- **价格提醒**: 设置涨跌阈值和目标价提醒
- **技术指标**: MA/MACD/RSI/KDJ/布林带信号
- **交易建议**: 基于多指标综合分析的操作建议
- **每日选股**: 自动筛选符合技术条件的股票

## 安装

### 依赖

```bash
pip install requests pandas numpy
```

### 配置

```bash
cp config.ini.example config.ini
# 编辑 config.ini 设置监控参数
```

## 使用

### 查看行情

```bash
python core.py
```

### 每日选股

```bash
python daily_pick.py
```

### 股票筛选

```bash
python screener.py
```

## 定时任务

```bash
# 添加到 crontab
*/5 9-15 * * 1-5 cd /path/to/stock && ./check.sh
0 18 * * 1-5 cd /path/to/stock && ./run_daily_pick.sh
```

## 技术指标

| 指标 | 买入信号 | 卖出信号 |
|------|---------|---------|
| MA均线 | 快线金叉慢线 | 快线死叉慢线 |
| MACD | DIF上穿DEA | DIF下穿DEA |
| RSI | < 30 超卖 | > 70 超买 |
| KDJ | K、D<20超卖或金叉 | K、D>80超买或死叉 |
| 布林带 | 触及下轨 | 触及上轨 |

## 评分体系

| 信号数量 | 建议仓位 |
|---------|---------|
| 3+个信号 | 50-70% |
| 2个信号 | 30-50% |
| 1个信号 | 10-20% |

## 文件结构

```
stock/
├── core.py           # 核心监控脚本
├── daily_pick.py     # 每日选股
├── screener.py       # 股票筛选
├── Ashare.py         # 数据接口
├── analyze.py        # 深度分析
├── config.ini.example # 配置模板
└── *.sh              # 定时任务脚本
```

## 注意事项

- 数据源：新浪/腾讯双核心，自动故障切换
- 分钟数据有约15分钟延迟
- 技术指标不构成投资建议，仅供研究参考

## License

MIT