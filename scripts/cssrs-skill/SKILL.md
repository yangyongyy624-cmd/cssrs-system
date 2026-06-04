# C-SSRS 操作技能

> C-SSRS 电子评估系统 — 云端操作接口
>
> **⚠️ 敏感信息已脱敏：IP 地址、PIN 码、管理密码、Token 等均未收录。**
> 实际值见本地配置文件或询问系统管理员。

---

## 这是什么

C-SSRS（Columbia Suicide Severity Rating Scale）电子评估系统。云端服务器上运行网关服务，负责：
- 患者扫码答题入口
- 医生手机端访问（PIN 认证）
- 管理后台（医生准入码管理）
- 查询评估数据

**重要：你只通过 HTTP API 操作，不要用浏览器工具。**

---

## 系统架构

```
患者手机 → 云端网关 (仅转发) → SSH隧道 → 本地 Mac (数据存储 + 评分)
医生手机 → 云端网关 (PIN认证) → SSH隧道 → 本地 Mac
管理后台 → 云端网关 (管理密码) → SSH隧道 → 本地 Mac
```

### 网络端口

| 端口 | 用途 | 方向 |
|------|------|------|
| 8888 | 云端网关 (公开访问) | 入站 |
| 8889 | SSH 反向隧道 (内部) | 云端内部 |
| 8000 | 本地 FastAPI 服务 | 本地 |

---

## Web 入口（手机端）

### 1. 医生端 `/mobile`
医生手机浏览器访问，输入 4 位准入 PIN → 查看评估列表、新建评估、生成患者二维码。
- 新建评估后自动轮询，患者完成答题自动跳转报告
- QR 直链 patient.html，患者扫码后直接答题，无需输入6位码

### 2. 管理后台 `/admin`
管理员手机浏览器访问，输入管理密码 → 创建/撤销医生准入码。
- 管理密码是 4 位数字，默认值由管理员首次设定
- 创建医生 PIN 后显示大号准入码，支持一键复制
- 撤销后已登录医生下次请求自动踢出

### 3. 患者端 `/patient.html`
患者手机浏览器访问，答题并提交。

### 4. 医生入口码页面 `/doctor-qr`
可打印的医生端入口二维码页面，贴在诊室桌上供医生扫码。

### 5. 桌面医生端 `/`
电脑浏览器访问，包含：管理后台、医生入口码打印、手机端入口、导出评分。

---

## API 调用方法

所有 API 都在云端网关端口 8888，用 `curl` 调用。

### 1. 生成患者评估（二维码）

当用户说"生成评估码"、"新建评估"、"患者码"、"生成二维码"时：

```bash
curl -s -X POST http://<SERVER>:8888/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"张三","patient_phone":"138****0000","version":"baseline"}'
```

返回示例：
```json
{
  "session_id": "uuid",
  "patient_id": "张三",
  "patient_phone": "138****0000",
  "access_code": "A1B2C3",
  "version": "baseline",
  "created_at": "2026-06-04T10:00:00"
}
```

### 2. 医生 PIN 认证

```bash
curl -s -X POST http://<SERVER>:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"pin":"<4位数字>"}'
```

### 3. 查看评估数据（需要医生 PIN）

所有数据查询接口需要在请求头中携带 `X-Doctor-PIN`：

```bash
curl -s -H "X-Doctor-PIN: <PIN>" http://<SERVER>:8888/api/report
```

### 4. 查看完整报告

```bash
curl -s -H "X-Doctor-PIN: <PIN>" http://<SERVER>:8888/api/report/<SESSION_ID>
```

含患者答卷原文和全部评分。

### 5. 脱敏摘要

```bash
curl -s -H "X-Doctor-PIN: <PIN>" "http://<SERVER>:8888/api/summary?limit=5"
```

只返回患者ID + 风险等级 + 日期，适合语音播报。

### 6. 管理医生准入码（管理后台 API）

**创建医生 PIN：**
```bash
curl -s -X POST http://<SERVER>:8888/api/admin/pins \
  -H "Content-Type: application/json" \
  -d '{"doctor_name":"医生名字"}'
```
返回自动生成的 4 位 PIN。

**查看所有 PIN：**
```bash
curl -s http://<SERVER>:8888/api/admin/pins
```

**撤销医生 PIN：**
```bash
curl -s -X DELETE http://<SERVER>:8888/api/admin/pins/<PIN>
```

---

## 二维码

| 二维码 | 用途 | 生成方式 |
|--------|------|---------|
| 医生入口码 | 医生手机扫码 → 进入医生端 | 打印 `/doctor-qr` 页面 |
| 管理后台码 | 管理员手机扫码 → 进入管理后台 | 扫码 URL: `/admin` |
| 患者答题码 | 医生创建评估后自动生成 | 调用 `/api/sessions` 后生成 |

---

## 评分系统

### 5 层评分模型

| 层级 | 维度 | 范围 |
|------|------|------|
| 筛查 | 自杀意念 | 阴性/阳性 |
| 意念严重度 | 最高级别 | 0-5 |
| 意念强度 | 5 维度总分 | 0-25 |
| 行为 | 自杀行为 | B1-B5 |
| 致死性 | 企图致死性 | 0-6 |

### 风险分层

| 等级 | 条件 |
|------|------|
| 无风险 | 筛查阴性 |
| 低风险 | 仅渴望死亡，无计划意图 |
| 中风险 | 有方法的主动意念 |
| 高风险 | 有计划或有意图 |
| 极高风险 | 有计划且有意图 |

---

## 服务状态检查

```bash
curl -s -o /dev/null -w "%{http_code}" http://<SERVER>:8888/
```
非 200 则重启: `sudo systemctl restart cssrs-cloud`

---

## 注意事项

- **不要用浏览器工具**，直接用 curl
- 患者评估码 = 6 位字母数字，**只给二维码图片链接**
- 医生访问码 = 4 位数字 PIN
- 评估数据仅存本地 Mac mini，云端不保存任何患者数据
- 所有医生端访问必须经过 PIN 认证
- 管理后台需要独立的管理密码
- **GitHub 仓库不包含任何真实 IP、PIN 码或密码**
