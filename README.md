# codex-history-compat

针对 OpenAI Codex 上游提交 `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca` 的实验性兼容补丁。它只规范即将发送给模型服务的请求副本，不改写持久历史。

## 解决的问题

部分 Responses 兼容服务不能接受加密推理项、孤立的工具调用/输出，或夹在调用与输出之间的图片缩放提示。本补丁将同一处理接入普通请求、WebSocket、本地压缩和两种远程压缩路径。

## 应用和测试

```powershell
git clone https://github.com/openai/codex.git
git -C codex checkout b5bffd3ec4db487e7e3dec59663875b0ef7b72ca
.\apply.ps1 -CodexRoot .\codex
cargo test --manifest-path .\codex\codex-rs\Cargo.toml -p codex-core prompt_history_compat --lib -- --test-threads 1
```

Linux/macOS 可使用 `./apply.sh /path/to/codex`。补丁拒绝错误提交或非干净工作树。

English overview: [README.en.md](README.en.md)。相关项目：[electron-update-safety](https://github.com/catterhu1207-ux/electron-update-safety)、[desktop-adaptation-lab](https://github.com/catterhu1207-ux/desktop-adaptation-lab)。

## 边界

仓库不包含 Codex 二进制、用户会话或真实服务请求。合成样例只保留造成结构错误所需的项目。项目遵守上游 Apache-2.0 许可证并保留 NOTICE。
