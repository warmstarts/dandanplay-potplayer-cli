# dandanplay PotPlayer CLI MVP

Windows 上的 Python 命令行工具 MVP，用本地视频文件信息调用弹弹play `/api/v2/match`，打印匹配结果。

当前版本只做文件识别：

- 不接 PotPlayer
- 不下载弹幕正文
- 不转换 ASS

## 文件结构

```text
main.py
dandan_api.py
config.example.json
requirements.txt
README.md
```

## fileHash 算法

根据弹弹play开放平台 `/api/v2/match` 的 `MatchRequest` 说明：

- `fileName`: 视频文件名，当前程序使用完整文件名和扩展名，例如 `xxx.mkv`
- `fileSize`: 文件总长度，单位 Byte
- `fileHash`: 文件前 16 MiB，也就是 `16 * 1024 * 1024` Byte 数据的 32 位 MD5 结果

程序会读取视频文件开头最多 16 MiB，计算小写 32 位十六进制 MD5，并在请求前打印实际发送的 payload。

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

`config.json` 包含密钥，不要提交。项目 `.gitignore` 已忽略它。

## 测试

准备一个真实存在的视频文件路径，然后运行：

```powershell
python main.py "D:\Anime\xxx.mkv"
```

程序会先打印读取到的文件信息：

```text
fileName: xxx.mkv
fileSize: 123456789
fileHash: 0123456789abcdef0123456789abcdef
```

请求前会打印实际发送给 `/api/v2/match` 的 payload：

```json
{
  "fileName": "xxx.mkv",
  "fileHash": "0123456789abcdef0123456789abcdef",
  "fileSize": 123456789
}
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
