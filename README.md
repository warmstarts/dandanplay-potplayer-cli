# dandanplay PotPlayer CLI MVP

Windows 上的 Python 命令行工具 MVP，用本地视频文件名和文件大小调用弹弹play `/api/v2/match`，打印匹配结果。

当前版本只做文件识别：

- 不接 PotPlayer
- 不下载弹幕正文
- 不转换 ASS
- `fileHash` 预留为空字符串

## 文件结构

```text
main.py
dandan_api.py
config.example.json
requirements.txt
README.md
```

## 安装

```powershell
cd E:\vscode_files\Python_files\Projects\dandanplay_potplayer_cli
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 配置

复制示例配置：

```powershell
Copy-Item config.example.json config.json
```

编辑 `config.json`：

```json
{
  "app_id": "your_app_id",
  "app_secret": "your_app_secret",
  "auth_mode": "secret"
}
```

也可以不用 `config.json`，改用环境变量：

```powershell
$env:DANDANPLAY_APP_ID = "your_app_id"
$env:DANDANPLAY_APP_SECRET = "your_app_secret"
$env:DANDANPLAY_AUTH_MODE = "secret"
```

`auth_mode` 支持：

- `secret`: 请求头使用 `X-AppId` 和 `X-AppSecret`
- `signature`: 请求头使用 `X-AppId`、`X-Timestamp` 和 `X-Signature`

## 测试

准备一个真实存在的视频文件路径，然后运行：

```powershell
python main.py "D:\Anime\xxx.mkv"
```

程序会先打印读取到的文件信息：

```text
fileName: xxx
fileSize: 123456789
fileHash:
```

然后打印弹弹play返回的匹配状态和候选项：

```text
success: True
errorCode: 0
errorMessage:
isMatched: False
matches:
[1]
  animeTitle: ...
  episodeTitle: ...
  episodeId: ...
```

如果返回多个候选，会按 API 返回顺序依次列出。
