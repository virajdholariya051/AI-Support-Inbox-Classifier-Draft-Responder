"""AI Support Inbox Classifier & Draft Responder - Streamlit Application.

An intelligent customer support management system featuring local machine-learning classification,
urgency scoring, risk detection, team routing, knowledge base retrieval, and human-in-the-loop draft review.
"""

from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.approval_service import (
    approve_draft,
    can_send_draft,
    edit_draft_content,
    reject_draft,
    simulate_send_draft,
)
from backend.database import (
    DEFAULT_DB_PATH,
    delete_kb_article,
    get_activity_logs,
    get_all_drafts,
    get_all_emails,
    get_all_kb_articles,
    get_draft_by_id,
    get_email_by_id,
    get_summary_stats,
    init_db,
    insert_kb_article,
    update_email_status,
    update_kb_article,
)
from backend.draft_generator import generate_support_draft
from backend.email_classifier import CATEGORIES, classify_support_email
from backend.email_processor import import_emails_from_csv, process_and_save_email
from backend.knowledge_base import find_relevant_articles
from backend.risk_detector import detect_risk
from backend.team_assignment import TEAMS, assign_support_team
from backend.urgency_detector import detect_urgency

# -----------------------------------------------------------------------------
# Configuration and Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Support Inbox Classifier & Draft Responder",
    page_icon="📨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema and seed KB articles on application start
init_db(DEFAULT_DB_PATH, seed_kb=True)


def get_urgency_badge(urgency: str) -> str:
    """Returns color-coded HTML pill for urgency."""
    colors = {
        "Critical": "#d9534f",
        "High": "#f0ad4e",
        "Medium": "#0275d8",
        "Low": "#5cb85c",
    }
    bg = colors.get(urgency, "#6c757d")
    return f'<span style="background-color: {bg}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 0.82em;">{urgency}</span>'


def get_status_badge(status: str) -> str:
    """Returns color-coded HTML pill for draft/email status."""
    colors = {
        "APPROVED": "#28a745",
        "PENDING_APPROVAL": "#ffc107",
        "REJECTED": "#dc3545",
        "SENT": "#17a2b8",
        "NEW": "#007bff",
        "PROCESSED": "#6f42c1",
        "REPLIED": "#20c997",
    }
    text_color = "#000" if status == "PENDING_APPROVAL" else "#fff"
    bg = colors.get(status, "#6c757d")
    return f'<span style="background-color: {bg}; color: {text_color}; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 0.82em;">{status}</span>'


# -----------------------------------------------------------------------------
# Sidebar Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("📨 AI Support Inbox")
st.sidebar.markdown("**M.Sc. IT Final Project**")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Dashboard",
        "📥 Inbox",
        "🔍 Analyze Email",
        "✍️ Draft Responses",
        "📚 Knowledge Base",
        "📈 Reports & CSV Import",
    ],
    index=0,
)

st.sidebar.markdown("---")
# Quick database summary in sidebar
stats = get_summary_stats(DEFAULT_DB_PATH)
st.sidebar.caption("System Status: Online (Local SQLite)")
st.sidebar.caption(f"Emails in DB: **{stats['total_emails']}**")
st.sidebar.caption(f"Pending Reviews: **{stats['pending_drafts']}**")
st.sidebar.caption(f"Sent Responses: **{stats['sent_drafts']}**")


