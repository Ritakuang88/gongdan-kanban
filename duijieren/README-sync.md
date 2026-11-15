# 地区对接人速查 · 同步脚本与迁移说明

本目录三个文件：
- `index.html`：公网页面（Render 静态托管自动部署），数据内嵌的静态快照；
- `sync.py`：一键同步脚本（读企微智能表 → 清洗 → 生成 index.html → 隐私自检）；
- `README-sync.md`：本说明。

## 关键信息
- 公网地址：https://gongdan-kanban.onrender.com/duijieren/
- 数据源：企微智能表格【地区对接人名单】（docid 写在 sync.py 内），子表「对接人名单-一维表」「人员职位」；
- 触发语：对千问办公说「更新对接人」= 按本说明跑 sync.py 并推送；
- 页面只含 姓名/职位/大区/片区/角色/临时备注；sync.py 自检会扫描手机号/银行卡/内部ID 残留，不通过则退出码 1、禁止推送。

## 换电脑后的接手步骤
1. 新电脑安装千问办公桌面版；「设置 > 连接器 > 企业微信」扫码登录（须维护人本人的企微账号）。
2. 克隆本仓库（git 根目录即本 portal 目录）；GitHub 走 SSH（ssh.github.com:443 通道），本机 HTTPS 直连会超时。
3. 推送凭证在新机器上重新配置：新建 SSH key 或到 github.com 新建 PAT；旧电脑凭证随旧机报废、应视为失效。
4. 在仓库的 `duijieren/` 目录内直接运行 `python sync.py`（脚本把 data.json / index.html 生成在自己所在目录）；若提示「智能表自上次同步后无变化」则无需推送。
5. 推送：`git add index.html && git commit && git push`；Render 约 1 分钟自动部署完成。
6. 验证：浏览器打开公网地址（Ctrl+F5 强刷），核对顶部「数据 …… 同步」时间为本次。

## 坑位备忘
- wecom-cli 必须直调千问连接器 shim（Windows：`{用户目录}\.qwenworkcn\bin\ext\cli-common-shim-windows-amd64.exe`，环境变量 `QWORK_SHIM_ROUTE=wecom-cli`）；PATH 里若存在 workbuddy 时代旧版 wecom-cli.exe（无 smartsheet 子命令）切勿误用；
- 推送被拒 = 远端被定时任务/他人推进：先 `git fetch` 再普通合并（保留双方改动），严禁强推；
- 看板母版 index.html 通知栏里的速查链接可能被看板侧重建回滚，每次看板日更后顺手核对；
- 表头/首列冻结依赖 `border-collapse:separate`（Chrome 下 collapse 会使 sticky 失效）；
- 搜索逻辑：每次搜索重置旧角色标签选择；角色匹配先特定词（AI管家/管家账号）后通用词（管家→管家接口人）。

## 仓库副本同步约定
每次推送 `index.html` 时，若 `sync.py` 有改动，同一提交里同步更新本目录副本，保证云端备份始终可用。
