# ChatGPT Local Code Skill

让 ChatGPT 网页版通过 **CodexPro + MCP + ngrok 固定地址**读取你明确允许的本地代码。连接器只提供目录浏览、文本搜索和文本读取三个工具。

这是 Agent Skill 和可复现部署辅助脚本，不是新的模型服务，也不是 CodexPro 官方发行版。它不会绕过账号权限、获取 ChatGPT Cookie、接管 Codex 模型路由，或自动替你添加 ChatGPT 插件。

## 安装 Skill

从仓库或解压后的安装包中，将 `skills/chatgpt-local-code` 复制到你的 Agent 支持的 Skill 目录。Codex 的常见用户目录是 `~/.codex/skills/`；如果设置了 `CODEX_HOME`，使用对应目录。不要覆盖已有同名 Skill 而不先检查差异。

```sh
git clone https://github.com/Lianminx/chatgpt-local-code-skill.git
mkdir -p ~/.codex/skills
cp -R chatgpt-local-code-skill/skills/chatgpt-local-code ~/.codex/skills/
```

之后可以要求支持该格式的 Agent：

> 使用 $chatgpt-local-code，把我指定的一个本地仓库以只读方式接入 ChatGPT，使用 ngrok 免费固定域名；配置前先说明公开范围。

## 手动运行

首版支持 **macOS、Python 3.9+、Node.js 22+、Git、npm、独立安装的 ngrok CLI**。先登录官方 ChatGPT/ngrok，确认账号可以添加自定义 MCP 插件，取得 ngrok 分配的免费 dev domain。Skill 不附带 ngrok 二进制，也不自动升级套餐。

```sh
cd chatgpt-local-code-skill/skills/chatgpt-local-code
python3 scripts/bridge.py install
python3 scripts/bridge.py configure \
  --root /absolute/path/to/repo \
  --domain your-assigned-name.ngrok-free.dev \
  --ngrok /absolute/path/to/ngrok \
  --confirm-public-access
```

如果用的是 ZIP 安装包，从解压目录进入 `skills/chatgpt-local-code` 即可。

按隐藏输入提示粘贴 **ngrok authtoken 的值**，不要把它发给 Agent。所有状态和令牌默认保存在 `~/.local/share/chatgpt-local-code`，权限收紧到当前用户；不放进被开放目录。`--state` 可在子命令之前指定独立状态目录。

先在一个终端执行 `python3 scripts/bridge.py serve`，另一个终端执行 `python3 scripts/bridge.py verify`。停止前台服务后，再按需启用登录后自启动：

```sh
python3 scripts/bridge.py enable-autostart --confirm-autostart
python3 scripts/bridge.py verify --public
```

将状态目录 `connector-url.txt` 的完整 URL 填到 ChatGPT 自定义 MCP 插件；选择 No authentication 是兼容 query token 的界面配置，**服务端仍验证 URL 中的令牌**。文件里的链接等价于读代码的钥匙，不能分享。创建插件后安装，并在对话中通过 `@` 选择。界面与账号权限以当前官方文档为准。

```sh
python3 scripts/bridge.py status
python3 scripts/bridge.py stop
python3 scripts/bridge.py start
python3 scripts/bridge.py disable-autostart
```

`stop` 只停本次登录会话，下次登录会自动启动；`disable-autostart` 才永久取消。不是开机前常驻的系统守护进程。电脑休眠、离线时不可访问。

已有旧版安装或要改目录、域名、端口，先看[升级与重新配置](skills/chatgpt-local-code/references/setup.md#upgrades-and-reconfiguration)。更新 Skill 文件不会替换旧版已运行的服务。

## 测试与边界

- 运行时固定到 CodexPro 0.30.3 的指定 commit，依赖使用本仓库快照。安装时构建、审计并运行上游 smoke 测试。
- `verify` 用临时样例检查三个工具、拒绝写入、敏感路径、目录和符号链接越界、鉴权和管理入口。先在不含真实代码的样例目录试跑；`--public` 会把样例经 ngrok 发出。
- 目录过滤 **不是操作系统沙箱或完整密钥检测**；`.gitignore` 也不是保密边界。选择单个已获准分享的项目，避免包含凭据、个人文件或不应传出的代码和日志。
- 代码经过 ngrok 和 ChatGPT，不是离线方案。不保证服务商没有日志或保留行为；本机关闭 ngrok inspection 不等于云端日志一定关闭。
- ngrok 的域名和额度受账号及服务条款约束。依赖审计结果也会随新公告变化；没有漏洞报告不代表绝对安全。
- 首版不宣称 Windows/Linux 自启动已支持，不保证所有 ChatGPT 账号、模型或网络环境可用。

详细说明见 [setup.md](skills/chatgpt-local-code/references/setup.md)。分享时只发本仓库或 Skill 安装包；每位使用者各自生成连接地址。

## 本仓库验证

```sh
python3 -m unittest discover -s tests -v
node --check skills/chatgpt-local-code/assets/server.mjs
node --check skills/chatgpt-local-code/assets/verify.mjs
```

## 致谢与许可

核心 MCP 服务来自 [rebel0789/codexpro](https://github.com/rebel0789/codexpro)（MIT）；我们保留项目归属，不将它包装成原创服务。这里仅分发原创建议、编排脚本及其 npm 依赖快照，不打包上游源码或依赖二进制。各上游组件适用各自许可证。

本仓库原创内容以 MIT 许可发布，见 [LICENSE](LICENSE)。非 OpenAI、ngrok 或 Cloudflare 官方项目。