# =============================================================================
# PAGE 1: DASHBOARD
# =============================================================================
if menu == "📊 Dashboard":
    st.header("📊 Executive Support Overview")
    st.markdown("Real-time operational metrics, classification breakdowns, and risk monitoring.")

    # KPI Metric Cards
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Total Ingested", stats["total_emails"])
    kpi2.metric("Pending Approval", stats["pending_drafts"], delta_color="inverse")
    kpi3.metric("Approved Drafts", stats["approved_drafts"])
    kpi4.metric("Simulated Sent", stats["sent_drafts"])
    kpi5.metric("Critical Urgency", stats["critical_emails"], delta_color="inverse")
    kpi6.metric("High Risk Flags", stats["high_risk_emails"], delta_color="inverse")

    st.markdown("---")

    emails = get_all_emails(db_path=DEFAULT_DB_PATH)
    if not emails:
        st.info("No emails in database yet. Navigate to **📈 Reports & CSV Import** or **🔍 Analyze Email** to load sample data.")
        if st.button("🚀 Load 15 Sample Support Emails Now"):
            sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_emails.csv")
            if os.path.exists(sample_path):
                import_emails_from_csv(sample_path, db_path=DEFAULT_DB_PATH)
                st.success("Sample emails imported successfully!")
                st.rerun()
    else:
        df_emails = pd.DataFrame(emails)

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Urgency Level Breakdown")
            urg_counts = df_emails["urgency"].value_counts().reset_index()
            urg_counts.columns = ["Urgency", "Count"]
            urgency_colors = {
                "Critical": "#d9534f",
                "High": "#f0ad4e",
                "Medium": "#0275d8",
                "Low": "#5cb85c",
            }
            fig_urg = px.pie(
                urg_counts,
                values="Count",
                names="Urgency",
                hole=0.45,
                color="Urgency",
                color_discrete_map=urgency_colors,
            )
            fig_urg.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig_urg, use_container_width=True)

        with col_right:
            st.subheader("Category Distribution")
            cat_counts = df_emails["category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            fig_cat = px.bar(
                cat_counts,
                x="Category",
                y="Count",
                color="Category",
                text="Count",
            )
            fig_cat.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300, showlegend=False)
            st.plotly_chart(fig_cat, use_container_width=True)

        st.subheader("Team Routing & Workload Allocation")
        team_counts = df_emails["team"].value_counts().reset_index()
        team_counts.columns = ["Support Team", "Tickets"]
        fig_team = px.bar(
            team_counts,
            x="Tickets",
            y="Support Team",
            orientation="h",
            color="Tickets",
            color_continuous_scale="Teal",
        )
        fig_team.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=250)
        st.plotly_chart(fig_team, use_container_width=True)

        # Recent Audit Logs
        st.subheader("Recent System Activity Feed")
        logs = get_activity_logs(limit=8, db_path=DEFAULT_DB_PATH)
        if logs:
            df_logs = pd.DataFrame(logs)[["timestamp", "action", "details"]]
            st.dataframe(df_logs, use_container_width=True, hide_index=True)


# =============================================================================
# PAGE 2: INBOX
# =============================================================================
elif menu == "📥 Inbox":
    st.header("📥 Customer Support Inbox")
    st.markdown("Browse, filter, and inspect incoming customer communications.")

    # Filter Controls
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 3])
    with f_col1:
        selected_status = st.selectbox("Status Filter", ["All", "NEW", "PROCESSED", "REPLIED", "ARCHIVED"])
    with f_col2:
        selected_urgency = st.selectbox("Urgency Filter", ["All", "Critical", "High", "Medium", "Low"])
    with f_col3:
        selected_category = st.selectbox("Category Filter", ["All"] + CATEGORIES)
    with f_col4:
        search_query = st.text_input("Search (Subject, Body, Sender)", "")

    # Query matching emails
    status_filter = None if selected_status == "All" else selected_status
    urgency_filter = None if selected_urgency == "All" else selected_urgency
    category_filter = None if selected_category == "All" else selected_category
    search_term = search_query.strip() if search_query.strip() else None

    emails = get_all_emails(
        status=status_filter,
        category=category_filter,
        urgency=urgency_filter,
        search_query=search_term,
        db_path=DEFAULT_DB_PATH,
    )

    if not emails:
        st.info("No tickets match the selected filter criteria.")
    else:
        st.markdown(f"**Showing {len(emails)} tickets:**")
        for email in emails:
            with st.expander(
                f"#{email['id']} | [{email['urgency'].upper()}] {email['subject']} — From: {email['sender']}",
                expanded=False,
            ):
                top_c1, top_c2, top_c3, top_c4 = st.columns(4)
                top_c1.markdown(f"**Category:** {email['category']}")
                top_c2.markdown(f"**Urgency:** {get_urgency_badge(email['urgency'])}", unsafe_allow_html=True)
                top_c3.markdown(f"**Assigned Team:** {email['team']}")
                top_c4.markdown(f"**Status:** {get_status_badge(email['status'])}", unsafe_allow_html=True)

                if email.get("risk_flag") == 1:
                    st.error(f"⚠️ **Risk Flag Detected:** {email.get('risk_reason', 'Customer risk identified')}")

                st.markdown("**Email Body:**")
                st.info(email["body"])

                # Status management
                b_c1, b_c2, b_c3 = st.columns([2, 2, 4])
                with b_c1:
                    if email["status"] != "ARCHIVED":
                        if st.button("Archive Ticket", key=f"arch_{email['id']}"):
                            update_email_status(email["id"], "ARCHIVED", db_path=DEFAULT_DB_PATH)
                            st.success("Ticket archived.")
                            st.rerun()
                with b_c2:
                    if email["status"] == "ARCHIVED":
                        if st.button("Unarchive Ticket", key=f"unarch_{email['id']}"):
                            update_email_status(email["id"], "NEW", db_path=DEFAULT_DB_PATH)
                            st.success("Ticket unarchived.")
                            st.rerun()
                with b_c3:
                    st.caption(f"Received at: {email['created_at']}")


