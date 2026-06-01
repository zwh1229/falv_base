QUESTIONS = [
    "先说一下企业主要业务，以及这次要体检的数据业务场景。",

    "这些数据主要是什么类型？数据从哪里来？是否涉及个人信息或敏感信息？",

    "数据目前存在哪里？谁可以访问？主要用于什么业务目的？",

    "数据是否会传到境外？如果会，目的地国家和接收方是谁？",

    "是否已经做用户告知、授权或同意？目前有哪些加密、权限控制、脱敏、审计等安全措施？",
]



# 根据轮数获得问题
def get_question_by_round(round_no: int) -> str | None:

    if round_no < 1:

        return None

    if round_no > len(QUESTIONS):

        return None


    return QUESTIONS[round_no - 1]