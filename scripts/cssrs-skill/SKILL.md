# C-SSRS 操作技能

> C-SSRS 电子评估系统 -- 云端操作接口
> 服务器: 82.156.238.242:8888

---

## 这是什么

C-SSRS（Columbia Suicide Severity Rating Scale）电子评估系统。你在云端服务器上运行网关服务（端口 8888），负责：
- 生成患者评估码（6 位字母数字）
- 管理医生访问码（4 位数字 PIN）
- 查询评估摘要

**重要：你只通过 HTTP API 操作，不要用浏览器工具。**

## API 调用方法

所有 API 都在 `http://127.0.0.1:8888`，用 `curl` 调用。

### 1. 生成患者评估（二维码）

当用户说"生成评估码"、"新建评估"、"患者码"、"生成二维码"时：

**如果用户提供了患者手机号**，在请求中加上 `patient_phone`：

```bash
curl -s -X POST http://127.0.0.1:8888/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"张三","patient_phone":"13800138000","version":"baseline"}'
```

如果用户没提手机号，只传 patient_id：

```bash
curl -s -X POST http://127.0.0.1:8888/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"匿名","version":"baseline"}'
```

返回示例：
```json
{
  "session_id": "uuid",
  "patient_id": "匿名",
  "access_code": "A1B2C3",
  "version": "baseline",
  "created_at": "2026-05-24T10:00:00"
}
```

**回复用户：只给二维码图片链接。患者扫码后手机号自动带入，直接答题。**

回复格式（有手机号）：
```
✅ 新评估已创建
患者：张三
手机号：138****8000（扫码后自动带入）
患者扫码答题：http://82.156.238.242:8888/api/qr/A1B2C3
```

回复格式（无手机号）：
```
✅ 新评估已创建
患者ID：xxx
患者扫码答题：http://82.156.238.242:8888/api/qr/A1B2C3
```

如果用户指定了患者名称，把 `patient_id` 替换为实际名称。

### 2. 生成医生访问码（4 位 PIN）

当用户说"生成医生码"、"医生访问码"、"新医生"时：

```bash
curl -s -X POST http://127.0.0.1:8888/api/doctor-pin/create \
  -H "Content-Type: application/json" \
  -d '{"name":"医生名字"}'
```

返回：`{"pin": "1234", "doctor_name": "医生名字"}`

回复用户：提供 4 位 PIN、医生名字、二维码（手机扫码）和 HTML 入口（电脑双击进入）：

```
✅ 医生访问码已创建
医生：文医生
访问码：1234

手机扫码进入：http://82.156.238.242:8888/api/qr/doctor
电脑双击进入：http://82.156.238.242:8888/doctor-portal.html
（HTML 文件 → 右键另存到桌面 → 双击即可打开系统）
```

### 3. 查看所有医生访问码

```bash
curl -s http://127.0.0.1:8888/api/doctor-pin/list
```

### 4. 撤销医生访问码

```bash
curl -s -X POST http://127.0.0.1:8888/api/doctor-pin/revoke \
  -H "Content-Type: application/json" \
  -d '{"pin":"1234"}'
```

### 5. 查看评估摘要（脱敏）

```bash
curl -s "http://127.0.0.1:8888/api/summary?limit=5"
```

回复用户时只报：患者ID + 风险等级 + 日期，适合语音播报。

### 6. 查看完整报告

```bash
curl -s http://127.0.0.1:8888/api/report/SESSION_ID
```

含患者答卷原文和全部评分。

### 7. 二维码链接

- 二维码图片: `http://82.156.238.242:8888/api/qr/评估码`
- 患者答题页: `http://82.156.238.242:8888/code/评估码`

## 关键词匹配

| 用户说的话 | 执行操作 |
|-----------|---------|
| 生成评估码/新建评估/患者码/生成二维码 | 创建 session + 返回二维码 (操作 1) |
| 生成医生码/医生访问码/新医生 | 创建 doctor PIN (操作 2) |
| 医生码列表/所有医生 | 列出 doctor PIN (操作 3) |
| 撤销医生码/删除医生码 | 撤销 doctor PIN (操作 4) |
| 最新评估/评估情况 | 获取摘要 (操作 5) |
| 查看报告/详细报告 | 获取报告 (操作 6) |

## 服务状态

如果 API 调用失败：
```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8888/
```
非 200 则重启: `sudo systemctl restart cssrs-cloud`

## 注意事项

- **不要用浏览器工具**，直接用 curl
- 患者评估码 = 6 位字母数字，**只给二维码图片链接**，患者扫码后访问码自动预填
- 医生访问码 = 4 位数字 PIN
- 评估数据仅存本地 Mac mini，云端不保存