# =============================================================================
# PAGE 3: ANALYZE EMAIL
# =============================================================================
elif menu == "🔍 Analyze Email":
    st.header("🔍 Real-time Email Intake & Diagnostic Lab")
    st.markdown("Manually input an email to test local ML classification, urgency scoring, risk detection, and response synthesis.")

    with st.form("manual_intake_form"):
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            inp_sender = st.text_input("Customer Email Address", "customer@example.com")
        with col_s2:
            inp_subject = st.text_input("Subject Line", "Urgent: System crash on launch with 500 server error")

        inp_body = st.text_area(
            "Email Message Body",
            "Whenever I attempt to launch the application today, the screen freezes and returns HTTP 500 error. "
            "Our whole team is blocked from working and we have an immediate client deadline today! ASAP!",
            height=130,
        )

        submitted = st.form_submit_button("🧪 Run Diagnostic Analysis & Draft Synthesis")

    if submitted:
        if not inp_sender or "@" not in inp_sender:
            st.error("Please provide a valid sender email address.")
        elif not inp_subject.strip():
            st.error("Please enter a subject line.")
        elif not inp_body.strip():
            st.error("Please enter the email body.")
        else:
            with st.spinner("Processing through machine learning pipeline..."):
                # Classification
                class_res = classify_support_email(inp_subject, inp_body)
                # Urgency
                urg_res = detect_urgency(inp_subject, inp_body)
                # Risk
                risk_res = detect_risk(inp_subject, inp_body)
                # Team Assignment
                team_res = assign_support_team(
                    class_res["category"],
                    urgency=urg_res["urgency"],
                    risk_flag=risk_res["risk_flag"],
                )
                # Knowledge Base match
                kb_matches = find_relevant_articles(
                    f"{inp_subject} {inp_body}",
                    category=class_res["category"],
                    top_k=2,
                    approved_only=True,
                    db_path=DEFAULT_DB_PATH,
                )
                # Draft Generation
                draft_res = generate_support_draft(
                    sender=inp_sender,
                    subject=inp_subject,
                    body=inp_body,
                    category=class_res["category"],
                    urgency=urg_res["urgency"],
                    team=team_res["team"],
                    risk_flag=risk_res["risk_flag"],
                    risk_reason=risk_res["risk_reason"],
                    kb_articles=kb_matches,
                    db_path=DEFAULT_DB_PATH,
                )

            st.success("Analysis complete!")
            st.subheader("Diagnostic Results")

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Predicted Category", class_res["category"], f"Confidence: {int(class_res['confidence']*100)}%")
            r2.metric("Urgency Assessment", urg_res["urgency"], f"Score: {urg_res['score']}/100")
            r3.metric("Assigned Team", team_res["team"], f"SLA: {team_res['sla_hours']} hrs")
            r4.metric("Risk Level", risk_res["severity"], f"Score: {risk_res['risk_score']}/100")

            if risk_res["risk_flag"] == 1:
                st.error(f"🚨 **High Risk Alert:** {risk_res['risk_reason']}. Action: {risk_res['recommended_action']}")

            # Matched Knowledge Base
            st.markdown("#### Matched Knowledge Base Guidance")
            if kb_matches:
                for km in kb_matches:
                    st.write(f"- **{km['title']}** (Relevance: `{km['relevance_score']:.2f}`) — *Category: {km['category']}*")
            else:
                st.caption("No direct KB article matched above similarity threshold; using graceful fallback template.")

            # Draft Response Preview
            st.markdown("#### Synthesized Response Draft")
            st.text_area("Draft Preview", draft_res["draft_body"], height=220, disabled=True)

            # Option to commit directly to SQLite database
            if st.button("💾 Save Ticket & Draft to Database"):
                try:
                    res = process_and_save_email(
                        sender=inp_sender,
                        subject=inp_subject,
                        body=inp_body,
                        auto_generate_draft=True,
                        db_path=DEFAULT_DB_PATH,
                    )
                    st.success(f"Ticket #{res['email_id']} and Draft #{res['draft_id']} saved to database successfully!")
                except Exception as ex:
                    st.error(f"Error saving to database: {ex}")


