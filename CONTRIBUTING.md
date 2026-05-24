# Contributing to C-SSRS 电子评估系统

**作者**：杨勇（Yang Yong），武汉市普仁医院精神科医生

感谢关注本项目！欢迎以任何方式参与贡献。

## 快速开始

```bash
git clone https://github.com/yangyongyy624-cmd/cssrs-system.git
cd cssrs-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 架构概述

```
患者手机 → 云端轻量网关 → SSH 隧道 → 本地 Mac mini (数据仓库)
          (仅转发)                  (数据存储 + 评分)
```

- **云端网关**：轻量 FastAPI 服务，仅转发请求，不存储评估数据
- **本地服务**：运行在 Mac mini 上，负责数据存储、评分计算、报告生成、**患者答卷原文保存**
- **SSH 隧道**：加密传输评估数据，保障隐私安全

## 贡献方向

以下方向欢迎贡献：

- [x] **患者答卷原文显示**：医生端报告页已新增"患者答卷原文"区块
- [ ] **国际化**：添加英文患者问卷（C-SSRS 原版为英文）
- [ ] **多语言支持**：除中文外的其他语言患者端页面
- [x] **启动脚本**：`scripts/start-local.sh` 已实现自动清理端口和启动验证
- [x] **部署文档**：`docs/deployment.md` 已完善，含常见问题排查
- [ ] **Docker 支持**：一键 docker-compose 部署
- [ ] **报告导出**：PDF 格式的评估报告导出
- [ ] **统计分析**：患者群体的风险评估趋势图表
- [ ] **测试覆盖**：单元测试和集成测试
- [ ] **文档完善**：部署指南、API 文档

## 提交 PR

1. Fork 本仓库
2. 创建分支 `git checkout -b feature/your-feature`
3. 提交更改 `git commit -m 'feat: add your feature'`
4. 推送分支 `git push origin feature/your-feature`
5. 提交 Pull Request

## Commit 规范

遵循 Conventional Commits：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具链

## 隐私声明

本项目采用**隐私优先架构**：
- 评估数据仅存储在本地，不上传云端
- 云端网关仅转发请求，不保留评估内容
- 数据传输通过 SSH 加密隧道

贡献者请注意：
- **不要**将真实的评估数据、患者信息、服务器 IP 提交到代码库
- 配置文件使用 `.example` 模板，真实配置加入 `.gitignore`

## 许可证

MIT License
