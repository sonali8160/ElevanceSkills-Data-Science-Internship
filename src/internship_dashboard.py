from pathlib import Path
from datetime import datetime, date, timedelta
from types import SimpleNamespace
import sys, tempfile, re

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

def datetime_control(label: str, default_value: datetime, key_prefix: str) -> datetime:
    """Collect a date and time using Streamlit APIs available in supported versions."""
    date_value = st.date_input(
        f"{label} — date",
        value=default_value.date(),
        key=f"{key_prefix}_date",
    )
    time_value = st.time_input(
        f"{label} — time",
        value=default_value.time().replace(microsecond=0),
        key=f"{key_prefix}_time",
    )
    return datetime.combine(date_value, time_value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task1.analyzer import analyze_message
from task2.models import Agent, SLAConfig, SupportTicket
from task2.ticket_workflow import process_unresolved_conversation, build_default_sla_config
from task1.models import ConversationMessage
from task3.config import create_schedule
from task3.pipeline import KnowledgeBasePipeline
from task4.rag_assistant import RAGDocument, RAGKnowledgeAssistant
from task5.evidence_processor import EvidenceProcessor
from task6.multilingual_chat import MultilingualChatbot, Task6Config

st.set_page_config(page_title="Customer Service Chatbot", page_icon="🤖", layout="wide")

# Header and navigation styling based on the requested screenshot.
st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 1rem; max-width: 100%; }
    h1 { font-size: 2.7rem !important; font-weight: 750 !important; color: #343541 !important; margin-bottom: 0.8rem !important; }
    .dashboard-subtitle { color: #90919b; font-size: 16px; margin-top: 8px; margin-bottom: 22px; }
    div[data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #e8e8e8; }
    button[data-baseweb="tab"] { font-size: 15px !important; padding: 12px 10px !important; color: #424451 !important; white-space: nowrap; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #ff5b55 !important; border-bottom: 3px solid #ff5b55 !important; background-color: transparent !important; }
    button[data-baseweb="tab"]:hover { color: #ff5b55 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Customer Service Chatbot")
st.markdown(
    '<div class="dashboard-subtitle">'
    'Existing training project integrated with all six internship task demonstrations.'
    '</div>',
    unsafe_allow_html=True,
)

# Keep state separate by task and browser session.
if "unified_t2_result" not in st.session_state: st.session_state.unified_t2_result = None
if "unified_t3_pipeline" not in st.session_state: st.session_state.unified_t3_pipeline = KnowledgeBasePipeline(create_schedule())
if "unified_t3_dir" not in st.session_state: st.session_state.unified_t3_dir = tempfile.mkdtemp(prefix="elevance_kb_")
if "unified_t4_rag" not in st.session_state: st.session_state.unified_t4_rag = RAGKnowledgeAssistant()
if "unified_t5_processor" not in st.session_state: st.session_state.unified_t5_processor = EvidenceProcessor(retention_seconds=30*86400, processing_limit_seconds=30)
if "unified_t5_dir" not in st.session_state: st.session_state.unified_t5_dir = tempfile.mkdtemp(prefix="elevance_evidence_")
if "unified_t6_bot" not in st.session_state: st.session_state.unified_t6_bot = MultilingualChatbot()

Original,T1,T2,T3,T4,T5,T6 = st.tabs(["Original Chatbot", "Task 1: Sentiment", "Task 2: Tickets", "Task 3: Knowledge Pipeline", "Task 4: RAG Assistant", "Task 5: OCR Evidence", "Task 6: Multilingual Chat"])

with T1:
    st.header("Task 1 — Sentiment, tone and escalation")
    msg = st.text_area("Customer message", "I was charged twice for order ORD12345. Please help.", key="u_t1_msg")
    if st.button("Analyse sentiment and risk", key="u_t1_go", type="primary"):
        try:
            result = analyze_message(msg)
            st.json(result.__dict__ if hasattr(result, "__dict__") else result)
            if getattr(result, "risk_categories", None): st.warning("Risk detected: " + ", ".join(result.risk_categories))
        except Exception as e: st.error(f"Could not analyse message: {e}")

with T2:
    st.header("Task 2 — Unresolved conversation to support ticket")
    c1,c2 = st.columns(2)
    with c1:
        t2msg = st.text_area("Conversation (one message per line)", "My name is Rahul Sharma. My email is rahul@example.com. Order ID ORD456. I was charged twice for my course.", key="u_t2_msg")
        ticket_id = st.text_input("Ticket ID", "T-DEMO-001", key="u_t2_id")
        resolved = st.checkbox("Conversation is already resolved", key="u_t2_resolved")
    with c2:
        now = datetime.now().replace(second=0,microsecond=0)
        start_at = datetime_control("Conversation start time", now-timedelta(minutes=20), "u_t2_start")
        current_at = datetime_control("Simulated current time", now, "u_t2_now")
        oncall = st.checkbox("On-call/security agent available", True, key="u_t2_oncall")
    if st.button("Create / evaluate ticket", key="u_t2_go", type="primary"):
        if not t2msg.strip(): st.error("Enter a conversation first.")
        elif current_at < start_at: st.error("Current time must be after conversation start.")
        else:
            messages=[ConversationMessage(text=line.strip(),timestamp=start_at+timedelta(seconds=i),role="user") for i,line in enumerate(t2msg.splitlines()) if line.strip()]
            agents=[Agent(name="Payments Specialist",skills={"payments"},available=True,workload=1,max_workload=10),Agent(name="Security Specialist",skills={"security"},available=oncall,workload=1,max_workload=10,on_call=True),Agent(name="General Support",skills={"general_support","course_support","technical"},available=True,workload=1,max_workload=10)]
            try:
                result=process_unresolved_conversation(messages=messages,ticket_id=ticket_id or "T-DEMO-001",agents=agents,existing_tickets=[],current_time=current_at,sla_config=build_default_sla_config(),resolved=resolved)
                st.session_state.unified_t2_result=result
            except Exception as e: st.error(f"Ticket processing failed: {e}")
    res=st.session_state.unified_t2_result
    if res:
        if res.ticket is None: st.success("Resolved conversation — no active ticket created.")
        else:
            ticket=res.ticket
            a,b,c=st.columns(3); a.metric("Priority",ticket.priority.upper()); b.metric("Status",ticket.status.replace("_"," ").title()); c.metric("SLA used",f"{ticket.sla_consumed_ratio*100:.1f}%")
            st.json({"ticket_id":ticket.ticket_id,"customer":ticket.customer.name,"email":ticket.customer.email,"order_id":ticket.order_id,"product":ticket.product,"issue_category":ticket.issue_category,"severity":ticket.severity,"assigned_agent":ticket.assigned_agent,"queue":ticket.assigned_queue,"sla_breached":getattr(ticket, "sla_breached", False),"escalation_triggered":getattr(ticket, "escalation_triggered", False),"escalation_reason":getattr(ticket, "escalation_reason", None),"missing_information":res.missing_information,"routing_reason":res.routing.reason if res.routing else None})
            if res.information_request: st.info(res.information_request)

with T3:
    st.header("Task 3 — Knowledge-base update and monitoring")
    pipeline=st.session_state.unified_t3_pipeline
    role=st.selectbox("User role",["admin","update_operator","viewer"],key="u_t3_role")
    uploads=st.file_uploader("Upload knowledge documents (.txt, .md, .csv, .json)",type=["txt","md","csv","json"],accept_multiple_files=True,key="u_t3_upload")
    if uploads:
        for f in uploads:
            safe=Path(f.name).name
            Path(st.session_state.unified_t3_dir,safe).write_bytes(f.getvalue())
        st.success(f"{len(uploads)} file(s) saved for scanning.")
    x,y=st.columns(2)
    with x:
        if st.button("Scan new/changed documents",key="u_t3_scan",type="primary"):
            try:
                st.session_state.unified_t3_scan=pipeline.scan(st.session_state.unified_t3_dir,SimpleNamespace(role=role))
                st.success("Scan finished.")
            except Exception as e: st.error(str(e))
    with y:
        if st.button("Refresh monitoring",key="u_t3_monitor"):
            try: st.json(pipeline.monitoring_summary())
            except Exception as e: st.error(str(e))
    latest_scan = st.session_state.get("unified_t3_scan")
    if latest_scan is not None:
        st.write("Latest scan result")
        st.write(latest_scan)
    st.write("Active documents");
    try: st.write(pipeline.get_active_documents())
    except Exception: pass

with T4:
    st.header("Task 4 — Retrieval-augmented knowledge assistant")
    rag=st.session_state.unified_t4_rag
    with st.expander("Add a knowledge document"):
        d1,d2=st.columns(2)
        with d1:
            docid=st.text_input("Document ID", "FAQ-001", key="u_t4_id")
            product=st.text_input("Product", "general", key="u_t4_product")
            region=st.text_input("Region", "global", key="u_t4_region")
            access=st.selectbox("Access level",["public","customer","agent","admin"],key="u_t4_access")
        with d2:
            effective=st.date_input("Effective date",date.today(),key="u_t4_eff")
            expiry_enabled=st.checkbox("Set expiry date",key="u_t4_exp_enable")
            expiry=st.date_input("Expiry date",date.today()+timedelta(days=365),key="u_t4_exp") if expiry_enabled else None
            version=st.text_input("Version", "v1",key="u_t4_ver")
            doctype=st.selectbox("Document type",["faq","policy","troubleshooting","guide"],key="u_t4_type")
        content=st.text_area("Document content", "Customers can request help by contacting support with their order ID.",key="u_t4_content")
        if st.button("Add document to knowledge base",key="u_t4_add"):
            try:
                doc=RAGDocument(doc_id=docid,content=content,product=product,region=region,access_level=access,effective_date=effective,expiry_date=expiry,version=version,doc_type=doctype,source=docid)
                st.success("Document added." if rag.add_document(doc) else "Document rejected (duplicate ID, invalid metadata or unsafe instructions).")
            except Exception as e: st.error(str(e))
    q=st.text_input("Ask a question", "How can I contact support?",key="u_t4_q")
    q1,q2,q3=st.columns(3)
    with q1: qa=st.selectbox("Your access",["public","customer","agent","admin"],index=1,key="u_t4_qa")
    with q2: qp=st.text_input("Product filter (optional)",key="u_t4_qp")
    with q3: qr=st.text_input("Region filter (optional)",key="u_t4_qr")
    asof=st.date_input("Answer as of date",date.today(),key="u_t4_asof")
    if st.button("Find answer with citations",key="u_t4_go",type="primary"):
        try:
            ans=rag.answer(q,user_access=qa,product=qp or None,region=qr or None,as_of_date=asof)
            st.write(ans.answer)
            if ans.citations: st.success("Sources: "+", ".join(ans.citations))
            if ans.needs_clarification: st.warning("More information is needed to answer safely.")
        except Exception as e: st.error(str(e))

with T5:
    st.header("Task 5 — Evidence analysis, OCR and privacy")
    proc=st.session_state.unified_t5_processor
    retention=st.selectbox("File retention",[1,7,14,30,90],index=3,key="u_t5_retention")
    proc.retention_seconds=int(retention)*86400
    message=st.text_area("Customer message", "My order ORD12345 for Laptop was charged INR 1500.",key="u_t5_message")
    upload=st.file_uploader("Upload evidence (image, PDF, TXT or CSV)",type=["png","jpg","jpeg","webp","pdf","txt","csv"],key="u_t5_upload")
    required=st.multiselect("Evidence fields to check",["order_id","date","amount","product","error_code"],default=["order_id"],key="u_t5_required")
    expected_product=st.text_input("Expected product (optional)","Laptop",key="u_t5_product")
    delay=st.select_slider("Simulated processing time",options=[0,5,15,29,31,45],value=0,key="u_t5_delay")
    if st.button("Analyse evidence",key="u_t5_go",type="primary"):
        try:
            file_path=None
            if upload:
                file_path=str(Path(st.session_state.unified_t5_dir,Path(upload.name).name))
                Path(file_path).write_bytes(upload.getvalue())
            result=proc.process(message=message,file_path=file_path,required_fields=required,simulated_processing_seconds=delay,product=expected_product or None)
            st.session_state.unified_t5_result=result
        except Exception as e: st.error(str(e))
    if "unified_t5_result" in st.session_state:
        r=st.session_state.unified_t5_result
        st.info(r.message)
        st.json({"status":r.status,"evidence":r.evidence.__dict__,"conflicts":r.conflicts,"citations":r.citations,"background_job_id":r.background_job_id,"masked_log":r.log_message})
    if st.button("Delete expired files now",key="u_t5_clean"):
        try: st.success(f"Deleted {proc.delete_expired_files()} expired file(s).")
        except Exception as e: st.error(str(e))

with T6:
    st.header("Task 6 — Multilingual chat and session management")
    bot=st.session_state.unified_t6_bot
    with st.expander("Language and session configuration"):
        langs=st.multiselect("Enabled languages",["english","hindi","marathi","spanish"],default=bot.config.languages,key="u_t6_langs")
        lth=st.slider("Language confidence threshold",0.0,1.0,bot.config.language_threshold,0.05,key="u_t6_lth")
        ith=st.slider("Intent confidence threshold",0.0,1.0,bot.config.intent_threshold,0.05,key="u_t6_ith")
        ctx=st.slider("Context messages",1,20,bot.config.context_messages,key="u_t6_ctx")
        inactive=st.number_input("Inactivity timeout (minutes)",1,1440,bot.config.inactivity_minutes,key="u_t6_inactive")
        restore=st.number_input("Restore window (hours)",1,168,bot.config.restore_hours,key="u_t6_restore")
        if st.button("Apply chat configuration",key="u_t6_apply"):
            st.session_state.unified_t6_bot=MultilingualChatbot(Task6Config(languages=langs or ["english"],language_threshold=lth,intent_threshold=ith,context_messages=ctx,inactivity_minutes=int(inactive),restore_hours=int(restore)))
            bot=st.session_state.unified_t6_bot
            st.success("Configuration applied; in-memory sessions reset.")
    left,right=st.columns(2)
    with left:
        sid=st.text_input("Session ID","SESSION-001",key="u_t6_sid")
        cid=st.text_input("Customer ID","CUSTOMER-001",key="u_t6_cid")
        chatmsg=st.text_area("Message", "Mera order ORD12345 kab ayega?",key="u_t6_msg")
        simtime=datetime_control("Simulated message time", datetime.now().replace(microsecond=0), "u_t6_time")
        if st.button("Send message",key="u_t6_send",type="primary"):
            try:
                out=bot.process_message(sid,cid,chatmsg,simtime)
                st.session_state.unified_t6_result=out
            except Exception as e: st.error(str(e))
        latest_result = st.session_state.get("unified_t6_result")
        if latest_result is not None:
            st.json(latest_result)
        closeat=datetime_control("Session end / return time", datetime.now().replace(microsecond=0)+timedelta(minutes=31), "u_t6_close")
        c1,c2=st.columns(2)
        with c1:
            if st.button("End session",key="u_t6_end"): st.info("Session ended." if bot.end_session(sid,closeat) else "No active session found.")
        with c2:
            if st.button("Restore session",key="u_t6_restore_btn"): st.info("Session restored." if bot.restore_session(sid,closeat) else "No restorable session found.")
    with right:
        session=bot.get_session(sid)
        if session:
            st.write({"session_id":session.session_id,"customer_id":session.customer_id,"active":session.active,"messages_kept":len(session.messages),"last_activity":str(session.last_activity)})
            st.markdown("**Conversation summary**")
            st.write(session.summary or "No summary yet.")
            for item in session.messages[-bot.config.context_messages:]:
                st.markdown(f"**{item.language} · {item.intent} · confidence {item.confidence:.2f}**")
                st.write(item.text)
        else: st.info("No active session for this ID. Send a message to create one.")

def local_dataset_answer(question: str):
    """Find the closest prompt in dataset/dataset.csv without calling an API."""
    dataset_path = ROOT / "dataset" / "dataset.csv"
    if not dataset_path.is_file():
        return "The local dataset was not found at dataset/dataset.csv.", []

    df = None
    last_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(dataset_path, encoding=encoding)
            break
        except Exception as exc:
            last_error = exc
    if df is None:
        return f"Could not read the local dataset: {last_error}", []

    df.columns = [str(c).strip().lower() for c in df.columns]
    if not {"prompt", "response"}.issubset(df.columns):
        return ("The CSV must contain 'prompt' and 'response' columns. "
                f"Found: {list(df.columns)}"), []

    df = df.dropna(subset=["prompt", "response"]).copy()
    df["prompt"] = df["prompt"].astype(str).str.strip()
    df["response"] = df["response"].astype(str).str.strip()
    df = df[(df["prompt"] != "") & (df["response"] != "")]
    if df.empty:
        return "The local dataset has no valid question-answer records.", []

    def tokens(text):
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    query_tokens = tokens(question)
    if not query_tokens:
        return "Please enter a question using a few meaningful words.", []

    best_row = None
    best_score = 0.0
    for _, row in df.iterrows():
        prompt = str(row["prompt"])
        prompt_tokens = tokens(prompt)
        overlap = len(query_tokens & prompt_tokens)
        # Jaccard-like overlap with a small bonus for a phrase match.
        score = overlap / max(1, len(query_tokens | prompt_tokens))
        if question.strip().lower() in prompt.lower() or prompt.lower() in question.strip().lower():
            score += 0.35
        if score > best_score:
            best_score = score
            best_row = row

    if best_row is None or best_score < 0.08:
        return ("I couldn't find a close answer in the local dataset. "
                "Try rephrasing the question or enable Gemini AI if your API quota is available."), []

    answer = str(best_row["response"])
    source = [{"prompt": str(best_row["prompt"]), "match_score": round(best_score, 3)}]
    return answer, source


with Original:
    st.header("Original Customer Service Chatbot")

    st.write(
        "Use the training project's knowledge base "
        "to ask customer service questions."
    )

    # Initialize session state
    if "original_kb_created" not in st.session_state:
        st.session_state["original_kb_created"] = False

    # Create Knowledgebase
    if st.button(
        "Create Knowledgebase",
        key="original_create_kb",
        type="primary",
    ):
        try:
            from langchain_helper import create_vector_db

            with st.spinner("Creating knowledge base..."):
                create_vector_db()

            st.session_state["original_kb_created"] = True
            st.success("Knowledgebase created successfully!")

        except Exception as exc:
            st.session_state["original_kb_created"] = False
            st.error(f"Knowledgebase error: {exc}")

    st.divider()

    # Ask a question
    original_question = st.text_input(
        "Question",
        placeholder="Enter your customer service question...",
        key="original_chatbot_question",
    )

    # Get Answer
    if st.button("Get Answer", key="original_get_answer"):
        if not original_question.strip():
            st.warning("Please enter a question first.")

        elif not st.session_state["original_kb_created"]:
            st.warning("Please click Create Knowledgebase first.")

        else:
            try:
                from langchain_helper import get_qa_chain

                with st.spinner("finding an answer..."):
                    chain = get_qa_chain()
                    response = chain.invoke(
                        {"query": original_question.strip()}
                    )

                st.subheader("Answer")

                if isinstance(response, dict):
                    st.write(
                        response.get(
                            "result",
                            "No answer returned."
                        )
                    )
                else:
                    st.write(response)

            except Exception as exc:
                st.error(f"Original chatbot error: {exc}")
