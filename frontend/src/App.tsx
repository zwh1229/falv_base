import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpenCheck,
  Building2,
  Check,
  CircleHelp,
  Database,
  FileSearch,
  FileText,
  Gavel,
  Globe2,
  Loader2,
  RefreshCw,
  Scale,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import {
  createAuditAnalysis,
  createAuditTask,
  getAuditTask,
  getLatestAuditAnalysis,
  healthCheck,
  importLegalData,
  listLegalRecords,
  searchLegalHybrid,
  searchLegalVector,
  submitAuditAnswer,
} from "./api";
import type {
  AuditRiskAnalysis,
  AuditScope,
  AuditTask,
  LegalImportResponse,
  LegalRecord,
  LegalSearchResponse,
  SavedAnswer,
} from "./types";

type ViewKey = "audit" | "legal" | "report";

const scopeOptions: Array<{
  value: AuditScope;
  title: string;
  description: string;
  countries: string[];
}> = [
  {
    value: "china",
    title: "境内合规初筛",
    description: "适用于仅在中国境内采集、存储和处理的数据业务。",
    countries: ["China"],
  },
  {
    value: "china_singapore",
    title: "中国 + 新加坡",
    description: "适用于向新加坡主体提供、访问或落地处理数据的场景。",
    countries: ["China", "Singapore"],
  },
  {
    value: "china_vietnam",
    title: "中国 + 越南",
    description: "适用于越南业务拓展、海外落地或跨境传输审查。",
    countries: ["China", "Vietnam"],
  },
];

const countryLabels: Record<string, string> = {
  China: "中国",
  Singapore: "新加坡",
  Vietnam: "越南",
};

const domainLabels: Record<string, string> = {
  cross_border_data: "跨境数据",
  enterprise_landing: "海外落地",
  tax: "税务合规",
};

const statusLabels: Record<string, string> = {
  questioning: "问答采集中",
  answered: "信息已采集",
  analyzing: "分析中",
  completed: "已完成",
};

const fallbackQuestions = [
  "请先说明企业主要业务，以及本次需要体检的数据业务场景。",
  "这些数据主要是什么类型？数据从哪里来？是否涉及个人信息或敏感信息？",
  "数据目前存在哪里？谁可以访问？主要用于什么业务目的？",
  "数据是否会传到境外？如果会，目的地国家和接收方是谁？",
  "是否已经完成用户告知、授权或同意？目前有哪些加密、权限控制、脱敏、审计等安全措施？",
];

const storageKeys = {
  task: "compliance.audit.task",
  answers: "compliance.audit.answers",
};

function readStoredTask(): AuditTask | null {
  try {
    const value = localStorage.getItem(storageKeys.task);
    return value ? (JSON.parse(value) as AuditTask) : null;
  } catch {
    return null;
  }
}

function readStoredAnswers(): SavedAnswer[] {
  try {
    const value = localStorage.getItem(storageKeys.answers);
    return value ? (JSON.parse(value) as SavedAnswer[]) : [];
  } catch {
    return [];
  }
}

function formatScore(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "0.0000";
  return value.toFixed(4);
}

function findAnalysisValue(text: string, labels: string[]) {
  const lines = text.split(/\r?\n/);

  for (const line of lines) {
    const cleanedLine = line.trim().replace(/^[-•]\s*/, "");

    for (const label of labels) {
      if (cleanedLine.startsWith(`${label}：`) || cleanedLine.startsWith(`${label}:`)) {
        return cleanedLine.slice(label.length + 1).trim();
      }
    }
  }

  return "";
}

function parseCount(value: string) {
  if (!value) return null;
  if (value.includes("无")) return 0;

  const match = value.match(/\d+/);
  return match ? Number(match[0]) : null;
}

