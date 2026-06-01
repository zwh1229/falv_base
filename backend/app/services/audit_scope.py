from app.schemas.audit import AuditScope


#定义审查范围和国家列表的映射表

SCOPE_COUNTIRIES = {
    #国内
    AuditScope.china:['China'],
    #中越
    AuditScope.china_viethnam:["China", "Vietnam"],
    #中新
    AuditScope.china_singapore: ["China", "Singapore"],
}



def get_countries_by_scope(scope: AuditScope) -> list[str]:

    # What：从映射表里取出 scope 对应的国家列表。
    # Why：创建任务时需要把用户选择转成实际检索范围。
    # How：字典用 scope 作为 key，直接返回 value。
    return SCOPE_COUNTIRIES[scope]
