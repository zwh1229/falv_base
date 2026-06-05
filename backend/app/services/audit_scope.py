from app.schemas.audit import AuditScope


#定义审查范围和国家列表的映射表

SCOPE_COUNTIRIES = {
    #国内
    AuditScope.china:['China'],
    #中越
    AuditScope.china_vietnam:["China", "Vietnam"],
    #中新
    AuditScope.china_singapore: ["China", "Singapore"],
}



def get_countries_by_scope(scope: AuditScope) -> list[str]:

  
    return SCOPE_COUNTIRIES[scope]