function parseRiskSummary(text?: string | null) {
  if (!text) return null;

  const overallLevel = findAnalysisValue(text, ["综合等级", "风险等级"]) || "待人工复核";
  const conclusion = findAnalysisValue(text, ["结论一句话", "核心原因"]) || "已生成分析，请先查看重点风险和建议动作。";
  const priorityAction = findAnalysisValue(text, ["用户优先动作"]) || "先处理重点风险，再补齐缺失材料。";
  const criticalCount = parseCount(findAnalysisValue(text, ["重点风险数量"])) ?? 0;
  const warningCount = parseCount(findAnalysisValue(text, ["一般风险数量"])) ?? 0;
  const missingInfoCount = parseCount(findAnalysisValue(text, ["待补充信息数量", "缺失信息数量"])) ?? 0;

  return {
    overallLevel,
    conclusion,
    priorityAction,
    criticalCount,
    warningCount,
    missingInfoCount,
  };
}

function isMissingAnalysisError(error: unknown) {
  return error instanceof Error && error.message.includes("audit analysis result not found");
}

function App() {
  const [view, setView] = useState<ViewKey>("audit");
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [task, setTask] = useState<AuditTask | null>(() => readStoredTask());
  const [answers, setAnswers] = useState<SavedAnswer[]>(() => readStoredAnswers());
  const [companyName, setCompanyName] = useState("");
  const [scope, setScope] = useState<AuditScope>("china_singapore");
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [answerDraft, setAnswerDraft] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [legalRecords, setLegalRecords] = useState<LegalRecord[]>([]);
  const [legalFilters, setLegalFilters] = useState({ country: "", domain: "" });
  const [legalImport, setLegalImport] = useState<LegalImportResponse | null>(null);
  const [legalBusy, setLegalBusy] = useState(false);
  const [analysis, setAnalysis] = useState<AuditRiskAnalysis | null>(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [legalSearchQuery, setLegalSearchQuery] = useState("个人信息跨境传输 用户单独同意 安全评估");
  const [legalSearchMode, setLegalSearchMode] = useState<"hybrid" | "vector">("hybrid");
  const [legalSearchRebuild, setLegalSearchRebuild] = useState(false);
  const [legalSearchResult, setLegalSearchResult] = useState<LegalSearchResponse | null>(null);
  const [legalSearchBusy, setLegalSearchBusy] = useState(false);

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  useEffect(() => {
    if (task) {
      localStorage.setItem(storageKeys.task, JSON.stringify(task));
    } else {
      localStorage.removeItem(storageKeys.task);
    }
  }, [task]);

  useEffect(() => {
    localStorage.setItem(storageKeys.answers, JSON.stringify(answers));
  }, [answers]);

  const currentQuestion = useMemo(() => {
    if (!task) return fallbackQuestions[0];
    return task.next_question || fallbackQuestions[Math.min(task.current_round - 1, fallbackQuestions.length - 1)];
  }, [task]);

  const progress = task ? Math.min(((task.current_round - 1) / fallbackQuestions.length) * 100, 100) : 0;
  const selectedScope = scopeOptions.find((option) => option.value === (task?.scope || scope)) || scopeOptions[0];
  const riskSummary = useMemo(() => parseRiskSummary(analysis?.analysis), [analysis]);

  function downloadPdfReport(taskId: string) {
    const link = document.createElement("a");
    link.href = `/api/v1/audit-tasks/${taskId}/report/file`;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  async function handleCreateTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!consentAccepted) {
      setNotice("请先确认隐私承诺和使用限制，再启动体检。");
      return;
    }

    setBusy(true);
    setNotice("");
    try {
      const created = await createAuditTask({
        company_name: companyName.trim() || null,
        scope,
      });
      setTask(created);
      setAnswers([]);
      setAnalysis(null);
      setAnswerDraft("");
      setNotice("体检任务已创建，可以开始第一轮问答。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "创建任务失败，请确认后端服务已启动。");
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshTask() {
    if (!task) return;
    setBusy(true);
    setNotice("");
    try {
      const fresh = await getAuditTask(task.task_id);
      setTask(fresh);
      setNotice("任务状态已刷新。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "刷新失败。");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!task || !answerDraft.trim()) return;

    const submittedQuestion = currentQuestion;
    const submittedRound = task.current_round;
    setBusy(true);
    setNotice("");
    try {
      const updated = await submitAuditAnswer(task.task_id, { answer: answerDraft.trim() });
      setAnswers((current) => [
        ...current,
        {
          round: submittedRound,
          question: submittedQuestion,
          answer: answerDraft.trim(),
        },
      ]);
      setTask(updated);
      setAnswerDraft("");
      setNotice(updated.status === "answered" ? "五轮信息采集完成，已生成本地体检摘要。" : "回答已保存，进入下一轮问题。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "提交回答失败。");
    } finally {
      setBusy(false);
    }
  }

  async function handleLoadLegalRecords(nextFilters = legalFilters) {
    setLegalBusy(true);
    setNotice("");
    try {
      const records = await listLegalRecords({
        country: nextFilters.country || undefined,
        domain: nextFilters.domain || undefined,
      });
      setLegalRecords(records);
      if (records.length === 0) {
        setNotice("当前筛选条件下没有法规记录，可先执行数据包导入。");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载法规记录失败。");
    } finally {
      setLegalBusy(false);
    }
  }

  async function handleImportLegalData() {
    setLegalBusy(true);
    setNotice("");
    try {
      const result = await importLegalData();
      setLegalImport(result);
      setNotice(`法规包导入完成：新增 ${result.inserted_records} 条，更新 ${result.updated_records} 条。`);
      await handleLoadLegalRecords();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "导入法规数据失败。");
    } finally {
      setLegalBusy(false);
    }
  }

  async function handleCreateAnalysis() {
    if (!task) return;

    setAnalysisBusy(true);
    setNotice("");
    try {
      const result = await createAuditAnalysis(task.task_id);
      setAnalysis(result);
      setNotice(`风险分析已生成，命中 ${result.evidences.length} 条法规依据。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "生成风险分析失败，请确认问答已完成且模型/检索配置可用。");
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function handleLoadLatestAnalysis() {
    if (!task) return;

    setAnalysisBusy(true);
    setNotice("");
    try {
      const result = await getLatestAuditAnalysis(task.task_id);
      setAnalysis(result);
      setNotice("已加载最近一次风险分析。");
    } catch (error) {
      if (isMissingAnalysisError(error)) {
        setNotice("该任务还没有风险分析结果，请先点击“生成风险分析”。");
      } else {
        setNotice(error instanceof Error ? error.message : "暂未找到该任务的历史风险分析。");
      }
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function handleDownloadPdfReport() {
    if (!task) return;

    setAnalysisBusy(true);
    setNotice("");
    try {
      if (!analysis) {
        try {
          const latest = await getLatestAuditAnalysis(task.task_id);
          setAnalysis(latest);
        } catch (error) {
          if (!isMissingAnalysisError(error) || task.status !== "answered") {
            throw error;
          }

          setNotice("该任务还没有风险分析，正在先生成风险分析，然后下载 PDF。");
          const generated = await createAuditAnalysis(task.task_id);
          setAnalysis(generated);
        }
      }

      downloadPdfReport(task.task_id);
      setNotice("PDF 报告已开始下载。重复下载会直接使用缓存文件。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "下载 PDF 失败，请先完成问答并生成风险分析。");
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function handleLegalSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!legalSearchQuery.trim()) return;

    setLegalSearchBusy(true);
    setNotice("正在检索法规依据。首次检索需要构建向量索引，可能需要等待 1-2 分钟。");
    try {
      const payload = {
        query: legalSearchQuery.trim(),
        top_k: 8,
        countries: legalFilters.country ? [legalFilters.country] : undefined,
        domains: legalFilters.domain ? [legalFilters.domain] : undefined,
        rebuild_index: legalSearchRebuild,
      };
      const result =
        legalSearchMode === "hybrid" ? await searchLegalHybrid(payload) : await searchLegalVector(payload);
      setLegalSearchResult(result);
      setNotice(`法规检索完成，返回 ${result.hits.length} 条命中。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "法规检索失败，请确认已导入法规并配置 embedding。");
    } finally {
      setLegalSearchBusy(false);
      setLegalSearchRebuild(false);
    }
  }

  function resetCurrentTask() {
    setTask(null);
    setAnswers([]);
    setAnalysis(null);
    setAnswerDraft("");
    setCompanyName("");
    setConsentAccepted(false);
    setNotice("已清空本地任务缓存，可以重新创建体检。");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand-block">
          <div className="brand-mark">
            <Scale size={23} aria-hidden="true" />
          </div>
          <div>
            <p className="brand-kicker">MVP 工作台</p>
            <h1>数据跨境合规体检智能体</h1>
          </div>
        </div>

        <nav className="nav-stack">
          <button className={view === "audit" ? "nav-item active" : "nav-item"} onClick={() => setView("audit")}>
            <Sparkles size={18} aria-hidden="true" />
            企业体检
          </button>
          <button className={view === "legal" ? "nav-item active" : "nav-item"} onClick={() => setView("legal")}>
            <Database size={18} aria-hidden="true" />
            法规资料库
          </button>
          <button className={view === "report" ? "nav-item active" : "nav-item"} onClick={() => setView("report")}>
            <FileText size={18} aria-hidden="true" />
            体检摘要
          </button>
        </nav>

        <div className={`api-pill ${apiStatus}`}>
          <span />
          {apiStatus === "checking" ? "接口检查中" : apiStatus === "online" ? "后端已连接" : "后端未连接"}
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">企业数据出境 / 海外落地 / 法规依据溯源</p>
            <h2>{view === "audit" ? "企业合规体检" : view === "legal" ? "法规资料维护" : "分析与报告"}</h2>
          </div>
          {task ? (
            <div className="task-chip">
              <ShieldCheck size={17} aria-hidden="true" />
              <span>{statusLabels[task.status] || task.status}</span>
            </div>
          ) : null}
        </header>

        {notice ? (
          <div className="notice" role="status">
            <CircleHelp size={18} aria-hidden="true" />
            {notice}
          </div>
        ) : null}

        {view === "audit" ? (
          <section className="content-grid">
            <div className="workflow-pane">
              <div className="section-title">
                <Building2 size={20} aria-hidden="true" />
                <div>
                  <h3>创建审查任务</h3>
                  <p>对应后端 POST /api/v1/audit-tasks</p>
                </div>
              </div>

              <form className="audit-form" onSubmit={handleCreateTask}>
                <label className="field">
                  <span>企业名称</span>
                  <input
                    value={companyName}
                    onChange={(event) => setCompanyName(event.target.value)}
                    placeholder="例如：某跨境电商有限公司"
                    disabled={Boolean(task)}
                  />
                </label>

                <div className="field">
                  <span>审查范围</span>
                  <div className="scope-grid" role="radiogroup" aria-label="审查范围">
                    {scopeOptions.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        className={(task?.scope || scope) === option.value ? "scope-option selected" : "scope-option"}
                        onClick={() => setScope(option.value)}
                        disabled={Boolean(task)}
                      >
                        <strong>{option.title}</strong>
                        <small>{option.description}</small>
                      </button>
                    ))}
                  </div>
                </div>

                <label className="consent-row">
                  <input
                    type="checkbox"
                    checked={consentAccepted}
                    onChange={(event) => setConsentAccepted(event.target.checked)}
                    disabled={Boolean(task)}
                  />
                  <span>确认本工具仅用于初步合规筛查，不替代正式法律意见；输入内容应避免不必要的敏感信息。</span>
                </label>

                <div className="button-row">
                  <button className="primary-button" type="submit" disabled={busy || Boolean(task)}>
                    {busy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <ArrowRight size={18} aria-hidden="true" />}
                    启动体检
                  </button>
                  <button className="ghost-button" type="button" onClick={resetCurrentTask}>
                    重新开始
                  </button>
                </div>
              </form>
            </div>

            <div className="question-pane">
              <div className="task-summary">
                <div>
                  <p className="eyebrow">当前任务</p>
                  <h3>{task?.company_name || companyName || "尚未创建任务"}</h3>
                </div>
                <button className="icon-button" type="button" onClick={handleRefreshTask} disabled={!task || busy} aria-label="刷新任务">
                  <RefreshCw size={18} aria-hidden="true" />
                </button>
              </div>

              <div className="country-strip">
                {selectedScope.countries.map((country) => (
                  <span key={country}>
                    <Globe2 size={14} aria-hidden="true" />
                    {countryLabels[country] || country}
                  </span>
                ))}
              </div>

              <div className="progress-wrap" aria-label="问答进度">
                <div style={{ width: `${task?.status === "answered" ? 100 : progress}%` }} />
              </div>

              <div className="qa-thread">
                {answers.map((item) => (
                  <div className="qa-pair" key={`${item.round}-${item.question}`}>
                    <div className="agent-bubble">
                      <span>第 {item.round} 轮</span>
                      <p>{item.question}</p>
                    </div>
                    <div className="user-bubble">{item.answer}</div>
                  </div>
                ))}

                {task?.status !== "answered" ? (
                  <div className="agent-bubble current">
                    <span>第 {task?.current_round || 1} 轮 / 5</span>
                    <p>{currentQuestion}</p>
                  </div>
                ) : (
                  <div className="done-state">
                    <Check size={24} aria-hidden="true" />
                    <div>
                      <strong>五轮问答已完成</strong>
                      <p>当前后端已保存回答；风险分析和报告接口接入后可继续生成正式报告。</p>
                    </div>
                  </div>
                )}
              </div>

              <form className="answer-form" onSubmit={handleSubmitAnswer}>
                <textarea
                  value={answerDraft}
                  onChange={(event) => setAnswerDraft(event.target.value)}
                  placeholder={task ? "输入本轮回答，尽量包含数据类型、流向、接收方、权限和安全措施。" : "请先创建体检任务。"}
                  disabled={!task || task.status !== "questioning" || busy}
                />
                <button className="send-button" type="submit" disabled={!task || !answerDraft.trim() || task.status !== "questioning" || busy}>
                  {busy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
                  提交回答
                </button>
              </form>
            </div>
          </section>
        ) : null}

        {view === "legal" ? (
          <section className="legal-layout">
            <div className="toolbar">
              <div className="section-title compact">
                <BookOpenCheck size={20} aria-hidden="true" />
                <div>
                  <h3>法规主记录</h3>
                  <p>对应 POST /legal-data/import 与 GET /legal-data/records</p>
                </div>
              </div>
              <div className="toolbar-actions">
                <select
                  value={legalFilters.country}
                  onChange={(event) => {
                    const next = { ...legalFilters, country: event.target.value };
                    setLegalFilters(next);
                  }}
                  aria-label="按国家筛选"
                >
                  <option value="">全部国家</option>
                  <option value="China">中国</option>
                  <option value="Singapore">新加坡</option>
                  <option value="Vietnam">越南</option>
                </select>
                <select
                  value={legalFilters.domain}
                  onChange={(event) => {
                    const next = { ...legalFilters, domain: event.target.value };
                    setLegalFilters(next);
                  }}
                  aria-label="按领域筛选"
                >
                  <option value="">全部领域</option>
                  <option value="cross_border_data">跨境数据</option>
                  <option value="enterprise_landing">海外落地</option>
                  <option value="tax">税务合规</option>
                </select>
                <button className="ghost-button" type="button" onClick={() => handleLoadLegalRecords()} disabled={legalBusy}>
                  <Search size={18} aria-hidden="true" />
                  查询
                </button>
                <button className="primary-button" type="button" onClick={handleImportLegalData} disabled={legalBusy}>
                  {legalBusy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Database size={18} aria-hidden="true" />}
                  导入数据包
                </button>
              </div>
            </div>

            {legalImport ? (
              <div className="import-summary">
                <span>{legalImport.package_name}</span>
                <span>有效日期：{legalImport.validity_as_of || "未标注"}</span>
                <span>总记录：{legalImport.total_records}</span>
                <span>新增：{legalImport.inserted_records}</span>
                <span>更新：{legalImport.updated_records}</span>
              </div>
            ) : null}

            <form className="search-panel" onSubmit={handleLegalSearch}>
              <div className="section-title compact">
                <FileSearch size={20} aria-hidden="true" />
                <div>
                  <h3>法规语义检索</h3>
                  <p>对应 POST /legal-search/hybrid 与 /legal-search/vector</p>
                </div>
              </div>
              <div className="search-controls">
                <input
                  value={legalSearchQuery}
                  onChange={(event) => setLegalSearchQuery(event.target.value)}
                  placeholder="输入企业事实、合规问题或法规关键词"
                />
                <div className="segmented" role="radiogroup" aria-label="检索模式">
                  <button
                    type="button"
                    className={legalSearchMode === "hybrid" ? "selected" : ""}
                    onClick={() => setLegalSearchMode("hybrid")}
                  >
                    Hybrid
                  </button>
                  <button
                    type="button"
                    className={legalSearchMode === "vector" ? "selected" : ""}
                    onClick={() => setLegalSearchMode("vector")}
                  >
                    Vector
                  </button>
                </div>
                <label className="mini-check">
                  <input
                    type="checkbox"
                    checked={legalSearchRebuild}
                    onChange={(event) => setLegalSearchRebuild(event.target.checked)}
                  />
                  重建索引
                </label>
                <button className="primary-button" type="submit" disabled={legalSearchBusy}>
                  {legalSearchBusy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Search size={18} aria-hidden="true" />}
                  检索依据
                </button>
              </div>
              {legalSearchResult ? (
                <div className="search-results">
                  <div className="result-meta">
                    <span>命中：{legalSearchResult.hits.length}</span>
                    <span>向量维度：{legalSearchResult.index_dimension}</span>
                    {legalSearchResult.vector_index_chunk_count ? <span>向量切片：{legalSearchResult.vector_index_chunk_count}</span> : null}
                    {legalSearchResult.bm25_index_chunk_count ? <span>BM25 切片：{legalSearchResult.bm25_index_chunk_count}</span> : null}
                  </div>
                  {legalSearchResult.hits.slice(0, 5).map((hit) => (
                    <article className="search-hit" key={`${hit.record_id}-${hit.chunk_index}`}>
                      <div>
                        <strong>{hit.law_title}</strong>
                        <span>
                          {hit.record_id} · {countryLabels[hit.country] || hit.country} · {domainLabels[hit.domain] || hit.domain} · Chunk {hit.chunk_index}
                        </span>
                      </div>
                      <p>{hit.text}</p>
                      <small>
                        Hybrid {formatScore(hit.hybrid_score)} / Vector {formatScore(hit.vector_score ?? hit.score)} / BM25 {formatScore(hit.bm25_score)}
                      </small>
                    </article>
                  ))}
                </div>
              ) : null}
            </form>

            <div className="record-table" role="table" aria-label="法规记录">
              <div className="record-row header" role="row">
                <span>编号</span>
                <span>国家</span>
                <span>领域</span>
                <span>法规名称</span>
                <span>状态</span>
                <span>依据标签</span>
              </div>
              {legalRecords.map((record) => (
                <div className="record-row" role="row" key={record.record_id}>
                  <span>{record.record_id}</span>
                  <span>{countryLabels[record.country] || record.country}</span>
                  <span>{domainLabels[record.domain] || record.domain}</span>
                  <span className="record-title">{record.law_title_local || record.law_title_en || "未命名法规"}</span>
                  <span>{record.is_currently_effective === false ? "失效/待确认" : "现行有效"}</span>
                  <span className="tag-list">
                    {(record.agent_tags || []).slice(0, 3).map((tag) => (
                      <em key={tag}>{tag}</em>
                    ))}
                  </span>
                </div>
              ))}
              {!legalBusy && legalRecords.length === 0 ? (
                <div className="empty-state">
                  <Gavel size={26} aria-hidden="true" />
                  <p>尚未加载法规记录。可以先查询，或导入本地三国法规数据包。</p>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        {view === "report" ? (
          <section className="report-layout">
            <div className="report-hero">
              <div>
                <p className="eyebrow">风险分析 / 法规依据 / PDF 报告</p>
                <h3>{task?.company_name || "未命名企业"}的跨境合规体检报告</h3>
              </div>
              <span>{task ? statusLabels[task.status] || task.status : "未开始"}</span>
            </div>

            <div className="report-actions">
              <button className="primary-button" type="button" onClick={handleCreateAnalysis} disabled={!task || task.status !== "answered" || analysisBusy}>
                {analysisBusy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Sparkles size={18} aria-hidden="true" />}
                生成风险分析
              </button>
              <button className="ghost-button" type="button" onClick={handleLoadLatestAnalysis} disabled={!task || analysisBusy}>
                <RefreshCw size={18} aria-hidden="true" />
                加载最新分析
              </button>
              <button className="ghost-button" type="button" onClick={handleDownloadPdfReport} disabled={!task || analysisBusy}>
                <FileText size={18} aria-hidden="true" />
                生成/下载 PDF
              </button>
            </div>

            <div className="report-grid">
              <article className="metric-card risk-overview">
                <ShieldCheck size={22} aria-hidden="true" />
                <strong>综合结论</strong>
                <p>{riskSummary?.overallLevel || (analysis ? "待人工复核" : "尚未生成分析")}</p>
                <small>{riskSummary?.conclusion || selectedScope.title}</small>
              </article>
              <article className="metric-card risk-critical">
                <AlertTriangle size={22} aria-hidden="true" />
                <strong>重点风险</strong>
                <p>{riskSummary ? `${riskSummary.criticalCount} 项需要优先处理` : answers.length >= 4 ? "等待生成" : "信息不足"}</p>
                <small>{riskSummary?.priorityAction || "用户最关心的红色风险会放在这里。"}</small>
              </article>
              <article className="metric-card risk-warning">
                <AlertTriangle size={22} aria-hidden="true" />
                <strong>一般风险</strong>
                <p>{riskSummary ? `${riskSummary.warningCount} 项需要跟进` : "等待生成"}</p>
                <small>黄色风险适合安排整改计划和补充材料。</small>
              </article>
              <article className="metric-card">
                <BookOpenCheck size={22} aria-hidden="true" />
                <strong>法规依据</strong>
                <p>{analysis ? `本次引用 ${analysis.evidences.length} 条法规切片` : "等待检索"}</p>
                <small>{riskSummary ? `待补充信息 ${riskSummary.missingInfoCount} 项` : "风险分析会自动检索 cross_border_data 法规依据。"}</small>
              </article>
            </div>

            {analysis ? (
              <div className="analysis-panel">
                <div className="section-title compact">
                  <Sparkles size={20} aria-hidden="true" />
                  <div>
                    <h3>风险分析结果</h3>
                    <p>
                      {analysis.model_name || "未记录模型"} · {analysis.retrieval_method} · {analysis.created_at_utc}
                    </p>
                  </div>
                </div>
                <pre className="analysis-text">{analysis.analysis}</pre>
                <div className="evidence-grid">
                  {analysis.evidences.map((evidence) => (
                    <article className="evidence-card" key={`${evidence.record_id}-${evidence.chunk_index}`}>
                      <strong>{evidence.law_title}</strong>
                      <span>
                        {evidence.record_id} · {countryLabels[evidence.country] || evidence.country} · {domainLabels[evidence.domain] || evidence.domain}
                      </span>
                      <small>
                        Hybrid {formatScore(evidence.hybrid_score)} / Vector {formatScore(evidence.vector_score)} / BM25 {formatScore(evidence.bm25_score)}
                      </small>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="answer-review">
              <h3>已采集信息</h3>
              {answers.length > 0 ? (
                answers.map((item) => (
                  <div className="review-item" key={`review-${item.round}`}>
                    <span>第 {item.round} 轮</span>
                    <p>{item.answer}</p>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  <FileText size={26} aria-hidden="true" />
                  <p>还没有问答记录。完成企业体检后，这里会展示结构化摘要入口。</p>
                </div>
              )}
            </div>
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default App;