# =============================================================================
# PAGE 4: DRAFT RESPONSES (HUMAN IN THE LOOP)
# =============================================================================
elif menu == "✍️ Draft Responses":
    st.header("✍️ Draft Responses & Human Approval Station")
    st.markdown(
        "Review AI-synthesized responses before dispatch. "
        "Strict Policy: All drafts require explicit human approval. "
        "Editing an approved draft resets its status back to Pending Approval."
    )

    filter_status = st.selectbox(
        "Filter Drafts by Status",
        ["PENDING_APPROVAL", "APPROVED", "REJECTED", "SENT", "All"],
        index=0,
    )
    query_status = None if filter_status == "All" else filter_status

    drafts = get_all_drafts(status=query_status, db_path=DEFAULT_DB_PATH)

    if not drafts:
        st.info(f"No drafts currently in '{filter_status}' status.")
    else:
        st.write(f"**Found {len(drafts)} drafts:**")

        for draft in drafts:
            with st.container():
                st.markdown("---")
                d_head1, d_head2, d_head3 = st.columns([5, 3, 2])
                with d_head1:
                    st.markdown(f"### Draft #{draft['id']} (Ticket #{draft['email_id']})")
                    st.markdown(f"**To:** {draft.get('sender')} | **Subject:** {draft.get('subject')}")
                with d_head2:
                    st.markdown(f"**Category:** {draft.get('category')} | **Team:** {draft.get('team')}")
                    st.markdown(f"**Urgency:** {get_urgency_badge(draft.get('urgency', 'Low'))}", unsafe_allow_html=True)
                with d_head3:
                    st.markdown(f"**Status:** {get_status_badge(draft['status'])}", unsafe_allow_html=True)
                    if draft.get("approved_by"):
                        st.caption(f"Approved by: {draft['approved_by']}")
                    if draft.get("sent_at"):
                        st.caption(f"Sent at: {draft['sent_at']}")

                if draft.get("risk_flag") == 1:
                    st.warning("⚠️ Notice: This ticket triggered an elevated risk signal. Ensure tone is professional and empathetic.")

                # Editable draft text area
                draft_content = st.text_area(
                    "Draft Content (Review & Edit)",
                    value=draft["draft_body"],
                    height=200,
                    key=f"body_{draft['id']}",
                    disabled=(draft["status"] == "SENT"),
                )

                # Reviewer name input
                col_rev, col_act1, col_act2, col_act3, col_act4 = st.columns([2, 1.5, 1.5, 1.5, 2])
                with col_rev:
                    reviewer = st.text_input("Reviewer Name", "Agent Viraj", key=f"rev_{draft['id']}")

                # Action 1: Save Edits
                with col_act1:
                    if draft["status"] != "SENT":
                        if st.button("💾 Save Edits", key=f"save_{draft['id']}"):
                            edit_res = edit_draft_content(
                                draft_id=draft["id"],
                                new_body=draft_content,
                                editor_name=reviewer,
                                db_path=DEFAULT_DB_PATH,
                            )
                            if edit_res["success"]:
                                st.success("Draft updated. Status reset to PENDING_APPROVAL.")
                                st.rerun()
                            else:
                                st.error(edit_res.get("error", "Update failed."))

                # Action 2: Approve
                with col_act2:
                    if draft["status"] != "SENT":
                        if st.button("✅ Approve", key=f"app_{draft['id']}"):
                            app_res = approve_draft(
                                draft_id=draft["id"],
                                reviewer_name=reviewer,
                                db_path=DEFAULT_DB_PATH,
                            )
                            if app_res["success"]:
                                st.success(f"Draft #{draft['id']} approved.")
                                st.rerun()
                            else:
                                st.error(app_res.get("error", "Approval failed."))

                # Action 3: Reject
                with col_act3:
                    if draft["status"] != "SENT":
                        if st.button("❌ Reject", key=f"rej_{draft['id']}"):
                            rej_res = reject_draft(
                                draft_id=draft["id"],
                                reviewer_name=reviewer,
                                reason="Human reviewer rejected draft",
                                db_path=DEFAULT_DB_PATH,
                            )
                            if rej_res["success"]:
                                st.warning(f"Draft #{draft['id']} rejected.")
                                st.rerun()
                            else:
                                st.error(rej_res.get("error", "Rejection failed."))

                # Action 4: Simulate Send
                with col_act4:
                    can_send, reason = can_send_draft(draft["id"], db_path=DEFAULT_DB_PATH)
                    if draft["status"] == "APPROVED":
                        if st.button("🚀 Simulate Send", key=f"send_{draft['id']}", type="primary"):
                            send_res = simulate_send_draft(
                                draft_id=draft["id"],
                                sender_identity=reviewer,
                                db_path=DEFAULT_DB_PATH,
                            )
                            if send_res["success"]:
                                st.balloons()
                                st.success(f"Dispatched! Receipt generated for {send_res['dispatch_receipt']['recipient']}.")
                                st.rerun()
                            else:
                                st.error(send_res.get("error", "Failed to send."))
                    elif draft["status"] == "SENT":
                        st.info("✅ Already Sent")
                    else:
                        st.caption(f"🔒 Send Locked ({reason})")


