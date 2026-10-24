from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models import (
    Conversation,
    Customer,
    KbCategory,
    KbDocument,
    KbFaq,
    Message,
    User,
)
from app.services.indexer import index_document, index_faq
from app.rag import store as vector_store


def seed() -> None:
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    ) if settings.database_url.startswith("sqlite") else None

    Base.metadata.create_all(bind=engine)
    # init milvus collection
    vector_store.get_client()

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    nickname="陈屿",
                    role="admin",
                )
            )
            db.add(
                User(
                    username="agent",
                    password_hash=hash_password("agent123"),
                    nickname="李沐",
                    role="agent",
                )
            )
            db.commit()

        if db.query(KbCategory).count() == 0:
            cats = [
                KbCategory(name="售后政策", sort=1),
                KbCategory(name="物流配送", sort=2),
                KbCategory(name="支付退款", sort=3),
                KbCategory(name="商品说明", sort=4),
            ]
            db.add_all(cats)
            db.commit()

        if db.query(KbFaq).count() == 0:
            refund_cat = db.query(KbCategory).filter(KbCategory.name == "支付退款").first()
            after_cat = db.query(KbCategory).filter(KbCategory.name == "售后政策").first()
            faqs = [
                KbFaq(
                    category_id=refund_cat.id if refund_cat else None,
                    question="退款多久能到账？",
                    answer=(
                        "退款一般在仓库签收后 1-2 个工作日内原路退回。"
                        "微信支付通常 2 小时内到账，银行卡可能需要 3-5 个工作日。"
                        "若超过 5 个工作日未到账，请提交支付凭证由财务核查。"
                    ),
                    similar_questions=json.dumps(
                        ["退款什么时候到", "钱什么时候退回来", "退款时效"],
                        ensure_ascii=False,
                    ),
                    status="published",
                ),
                KbFaq(
                    category_id=after_cat.id if after_cat else None,
                    question="七天无理由退货怎么申请？",
                    answer=(
                        "自签收次日起 7 天内可申请无理由退货，商品需保持完好、不影响二次销售。"
                        "请在订单页提交退货申请，审核通过后按页面指引寄回。"
                    ),
                    similar_questions=json.dumps(
                        ["可以退货吗", "无理由退货", "怎么退货"],
                        ensure_ascii=False,
                    ),
                    status="published",
                ),
                KbFaq(
                    category_id=db.query(KbCategory)
                    .filter(KbCategory.name == "物流配送")
                    .first()
                    .id,
                    question="物流超过 72 小时无揽收怎么办？",
                    answer=(
                        "超过 72 小时无揽收记录，可发起物流工单并同步客户补偿方案。"
                        "坐席可协助催促揽收或改派承运商。"
                    ),
                    similar_questions=json.dumps(
                        ["一直不发货", "物流不动", "没揽收"],
                        ensure_ascii=False,
                    ),
                    status="published",
                ),
            ]
            db.add_all(faqs)
            db.commit()
            for faq in db.query(KbFaq).all():
                index_faq(db, faq)

        if db.query(KbDocument).count() == 0:
            sample = Path(settings.upload_dir) / "refund_policy_sample.txt"
            sample.write_text(
                "退款到账时效说明\n\n"
                "1. 仓库签收退货后启动退款流程。\n"
                "2. 微信支付：多数情况下 2 小时内到账。\n"
                "3. 银行卡：一般 1-5 个工作日。\n"
                "4. 超时未到账请提供订单号与支付截图。\n",
                encoding="utf-8",
            )
            doc = KbDocument(
                title="退款到账时效说明",
                filename="refund_policy_sample.txt",
                filepath=str(sample),
                content_type="text/plain",
                status="processing",
                category_id=db.query(KbCategory)
                .filter(KbCategory.name == "支付退款")
                .first()
                .id,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            index_document(db, doc)

        if db.query(Customer).count() == 0:
            customers = [
                Customer(
                    name="张悠然",
                    phone_mask="138****6621",
                    level="黑金会员",
                    tags="退款中,VIP",
                ),
                Customer(
                    name="王小川",
                    phone_mask="186****1024",
                    level="银卡",
                    tags="物流咨询",
                ),
                Customer(
                    name="赵晴",
                    phone_mask="159****8830",
                    level="普通",
                    tags="商品咨询",
                ),
                Customer(
                    name="周明",
                    phone_mask="177****4412",
                    level="金卡",
                    tags="售后",
                ),
            ]
            db.add_all(customers)
            db.commit()

            agent = db.query(User).filter(User.username == "admin").first()
            c1, c2, c3, c4 = db.query(Customer).order_by(Customer.id).all()
            convs = [
                Conversation(
                    session_no="A-2048",
                    customer_id=c1.id,
                    channel="wechat_mp",
                    status="active",
                    agent_id=agent.id if agent else None,
                    subject="退款到账咨询",
                ),
                Conversation(
                    session_no="A-2051",
                    customer_id=c2.id,
                    channel="wecom",
                    status="active",
                    subject="物流揽收异常",
                ),
                Conversation(
                    session_no="A-2055",
                    customer_id=c3.id,
                    channel="app",
                    status="queue",
                    subject="尺码建议",
                ),
                Conversation(
                    session_no="A-2060",
                    customer_id=c4.id,
                    channel="web",
                    status="active",
                    subject="七天无理由退货",
                ),
            ]
            db.add_all(convs)
            db.commit()

            a2048 = db.query(Conversation).filter(Conversation.session_no == "A-2048").first()
            a2051 = db.query(Conversation).filter(Conversation.session_no == "A-2051").first()
            a2060 = db.query(Conversation).filter(Conversation.session_no == "A-2060").first()
            msgs = [
                Message(
                    conversation_id=a2048.id,
                    sender="customer",
                    content="你好，我的退款多久能到账？订单 SO-20261012-8842",
                ),
                Message(
                    conversation_id=a2048.id,
                    sender="agent",
                    content="您好，我帮您查询一下退款进度。",
                    is_ai_assisted=False,
                ),
                Message(
                    conversation_id=a2048.id,
                    sender="customer",
                    content="仓库那边说已经签收了，怎么还没退款？",
                ),
                Message(
                    conversation_id=a2051.id,
                    sender="customer",
                    content="快递都三天了还没揽收，能催一下吗？",
                ),
                Message(
                    conversation_id=a2060.id,
                    sender="customer",
                    content="收到货不满意，想走七天无理由，怎么操作？",
                ),
            ]
            db.add_all(msgs)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
