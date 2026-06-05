import re

from bs4 import BeautifulSoup




NOISE_TAGS = [
    "script",
    "style",
    "meta",
    "noscript",
    "svg",
    "header",
    "footer",
    "nav",
    "aside",
    "form",
    "button",
]



NOISE_KEYWORDS = [
    "nav",
    "menu",
    "sidebar",
    "toolbar",
    "breadcrumb",
    "footer",
    "header",
    "modal",
    "cookie",
    "search",
    "social",
    "share",
    "feedback",
    "print",
    "toc",
]



CONTENT_SELECTORS = [
    "#colLegis",
    ".col-legis",
    ".main-content",
    "article",
    "main",
    "[role='main']",
    "#main",
    "body",
]


# 判断文本是否为 HTML。
def looks_like_html(text: str) -> bool:
    lower_text = text[:2000].lower()

    return (
        "<html" in lower_text
        or "<!doctype html" in lower_text
        or "<body" in lower_text
        or "<script" in lower_text
    )


# 判断标签网页噪声块。
def is_noise_block(tag) -> bool:
    if tag is None or tag.attrs is None:
        return False

    values: list[str] = []

    tag_id = tag.get("id")
    if tag_id:
        values.append(str(tag_id))

    tag_classes = tag.get("class") or []
    values.extend(str(item) for item in tag_classes)

    joined = " ".join(values).lower()

    return any(keyword in joined for keyword in NOISE_KEYWORDS)


# 删除 HTML 里的噪声标签和噪声块。

def remove_noise(soup: BeautifulSoup) -> None:
    for tag in soup(NOISE_TAGS):
        tag.decompose()


    for tag in list(soup.find_all(True)):
        if tag.parent is not None and is_noise_block(tag):
            tag.decompose()
  



def find_content_root(soup: BeautifulSoup):
    for selector in CONTENT_SELECTORS:
        node = soup.select_one(selector)

        if node is None:
            continue

        text = node.get_text(separator="\n", strip=True)

        if len(text) >= 200:
            return node

    return soup



def normalize_legal_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    lines = [re.sub(r"\s+", " ", line) for line in lines]

    return "\n".join(lines)



def clean_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    remove_noise(soup)

    content_root = find_content_root(soup)

    text = content_root.get_text(separator="\n")

    return normalize_legal_text(text)


#清洗入口
def clean_legal_text(raw_text: str) -> str:
    if looks_like_html(raw_text):
        return clean_html_text(raw_text)

    return normalize_legal_text(raw_text)