# =============================================================================
# PAGE 5: KNOWLEDGE BASE
# =============================================================================
elif menu == "📚 Knowledge Base":
    st.header("📚 Knowledge Base Management")
    st.markdown("Maintain authoritative troubleshooting guidance used to synthesize customer draft responses.")

    kb_tab1, kb_tab2 = st.tabs(["📖 Article Directory", "➕ Add New Article"])

    with kb_tab1:
        c_k1, c_k2, c_k3 = st.columns([2, 2, 4])
        with c_k1:
            kb_cat_filter = st.selectbox("Filter Category", ["All"] + CATEGORIES, key="kb_cat")
        with c_k2:
            kb_status_filter = st.selectbox("Approval Status", ["All", "Approved Only", "Unapproved Only"])
        with c_k3:
            kb_search = st.text_input("Search Knowledge Base", "", key="kb_search_txt")

        # Query articles
        cat_arg = None if kb_cat_filter == "All" else kb_cat_filter
        app_arg = True if kb_status_filter == "Approved Only" else False
        search_arg = kb_search.strip() if kb_search.strip() else None

        kb_articles = get_all_kb_articles(
            approved_only=app_arg,
            category=cat_arg,
            search_query=search_arg,
            db_path=DEFAULT_DB_PATH,
        )

        if kb_status_filter == "Unapproved Only":
            kb_articles = [a for a in kb_articles if a["is_approved"] == 0]

        st.markdown(f"**Total Articles: {len(kb_articles)}**")

        for art in kb_articles:
            status_text = "Approved" if art["is_approved"] == 1 else "Unapproved"
            with st.expander(f"KB #{art['id']}: {art['title']} [{art['category']}] ({status_text})"):
                st.markdown(f"**Tags:** `{art.get('tags', '')}`")
                st.markdown(f"**Content:**\n\n{art['content']}")

                col_t1, col_t2 = st.columns([2, 6])
                with col_t1:
                    new_approval = 0 if art["is_approved"] == 1 else 1
                    toggle_label = "Revoke Approval" if art["is_approved"] == 1 else "Approve Article"
                    if st.button(toggle_label, key=f"togg_{art['id']}"):
                        update_kb_article(
                            art["id"],
                            art["title"],
                            art["category"],
                            art["content"],
                            art["tags"],
                            new_approval,
                            db_path=DEFAULT_DB_PATH,
                        )
                        st.success("Approval status updated.")
                        st.rerun()
                with col_t2:
                    if st.button("Delete Article", key=f"del_{art['id']}"):
                        delete_kb_article(art["id"], db_path=DEFAULT_DB_PATH)
                        st.warning("Article deleted.")
                        st.rerun()

    with kb_tab2:
        st.subheader("Create a New Knowledge Base Article")
        with st.form("new_kb_form"):
            new_title = st.text_input("Article Title")
            new_category = st.selectbox("Category", CATEGORIES)
            new_tags = st.text_input("Search Tags (comma-separated)", "troubleshooting, fix, guide")
            new_content = st.text_area("Resolution Steps & Guidance Content", height=150)
            new_is_approved = st.checkbox("Mark as Approved immediately", value=True)

            kb_submitted = st.form_submit_button("Create Article")

        if kb_submitted:
            if not new_title.strip() or not new_content.strip():
                st.error("Title and Content are required fields.")
            else:
                art_id = insert_kb_article(
                    {
                        "title": new_title.strip(),
                        "category": new_category,
                        "tags": new_tags.strip(),
                        "content": new_content.strip(),
                        "is_approved": 1 if new_is_approved else 0,
                    },
                    db_path=DEFAULT_DB_PATH,
                )
                st.success(f"Article #{art_id} '{new_title}' successfully added!")
                st.rerun()


