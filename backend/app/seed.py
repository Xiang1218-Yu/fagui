import os
import zipfile
from pathlib import Path

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Source, Subscription, User
from app.security import hash_password

DEMO_BASE_URL = os.getenv("DEMO_BASE_URL", "http://127.0.0.1:8000/demo-site/")


def _demo_dir() -> Path:
    path = Path(settings.demo_site_dir)
    (path / "attachments").mkdir(parents=True, exist_ok=True)
    (path / "private").mkdir(parents=True, exist_ok=True)
    return path


def _page(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: "Songti SC", serif; max-width: 860px; margin: 24px auto; line-height: 1.9; color: #222; }}
.meta {{ color: #666; font-size: 14px; }}
.article {{ margin-top: 18px; }}
h1 {{ font-size: 22px; text-align: center; }}
</style>
</head>
<body>
<div class="meta">北都市地方金融监督管理局（演示站点）</div>
<div class="article">
{body_html}
</div>
</body>
</html>
"""


def _index_html(include_2026_plan: bool) -> str:
    extra = (
        '<li><a href="notice_003.html">关于印发《2026年度现场检查工作计划》的通知（京金规〔2026〕7号）</a></li>\n'
        if include_2026_plan
        else ""
    )
    body = f"""
<h1>政策法规公开栏目</h1>
<ul>
<li><a href="notice_001.html">关于加强数据合规管理的通知（京金规〔2026〕3号）</a></li>
<li><a href="notice_002.html">关于《跨境数据流动管理办法（征求意见稿）》公开征求意见的公告</a></li>
{extra}<li><a href="private/internal.html">内部监管工作会议纪要（不对外公开）</a></li>
</ul>
"""
    return _page("政策法规公开栏目 - 北都市地方金融监督管理局", body)


def _notice_001_html(v2: bool) -> str:
    extra_clauses = ""
    revision_note = ""
    if v2:
        revision_note = '<p class="meta">修订记录：2026-08-20 根据执法实践修订第十五条、第十六条，并更新配套附件《合规检查要点》。</p>'
        extra_clauses = """
<p><strong>第十五条</strong> 金融机构应当于每季度结束后十五个工作日内，向监管部门报送数据合规季度报告，报告应当包含数据出境、第三方合作、投诉处理三类台账。</p>
<p><strong>第十六条</strong> 违反本通知第十五条规定，未按期报送或报送内容弄虚作假的，监管部门可依法采取监管谈话、责令改正并予以通报。</p>
"""
    body = f"""
{revision_note}
<h1>关于加强数据合规管理的通知</h1>
<p class="meta">文号：京金规〔2026〕3号　|　发布日期：2026-03-15　|　施行日期：2026-05-01</p>
<p>各驻市金融机构、各区金融工作部门：</p>
<p>为进一步规范金融机构数据处理活动，防范数据安全风险，根据《中华人民共和国数据安全法》《中华人民共和国个人信息保护法》等法律法规，现就加强数据合规管理有关事项通知如下：</p>
<p><strong>第一条</strong> 金融机构应当建立健全数据合规管理制度，明确数据合规负责人，覆盖数据收集、存储、使用、传输、删除全生命周期。</p>
<p><strong>第二条</strong> 处理个人金融信息应当遵循合法、正当、必要原则，取得个人单独同意的场景应当留存同意记录不少于三年。</p>
<p><strong>第三条</strong> 金融机构应当对核心数据、重要数据实行分类分级管理，重要数据目录每年至少更新一次并报送监管部门。</p>
<p><strong>第四条</strong> 向境外提供金融数据的，应当依法完成数据出境安全评估或订立标准合同，不得通过拆分、伪装等方式规避监管。</p>
<p><strong>第五条</strong> 金融机构委托第三方处理数据的，应当签订数据处理协议，明确安全保护义务，并对第三方进行年度评估。</p>
<p><strong>第六条</strong> 发生数据安全事件的，应当在二十四小时内向监管部门报告，并启动应急预案。</p>
{extra_clauses}
<p>附件：<a href="attachments/checklist.docx">附件1：合规检查要点.docx</a></p>
<p>北都市地方金融监督管理局<br>2026年3月15日</p>
"""
    return _page("关于加强数据合规管理的通知（京金规〔2026〕3号）", body)


def _notice_002_html() -> str:
    body = """
<h1>关于《跨境数据流动管理办法（征求意见稿）》公开征求意见的公告</h1>
<p class="meta">发布日期：2026-07-02　|　意见反馈截止：2026-09-02</p>
<p>为规范跨境数据流动活动，我局起草了《跨境数据流动管理办法（征求意见稿）》，现向社会公开征求意见。</p>
<p><strong>一、主要内容</strong>：征求意见稿共五章二十八条，明确了跨境数据流动分类分级、安全评估、标准合同、负面清单等制度安排。</p>
<p><strong>二、反馈方式</strong>：通过电子邮件或信函方式反馈，邮件主题请注明“跨境数据流动办法反馈意见”。</p>
<p><strong>三、注意事项</strong>：反馈意见应当说明具体条款及修改理由，征集截止后我局将汇总研究并公布采纳情况。</p>
<p>北都市地方金融监督管理局<br>2026年7月2日</p>
"""
    return _page("关于《跨境数据流动管理办法（征求意见稿）》公开征求意见的公告", body)


def _notice_003_html() -> str:
    body = """
<h1>关于印发《2026年度现场检查工作计划》的通知</h1>
<p class="meta">文号：京金规〔2026〕7号　|　发布日期：2026-08-18　|　施行日期：2026-08-18</p>
<p>各驻市金融机构：</p>
<p>现将《2026年度现场检查工作计划》印发给你们，请按要求做好自查与迎检准备。</p>
<p><strong>一、检查范围</strong>：全市银行、保险、证券、地方金融组织共抽取不少于六十家机构。</p>
<p><strong>二、检查重点</strong>：数据合规、消费者权益保护、反洗钱、公司治理四个领域。</p>
<p><strong>三、时间安排</strong>：2026年9月至11月开展现场检查，12月通报检查结果。</p>
<p>北都市地方金融监督管理局<br>2026年8月18日</p>
"""
    return _page("关于印发《2026年度现场检查工作计划》的通知（京金规〔2026〕7号）", body)


def _private_html() -> str:
    body = """
<h1>内部监管工作会议纪要</h1>
<p class="meta">秘密等级：内部资料，注意保管</p>
<p>本页面为内部资料，robots.txt 已禁止抓取，合规采集器不应访问本页面。</p>
"""
    return _page("内部监管工作会议纪要", body)


_ROBOTS = """User-agent: *
Allow: /
Disallow: /demo-site/private/
Crawl-delay: 1
"""


def _make_docx(path: Path, paragraphs: list[str]) -> None:
    def esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{esc(p)}</w:t></w:r></w:p>' for p in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def _checklist_paragraphs(v2: bool) -> list[str]:
    paragraphs = [
        "附件1：合规检查要点",
        "一、数据合规制度建设：是否设立数据合规负责人，是否建立全生命周期管理制度。",
        "二、个人信息保护：单独同意场景是否留存记录，隐私政策是否完整披露。",
        "三、数据分类分级：是否形成重要数据目录并按年度更新。",
        "四、数据出境：是否完成安全评估或签订标准合同，台账是否完整。",
        "五、第三方管理：数据处理协议是否齐备，年度评估是否开展。",
        "六、应急响应：数据安全事件报告时限是否满足二十四小时要求。",
        "七、员工培训：年度数据合规培训覆盖率是否达到百分之百。",
    ]
    if v2:
        paragraphs.append("八、季度报告：是否按通知第十五条要求按时报送数据合规季度报告，三类台账是否齐全。")
        paragraphs.append("九、检查方式：新增线上台账抽查与监管谈话机制，弄虚作假将直接通报。")
    return paragraphs


def write_demo_site(v2: bool) -> None:
    root = _demo_dir()
    (root / "robots.txt").write_text(_ROBOTS, encoding="utf-8")
    (root / "index.html").write_text(_index_html(include_2026_plan=v2), encoding="utf-8")
    (root / "notice_001.html").write_text(_notice_001_html(v2=v2), encoding="utf-8")
    (root / "notice_002.html").write_text(_notice_002_html(), encoding="utf-8")
    if v2:
        (root / "notice_003.html").write_text(_notice_003_html(), encoding="utf-8")
    else:
        stale = root / "notice_003.html"
        if stale.exists():
            stale.unlink()
    (root / "private" / "internal.html").write_text(_private_html(), encoding="utf-8")
    _make_docx(root / "attachments" / "checklist.docx", _checklist_paragraphs(v2=v2))
    (root / ".version").write_text("v2" if v2 else "v1", encoding="utf-8")


def demo_version() -> str:
    marker = _demo_dir() / ".version"
    return marker.read_text(encoding="utf-8").strip() if marker.exists() else "v1"


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    init_db()
    write_demo_site(v2=False)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all(
                [
                    User(
                        username="admin",
                        display_name="系统管理员",
                        role="admin",
                        password_hash=hash_password("admin123"),
                    ),
                    User(
                        username="analyst",
                        display_name="合规分析师",
                        role="analyst",
                        password_hash=hash_password("analyst123"),
                    ),
                ]
            )
            db.commit()
        if db.query(Source).count() == 0:
            base = DEMO_BASE_URL.rstrip("/") + "/"
            db.add(
                Source(
                    name="北都市地方金融监督管理局（演示）",
                    org_type="regulator",
                    base_url=base,
                    homepage_url=base + "index.html",
                    frequency="daily",
                    interval_minutes=1440,
                    enabled=True,
                    respect_robots=True,
                    allowed_paths=["/demo-site/"],
                    max_depth=2,
                    description="内置演示监管站点：含通知正文、DOCX 附件、征求意见稿与 robots 禁抓目录，可用于演练采集-变更-复核-研判闭环。",
                )
            )
        admin = db.query(User).filter(User.username == "admin").first()
        if admin and db.query(Subscription).count() == 0:
            db.add(
                Subscription(
                    user_id=admin.id,
                    name="全部法规变更（站内）",
                    channel="inapp",
                    event_types=["change_detected", "review_decided", "impact_published"],
                    source_ids=[],
                    keywords=[],
                    enabled=True,
                )
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("种子数据初始化完成")
