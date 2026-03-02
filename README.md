# 个人日历 MVP

一个基于 Flask 的网页版个人日历，支持月视图和日程 CRUD。

## 功能

- 月视图日历展示
- 日程新增、查看、编辑、删除
- 字段：标题、开始时间、结束时间、备注、地点（可选）
- 校验：结束时间不能早于开始时间
- 跨天日程在覆盖日期中可见
- 基础响应式（手机可用）

## 快速启动

```bash
cd personal-calendar
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

如果系统提示 `ensurepip is not available` 或 `No module named pip`，先安装依赖后再执行上面命令：

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
```

启动后访问：

- http://127.0.0.1:5000
- 局域网访问：http://<本机IP>:5000

## 目录结构

```text
personal-calendar/
  app.py
  requirements.txt
  calendar.db            # 首次运行自动创建
  templates/
  static/
```

## 说明

- 数据库为 SQLite，默认文件 `calendar.db`。
- 运行日志长期保存在 `logs/app.log`，并自动按大小轮转（最多 5 个备份）。
- 如需初始化空数据，可删除 `calendar.db` 后重启应用。
