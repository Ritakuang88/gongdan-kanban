# 地区对接人速查 · 同步脚本与迁移说明

本目录三个文件：
- `index.html`：公网页面（Render 静态托管自动部署），数据内嵌的静态快照；
- `sync.py`：一键同步脚本（读企微智能表 → 清洗 → 生成 index.html → 隐私自检）；
- `README-sync.md`：本说明。

## 关键信息
- 公网地址：https://gongdan-kanban.onrender.com/duijieren/
- 数据源：企微智能表格【地区对接人名单】（docid 写在 sync.py 内），子表「对接人名单-一维表」「人员职位」；
- 触发语：对 Kimi 说「更新对接人」= 按本说明跑 sync.py 并推送；
- 页面只含 姓名/职位/大区/片区/角色/临时备注；sync.py 自检会扫描手机号/银行卡/内部ID 残留，不通过则退出码 1、禁止推送。

## 换电脑后的接手步骤
1. 新电脑安装 Kimi 桌面版（Kimi Work），安装企业微信插件（wecom-unified）并扫码授权（须维护人本人的企微账号）。
2. 克隆本仓库（git 根目录即本 portal 目录）；GitHub 走 SSH（ssh.github.com:443 通道），本机 HTTPS 直连会超时。
3. 推送凭证在新机器上重新配置：新建 SSH key 或到 github.com 新建 PAT；旧电脑凭证随旧机报废、应视为失效。
4. 在仓库的 `duijieren/` 目录内直接运行 `python sync.py`（脚本把 data.json / index.html 生成在自己所在目录）；若提示「智能表自上次同步后无变化」则无需推送。
5. 推送：`git add index.html && git commit && git push`；Render 约 1 分钟自动部署完成。
6. 验证：浏览器打开公网地址（Ctrl+F5 强刷），核对顶部「数据 …… 同步」时间为本次。

## 坑位备忘
- 企微 CLI 一律走固定版本 `npx -y @wecom/cli@1.3.4`（Kimi Work 企微插件约定），不要装全局 wecom-cli，也不要用旧平台（千问办公）的 shim；
- 脚本内分页拉取：主表按 limit=200、职位表按 limit=1000 翻页到 `has_more=false`，新增片区/人员不会漏（注意 limit × 返回列数须 < 10000）；
- 推送被拒 = 远端被定时任务/他人推进：先 `git fetch` 再普通合并（保留双方改动），严禁强推；
- 看板母版 index.html 通知栏里的速查链接可能被看板侧重建回滚，每次看板日更后顺手核对；
- 表头/首列冻结依赖 `border-collapse:separate`（Chrome 下 collapse 会使 sticky 失效）；
- 搜索逻辑：每次搜索重置旧角色标签选择；角色匹配先特定词（AI管家/管家账号）后通用词（管家→管家接口人）。

## 仓库副本同步约定
每次推送 `index.html` 时，若 `sync.py` 有改动，同一提交里同步更新本目录副本，保证云端备份始终可用。

## 迁移记录
- 2026-11-17：从千问办公平台迁移至 Kimi Work。`sync.py` 的取数方式由「连接器 shim（QWORK_SHIM_ROUTE=wecom-cli）」改为直接调用 `npx -y @wecom/cli@1.3.4`，并新增子表分页拉取；页面文案「千问办公」改为「Kimi」。已用新链路完成一次全量同步验证（8 大区 / 85 片区 / 21 角色 / 职位表 190 人，隐私自检通过）。
