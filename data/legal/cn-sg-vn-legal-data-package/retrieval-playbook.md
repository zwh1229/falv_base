# Retrieval Playbook

## 1) 意图路由

把用户问题映射为：

- `country`: China | Singapore | Vietnam | Multi
- `domain`: enterprise_landing | tax | cross_border_data
- `task_type`: legal_basis | compliance_checklist | jurisdiction_compare

## 2) 检索策略

先过滤：

1. `country` 精确匹配；
2. `domain` 精确匹配；
3. `is_currently_effective` 优先为 `true`；
4. `agent_tags` 语义匹配（例如 `data_localization`, `CIT`, `standard_contract`）。

再排序：

1. `retrieval_priority`（high > medium）；
2. `effective_date`（新到旧）；
3. 标题语义相关度。

## 3) 回答模板（建议）

### A. 法律依据型

- 结论一句话
- 法律依据（2-4条，带 `law_title_local + citation + official_url`）
- 适用边界（何种主体/触发条件）
- 待核验项（最新修订、部门规章、地方实践）

### B. 操作清单型

- 第一步：判断主体与数据类型
- 第二步：映射合规路径（申报/备案/合同/认证）
- 第三步：准备材料
- 第四步：提交路径与后续义务

## 4) 高风险问题触发人工复核

以下场景建议输出“需律师复核”：

- 跨境数据传输门槛临界值判断；
- 税务居民身份或常设机构认定；
- 外资准入负面清单边界争议；
- 监管处罚或行政复议相关问题。
