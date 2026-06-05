from app.models.audit import AuditAnswer

#整理上下文文本
def build_audit_answer_context(
    answers:list[AuditAnswer]
)->str:
    lines:list[str]=[]
    for answer in answers:
        line = f"Round {answer.round_no}:{answer.answer}"
        lines.append(line)


    return "\n".join(lines)