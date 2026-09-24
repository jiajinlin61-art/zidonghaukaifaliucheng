# 教程一：安装 AgentDock 并连接网页版 ChatGPT

本教程先完成最小目标：让网页版 ChatGPT 通过已认证的 MCP 连接真实电脑，并用一组从只读到受控写入的测试证明链路可用。任务板和定时开发放在下一篇教程中。

AgentDock 的界面、安装参数和版本行为可能变化。以下官方资料是权威来源，本教程负责把它们组织成一条实践路线：

- [AgentDock 官方源码](https://github.com/uvwt/agentdock)
- [AgentDock 中文说明](https://github.com/uvwt/agentdock/blob/main/README.zh-CN.md)
- [官方安装总览](https://uvwt.github.io/agentdock-docs/zh-CN/docs/getting-started/install)
- [macOS 图形安装教程](https://uvwt.github.io/agentdock-docs/zh-CN/docs/getting-started/macos)
- [最新正式版本下载](https://github.com/uvwt/agentdock/releases/latest)
- [使用 ChatGPT 连接 AgentDock](https://uvwt.github.io/agentdock-docs/zh-CN/docs/guides/chatgpt)

如果本教程与官方文档冲突，以官方文档为准。

## 1. 先理解连接链路

```text
网页版 ChatGPT
    ↓ HTTPS + OAuth
公网 MCP 地址
    ↓
AgentDock
    ↓
允许访问的文件 / 命令 / Git / 浏览器
```

AgentDock 是工具运行层，不提供聊天模型，也不是项目任务状态的来源。它让 ChatGPT 能在明确权限下调用真实电脑；项目如何持续开发由下一篇教程定义。

## 2. 选择连接方式

| 方式 | 适合场景 | 需要准备 | 主要限制 |
|---|---|---|---|
| 仅本机 | MCP 客户端也运行在这台电脑 | 无 | 网页版 ChatGPT 无法访问本机回环地址 |
| 临时公网地址 | 第一次试用、暂时没有域名 | 可访问互联网 | Tunnel 或电脑重启后地址可能变化 |
| 固定域名 | 长期连接网页版 ChatGPT | 官方方案需要 Cloudflare 域名与 Tunnel Token | 电脑睡眠或断网时仍会离线 |

第一次实践推荐使用“临时公网地址”。先证明 OAuth 和 MCP 调用正常，再决定是否配置固定域名。

## 3. 在 macOS 安装官方应用

本节是 [macOS 官方安装教程](https://uvwt.github.io/agentdock-docs/zh-CN/docs/getting-started/macos) 的实践摘要。

1. 从 [官方 Release](https://github.com/uvwt/agentdock/releases/latest) 下载 `AgentDock-macos-universal.dmg`。
2. 打开 DMG，把 `AgentDock.app` 拖到“应用程序”。同一安装包支持 Apple 芯片和 Intel Mac。
3. 第一次启动时，在“应用程序”中右键 AgentDock 并选择“打开”，再确认一次。
4. 不要关闭 Gatekeeper，也不要修改系统全局安全设置。
5. 打开 AgentDock 主窗口，选择“临时地址”，点击“安装并启动”。
6. 等待状态显示运行正常。

如果你使用 Windows、Linux 或 Docker，从 [官方安装总览](https://uvwt.github.io/agentdock-docs/zh-CN/docs/getting-started/install) 进入对应平台教程，不要照抄 macOS 命令。

## 4. 先验证本机服务

默认端口通常是 `8765`，但应以控制面板显示为准。

```bash
curl -fsS http://127.0.0.1:8765/healthz
```

这一步失败时，先在控制面板重启服务并查看日志。不要在本机服务未正常前排查域名或 ChatGPT。

本机 MCP 地址通常类似：

```text
http://127.0.0.1:8765/mcp
```

它只能供本机客户端使用。不要把它填进网页版 ChatGPT，因为云端无法访问你电脑的 `127.0.0.1`。

## 5. 取得公网地址和 OAuth 密码

开启临时或固定公网访问后，AgentDock 控制面板会显示：

- 公网 MCP 地址，结尾应为 `/mcp`；
- OAuth 登录密码；
- Bearer Token（供支持该认证方式的客户端使用）。

凭据默认遮罩是正常的。只在授权页面中输入 OAuth 密码，不要把密码或 Token 发到聊天、截图、Issue 或 Git。

## 6. 在 ChatGPT 中创建连接

界面入口可能随 ChatGPT 更新而变化，操作时同时参考 [官方 ChatGPT 接入教程](https://uvwt.github.io/agentdock-docs/zh-CN/docs/guides/chatgpt)。当前流程是：

1. 在 ChatGPT 设置中进入插件相关设置。
2. 打开高级设置并启用开发人员模式。
3. 创建插件，名称可填写 `AgentDock`。
4. MCP Server URL 填写控制面板复制的公网地址，例如：

   ```text
   https://your-public-host.example/mcp
   ```

5. 发起连接，浏览器跳转到 AgentDock 授权页后输入 OAuth 密码。
6. 返回 ChatGPT，确认插件可用。

ChatGPT 会通过 OAuth 动态注册完成授权，不需要手工填写 Client ID、Client Secret 或 Token 地址。

## 7. 用真实调用验证连接

OAuth 页面跳回不代表工具一定可用。按风险从低到高逐层验证。

### 7.1 服务信息

```text
调用 AgentDock 的 server_info，只告诉我服务版本、操作系统和当前认证方式。不要修改任何文件。
```

### 7.2 指定目录只读检查

```text
列出我指定的测试目录，只返回第一层文件名。不要读取其他目录，不要修改任何内容。
```

### 7.3 文件和 Git

```text
读取测试目录中的 README.md，然后查看该仓库的 git status。保持只读。
```

### 7.4 无副作用命令

```text
在指定测试目录打印当前路径并查看 Git 分支，不安装软件，不修改文件。
```

### 7.5 受控写入

只在专门的测试目录执行：

```text
在我指定的测试目录创建 mcp-smoke.txt，写入一行 smoke test，读回确认后告诉我结果。不要操作其他路径。
```

验证完成后可以删除该测试文件。不要用重要项目作为第一次写入测试。

## 8. 可选能力

### 浏览器工具

根据 [macOS 官方教程](https://uvwt.github.io/agentdock-docs/zh-CN/docs/getting-started/macos)，在高级设置中启用浏览器工具前，先安装受支持的 Chrome、Chromium 或 Edge。AgentDock 使用独立会话和 Profile，不应默认接管日常浏览器主 Profile。

### 登录后自动启动

官方图形应用提供“登录后自动启动 AgentDock 服务”和“登录后显示菜单栏”两个独立选项。长期使用时保持核心服务自动启动，并实际重启或重新登录验证。

### 更新和日志

优先使用主窗口的检查更新功能。服务异常时先重启，再从控制面板打开日志目录，不要凭旧教程猜测安装路径。

## 9. 进阶：自建 VPS 固定域名

官方图形安装已经支持 Cloudflare 固定域名。只有希望自主管理 VPS、Nginx 和 SSH 隧道时，才需要本节。

```text
ChatGPT
  ↓ HTTPS + OAuth
agentdock.example.com
  ↓
VPS Nginx :443
  ↓
VPS 127.0.0.1:18765
  ↓ reverse SSH
Mac 127.0.0.1:8765
  ↓
AgentDock
```

这个结构不要求家庭网络拥有固定公网 IP，也不需要在家庭路由器开放端口。AgentDock 和 VPS 转发端口都只监听回环地址，公网只开放 HTTPS。

### 9.1 先手动验证反向 SSH

在 Mac 使用独立密钥建立隧道：

```bash
ssh -NT \
  -o BatchMode=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -i /ABSOLUTE/PATH/TO/TUNNEL_KEY \
  -R 127.0.0.1:18765:127.0.0.1:8765 \
  agentdock-tunnel@VPS_HOSTNAME
```

保持 SSH 运行，在 VPS 验证：

```bash
curl -fsS http://127.0.0.1:18765/healthz
```

只有这一步成功，才继续配置 Nginx。

### 9.2 使用受限账号

长期隧道使用独立系统账号和 SSH Key。账号不授予 sudo，禁用密码登录；公钥可以按服务器 SSH 版本限制为只允许指定回环端口转发：

```text
restrict,port-forwarding,permitlisten="127.0.0.1:18765" ssh-ed25519 REPLACE_WITH_PUBLIC_KEY agentdock-tunnel
```

不要把 SSH 私钥内容写入任何 Markdown、plist 或 Git 文件。

为避免 Mac 断网或睡眠后旧连接长期占用反向转发端口，在 VPS 的 `sshd_config` 或独立配置片段中设置：

```text
ClientAliveInterval 30
ClientAliveCountMax 3
TCPKeepAlive yes
```

执行 `sshd -t` 验证配置后再重新加载 SSH 服务。Mac 端保留 `ServerAliveInterval=30`、`ServerAliveCountMax=3` 和 LaunchAgent 单实例；不要并行启动第二条相同端口的隧道。

### 9.3 配置 Nginx 和 HTTPS

使用 [`nginx-agentdock.conf.example`](../config-examples/nginx-agentdock.conf.example) 作为占位符示例。反向代理必须原样转发 MCP 和 OAuth 所需路径，包括：

```text
/mcp
/register
/oauth/*
/.well-known/*
```

示例使用统一的 `location /`，避免遗漏注册或 OAuth 元数据端点。启用站点前执行 Nginx 配置检查，并使用 ACME/Certbot 等方式配置有效证书。

### 9.4 配置 AgentDock OAuth Origin

手动部署才需要参考 [`agentdock.env.example`](../config-examples/agentdock.env.example)。关键规则：

- `AGENTDOCK_SERVER_URL` 只填写 HTTPS Origin，不包含 `/mcp`；
- OAuth 密码至少 12 个字符；
- Token 签名密钥至少 32 字节并稳定保存；
- 示例文件不能直接用于生产，真实值只能保存在权限受限的本机配置或秘密管理系统中。

重启 AgentDock 和反向代理后，先验证公网健康检查与 OAuth 元数据：

```bash
curl -fsS https://agentdock.example.com/healthz
curl -fsS https://agentdock.example.com/.well-known/oauth-authorization-server
curl -fsS https://agentdock.example.com/.well-known/oauth-protected-resource/mcp
```

元数据应包含与公网 Origin 一致的授权、Token 和动态注册端点。不要直接手工访问 `/oauth/authorize`；正常授权请求需要 ChatGPT 生成的客户端、回调地址和 PKCE 参数。

### 9.5 让隧道自动恢复

macOS 用户登录后的自动恢复可参考 [`agentdock-reverse-tunnel.sh.example`](../config-examples/agentdock-reverse-tunnel.sh.example) 和 [`com.example.agentdock-tunnel.plist.example`](../config-examples/com.example.agentdock-tunnel.plist.example)。循环脚本保证 SSH 异常退出后等待 60 秒再重连，LaunchAgent 只负责保持该循环运行。替换占位符并给脚本添加执行权限后：

```bash
chmod 700 /ABSOLUTE/PATH/TO/agentdock-reverse-tunnel.sh
plutil -lint /ABSOLUTE/PATH/TO/com.example.agentdock-tunnel.plist
launchctl bootstrap gui/$(id -u) /ABSOLUTE/PATH/TO/com.example.agentdock-tunnel.plist
```

然后实际终止一次 SSH 进程、切换网络并唤醒电脑，确认服务能够恢复。LaunchAgent 是用户登录后运行；无人登录时的 LaunchDaemon 是不同安全模型，本教程不混用。

## 10. 分层验证和排障

| 层 | 检查 | 预期 |
|---|---|---|
| AgentDock | 本机 `/healthz` | 成功返回 |
| SSH | VPS 回环 `/healthz` | 与本机一致 |
| Nginx/TLS | 公网 `/healthz` | HTTPS 证书有效 |
| OAuth metadata | 公网 `/.well-known/...` | 返回授权、Token、注册端点 |
| ChatGPT | `server_info` | 完成真实工具调用 |
| 文件权限 | 指定测试目录 | 只访问授权范围 |

常见故障：

- **公网 502**：先检查本机 AgentDock、SSH 进程和 VPS 回环端口，再检查 Nginx。
- **`remote port forwarding failed`**：检查旧 SSH 会话是否占用转发端口。
- **LaunchAgent 退出码为 `255`，但 SSH 端口和密钥正常**：先确认 VPS 的回环转发端口没有被旧会话占用，再重新加载现有 LaunchAgent。不要在未确认端口状态时反复启动多个隧道。

  ```bash
  launchctl bootout gui/$(id -u)/com.example.agentdock-tunnel 2>/dev/null || true
  launchctl bootstrap gui/$(id -u) /ABSOLUTE/PATH/TO/com.example.agentdock-tunnel.plist
  launchctl kickstart -k gui/$(id -u)/com.example.agentdock-tunnel
  launchctl print gui/$(id -u)/com.example.agentdock-tunnel
  ```

  恢复后必须同时确认 VPS 回环端口已经监听、公网 `/healthz` 返回成功、OAuth 元数据可用；只看到 SSH 进程并不足以证明 ChatGPT 链路已恢复。
- **没有跳转到 OAuth**：检查 MCP URL 是否以 `/mcp` 结尾、Origin 是否一致、OAuth 元数据和反向代理路径是否可达。
- **临时地址变化**：从控制面板复制新地址，更新 ChatGPT 连接并重新授权。
- **Mac 睡眠后离线**：固定域名只能固定入口，不能让断网或睡眠中的电脑继续运行。

## 11. 进入下一篇教程前的验收

- 本机健康检查成功；
- ChatGPT 使用公网 HTTPS MCP 地址完成 OAuth；
- `server_info` 真实调用成功；
- 指定目录、文件、Git 和命令的只读测试成功；
- 测试目录受控写入成功；
- 凭据和个人配置没有进入 Git；
- 已理解 AgentDock 只提供工具能力，不负责决定下一个开发任务。

满足这些条件后，继续阅读 [教程二：任务板与定时自动开发](02-task-board-and-scheduled-development.md)。
