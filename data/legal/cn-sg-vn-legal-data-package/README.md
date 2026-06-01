# CN-SG-VN 法律数据包（企业落地 / 税务 / 数据跨境）

这个数据包面向智能体的法规检索和合规问答，覆盖中国、新加坡、越南三地核心法律来源，按业务场景分为：

- `enterprise_landing`：设立主体、投资准入、登记规则
- `tax`：企业税、税务征管、间接税
- `cross_border_data`：个人信息/数据出境、数据本地化、跨境传输要求

## 文件说明

- `cn-sg-vn-legal-dataset.json`：主数据文件（结构化法规清单）
- `retrieval-playbook.md`：智能体检索与问答策略

## 推荐接入方式（RAG）

1. 将 `records` 按 `country + domain` 分桶建立索引。
2. 每条记录至少保留以下元数据：
  - `id`, `country`, `domain`, `law_title_local`, `citation`, `effective_date`, `is_currently_effective`, `valid_until`, `official_url`, `agent_tags`
3. 用户提问时先做意图分类：
  - 目标国家（单选/多选）
  - 问题类型（设立、税务、数据跨境）
  - 输出类型（要求条文依据 / 需要实操清单 / 需要多法域对比）
4. 检索后按优先级输出：
  - `retrieval_priority = high` 的法规先展示；
  - 再补充 `medium` 的细化法规/监管指引。

## 生产使用注意事项

- 法律会动态修订，最终决策前应再次核验官方数据库现行版本。
- 涉及执法口径和审批实践（尤其数据出境）时，建议追加监管问答或地方实施细则。
- 本数据包适合作为智能体“法条定位与合规导航层”，不替代执业律师意见。


## 本仓库补充资料

- `CN-DATA-007`：国务院关于对外投资的规定，归入 `China/cross_border_data`，来源为本地 DOCX，并已抽取为 `content.txt`。
