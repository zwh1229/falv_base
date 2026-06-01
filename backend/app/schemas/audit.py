from enum import Enum
from typing import Optional
from pydantic import BaseModel



#定义体检任务的审查范围
class AuditScope(str, Enum):
    china = 'china'
    #中新
    china_singapore = 'china_singapore'
    #中越
    china_vietnam = 'china_vietnam'


#定义创建任务时的数据格式

class CreateAuditTaskRequest(BaseModel):
    #企业名称
    company_name: Optional[str] = None
    #审查范围
    scope: AuditScope


#定义后端给前端返回的数据格式
class AuditTaskResponse(BaseModel):
    #任务id
    task_id: str

    
    company_name: Optional[str] = None

    # AuditScope，保证返回值也固定。
    scope: AuditScope

    #  scope 转成 ["China", "Singapore"] 这种列表。
    countries: list[str]

  
    #第一版先用字符串，后面需要时再改成枚举。
    status: str

    
    #暂定 5 轮问答，后端要知道现在到第几轮。
    #任务创建时是 1，每提交一轮回答就加 1。
    current_round: int
    #下一轮要问的问题
    next_question: Optional[str] = None 


# 提交问题模型 
class SubmitAuditAnswerRequest(BaseModel):

    answer: str


class AuditAnswerResponse(BaseModel):
    id: int
    task_id: str
    round_no: int
    answer: str
