# falv_base

数据跨境合规体检智能体后端原型。

当前已包含：

- FastAPI 后端基础服务
- 本地 SQLite 模拟数据库
- 审查任务创建与查询
- 5 轮问答流程基础结构
- 法规数据包接入方向文档

## 本地启动

```powershell
cd backend
conda activate rag-backend
uvicorn main:app --reload
```