# =============================================================================
# PAGE 6: REPORTS & CSV IMPORT
# =============================================================================
elif menu == "📈 Reports & CSV Import":
    st.header("📈 Operational Reports & Batch CSV Intake")
    st.markdown("Export operational data, inspect SLA response times, and upload batch CSV email tickets.")

    tab_rep1, tab_rep2 = st.tabs(["📊 Analytics & Data Export", "📥 CSV Batch Intake"])

    with tab_rep1:
        st.subheader("Support Operational Performance")
        emails = get_all_emails(db_path=DEFAULT_DB_PATH)

        if not emails:
            st.info("No data available to generate reports.")
        else:
            df = pd.DataFrame(emails)

            col_sla1, col_sla2, col_sla3 = st.columns(3)
            # Calculated metrics
            total = len(df)
            replied = len(df[df["status"] == "REPLIED"])
            resolution_rate = round((replied / total) * 100, 1) if total > 0 else 0
            risk_rate = round((len(df[df["risk_flag"] == 1]) / total) * 100, 1) if total > 0 else 0

            col_sla1.metric("Total Ingested Tickets", total)
            col_sla2.metric("Replied Resolution Rate", f"{resolution_rate}%")
            col_sla3.metric("Customer Risk Rate", f"{risk_rate}%")

            st.markdown("---")
            st.subheader("Export System Tables")

            e_col1, e_col2 = st.columns(2)
            with e_col1:
                # Export Emails
                csv_emails = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Download Ingested Emails (CSV)",
                    data=csv_emails,
                    file_name="support_emails_export.csv",
                    mime="text/csv",
                )

            with e_col2:
                # Export Drafts
                drafts = get_all_drafts(db_path=DEFAULT_DB_PATH)
                if drafts:
                    df_drafts = pd.DataFrame(drafts)
                    csv_drafts = df_drafts.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download Response Drafts (CSV)",
                        data=csv_drafts,
                        file_name="support_drafts_export.csv",
                        mime="text/csv",
                    )

    with tab_rep2:
        st.subheader("Batch CSV Ingestion Pipeline")
        st.markdown(
            "Upload a CSV file containing `sender`, `subject`, and `body` columns. "
            "Each row will be automatically classified, urgency-scored, risk-checked, and assigned to a team, "
            "with a draft response synthesized in SQLite."
        )

        uploaded_file = st.file_uploader("Upload Support Emails CSV", type=["csv"])

        if uploaded_file is not None:
            if st.button("🚀 Process & Ingest CSV Tickets"):
                with st.spinner("Ingesting and analyzing batch emails..."):
                    result = import_emails_from_csv(uploaded_file, db_path=DEFAULT_DB_PATH)

                st.success(f"Processing Complete! Successfully imported **{result['imported_count']}** tickets.")
                if result["skipped_count"] > 0:
                    st.warning(f"Skipped {result['skipped_count']} invalid or blank rows.")
                    with st.expander("Inspection Errors"):
                        for err in result["errors"]:
                            st.write(f"- {err}")
                st.rerun()

        st.markdown("---")
        st.subheader("Load Built-in Sample Dataset")
        st.caption("Instantly populate the system with 15 pre-configured customer tickets.")
        if st.button("📥 Load Built-in sample_emails.csv"):
            sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_emails.csv")
            if os.path.exists(sample_path):
                res = import_emails_from_csv(sample_path, db_path=DEFAULT_DB_PATH)
                st.success(f"Loaded {res['imported_count']} sample tickets into database!")
                st.rerun()
            else:
                st.error("Sample CSV file not found in data/ directory.")
