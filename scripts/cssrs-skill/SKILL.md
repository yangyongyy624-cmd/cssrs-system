# C-SSRS 操作技能

> C-SSRS 电子评估系统 — 云端操作接口
> 
> **服务器**：YOUR_SERVER_IP
> **管理员密码**：4-6 位数字（默认，可修改）
> **医生准入码**：由管理员创建

---

## 这是什么

C-SSRS（Columbia Suicide Severity Rating Scale）电子评估系统。云端服务器上运行网关服务，负责：
- 患者扫码答题入口
- 医生手机端访问（PIN 认证）
- 管理后台（医生准入码管理、查看所有患者量表）
- 查询评估数据

**重要：你只通过 HTTP API 操作，不要用浏览器工具。**

---

## 系统架构

```
患者手机(流量) → 云端网关(YOUR_SERVER_IP:8888) → SSH隧道(8889) → 本地电脑(8000)
医生手机(流量) → 云端网关(YOUR_SERVER_IP:8888) → SSH隧道(8889) → 本地电脑(8000)
```

### 网络端口

| 端口 | 用途 | 方向 |
|------|------|------|
| 8888 | 云端网关 (公开访问) | 入站 |
| 8889 | SSH 反向隧道 (内部) | 云端内部 |
| 8000 | 本地 FastAPI 服务 | 本地 |

---

## Web 入口（手机端）

### 1. 入口页 `/`
显示两个卡片：医生入口和管理员入口。医生扫码后选择入口。

### 2. 医生端 `/mobile`
医生手机浏览器访问，输入 4 位准入 PIN → 查看评估列表、新建评估、生成患者二维码。
- 新建评估后自动轮询，患者完成答题自动跳转报告
- 报告页显示风险等级 + 评分摘要
- 点击「查看完整量表内容」→ 红色高亮显示患者填写内容
- **权限**：医生只能看到自己创建的评估

### 3. 管理后台 `/admin`
管理员手机浏览器访问，输入管理密码 → 创建/撤销医生准入码、查看所有患者量表。
- **医生管理**：创建/撤销医生 PIN
- **患者量表**：查看所有医生的全部评估记录，点击查看完整量表内容
- **批量删除**：多选模式批量删除评估记录
- **修改密码**：点击顶部「改密码」按钮
- **权限**：管理员可以看到所有数据

### 4. 患者端 `/patient.html`
患者手机浏览器访问，答题并提交。

### 5. 医生入口码页面 `/doctor-qr`
可打印的医生端入口二维码页面，贴在诊室桌上供医生扫码。

---

## API 调用方法

所有 API 都在云端网关端口 8888，用 `curl` 调用。

### 1. 生成患者评估（二维码）

```bash
curl -s -X POST http://YOUR_SERVER_IP:8888/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-Doctor-PIN: <PIN>" \
  -d '{"patient_id":"张三","patient_phone":"138****0000","version":"baseline"}'
```

### 2. 医生 PIN 认证

```bash
curl -s -X POST http://YOUR_SERVER_IP:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"pin":"<4位数字>"}'
```

### 3. 查看医生自己的评估数据

```bash
curl -s -H "X-Doctor-PIN: <PIN>" http://YOUR_SERVER_IP:8888/api/doctor/report
```

**注意**：`/api/doctor/report` 只返回该医生创建的评估。

### 4. 查看完整报告

```bash
curl -s -H "X-Doctor-PIN: <PIN>" http://YOUR_SERVER_IP:8888/api/report/<SESSION_ID>
```

含患者答卷原文和全部评分。

### 5. 管理员查看所有评估

```bash
curl -s -H "X-Admin-PIN: <管理密码>" http://YOUR_SERVER_IP:8888/api/admin/report
```

### 6. 管理医生准入码

**创建医生 PIN：**
```bash
curl -s -X POST http://YOUR_SERVER_IP:8888/api/admin/pins \
  -H "Content-Type: application/json" \
  -H "X-Admin-PIN: <管理密码>" \
  -d '{"doctor_name":"医生名字"}'
```

**查看所有 PIN：**
```bash
curl -s -H "X-Admin-PIN: <管理密码>" http://YOUR_SERVER_IP:8888/api/admin/pins
```

**撤销医生 PIN：**
```bash
curl -s -X DELETE http://YOUR_SERVER_IP:8888/api/admin/pins/<PIN> \
  -H "X-Admin-PIN: <管理密码>"
```

---

## 二维码

| 二维码 | 用途 | 生成方式 |
|--------|------|---------|
| 医生入口码 | 医生手机扫码 → 进入入口页 | 访问 `/doctor-qr` 页面截图或打印 |
| 患者答题码 | 医生创建评估后自动生成 | 调用 `/api/sessions` 后系统生成 |

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
curl -s -o /dev/null -w "%{http_code}" http://YOUR_SERVER_IP:8888/
```
非 200 则检查 SSH 隧道状态。

---

## 注意事项

- **不要用浏览器工具**，直接用 curl
- 患者评估码 = 6 位字母数字
- 医生访问码 = 4 位数字 PIN
- 管理密码 = 4-6 位数字
- 评估数据仅存本地，云端不保存任何患者数据
- 医生只能看到自己的数据，管理员可以看到全部
- 管理员可以自由修改密码
