# dandanplay PotPlayer CLI MVP

Windows 上的 Python 命令行工具 MVP，用本地视频文件信息调用弹弹play `/api/v2/match`，拿到 `episodeId` 后下载原始弹幕 JSON。

当前版本只做：

- 识别本地视频对应的弹幕库
- 下载原始弹幕 JSON
- 保存到视频同目录

当前版本暂时不做：

- 不接 PotPlayer
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

## 弹幕下载流程

1. 调用 `POST https://api.dandanplay.net/api/v2/match`
2. 打印匹配状态和候选项
3. 取第一个有效候选的 `episodeId`
4. 调用 `GET https://api.dandanplay.net/api/v2/comment/{episodeId}?withRelated=true&chConvert=1`
5. 允许 `302` 自动跳转并读取最终返回的 JSON
6. 将原始弹幕 JSON 保存为 `原视频文件名.dandan.json`

弹幕接口同样会带 `X-AppId` 和 `X-AppSecret`，或在 `auth_mode=signature` 时带签名认证头。签名使用的 path 是 `/api/v2/comment/{episodeId}`，不包含 query string。

例如视频为：

```text
D:\Anime\xxx.mkv
```

输出文件为：

```text
D:\Anime\xxx.mkv.dandan.json
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
isMatched: True
matches:
[1]
  animeTitle: ...
  episodeTitle: ...
  episodeId: 123456
```

弹幕下载成功后会打印弹幕数量和保存路径：

```text
commentCount: 3000
saved: D:\Anime\xxx.mkv.dandan.json
```

如果返回多个候选，程序会按 API 返回顺序打印，并暂时使用第一个包含 `episodeId` 的候选下载弹幕。

## 错误处理

程序会处理并打印以下错误：

- 本地视频文件不存在
- 配置缺少 `app_id` 或 `app_secret`
- 匹配 API `success=false`
- 无匹配或没有可用 `episodeId`
- 弹幕 API `success=false`
- 无弹幕
- 网络错误或 HTTP 错误
- 视频目录不可写或保存失败

弹幕下载阶段如果发生 HTTP 错误，程序会额外打印 `status_code`、`reason`、最终请求 URL、响应头，以及响应正文前 1000 个字符，方便排查 302 跳转后的实际失败原因。

弹幕接口返回 JSON 但 `success=false` 时，程序会打印完整 JSON、`success`、`errorCode`、`errorMessage`、`message`、`code`、其他顶层字段，以及 `data` 字段中的键名。

弹幕接口返回成功时，程序会先打印返回结构，包括 JSON 顶层类型、顶层 key、每个 key 的数据类型；如果返回顶层 list，会打印长度和前 3 个元素。程序兼容顶层 `list[dict]`、`{"comments": [...]}`、`{"data": [...]}` 以及 `data` 中嵌套列表的结构，并按实际弹幕列表统计数量后保存原始 JSON。
