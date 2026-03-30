#!/usr/bin/env python3
"""
PG: RO-ED AI Agent
Myanmar PDF Data Extraction Pipeline
Streamlit Web Interface with shadcn-ui Components
Version 5.0
"""

import streamlit as st
import streamlit_shadcn_ui as ui
from pathlib import Path
import time
from datetime import datetime
from math import ceil
import uuid
import json
import pandas as pd
from io import BytesIO
import fitz
import plotly.graph_objects as go
import plotly.express as px

# Backend imports
import database
import config
import step1_analyze_metadata
import step2_extract_text_pages
import step3_ocr_image_pages
import step4_claude_structured_extraction
import step1b_filter_agent
import step4b_self_review
import step5_cross_validate
import step6_accuracy_matrix
import step7_create_final_excel
import agent_decision_gate

# =============================================================================
# CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="RO-ED AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Theme
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    :root {
        --brand-primary: #2563eb;
        --brand-accent: #3b82f6;
        --brand-success: #10b981;
        --brand-surface: #f8fafc;
        --brand-border: #e2e8f0;
    }

    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    [data-testid="stMetricValue"] { font-weight: 700; }

    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 { color: #ffffff !important; }

    .streamlit-expanderHeader { font-weight: 600; font-size: 1rem; }

    [data-testid="stFileUploader"] {
        border: 2px dashed var(--brand-border);
        border-radius: 12px;
        padding: 1rem;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        border: none; border-radius: 8px; font-weight: 600; transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }

    .stDownloadButton > button { border-radius: 8px; font-weight: 500; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Secondary button (Reset / New Session) — red outline */
    .stButton > button[kind="secondary"] {
        background: transparent;
        color: #dc2626;
        border: 2px solid #dc2626;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #dc2626;
        color: white;
    }

    /* Terminal log styling */
    .terminal-log {
        background: #0f172a;
        color: #22d3ee;
        font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
        font-size: 0.78rem;
        padding: 1rem;
        border-radius: 8px;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        line-height: 1.5;
        border: 1px solid #1e293b;
    }
    .terminal-log .step-header {
        color: #a78bfa;
        font-weight: bold;
    }
    .terminal-log .step-done {
        color: #4ade80;
    }
    .terminal-log .step-cost {
        color: #fbbf24;
    }
    .terminal-log .step-detail {
        color: #94a3b8;
    }
    /* Login page styling */
    .login-container {
        max-width: 420px;
        margin: 80px auto;
        padding: 2.5rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
        border: 1px solid var(--brand-border);
    }
    .login-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .login-header h2 {
        color: #1e293b;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .login-header p {
        color: #64748b;
        font-size: 0.9rem;
    }
    .user-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .user-badge.admin { background: #fee2e2; color: #dc2626 !important; }
    .user-badge.user { background: #dbeafe; color: #2563eb !important; }

    /* Compact sidebar metric cards */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        margin-bottom: -12px;
    }
    [data-testid="stSidebar"] iframe {
        height: 60px !important;
        min-height: 60px !important;
    }
    .sidebar-user-info {
        background: rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 4px;
    }
    .sidebar-user-info .name {
        color: #ffffff !important;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .sidebar-user-info .role-label {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-left: 6px;
    }
    .sidebar-user-info .role-admin { background: #f87171; color: #fff !important; }
    .sidebar-user-info .role-user { background: #60a5fa; color: #fff !important; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# AUTHENTICATION
# =============================================================================

# Session timeout (seconds)
SESSION_TIMEOUT = 3600  # 1 hour
AUTH_SESSION_FILE = config.RESULTS_DIR / '_auth_session.json'

import html as _html

def _save_auth_to_disk(user, remember_me=False):
    """Persist auth session to disk so it survives refresh."""
    session_data = {
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'display_name': user.get('display_name', ''),
        'remember_me': remember_me,
        'login_time': time.time(),
    }
    with open(AUTH_SESSION_FILE, 'w') as f:
        json.dump(session_data, f)

def _load_auth_from_disk():
    """Restore auth session from disk after refresh."""
    if not AUTH_SESSION_FILE.exists():
        return None
    try:
        with open(AUTH_SESSION_FILE, 'r') as f:
            data = json.load(f)
        # Check timeout
        elapsed = time.time() - data.get('login_time', 0)
        if elapsed > SESSION_TIMEOUT and not data.get('remember_me'):
            AUTH_SESSION_FILE.unlink()
            return None
        return data
    except Exception:
        return None

def _clear_auth_from_disk():
    """Remove persisted auth session."""
    if AUTH_SESSION_FILE.exists():
        AUTH_SESSION_FILE.unlink()

# Init auth state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'remember_me' not in st.session_state:
    st.session_state.remember_me = False
if 'login_time' not in st.session_state:
    st.session_state.login_time = None

database.init_database()

# Restore auth from disk if session_state lost (browser refresh)
if not st.session_state.authenticated:
    saved_auth = _load_auth_from_disk()
    if saved_auth:
        # Verify user still exists and is active in DB
        all_users = database.get_all_users()
        valid_user = next(
            (u for u in all_users
             if u['id'] == saved_auth['user_id'] and u['is_active']),
            None
        )
        if valid_user:
            st.session_state.authenticated = True
            st.session_state.user = {
                'id': valid_user['id'],
                'username': valid_user['username'],
                'role': valid_user['role'],
                'display_name': valid_user.get('display_name', ''),
            }
            st.session_state.remember_me = saved_auth.get('remember_me', False)
            st.session_state.login_time = saved_auth.get('login_time', time.time())
        else:
            # User deleted or disabled — clear stale session
            _clear_auth_from_disk()

# Session timeout check (for already-authenticated sessions)
if st.session_state.authenticated and st.session_state.login_time:
    elapsed = time.time() - st.session_state.login_time
    if elapsed > SESSION_TIMEOUT and not st.session_state.remember_me:
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.login_time = None
        _clear_auth_from_disk()

def render_login_page():
    """Render the login page."""
    # Hide sidebar on login
    st.markdown("<style>[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div class="login-header" style="text-align:center; margin-top:60px;">
        <h2 style="font-size:2rem;">RO-ED AI Agent</h2>
        <p style="color:#64748b;">Myanmar Import PDF Data Extraction Pipeline</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("#### Sign In")

        username = st.text_input("Username", key="login_username", placeholder="Enter username")

        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
            placeholder="Enter password"
        )

        remember = st.checkbox("Remember me", key="login_remember")

        if st.button("Sign In", type="primary", use_container_width=True):
            if username and password:
                user = database.authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.session_state.remember_me = remember
                    st.session_state.login_time = time.time()
                    _save_auth_to_disk(user, remember)
                    database.log_activity(user['id'], user['username'], "LOGIN", "Signed in")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter username and password")

        st.markdown("---")
        st.caption("Contact your administrator for credentials")
        st.caption("Created by City AI Team")


def _render_activity_log():
    """Render the Activity Log view for admins."""
    st.subheader("Activity Log")
    st.caption("Track who did what across the system")

    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        users_list = database.get_all_users()
        user_options = ["All Users"] + [u['username'] for u in users_list]
        log_user_filter = st.selectbox("Filter by user", options=user_options, key="log_user_filter")
    with f2:
        action_logs = database.get_activity_logs(limit=500)
        action_types = sorted(set(l['action'] for l in action_logs)) if action_logs else []
        log_action_filter = st.selectbox("Filter by action", options=["All Actions"] + action_types, key="log_action_filter")
    with f3:
        log_date_range = st.date_input("Filter by date", value=[], key="log_date_range")

    # Fetch logs
    filter_uid = None
    if log_user_filter != "All Users":
        match = [u for u in users_list if u['username'] == log_user_filter]
        if match:
            filter_uid = match[0]['id']

    logs = database.get_activity_logs(limit=500, user_id=filter_uid)

    # Apply action filter
    if log_action_filter != "All Actions":
        logs = [l for l in logs if l['action'] == log_action_filter]

    # Apply date filter
    if log_date_range and len(log_date_range) == 2:
        d_start, d_end = str(log_date_range[0]), str(log_date_range[1])
        logs = [l for l in logs if d_start <= (l.get('created_at') or '')[:10] <= d_end]

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        ui.metric_card(title="Total Events", content=str(len(logs)), key="log_total")
    with col2:
        login_count = sum(1 for l in logs if l['action'] == 'LOGIN')
        ui.metric_card(title="Logins", content=str(login_count), key="log_logins")
    with col3:
        job_count = sum(1 for l in logs if l['action'] == 'RUN_JOB')
        ui.metric_card(title="Jobs Run", content=str(job_count), key="log_jobs")

    st.markdown("---")

    if logs:
        # Action icon mapping
        action_icons = {
            'LOGIN': '🔑', 'LOGOUT': '🚪', 'RUN_JOB': '⚡',
            'DOWNLOAD': '📥', 'DELETE_JOB': '🗑️', 'CREATE_USER': '👤',
            'UPDATE_USER': '✏️', 'DELETE_USER': '❌',
        }

        logs_df = pd.DataFrame([{
            "": action_icons.get(l['action'], '📋'),
            "Time": (l.get('created_at') or '')[:19],
            "User": l.get('username', 'N/A'),
            "Action": l.get('action', ''),
            "Detail": (l.get('detail') or '')[:80],
        } for l in logs])
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(logs)} events")
    else:
        st.info("No activity logged yet")


def render_admin_user_management():
    """Render the User Management tab for admins — users + activity log."""
    st.header("User Management")

    um_section = ui.tabs(
        options=["Users", "Activity Log"],
        default_value="Users",
        key="um_tabs"
    )

    if um_section == "Activity Log":
        _render_activity_log()
        return

    users = database.get_all_users()

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        ui.metric_card(title="Total Users", content=str(len(users)), key="um_total")
    with col2:
        admins = sum(1 for u in users if u['role'] == 'admin')
        ui.metric_card(title="Admins", content=str(admins), key="um_admins")
    with col3:
        active = sum(1 for u in users if u['is_active'])
        ui.metric_card(title="Active", content=str(active), key="um_active")

    st.markdown("---")

    # Create new user form
    st.subheader("Create New User")
    with st.form("create_user_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            new_username = st.text_input("Username", placeholder="e.g. john.doe")
            new_display = st.text_input("Display Name", placeholder="e.g. John Doe")
        with fc2:
            new_password = st.text_input("Password", type="password", placeholder="Min 4 characters")
            new_role = st.selectbox("Role", options=["user", "admin"])

        submitted = st.form_submit_button("Create User", type="primary", use_container_width=True)
        if submitted:
            import re as _re
            if not new_username or not new_password:
                st.error("Username and password are required")
            elif not _re.match(r'^[a-zA-Z0-9._-]{3,32}$', new_username):
                st.error("Username must be 3-32 characters (letters, numbers, . _ - only)")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                success = database.create_user(new_username, new_password, new_display or new_username, new_role)
                if success:
                    database.log_activity(
                        st.session_state.user['id'], st.session_state.user['username'],
                        "CREATE_USER", f"Created {new_role} user: {new_username}"
                    )
                    st.success(f"User **{new_username}** created as **{new_role}**")
                    st.rerun()
                else:
                    st.error(f"Username **{new_username}** already exists")

    st.markdown("---")

    # Users table
    st.subheader("All Users")

    if users:
        users_df = pd.DataFrame([{
            "Username": u['username'],
            "Display Name": u['display_name'] or u['username'],
            "Role": u['role'].upper(),
            "Active": "Yes" if u['is_active'] else "No",
            "Created": (u.get('created_at') or '')[:19],
            "Last Login": (u.get('last_login') or 'Never')[:19],
        } for u in users])
        st.dataframe(users_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Edit/delete users
    st.subheader("Manage User")

    user_options = [f"{u['username']} ({u['role']})" for u in users]
    selected_user_label = st.selectbox("Select user", options=user_options, key="manage_user_select")

    if selected_user_label:
        sel_idx = user_options.index(selected_user_label)
        sel_user = users[sel_idx]

        ec1, ec2 = st.columns(2)
        with ec1:
            edit_display = st.text_input("Display Name", value=sel_user['display_name'] or '', key="edit_display")
            edit_role = st.selectbox("Role", options=["user", "admin"],
                                     index=0 if sel_user['role'] == 'user' else 1, key="edit_role")
        with ec2:
            edit_active = st.selectbox("Status", options=["Active", "Disabled"],
                                        index=0 if sel_user['is_active'] else 1, key="edit_active")
            edit_password = st.text_input("New Password (leave blank to keep)", type="password", key="edit_password")

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("Save Changes", type="primary", use_container_width=True):
                database.update_user(
                    sel_user['id'],
                    display_name=edit_display if edit_display else None,
                    role=edit_role,
                    is_active=1 if edit_active == "Active" else 0,
                    password=edit_password if edit_password else None
                )
                database.log_activity(
                    st.session_state.user['id'], st.session_state.user['username'],
                    "UPDATE_USER", f"Updated user: {sel_user['username']} (role={edit_role}, active={edit_active})"
                )
                st.success(f"User **{sel_user['username']}** updated")
                st.rerun()
        with bc2:
            # Don't allow deleting yourself or the last admin
            is_self = sel_user['username'] == st.session_state.user['username']
            is_last_admin = sel_user['role'] == 'admin' and sum(1 for u in users if u['role'] == 'admin') <= 1

            if is_self:
                st.button("Delete User", disabled=True, use_container_width=True, key="del_user_btn")
                st.caption("Cannot delete yourself")
            elif is_last_admin:
                st.button("Delete User", disabled=True, use_container_width=True, key="del_user_btn")
                st.caption("Cannot delete last admin")
            else:
                if st.button("Delete User", type="secondary", use_container_width=True, key="del_user_btn"):
                    database.delete_user(sel_user['id'])
                    database.log_activity(
                        st.session_state.user['id'], st.session_state.user['username'],
                        "DELETE_USER", f"Deleted user: {sel_user['username']}"
                    )
                    st.success(f"User **{sel_user['username']}** deleted")
                    st.rerun()


# Check authentication — show login or app
if not st.session_state.authenticated:
    render_login_page()
    st.stop()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _format_excel_sheet(workbook, worksheet, df):
    """Apply header formatting and auto-size columns to a worksheet."""
    header_format = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        column_len = max(df[value].astype(str).str.len().max(), len(value)) + 2
        worksheet.set_column(col_num, col_num, min(column_len, 50))

def to_excel(df):
    """Convert single DataFrame to formatted Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
        _format_excel_sheet(writer.book, writer.sheets['Data'], df)
    return output.getvalue()

def to_excel_2sheet(items_df, decl_df):
    """Convert items + declaration DataFrames into a single 2-sheet Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if items_df is not None and not items_df.empty:
            items_df.to_excel(writer, index=False, sheet_name='Product Items')
            _format_excel_sheet(writer.book, writer.sheets['Product Items'], items_df)
        if decl_df is not None and not decl_df.empty:
            decl_df.to_excel(writer, index=False, sheet_name='Declaration')
            _format_excel_sheet(writer.book, writer.sheets['Declaration'], decl_df)
    return output.getvalue()

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return path"""
    timestamp = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{uploaded_file.name}"
    filepath = config.UPLOAD_FOLDER / filename
    with open(filepath, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return filepath

def verify_pdf(pdf_path):
    """Verify PDF file and return page count"""
    try:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        return page_count, None
    except Exception as e:
        return 0, str(e)

LAST_SESSION_FILE = config.RESULTS_DIR / '_last_session.json'

def save_session_to_disk(job_data):
    """Persist job results to disk so they survive browser refresh."""
    with open(LAST_SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False, default=str)

def load_session_from_disk():
    """Load last job results from disk if available."""
    if LAST_SESSION_FILE.exists():
        try:
            with open(LAST_SESSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def clear_session_from_disk():
    """Remove persisted session file."""
    if LAST_SESSION_FILE.exists():
        LAST_SESSION_FILE.unlink()

def render_export_buttons(df, base_filename):
    """Render CSV and Excel download buttons"""
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download CSV", data=csv,
            file_name=f"{base_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", use_container_width=True, type="primary")
    with col2:
        excel_data = to_excel(df)
        st.download_button(label="Download Excel", data=excel_data,
            file_name=f"{base_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, type="primary")

def render_status_badge(status):
    if status == "COMPLETED":
        return ("COMPLETED", "default")
    elif status == "PENDING":
        return ("PENDING", "secondary")
    else:
        return (status, "destructive")

def render_terminal_logs(log_lines):
    """Render pipeline logs in a terminal-style dark box."""
    html_lines = []
    for line in log_lines:
        if line.startswith("[STEP"):
            html_lines.append(f'<span class="step-header">{line}</span>')
        elif "DONE" in line or "Complete" in line:
            html_lines.append(f'<span class="step-done">{line}</span>')
        elif "$" in line:
            html_lines.append(f'<span class="step-cost">{line}</span>')
        else:
            html_lines.append(f'<span class="step-detail">{line}</span>')
    html = "\n".join(html_lines)
    st.markdown(f'<div class="terminal-log">{html}</div>', unsafe_allow_html=True)

def _find_pdf_file(pdf_path, pdf_name=None):
    """Find the actual PDF file — try direct path first, then search uploads folder."""
    if pdf_path:
        p = Path(pdf_path)
        if p.is_file():
            return p
    # Fallback: search uploads folder by pdf_name
    if pdf_name:
        uploads = config.UPLOAD_FOLDER
        if uploads.exists():
            matches = list(uploads.glob(f"*{pdf_name}*")) if pdf_name else []
            if not matches:
                # pdf_name might include the hash prefix already
                matches = [f for f in uploads.iterdir() if pdf_name in f.name]
            if matches:
                return matches[-1]  # most recent
    return None

def render_pdf_preview(pdf_path, total_pages=0, text_pages_list=None, image_pages_list=None, prefix="pdf", pdf_name=None):
    """Render PDF first-page thumbnail, page type heatmap, and download button."""
    pdf_file = _find_pdf_file(pdf_path, pdf_name)

    if not pdf_file:
        st.caption("PDF file not available for preview")
        return

    preview_col, info_col = st.columns([1, 2])

    with preview_col:
        # Render first page as image
        try:
            doc = fitz.open(str(pdf_file))
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_bytes = pix.tobytes("png")
            doc.close()
            st.image(img_bytes, caption="Page 1 Preview", use_container_width=True)
        except Exception:
            st.caption("Could not render preview")

        # Download original PDF
        with open(pdf_file, 'rb') as f:
            st.download_button(
                label="Download Original PDF",
                data=f,
                file_name=pdf_file.name,
                mime="application/pdf",
                use_container_width=True,
                key=f"{prefix}_dl_pdf"
            )

    with info_col:
        # Page type heatmap
        if total_pages > 0:
            st.markdown("**Page Classification Map**")
            text_set = set(text_pages_list or [])
            image_set = set(image_pages_list or [])

            heatmap_html = '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px;">'
            for pg in range(1, total_pages + 1):
                if pg in text_set:
                    color = "#22c55e"  # green
                    label = "T"
                    tip = f"Page {pg}: TEXT"
                elif pg in image_set:
                    color = "#f59e0b"  # amber
                    label = "I"
                    tip = f"Page {pg}: IMAGE"
                else:
                    color = "#6b7280"  # gray
                    label = "?"
                    tip = f"Page {pg}: UNKNOWN"
                heatmap_html += f'<div title="{tip}" style="width:36px;height:36px;background:{color};color:white;display:flex;align-items:center;justify-content:center;border-radius:6px;font-size:12px;font-weight:700;font-family:monospace;cursor:default;">{label}{pg}</div>'
            heatmap_html += '</div>'

            heatmap_html += '<div style="display:flex;gap:12px;margin-top:4px;font-size:12px;color:#64748b;">'
            heatmap_html += f'<span style="color:#22c55e;">■ TEXT ({len(text_set)})</span>'
            heatmap_html += f'<span style="color:#f59e0b;">■ IMAGE ({len(image_set)})</span>'
            heatmap_html += '</div>'

            st.markdown(heatmap_html, unsafe_allow_html=True)

            # Pipeline step timeline
            st.markdown("**Processing Pipeline**")
            steps = [
                ("Classify", "#6366f1"),
                ("Text Extract", "#22c55e"),
                ("OCR", "#f59e0b"),
                ("AI Extract", "#3b82f6"),
                ("Validate", "#8b5cf6"),
                ("Accuracy", "#06b6d4"),
                ("Excel", "#10b981"),
            ]
            timeline_html = '<div style="display:flex;gap:2px;margin-bottom:4px;">'
            for i, (name, color) in enumerate(steps):
                timeline_html += f'<div style="flex:1;background:{color};color:white;text-align:center;padding:4px 2px;font-size:10px;font-weight:600;border-radius:{"6px 0 0 6px" if i==0 else "0 6px 6px 0" if i==6 else "0"};">{i+1}</div>'
            timeline_html += '</div>'
            timeline_html += '<div style="display:flex;gap:2px;font-size:9px;color:#64748b;">'
            for name, _ in steps:
                timeline_html += f'<div style="flex:1;text-align:center;">{name}</div>'
            timeline_html += '</div>'
            st.markdown(timeline_html, unsafe_allow_html=True)


def _table_with_download(df, title, description, csv_name, prefix):
    """Render a table section with header info and inline download buttons."""
    hdr_col, dl_col1, dl_col2 = st.columns([4, 1, 1])
    with hdr_col:
        st.markdown(f"**{title}**")
        st.caption(description)
    with dl_col1:
        st.download_button(
            label="CSV", data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"{csv_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", use_container_width=True, key=f"{prefix}_csv"
        )
    with dl_col2:
        st.download_button(
            label="Excel", data=to_excel(df),
            file_name=f"{csv_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, key=f"{prefix}_xlsx"
        )
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={col: st.column_config.TextColumn(col, width="medium") for col in df.columns}
    )


def render_job_results(job_data, prefix="saved"):
    """Render completed job results with all enhancements."""

    decl = job_data.get('declaration', {})
    decl_fields = sum(1 for v in decl.values() if v is not None and str(v).strip()) if decl else 0
    items = job_data.get('items', [])

    # ══════════════════════════════════════════════════════════════
    # SECTION 1: KPI Cards (matching History style)
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")

    # Row 1: Document KPIs (same as History job expander)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        ui.metric_card(title="Pages", content=str(job_data['total_pages']), key=f"{prefix}_pg")
    with c2:
        ui.metric_card(title="Text / Image", content=f"{job_data['text_pages']} / {job_data['image_pages']}", key=f"{prefix}_ti")
    with c3:
        ui.metric_card(title="Time", content=f"{job_data['processing_time']:.1f}s", key=f"{prefix}_time")
    with c4:
        ui.metric_card(title="Accuracy", content=f"{job_data['accuracy']:.1f}%", key=f"{prefix}_accuracy")
    with c5:
        ui.metric_card(title="Cost", content=f"${job_data.get('cost', 0.0108):.4f}", key=f"{prefix}_cost")

    # Row 2: Extraction details
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        ui.metric_card(title="Items Extracted", content=str(job_data['items_count']), description="Format 1", key=f"{prefix}_items")
    with c2:
        ui.metric_card(title="Declaration Fields", content=f"{decl_fields}/16", description="Format 2", key=f"{prefix}_decl_count")
    with c3:
        ui.metric_card(title="Completeness", content=f"{job_data['completeness']:.1f}%", key=f"{prefix}_comp")
    with c4:
        fkb = job_data.get('file_size_kb', 0)
        ui.metric_card(title="File Size", content=f"{fkb:.0f} KB" if fkb < 1024 else f"{fkb/1024:.1f} MB", key=f"{prefix}_fsize")
    with c5:
        ui.metric_card(title="Valid Fields", content=f"{job_data['valid_fields']}/{job_data['total_fields']}", key=f"{prefix}_vf")

    # ══════════════════════════════════════════════════════════════
    # SECTION 2: PDF Preview + Page Heatmap + Page Thumbnails
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("**Document Preview & Page Analysis**")

    _text_pgs = job_data.get('text_page_numbers', [])
    _image_pgs = job_data.get('image_page_numbers', [])
    if not _text_pgs and not _image_pgs:
        mf = config.RESULTS_DIR / 'pdf_metadata.json'
        if mf.exists():
            try:
                _m = json.load(open(mf))
                _text_pgs = _m.get('text_page_numbers', [])
                _image_pgs = _m.get('image_page_numbers', [])
            except Exception:
                pass

    render_pdf_preview(
        pdf_path=job_data.get('pdf_path', ''),
        total_pages=job_data['total_pages'],
        text_pages_list=_text_pgs,
        image_pages_list=_image_pgs,
        prefix=f"{prefix}_preview",
        pdf_name=job_data.get('pdf_name', '')
    )

    # ══════════════════════════════════════════════════════════════
    # SECTION 3: Pipeline Log
    # ══════════════════════════════════════════════════════════════
    if job_data.get('log_lines'):
        st.markdown("---")
        with st.expander("Pipeline Execution Log", expanded=False):
            render_terminal_logs(job_data['log_lines'])

    # ══════════════════════════════════════════════════════════════
    # SECTION 3B: Page-by-Page Content Viewer
    # ══════════════════════════════════════════════════════════════
    page_data = job_data.get('page_data', [])
    if page_data:
        st.markdown("---")
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:17px;font-weight:700;color:#0f172a;">Page-by-Page Content</span><span style="background:#6366f1;color:white;font-weight:700;font-size:13px;padding:2px 10px;border-radius:12px;">{len(page_data)} pages</span></div>', unsafe_allow_html=True)
        st.caption("All extracted text and OCR content per page — stored for future reference and re-extraction.")

        for pg in page_data:
            pg_num = pg['page']
            pg_type = pg['type']
            pg_source = pg.get('source', 'N/A')
            pg_content = pg.get('content', '')
            pg_skip = pg.get('skip', False)
            pg_filter_reason = pg.get('filter_reason', '')
            pg_filter_type = pg.get('filter_content_type', '')
            ocr_status = pg.get('ocr_status', '')

            if pg_skip:
                type_color = '#ef4444'
                type_label = 'SKIPPED'
                status_extra = f' — {pg_filter_type}: {pg_filter_reason}' if pg_filter_reason else ''
            elif pg_type == 'TEXT':
                type_color = '#22c55e'
                type_label = 'TEXT'
                status_extra = ''
            else:
                type_color = '#f59e0b'
                type_label = 'IMAGE'
                status_extra = f' [{ocr_status}]' if ocr_status and ocr_status != 'ok' else ''

            with st.expander(f"Page {pg_num} — {type_label} | {len(pg_content)} chars | {pg_source}{status_extra}", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f'<span style="background:{type_color};color:white;padding:2px 8px;border-radius:6px;font-size:12px;font-weight:600;">{type_label}</span>', unsafe_allow_html=True)
                with c2:
                    st.caption(f"Source: {pg_source}")
                with c3:
                    st.caption(f"Chars: {len(pg_content)}")

                if pg_skip:
                    st.info(f"Page skipped by Filter Agent: {pg_filter_type} — {pg_filter_reason}")

                if pg_content:
                    st.code(pg_content[:3000], language="text")
                    if len(pg_content) > 3000:
                        st.caption(f"Showing first 3000 of {len(pg_content)} characters")
                elif not pg_skip:
                    st.caption("No content extracted for this page")

    # ══════════════════════════════════════════════════════════════
    # SECTION 4: Product Items — Card View + Table View
    # ══════════════════════════════════════════════════════════════
    if items:
        st.markdown("---")
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:17px;font-weight:700;color:#0f172a;">Product Line Items</span><span style="background:#2563eb;color:white;font-weight:700;font-size:13px;padding:2px 10px;border-radius:12px;">{job_data["items_count"]} items</span></div>', unsafe_allow_html=True)
        st.caption("Format 1: 6 fields per item. Card view + editable table below.")

        items_df = pd.DataFrame(items)
        conf_cols = [c for c in items_df.columns if '_confidence' in c]
        data_cols = [c for c in items_df.columns if '_confidence' not in c]

        col_map = {
            'Item name': 'Product Name', 'Customs duty rate': 'Duty Rate',
            'Quantity (1)': 'Quantity', 'Invoice unit price': 'Unit Price',
            'Commercial tax %': 'Tax %', 'Exchange Rate (1)': 'Exchange Rate'
        }
        display_df = items_df[data_cols].rename(columns={k: v for k, v in col_map.items() if k in items_df.columns})

        # Card view for each item
        item_field_groups = {
            'Product': ['Product Name'],
            'Rates & Pricing': ['Duty Rate', 'Unit Price', 'Tax %'],
            'Quantity & Exchange': ['Quantity', 'Exchange Rate']
        }
        card_colors = {'Product': '#f0f9ff', 'Rates & Pricing': '#fefce8', 'Quantity & Exchange': '#f0fdf4'}

        for item_idx, row in display_df.iterrows():
            item_name = str(row.get('Product Name', f'Item {item_idx + 1}'))[:60]
            card_html = f'<div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:16px;background:#fafafa;">'
            card_html += f'<div style="font-weight:700;font-size:15px;color:#0f172a;margin-bottom:12px;">Item {item_idx + 1}: {item_name}</div>'
            card_html += '<div style="display:flex;gap:12px;flex-wrap:wrap;">'

            for group_name, group_fields in item_field_groups.items():
                bg = card_colors.get(group_name, '#f8fafc')
                card_html += f'<div style="flex:1;min-width:200px;background:{bg};border-radius:8px;padding:12px;">'
                card_html += f'<div style="font-weight:600;font-size:12px;color:#475569;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">{group_name}</div>'
                for fld in group_fields:
                    val = row.get(fld, '—')
                    display_val = str(val) if val is not None and str(val).strip() and str(val) != 'nan' else '—'
                    card_html += f'<div style="display:flex;justify-content:space-between;padding:3px 0;"><span style="color:#64748b;font-size:13px;">{fld}</span><span style="font-weight:600;font-size:13px;color:#0f172a;">{display_val}</span></div>'
                card_html += '</div>'

            card_html += '</div></div>'
            st.markdown(card_html, unsafe_allow_html=True)

        # Table view + download
        st.markdown("##### Table View")
        hdr_col, dl1, dl2 = st.columns([4, 1, 1])
        with dl1:
            st.download_button("CSV", display_df.to_csv(index=False).encode('utf-8'),
                f"items_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
                use_container_width=True, key=f"{prefix}_items_csv")
        with dl2:
            st.download_button("Excel", to_excel(display_df),
                f"items_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key=f"{prefix}_items_xlsx")

        edited_df = st.data_editor(display_df, use_container_width=True, hide_index=True, num_rows="fixed", key=f"{prefix}_items_edit")

        # Confidence heatmap
        if conf_cols:
            with st.expander("Field Confidence Scores", expanded=False):
                conf_df = items_df[conf_cols].copy()
                conf_df.columns = [c.replace('_confidence', '') for c in conf_cols]
                def _color_conf(val):
                    try:
                        v = float(val)
                        if v >= 0.9: return 'background-color: #dcfce7'
                        elif v >= 0.7: return 'background-color: #fef9c3'
                        else: return 'background-color: #fecaca'
                    except: return ''
                st.dataframe(conf_df.style.map(_color_conf), use_container_width=True, hide_index=True)
                st.caption("Green = high (>=0.9) | Yellow = medium (0.7-0.9) | Red = low (<0.7)")

    # ══════════════════════════════════════════════════════════════
    # SECTION 5: Declaration — Card View + Table View
    # ══════════════════════════════════════════════════════════════
    if decl:
        st.markdown("---")
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:17px;font-weight:700;color:#0f172a;">Customs Declaration</span><span style="background:#10b981;color:white;font-weight:700;font-size:13px;padding:2px 10px;border-radius:12px;">{decl_fields}/16 fields</span></div>', unsafe_allow_html=True)
        st.caption("Format 2: Single declaration record. Card view grouped by category + table below.")

        identity_fields = ['Declaration No', 'Declaration Date', 'Importer (Name)', 'Consignor (Name)']
        invoice_fields = ['Invoice Number', 'Invoice Price', 'Currency', 'Exchange Rate', 'Currency.1']
        financial_fields = ['Total Customs Value', 'Import/Export Customs Duty', 'Commercial Tax (CT)',
                           'Advance Income Tax (AT)', 'Security Fee (SF)', 'MACCS Service Fee (MF)', 'Exemption/Reduction']

        def _decl_get(field_name):
            """Flexible lookup — tries exact key, then with trailing space, then stripped."""
            val = decl.get(field_name)
            if val is None:
                val = decl.get(field_name + ' ')  # try with trailing space
            if val is None:
                val = decl.get(field_name.strip())
            # Also try case-insensitive match
            if val is None:
                for k, v in decl.items():
                    if k.strip().lower() == field_name.strip().lower():
                        return v
            return val

        def _render_decl_group(title, fields, color):
            html = f'<div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:16px;background:#fafafa;">'
            html += f'<div style="background:{color};border-radius:8px;padding:12px;">'
            html += f'<div style="font-weight:600;font-size:12px;color:#475569;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">{title}</div>'
            for f in fields:
                val = _decl_get(f)
                if val is not None:
                    display_val = str(val) if str(val).strip() else "0"
                else:
                    display_val = "—"
                if isinstance(val, (int, float)):
                    display_val = str(val)
                label = f.replace('(', '').replace(')', '').replace('  ', ' ').strip()
                html += f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(0,0,0,0.06);"><span style="color:#64748b;font-size:13px;">{label}</span><span style="font-weight:600;font-size:13px;color:#0f172a;">{display_val}</span></div>'
            html += '</div></div>'
            return html

        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(_render_decl_group("Identity & Document", identity_fields, "#f0f9ff"), unsafe_allow_html=True)
        with d2:
            st.markdown(_render_decl_group("Invoice Details", invoice_fields, "#fefce8"), unsafe_allow_html=True)
        with d3:
            st.markdown(_render_decl_group("Duties, Taxes & Fees", financial_fields, "#f0fdf4"), unsafe_allow_html=True)

        # Table view + download (same layout as items: header left, buttons right)
        decl_df = pd.DataFrame([decl])
        hdr_col, dl1, dl2 = st.columns([4, 1, 1])
        with hdr_col:
            st.markdown("##### Table View")
        with dl1:
            st.download_button("CSV", decl_df.to_csv(index=False).encode('utf-8'),
                f"declaration_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
                use_container_width=True, key=f"{prefix}_decl_csv")
        with dl2:
            st.download_button("Excel", to_excel(decl_df),
                f"declaration_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key=f"{prefix}_decl_xlsx")
        st.dataframe(decl_df, use_container_width=True, hide_index=True)


    # ══════════════════════════════════════════════════════════════
    # SECTION 6: Validation & Accuracy
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:17px;font-weight:700;color:#0f172a;">Validation & Accuracy</span><span style="background:#8b5cf6;color:white;font-weight:700;font-size:13px;padding:2px 10px;border-radius:12px;">{job_data["accuracy"]:.1f}% ({job_data["valid_fields"]}/{job_data["total_fields"]} fields)</span></div>', unsafe_allow_html=True)
    st.caption("Each field validated against business rules. PASS = 80%+, REVIEW = below threshold.")

    invalid = job_data['total_fields'] - job_data['valid_fields']
    acc_color = '#f0fdf4' if job_data['accuracy'] >= 90 else '#fefce8' if job_data['accuracy'] >= 60 else '#fef2f2'

    def _render_val_card(title, value, desc, color):
        html = f'<div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:16px;background:#fafafa;">'
        html += f'<div style="background:{color};border-radius:8px;padding:12px;">'
        html += f'<div style="font-weight:600;font-size:12px;color:#475569;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">{title}</div>'
        html += f'<div style="font-weight:700;font-size:24px;color:#0f172a;margin-bottom:4px;">{value}</div>'
        html += f'<div style="font-size:12px;color:#64748b;">{desc}</div>'
        html += '</div></div>'
        return html

    # Show items + declaration accuracy separately if available
    items_acc = job_data.get('items_accuracy', job_data['accuracy'])
    decl_acc = job_data.get('decl_accuracy', 0)
    items_v = job_data.get('items_valid', job_data['valid_fields'])
    items_t = job_data.get('items_total', job_data['total_fields'])
    decl_v = job_data.get('decl_valid', 0)
    decl_t = job_data.get('decl_total', 0)

    v1, v2, v3, v4, v5 = st.columns(5)
    with v1:
        st.markdown(_render_val_card("Overall", f"{job_data['accuracy']:.1f}%", f"{job_data['valid_fields']}/{job_data['total_fields']} fields", acc_color), unsafe_allow_html=True)
    with v2:
        i_color = '#f0fdf4' if items_acc >= 90 else '#fefce8' if items_acc >= 60 else '#fef2f2'
        st.markdown(_render_val_card("Items", f"{items_acc:.1f}%", f"{items_v}/{items_t} fields", i_color), unsafe_allow_html=True)
    with v3:
        d_color = '#f0fdf4' if decl_acc >= 90 else '#fefce8' if decl_acc >= 60 else '#fef2f2'
        st.markdown(_render_val_card("Declaration", f"{decl_acc:.1f}%", f"{decl_v}/{decl_t} fields", d_color), unsafe_allow_html=True)
    with v4:
        st.markdown(_render_val_card("Valid", str(job_data['valid_fields']), f"of {job_data['total_fields']}", "#f0fdf4"), unsafe_allow_html=True)
    with v5:
        inv_color = '#fef2f2' if invalid > 0 else '#f0fdf4'
        st.markdown(_render_val_card("Invalid", str(invalid), "Need review" if invalid > 0 else "All clear", inv_color), unsafe_allow_html=True)

    if job_data.get('field_accuracy'):
        acc_data = []
        for fn, fs in job_data['field_accuracy'].items():
            ap = fs.get('accuracy', 0)
            source = "Declaration" if fn.startswith("Decl:") else "Items"
            display_name = fn.replace("Decl: ", "") if fn.startswith("Decl:") else fn
            acc_data.append({'Source': source, 'Field': display_name, 'Valid': fs.get('valid', 0),
                           'Total': fs.get('total', 0), 'Accuracy %': f"{ap:.1f}",
                           'Status': 'PASS' if ap >= 80 else 'REVIEW'})

        if acc_data:
            # Plotly charts
            chart_col1, chart_col2 = st.columns([1, 2])

            with chart_col1:
                # Gauge chart — overall accuracy
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=job_data['accuracy'],
                    number={'suffix': '%', 'font': {'size': 36}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': '#2563eb'},
                        'bgcolor': '#f1f5f9',
                        'steps': [
                            {'range': [0, 30], 'color': '#fee2e2'},
                            {'range': [30, 60], 'color': '#fef3c7'},
                            {'range': [60, 90], 'color': '#dbeafe'},
                            {'range': [90, 100], 'color': '#dcfce7'},
                        ],
                        'threshold': {
                            'line': {'color': '#10b981', 'width': 3},
                            'thickness': 0.8,
                            'value': 90
                        }
                    }
                ))
                fig_gauge.update_layout(
                    height=220, margin=dict(l=20, r=20, t=30, b=10),
                    paper_bgcolor='rgba(0,0,0,0)', font={'color': '#1e293b'}
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

            with chart_col2:
                # Horizontal bar chart — per-field accuracy
                acc_df_chart = pd.DataFrame(acc_data)
                acc_df_chart['Accuracy'] = acc_df_chart['Accuracy %'].astype(float)
                acc_df_chart = acc_df_chart.sort_values('Accuracy', ascending=True)

                colors = ['#10b981' if a >= 90 else '#f59e0b' if a >= 60 else '#ef4444'
                          for a in acc_df_chart['Accuracy']]

                fig_bar = go.Figure(go.Bar(
                    x=acc_df_chart['Accuracy'],
                    y=acc_df_chart['Field'],
                    orientation='h',
                    marker_color=colors,
                    text=acc_df_chart['Accuracy'].apply(lambda x: f"{x:.0f}%"),
                    textposition='outside',
                    textfont={'size': 11}
                ))
                fig_bar.update_layout(
                    height=max(220, len(acc_data) * 28),
                    margin=dict(l=10, r=40, t=30, b=10),
                    xaxis=dict(range=[0, 110], title='', showgrid=True,
                               gridcolor='#f1f5f9'),
                    yaxis=dict(title=''),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font={'color': '#1e293b', 'size': 11},
                    showlegend=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            # Table below charts
            acc_df = pd.DataFrame(acc_data)
            st.dataframe(acc_df, use_container_width=True, hide_index=True)


    # ══════════════════════════════════════════════════════════════
    # SECTION 7: Download Reports
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("**Download Reports**")

    _items_df = pd.DataFrame(items) if items else pd.DataFrame()
    _decl_df = pd.DataFrame([decl]) if decl else pd.DataFrame()

    dl1, dl2 = st.columns(2)
    with dl1:
        combined_excel = to_excel_2sheet(_items_df, _decl_df)
        st.download_button(
            label="Download Excel",
            data=combined_excel,
            file_name=f"extraction_{job_data['pdf_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, type="primary", key=f"{prefix}_dl_combined"
        )
    with dl2:
        pdf_file_dl = _find_pdf_file(job_data.get('pdf_path', ''), job_data.get('pdf_name', ''))
        if pdf_file_dl and pdf_file_dl.is_file():
            with open(pdf_file_dl, 'rb') as f:
                st.download_button("Download PDF", f, pdf_file_dl.name, "application/pdf",
                    use_container_width=True, type="primary", key=f"{prefix}_dl_pdf")


def process_pipeline(pdf_path):
    """Execute the agentic extraction pipeline with self-review, decision gate, and retry."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.empty()
    log_lines = []
    start_time = time.time()
    total_steps = 10  # 9 + filter agent

    def _log(line):
        log_lines.append(line)
        with log_container.container():
            render_terminal_logs(log_lines)

    def _step(num, title, desc):
        progress_bar.progress(num / total_steps)
        status_text.text(f"Step {num}/{total_steps}: {title}")
        _log(f"[STEP {num}/{total_steps}] {title}")
        _log(f"  > {desc}")

    _log(f"[PIPELINE] Starting agentic extraction pipeline...")
    _log(f"[PIPELINE] PDF: {Path(pdf_path).name}")
    _log("")

    # ── Step 1: Scout Agent ──
    _step(1, "Scout Agent", "Analyzing document structure — classifying each page as TEXT or IMAGE")
    t0 = time.time()
    metadata = step1_analyze_metadata.analyze_pdf_metadata()
    if not metadata:
        raise Exception("Scout Agent failed: Could not analyze PDF metadata")
    total_pg = metadata.get('total_pages', 0)
    text_pg = metadata.get('text_pages', 0)
    image_pg = metadata.get('image_pages', 0)
    _log(f"  > Document scanned: {total_pg} pages detected")
    _log(f"  > Classification: {text_pg} text pages | {image_pg} image pages")
    _log(f"  > Text pages: {metadata.get('text_page_numbers', [])}")
    _log(f"  > Image pages: {metadata.get('image_page_numbers', [])}")
    for p in metadata.get('pages', []):
        _log(f"    Page {p['page']}: {p['type']} ({p['text_chars']} chars, {p['images']} images)")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 2: Filter Agent ──
    _step(2, "Filter Agent", "Analyzing image pages — skipping photos, stamps, signatures")
    t0 = time.time()
    metadata = step1b_filter_agent.filter_pages(metadata)
    skipped = metadata.get('skipped_pages', [])
    if skipped:
        _log(f"  > Skipped {len(skipped)} irrelevant pages: {skipped}")
        for sp in skipped:
            fr = metadata.get('filter_results', {}).get(sp, {})
            _log(f"    Page {sp}: {fr.get('content_type', '?')} — {fr.get('reason', '?')}")
        _log(f"  > Remaining image pages for OCR: {metadata.get('image_page_numbers', [])}")
    else:
        _log(f"  > All {len(metadata.get('image_page_numbers', []))} image pages contain useful data — none skipped")
    _log(f"  > Cost: ~${len(metadata.get('image_page_numbers_original', [])) * 0.0003:.4f}")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 3: Reader Agent ──
    _step(3, "Reader Agent", "Extracting text content from text-layer pages")
    t0 = time.time()
    text_data = step2_extract_text_pages.extract_text_pages()
    text_data = text_data or {}
    _log(f"  > Processed {len(text_data)} text pages")
    for pk, pv in text_data.items():
        _log(f"    Page {pv.get('page_number', '?')}: {pv.get('char_count', 0)} chars extracted")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 4: Vision Agent ──
    _step(4, "Vision Agent", "Running parallel OCR on scanned pages with retry + adaptive resolution")
    t0 = time.time()
    ocr_data = step3_ocr_image_pages.ocr_image_pages()
    ocr_data = ocr_data or {}
    ocr_count = len(ocr_data)
    if ocr_data:
        total_chars = sum(p.get('char_count', 0) for p in ocr_data.values())
        _log(f"  > OCR completed: {ocr_count} pages | {total_chars} total chars")
        for pk, pv in ocr_data.items():
            status = pv.get('ocr_status', 'ok')
            _log(f"    Page {pv.get('page_number', '?')}: {pv.get('char_count', 0)} chars [{status}]")
        hires = [p['page_number'] for p in ocr_data.values() if p.get('ocr_status') == 'high-res']
        if hires:
            _log(f"  > Auto-upgraded to high resolution: pages {hires}")
        _log(f"  > Cost: ~${ocr_count * 0.0006:.4f}")
    else:
        _log(f"  > No image pages — Vision Agent skipped")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 5: Extractor Agent ──
    _step(5, "Extractor Agent", "Talking to LLM for structured data extraction with confidence scoring")
    t0 = time.time()
    extracted = step4_claude_structured_extraction.extract_structured_data()
    if not extracted:
        extracted = {'items': [], 'declaration': {}, 'items_count': 0, 'completeness_percent': 0}
        _log(f"  > WARNING: Extractor Agent returned no data — continuing with empty results")
    items_count = extracted.get('items_count', len(extracted.get('items', [])))
    _log(f"  > Extraction complete: {items_count} items | Completeness: {extracted.get('completeness_percent', 0):.1f}%")
    for i, item in enumerate(extracted.get('items', []), 1):
        name = str(item.get('Item name', ''))[:40]
        _log(f"    Item {i}: {name}")
    if extracted.get('declaration'):
        decl_no = extracted['declaration'].get('Declaration No', 'N/A')
        _log(f"  > Declaration: {decl_no}")
    _log(f"  > Cost: ~$0.0054")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 6: Reviewer Agent ──
    _step(6, "Reviewer Agent", "Self-reviewing extraction for decimal errors, missing units, format issues")
    t0 = time.time()
    extracted = step4b_self_review.self_review(extracted)
    corrections = extracted.get('review_corrections', 0) if extracted else 0
    if corrections > 0:
        _log(f"  > Found and fixed {corrections} issues:")
        for detail in extracted.get('review_details', [])[:8]:
            _log(f"    - {detail.get('field', '?')}: {detail.get('old_value', '?')} -> {detail.get('new_value', '?')} ({detail.get('reason', '')})")
    else:
        _log(f"  > All values verified — no corrections needed")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 7: Validator Agent ──
    _step(7, "Validator Agent", "Cross-validating items (6 fields) + declaration (16 fields) against business rules")
    t0 = time.time()
    agent_decision_gate._save_extraction(extracted)
    validated = step5_cross_validate.cross_validate()
    if not validated:
        validated = {'overall_accuracy': 0, 'valid_fields': 0, 'total_fields': 0, 'items_accuracy': 0, 'items_valid': 0, 'items_total': 0, 'decl_accuracy': 0, 'decl_valid': 0, 'decl_total': 0, 'field_stats': {}, 'item_validations': [], 'decl_validations': {}}
    _log(f"  > Items validation: {validated.get('items_accuracy', 0):.1f}% ({validated.get('items_valid', 0)}/{validated.get('items_total', 0)} fields)")
    _log(f"  > Declaration validation: {validated.get('decl_accuracy', 0):.1f}% ({validated.get('decl_valid', 0)}/{validated.get('decl_total', 0)} fields)")
    _log(f"  > Overall accuracy: {validated.get('overall_accuracy', 0):.1f}% ({validated.get('valid_fields', 0)}/{validated.get('total_fields', 0)} fields)")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 8: Commander Agent ──
    _step(8, "Commander Agent", "Decision gate — analyzing accuracy and choosing next action")
    t0 = time.time()
    extracted, validated, accuracy_result, gate_log = agent_decision_gate.run_decision_gate(
        extracted, validated,
        cross_validate_func=step5_cross_validate.cross_validate,
        accuracy_func=step6_accuracy_matrix.calculate_accuracy_matrix
    )
    for gl in gate_log:
        _log(f"  > {gl}")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 9: Auditor Agent ──
    _step(9, "Auditor Agent", "Calculating field-level accuracy matrix")
    t0 = time.time()
    agent_decision_gate._save_extraction(extracted)
    accuracy = step6_accuracy_matrix.calculate_accuracy_matrix()
    _log(f"  > Final accuracy: {accuracy.get('overall_accuracy', 0):.1f}%")
    if accuracy.get('field_accuracy'):
        for fn, fs in accuracy['field_accuracy'].items():
            _log(f"    {fn}: {fs.get('accuracy', 0):.0f}%")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # ── Step 10: Reporter Agent ──
    _step(10, "Reporter Agent", "Generating final 2-sheet Excel report")
    t0 = time.time()
    excel_path = step7_create_final_excel.create_final_excel()
    _log(f"  > Excel saved: {excel_path}")
    _log(f"  DONE ({time.time()-t0:.1f}s)")
    _log("")

    # Final
    progress_bar.progress(1.0)
    processing_time = time.time() - start_time
    ocr_cost = (metadata.get('image_pages', 0) or 0) * 0.0006
    review_cost = 0.002 if corrections > 0 else 0
    total_cost = ocr_cost + 0.0054 + review_cost
    _log(f"[PIPELINE] Complete in {processing_time:.1f}s | Total cost: ~${total_cost:.4f}")
    _log(f"[PIPELINE] Agentic actions: {corrections} self-review fixes | Decision: {gate_log[0] if gate_log else 'N/A'}")
    status_text.empty()

    # Save to database
    pdf_path_obj = Path(st.session_state.uploaded_file_path)
    pdf_size = pdf_path_obj.stat().st_size if pdf_path_obj.exists() else 0

    _user = st.session_state.get('user', {})
    job_id = database.create_job(
        pdf_name=pdf_path_obj.name,
        pdf_path=str(pdf_path_obj),
        pdf_size=pdf_size,
        total_pages=metadata.get('total_pages', 0),
        text_pages=metadata.get('text_pages', 0),
        image_pages=metadata.get('image_pages', 0),
        user_id=_user.get('id'),
        username=_user.get('username')
    )
    st.session_state.current_job = job_id

    # Log activity
    database.log_activity(
        _user.get('id', 0), _user.get('username', 'unknown'),
        "RUN_JOB", f"Processed {pdf_path_obj.name} → {job_id}"
    )

    if extracted and 'items' in extracted:
        database.save_items(job_id, extracted['items'])
    if extracted and 'declaration' in extracted:
        database.save_declarations(job_id, [extracted['declaration']])

    database.update_job_status(job_id=job_id, status='COMPLETED')
    database.update_job_metrics(
        job_id=job_id,
        processing_time=processing_time,
        cost=0.0108,
        accuracy=validated.get('overall_accuracy', 0)
    )

    # Save to session_state for persistence
    file_size_kb = pdf_size / 1024 if pdf_size else 0
    ocr_cost = metadata.get('image_pages', 0) * 0.0006
    total_cost = ocr_cost + 0.0054  # OCR + extraction

    job_results = {
        'job_id': job_id,
        'pdf_name': pdf_path_obj.name,
        'pdf_path': str(pdf_path_obj),
        'processed_by': _user.get('username', 'unknown'),
        'processing_time': processing_time,
        'total_pages': metadata.get('total_pages', 0),
        'text_pages': metadata.get('text_pages', 0),
        'image_pages': metadata.get('image_pages', 0),
        'text_page_numbers': metadata.get('text_page_numbers', []),
        'image_page_numbers': metadata.get('image_page_numbers', []),
        'skipped_pages': metadata.get('skipped_pages', []),
        'skipped_count': metadata.get('skipped_count', 0),
        'file_size_kb': file_size_kb,
        'cost': total_cost,
        'accuracy': validated.get('overall_accuracy', 0),
        'items_accuracy': validated.get('items_accuracy', 0),
        'items_valid': validated.get('items_valid', 0),
        'items_total': validated.get('items_total', 0),
        'decl_accuracy': validated.get('decl_accuracy', 0),
        'decl_valid': validated.get('decl_valid', 0),
        'decl_total': validated.get('decl_total', 0),
        'items_count': len(extracted.get('items', [])),
        'items': extracted.get('items', []),
        'declaration': extracted.get('declaration', {}),
        'completeness': extracted.get('completeness_percent', 0),
        'excel_path': str(excel_path) if excel_path else None,
        'field_accuracy': accuracy.get('field_accuracy', {}),
        'valid_fields': validated.get('valid_fields', 0),
        'total_fields': validated.get('total_fields', 0),
        'log_lines': log_lines,
        'page_data': _build_page_data(metadata, text_data, ocr_data),
    }

    st.session_state.job_results = job_results
    save_session_to_disk(job_results)

    # Save page-by-page content to DB for search/RAG
    page_data = job_results.get('page_data', [])
    if page_data:
        database.save_page_contents(
            job_id=job_id,
            pdf_name=pdf_path_obj.name,
            pages=page_data,
            user_id=_user.get('id')
        )


def _build_page_data(metadata, text_data, ocr_data):
    """Combine metadata + text + OCR into per-page data for UI display."""
    pages = []
    text_data = text_data or {}
    ocr_data = ocr_data or {}

    for p in metadata.get('pages', []):
        pg_num = p['page']
        page_info = {
            'page': pg_num,
            'type': p['type'],
            'text_chars': p['text_chars'],
            'images': p['images'],
            'content': '',
            'source': '',
            'skip': p.get('skip', False),
            'filter_reason': p.get('filter_reason', ''),
            'filter_content_type': p.get('filter_content_type', ''),
        }
        text_key = f'page_{pg_num}'
        if text_key in text_data:
            page_info['content'] = text_data[text_key].get('text', '')[:2000]
            page_info['source'] = 'Reader Agent (text extraction)'
        elif text_key in ocr_data:
            page_info['content'] = ocr_data[text_key].get('ocr_text', '')[:2000]
            page_info['source'] = 'Vision Agent (OCR)'
            page_info['ocr_status'] = ocr_data[text_key].get('ocr_status', 'ok')

        pages.append(page_info)
    return pages


# =============================================================================
# INITIALIZE
# =============================================================================

if 'current_job' not in st.session_state:
    st.session_state.current_job = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'confirm_delete_job' not in st.session_state:
    st.session_state.confirm_delete_job = None
if 'job_results' not in st.session_state:
    # Try to restore last session from disk
    st.session_state.job_results = load_session_from_disk()
if 'pipeline_error' not in st.session_state:
    st.session_state.pipeline_error = None

# =============================================================================
# SIDEBAR
# =============================================================================

current_user = st.session_state.user
is_admin = current_user and current_user.get('role') == 'admin'

with st.sidebar:
    st.markdown("### RO-ED AI Agent")
    st.caption("Document Intelligence")
    st.markdown("---")

    # User info + logout
    display = current_user.get('display_name') or current_user.get('username', '')
    role_badge = "admin" if is_admin else "user"
    st.markdown(f'''<div class="sidebar-user-info">
        <span class="name">{display}</span>
        <span class="role-label role-{role_badge}">{role_badge}</span>
    </div>''', unsafe_allow_html=True)

    if st.button("Logout", use_container_width=True, key="sidebar_logout"):
        database.log_activity(current_user['id'], current_user['username'], "LOGOUT", "Signed out")
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.remember_me = False
        st.session_state.login_time = None
        _clear_auth_from_disk()
        st.rerun()

    st.markdown("---")

    if is_admin:
        stats = database.get_stats()
        st.caption("All Users")
    else:
        stats = database.get_user_stats(current_user['id'])
        st.caption("Your Stats")
    sb_c1, sb_c2 = st.columns(2)
    with sb_c1:
        st.metric("Jobs", stats['total_jobs'])
        st.metric("Accuracy", f"{stats['avg_accuracy']:.0f}%")
    with sb_c2:
        st.metric("Done", stats['completed_jobs'])
        st.metric("Cost", f"${stats['total_cost']:.3f}")

    st.markdown("---")
    st.caption("Created by City AI Team")

# =============================================================================
# HEADER
# =============================================================================

header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("PG : RO-ED AI Agent")
    st.caption("Myanmar Import PDF Data Extraction Pipeline")
with header_col2:
    ui.badges(badge_list=[("v1.0", "default"), ("Online", "secondary")], key="header_badges")

# =============================================================================
# TABS
# =============================================================================

tab_options = ['Agent', 'History', 'Product Items', 'Declaration Data', 'Document Search']
if is_admin:
    tab_options.append('User Management')

selected_tab = ui.tabs(
    options=tab_options,
    default_value='Agent',
    key="main_tabs"
)

# =============================================================================
# TAB 1: HOME
# =============================================================================

if selected_tab == 'Agent':

    def _do_new_session():
        """Clear all state and disk session."""
        st.session_state.job_results = None
        st.session_state.uploaded_file_path = None
        st.session_state.current_job = None
        st.session_state.processing = False
        clear_session_from_disk()
        if 'last_uploaded_file' in st.session_state:
            del st.session_state.last_uploaded_file

    # STATE 1: Processing
    if st.session_state.processing and st.session_state.uploaded_file_path:
        st.header("Processing Your PDF")

        config.PDF_PATH = Path(st.session_state.uploaded_file_path)
        page_count, error = verify_pdf(config.PDF_PATH)
        if error:
            st.error(f"Error opening PDF: {error}")
            st.session_state.processing = False
            st.stop()

        # Duplicate check — has this exact PDF been processed before?
        pdf_hash = database.calculate_pdf_hash(str(config.PDF_PATH))
        existing_job = database.find_job_by_hash(pdf_hash)

        if existing_job and not st.session_state.get('force_reprocess'):
            st.session_state.processing = False
            st.session_state.duplicate_job = existing_job
            st.rerun()
        else:
            st.session_state.pop('force_reprocess', None)
            try:
                process_pipeline(config.PDF_PATH)
                st.session_state.processing = False
                st.session_state.pipeline_error = None
                st.session_state.pop('duplicate_job', None)
                st.rerun()
            except Exception as pipeline_err:
                st.session_state.processing = False
                st.session_state.pipeline_error = str(pipeline_err)
                st.rerun()

    # STATE 1B: Pipeline failed — show error with retry
    elif st.session_state.get('pipeline_error'):
        st.header("Pipeline Error")
        st.error(f"Extraction failed: {st.session_state.pipeline_error}")

        r1, r2, _ = st.columns([1, 1, 3])
        with r1:
            if st.button("Retry", type="primary", use_container_width=True):
                st.session_state.pipeline_error = None
                st.session_state.processing = True
                st.rerun()
        with r2:
            if st.button("New Session", type="secondary", use_container_width=True, key="err_new_session"):
                st.session_state.pipeline_error = None
                _do_new_session()
                st.rerun()

    # STATE 1C: Duplicate PDF detected — show existing results
    elif st.session_state.get('duplicate_job'):
        dup = st.session_state.duplicate_job
        st.header("Duplicate PDF Detected")

        dup_date = (dup.get('created_at', '') or '')[:19]
        dup_acc = dup.get('accuracy_percent', 0) or 0
        dup_time = dup.get('processing_time_seconds', 0) or 0

        dup_user = dup.get('username') or 'Unknown'
        is_own_job = dup.get('user_id') == current_user.get('id')

        if is_own_job:
            st.warning("You have already processed this PDF.")
        else:
            st.warning(f"This PDF was already processed by **{_html.escape(dup_user)}**.")

        st.markdown(f"""
        | | |
        |---|---|
        | **Job ID** | `{dup['job_id']}` |
        | **Processed By** | {_html.escape(dup_user)} |
        | **Status** | {dup['status']} |
        | **Processed On** | {dup_date} |
        | **Accuracy** | {dup_acc:.1f}% |
        | **Processing Time** | {dup_time:.1f}s |
        """)

        b1, b2, b3, _ = st.columns([1, 1, 1, 2])
        with b1:
            if st.button("View Results", type="primary", use_container_width=True):
                # Load existing job results — transform DB format to LLM format
                job_details = database.get_job_details(dup['job_id'])
                if job_details:
                    # Transform items from DB columns to LLM field names
                    db_items = job_details.get('items', [])
                    llm_items = []
                    for it in db_items:
                        llm_items.append({
                            'Item name': it.get('item_name', ''),
                            'Customs duty rate': it.get('customs_duty_rate', 0),
                            'Quantity (1)': it.get('quantity', ''),
                            'Invoice unit price': it.get('invoice_unit_price', ''),
                            'Commercial tax %': it.get('commercial_tax_percent', 0),
                            'Exchange Rate (1)': it.get('exchange_rate', ''),
                        })

                    # Transform declaration from DB columns to LLM field names
                    db_decl = job_details['declarations'][0] if job_details.get('declarations') else {}
                    llm_decl = {}
                    if db_decl:
                        llm_decl = {
                            'Declaration No': db_decl.get('declaration_no', ''),
                            'Declaration Date': db_decl.get('declaration_date', ''),
                            'Importer (Name)': db_decl.get('importer_name', ''),
                            'Consignor (Name)': db_decl.get('consignor_name', ''),
                            'Invoice Number': db_decl.get('invoice_number', ''),
                            'Invoice Price ': db_decl.get('invoice_price', 0),
                            'Currency': db_decl.get('currency', ''),
                            'Exchange Rate': db_decl.get('exchange_rate', 0),
                            'Currency.1': db_decl.get('currency_2', 'MMK'),
                            'Total Customs Value ': db_decl.get('total_customs_value', 0),
                            'Import/Export Customs Duty ': db_decl.get('import_export_customs_duty', 0),
                            'Commercial Tax (CT)': db_decl.get('commercial_tax_ct', 0),
                            'Advance Income Tax (AT)': db_decl.get('advance_income_tax_at', 0),
                            'Security Fee (SF)': db_decl.get('security_fee_sf', 0),
                            'MACCS Service Fee (MF)': db_decl.get('maccs_service_fee_mf', 0),
                            'Exemption/Reduction': db_decl.get('exemption_reduction', 0),
                        }

                    st.session_state.job_results = {
                        'job_id': dup['job_id'],
                        'pdf_name': dup['pdf_name'],
                        'pdf_path': dup.get('pdf_path', ''),
                        'processed_by': dup.get('username', 'Unknown'),
                        'processing_time': dup_time,
                        'total_pages': dup.get('total_pages', 0) or 0,
                        'text_pages': dup.get('text_pages', 0) or 0,
                        'image_pages': dup.get('image_pages', 0) or 0,
                        'file_size_kb': (dup.get('pdf_size', 0) or 0) / 1024,
                        'cost': dup.get('cost_usd', 0) or 0,
                        'accuracy': dup_acc,
                        'items_count': len(llm_items),
                        'items': llm_items,
                        'declaration': llm_decl,
                        'completeness': 100.0 if llm_items else 0,
                        'excel_path': str(config.RESULTS_DIR / f"final_output_{dup['job_id']}.xlsx"),
                        'field_accuracy': {},
                        'valid_fields': 0,
                        'total_fields': 0,
                        'log_lines': [f"[INFO] Loaded existing job {dup['job_id']}", f"[INFO] Originally processed on {dup_date}"],
                    }
                    save_session_to_disk(st.session_state.job_results)
                    st.session_state.pop('duplicate_job', None)
                    st.rerun()
        with b2:
            can_reprocess = is_admin or is_own_job
            if can_reprocess:
                if st.button("Reprocess Anyway", type="secondary", use_container_width=True):
                    st.session_state.force_reprocess = True
                    st.session_state.processing = True
                    st.session_state.pop('duplicate_job', None)
                    st.rerun()
            else:
                st.button("Reprocess Anyway", disabled=True, use_container_width=True)
                st.caption(f"Only {_html.escape(dup_user)} or admin can reprocess")
        with b3:
            if st.button("New Session", use_container_width=True, key="dup_new_session"):
                st.session_state.pop('duplicate_job', None)
                _do_new_session()
                st.rerun()

    # STATE 2: Results exist — show them
    elif st.session_state.job_results is not None:
        job_data = st.session_state.job_results

        # Top bar: title + New Session button
        top_col1, top_col2 = st.columns([4, 1])
        with top_col1:
            st.header(f"Results: {job_data['pdf_name']}")
        with top_col2:
            if st.button("New Session", type="secondary", use_container_width=True, key="new_session_top"):
                _do_new_session()
                st.rerun()

        _processed_by = job_data.get('processed_by', '')
        badge_list = [("COMPLETED", "default"), (f"{job_data['total_pages']} pages", "secondary"), (f"Job: {job_data['job_id'][:16]}", "secondary")]
        if _processed_by:
            badge_list.append((f"By: {_processed_by}", "outline"))
        ui.badges(badge_list=badge_list, key="result_header_badges")

        render_job_results(job_data)

    # STATE 3: Upload form
    else:
        st.header("Process PDF Files")

        # Row: Upload | Run Job | New Session
        upload_col, run_col, new_col = st.columns([5, 1, 1])

        with upload_col:
            uploaded_file = st.file_uploader(
                "Upload PDF",
                type=['pdf'],
                help="Upload a Myanmar import PDF to extract customs data",
                label_visibility="collapsed"
            )

        file_ready = False
        if uploaded_file:
            if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
                filepath = save_uploaded_file(uploaded_file)
                st.session_state.uploaded_file_path = str(filepath)
                st.session_state.last_uploaded_file = uploaded_file.name
                if filepath.exists():
                    file_size = filepath.stat().st_size
                    st.toast(f"Uploaded: {uploaded_file.name} ({file_size / 1024:.1f} KB)")
            file_ready = True

        with run_col:
            if st.button("Run Job", type="primary", use_container_width=True, disabled=not file_ready):
                st.session_state.processing = True
                st.rerun()

        with new_col:
            if st.button("New Session", type="secondary", use_container_width=True, key="new_session_upload"):
                _do_new_session()
                st.rerun()

        # Only show file name confirmation after upload — no preview until Run Job
        if file_ready and st.session_state.uploaded_file_path:
            _upload_path = Path(st.session_state.uploaded_file_path)
            if _upload_path.is_file():
                _fsize = _upload_path.stat().st_size
                _fsize_str = f"{_fsize/1024:.0f} KB" if _fsize < 1024*1024 else f"{_fsize/1024/1024:.1f} MB"
                st.info(f"Ready to process: **{_upload_path.name}** ({_fsize_str}) — Click **Run Job** to start extraction.")

# =============================================================================
# TAB 2: HISTORY
# =============================================================================

elif selected_tab == 'History':
    st.header("Job History")

    if is_admin:
        all_history_jobs = database.get_all_jobs(limit=100)
    else:
        all_history_jobs = database.get_user_jobs(current_user['id'], limit=100)

    if not all_history_jobs:
        ui.alert(title="No History", description="Process your first PDF to get started.", key="history_empty_alert")
    else:
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            ui.metric_card(title="Total Jobs", content=str(len(all_history_jobs)), key="history_total")
        with col2:
            completed = sum(1 for j in all_history_jobs if j['status'] == 'COMPLETED')
            ui.metric_card(title="Completed", content=str(completed), key="history_completed")
        with col3:
            avg_acc = sum(j.get('accuracy_percent', 0) or 0 for j in all_history_jobs) / max(len(all_history_jobs), 1)
            ui.metric_card(title="Avg Accuracy", content=f"{avg_acc:.1f}%", key="history_avg_acc")

        st.markdown("---")

        # Filters: calendar, status, PDF name
        f1, f2, f3 = st.columns(3)
        with f1:
            hist_date_range = st.date_input("Filter by date range", value=[], key="hist_date_range")
        with f2:
            statuses = sorted(set(j['status'] for j in all_history_jobs))
            hist_status = st.selectbox("Filter by status", options=["All"] + statuses, key="hist_status_filter")
        with f3:
            pdf_names_hist = sorted(set(j['pdf_name'] for j in all_history_jobs))
            hist_pdf = st.selectbox("Filter by PDF", options=["All PDFs"] + pdf_names_hist, key="hist_pdf_filter")

        # Apply filters
        jobs = all_history_jobs
        if hist_status and hist_status != "All":
            jobs = [j for j in jobs if j['status'] == hist_status]
        if hist_pdf and hist_pdf != "All PDFs":
            jobs = [j for j in jobs if j['pdf_name'] == hist_pdf]
        if hist_date_range and len(hist_date_range) == 2:
            d_start, d_end = str(hist_date_range[0]), str(hist_date_range[1])
            jobs = [j for j in jobs if d_start <= (j.get('created_at', '') or '')[:10] <= d_end]

        st.caption(f"Showing {len(jobs)} of {len(all_history_jobs)} jobs")

        # Summary table
        if jobs:
            def _build_job_row(j):
                row = {
                    "PDF Name": j['pdf_name'][:35] + ("..." if len(j['pdf_name']) > 35 else ""),
                    "Status": j['status'],
                    "Time (s)": f"{j.get('processing_time_seconds', 0) or 0:.1f}",
                    "Accuracy": f"{j.get('accuracy_percent', 0) or 0:.0f}%",
                    "Cost": f"${j.get('cost_usd', 0) or 0:.4f}",
                    "Date": (j.get('created_at', '') or '')[:10]
                }
                if is_admin:
                    row["User"] = j.get('username') or 'N/A'
                return row
            jobs_df = pd.DataFrame([_build_job_row(j) for j in jobs])
            st.dataframe(jobs_df, use_container_width=True, hide_index=True)

        # ── History Charts ──
        if jobs and len(jobs) >= 1:
            st.markdown("---")

            hist_chart1, hist_chart2 = st.columns(2)

            with hist_chart1:
                # Accuracy + Cost timeline
                timeline_data = []
                for j in reversed(jobs):
                    date = (j.get('created_at') or '')[:16]
                    acc = j.get('accuracy_percent', 0) or 0
                    cost = (j.get('cost_usd', 0) or 0) * 1000  # in millicents for scale
                    name = (j.get('pdf_name') or '')[:25]
                    timeline_data.append({'Date': date, 'Accuracy %': acc, 'Cost (x1000)': cost, 'PDF': name})

                tl_df = pd.DataFrame(timeline_data)
                fig_tl = go.Figure()
                fig_tl.add_trace(go.Scatter(
                    x=tl_df['Date'], y=tl_df['Accuracy %'],
                    mode='lines+markers', name='Accuracy',
                    line=dict(color='#2563eb', width=2),
                    marker=dict(size=8),
                    hovertemplate='%{text}<br>Accuracy: %{y:.1f}%<extra></extra>',
                    text=tl_df['PDF']
                ))
                fig_tl.update_layout(
                    title=dict(text='Accuracy Over Time', font=dict(size=14)),
                    height=280, margin=dict(l=10, r=10, t=40, b=40),
                    xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
                    yaxis=dict(range=[0, 105], title='', gridcolor='#f1f5f9'),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1e293b'), showlegend=False
                )
                st.plotly_chart(fig_tl, use_container_width=True)

            with hist_chart2:
                # Accuracy distribution by PDF
                pdf_acc = []
                for j in jobs:
                    acc = j.get('accuracy_percent', 0) or 0
                    name = (j.get('pdf_name') or '')[:30]
                    status = j.get('status', '')
                    pdf_acc.append({'PDF': name, 'Accuracy': acc, 'Status': status})

                pdf_df = pd.DataFrame(pdf_acc)
                colors = ['#10b981' if a >= 90 else '#f59e0b' if a >= 60 else '#ef4444'
                          for a in pdf_df['Accuracy']]

                fig_dist = go.Figure(go.Bar(
                    x=pdf_df['PDF'], y=pdf_df['Accuracy'],
                    marker_color=colors,
                    text=pdf_df['Accuracy'].apply(lambda x: f"{x:.0f}%"),
                    textposition='outside', textfont=dict(size=10)
                ))
                fig_dist.update_layout(
                    title=dict(text='Accuracy by PDF', font=dict(size=14)),
                    height=280, margin=dict(l=10, r=10, t=40, b=80),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=9), showgrid=False),
                    yaxis=dict(range=[0, 110], title='', gridcolor='#f1f5f9'),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1e293b'), showlegend=False
                )
                st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("---")
        st.subheader("Job Details")
        st.caption("Expand a job to view extracted data, declaration, and download the report.")

        for idx, job in enumerate(jobs):
            pdf_name = job['pdf_name']
            short_name = pdf_name[:40] + "..." if len(pdf_name) > 40 else pdf_name
            status_icon = "🟢" if job['status'] == 'COMPLETED' else "🟡"
            proc_time = job.get('processing_time_seconds', 0) or 0
            accuracy = job.get('accuracy_percent', 0) or 0
            date_str = (job.get('created_at', '') or '')[:10]

            with st.expander(f"{status_icon} {short_name}  |  {accuracy:.0f}% accuracy  |  {proc_time:.1f}s  |  {date_str}", expanded=False):
                job_details = database.get_job_details(job['job_id'])

                if not job_details:
                    st.error("Could not load job details")
                    continue

                # Info cards
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    ui.metric_card(title="Pages", content=str(job_details.get('total_pages', '?')), key=f"hd_pg_{idx}")
                with c2:
                    ui.metric_card(title="Text / Image", content=f"{job_details.get('text_pages', '?')} / {job_details.get('image_pages', '?')}", key=f"hd_ti_{idx}")
                with c3:
                    ui.metric_card(title="Time", content=f"{proc_time:.1f}s", key=f"hd_tm_{idx}")
                with c4:
                    ui.metric_card(title="Accuracy", content=f"{accuracy:.1f}%", key=f"hd_ac_{idx}")
                with c5:
                    ui.metric_card(title="Cost", content=f"${job.get('cost_usd', 0) or 0:.4f}", key=f"hd_co_{idx}")

                # PDF Preview + Heatmap
                _hist_pdf_path = job_details.get('pdf_path', '')
                _hist_text_pgs = list(range(1, (job_details.get('text_pages', 0) or 0) + 1))  # approximate
                _hist_image_pgs = list(range((job_details.get('text_pages', 0) or 0) + 1, (job_details.get('total_pages', 0) or 0) + 1))

                # Try to get exact page numbers from metadata if this was the last processed job
                _hist_meta_file = config.RESULTS_DIR / 'pdf_metadata.json'
                if _hist_meta_file.exists():
                    try:
                        with open(_hist_meta_file) as _hmf:
                            _hm = json.load(_hmf)
                        if _hm.get('pdf_name', '') in pdf_name:
                            _hist_text_pgs = _hm.get('text_page_numbers', _hist_text_pgs)
                            _hist_image_pgs = _hm.get('image_page_numbers', _hist_image_pgs)
                    except Exception:
                        pass

                render_pdf_preview(
                    pdf_path=_hist_pdf_path,
                    total_pages=job_details.get('total_pages', 0) or 0,
                    text_pages_list=_hist_text_pgs,
                    image_pages_list=_hist_image_pgs,
                    prefix=f"hist_preview_{idx}",
                    pdf_name=job_details.get('pdf_name', '')
                )

                st.markdown("---")

                # ── Product Items — Card View ──
                _hist_items = job_details.get('items', [])
                _job_items_df = pd.DataFrame()
                if _hist_items:
                    _items_count = len(_hist_items)
                    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:15px;font-weight:700;">Product Line Items</span><span style="background:#2563eb;color:white;font-weight:700;font-size:12px;padding:2px 8px;border-radius:10px;">{_items_count} items</span></div>', unsafe_allow_html=True)

                    _job_items_df = pd.DataFrame(_hist_items).drop(columns=['id', 'job_id', 'is_valid', 'created_at'], errors='ignore')

                    _h_col_map = {'item_name': 'Product Name', 'customs_duty_rate': 'Duty Rate', 'quantity': 'Quantity', 'invoice_unit_price': 'Unit Price', 'commercial_tax_percent': 'Tax %', 'exchange_rate': 'Exchange Rate'}
                    _h_display = _job_items_df.rename(columns={k: v for k, v in _h_col_map.items() if k in _job_items_df.columns})

                    _h_groups = {'Product': ['Product Name'], 'Rates & Pricing': ['Duty Rate', 'Unit Price', 'Tax %'], 'Quantity & Exchange': ['Quantity', 'Exchange Rate']}
                    _h_colors = {'Product': '#f0f9ff', 'Rates & Pricing': '#fefce8', 'Quantity & Exchange': '#f0fdf4'}

                    for _hi, _hrow in _h_display.iterrows():
                        _hname = str(_hrow.get('Product Name', f'Item {_hi+1}'))[:50]
                        _hcard = f'<div style="border:1px solid #e2e8f0;border-radius:12px;padding:14px;margin-bottom:12px;background:#fafafa;">'
                        _hcard += f'<div style="font-weight:700;font-size:14px;color:#0f172a;margin-bottom:10px;">Item {_hi+1}: {_hname}</div>'
                        _hcard += '<div style="display:flex;gap:10px;flex-wrap:wrap;">'
                        for _gn, _gf in _h_groups.items():
                            _bg = _h_colors.get(_gn, '#f8fafc')
                            _hcard += f'<div style="flex:1;min-width:180px;background:{_bg};border-radius:8px;padding:10px;">'
                            _hcard += f'<div style="font-weight:600;font-size:11px;color:#475569;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">{_gn}</div>'
                            for _ff in _gf:
                                _fv = _hrow.get(_ff, '—')
                                _dv = str(_fv) if _fv is not None and str(_fv).strip() and str(_fv) != 'nan' else '—'
                                _hcard += f'<div style="display:flex;justify-content:space-between;padding:2px 0;"><span style="color:#64748b;font-size:12px;">{_ff}</span><span style="font-weight:600;font-size:12px;color:#0f172a;">{_dv}</span></div>'
                            _hcard += '</div>'
                        _hcard += '</div></div>'
                        st.markdown(_hcard, unsafe_allow_html=True)

                    st.dataframe(_h_display, use_container_width=True, hide_index=True)

                # ── Declaration — Card View ──
                _job_decl_df = pd.DataFrame()
                if job_details.get('declarations'):
                    _hdecl = job_details['declarations'][0]
                    _hdecl_clean = {k: v for k, v in _hdecl.items() if k not in ['id', 'job_id', 'is_valid', 'created_at']}
                    _hdecl_fields_count = sum(1 for v in _hdecl_clean.values() if v is not None and str(v).strip())
                    _job_decl_df = pd.DataFrame([_hdecl_clean])

                    st.markdown("---")
                    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:15px;font-weight:700;">Customs Declaration</span><span style="background:#10b981;color:white;font-weight:700;font-size:12px;padding:2px 8px;border-radius:10px;">{_hdecl_fields_count}/16 fields</span></div>', unsafe_allow_html=True)

                    _id_fields = ['declaration_no', 'declaration_date', 'importer_name', 'consignor_name']
                    _inv_fields = ['invoice_number', 'invoice_price', 'currency', 'exchange_rate', 'currency_2']
                    _fin_fields = ['total_customs_value', 'import_export_customs_duty', 'commercial_tax_ct', 'advance_income_tax_at', 'security_fee_sf', 'maccs_service_fee_mf', 'exemption_reduction']

                    def _hrender_grp(title, fields, color):
                        html = f'<div style="border:1px solid #e2e8f0;border-radius:12px;padding:14px;margin-bottom:12px;background:#fafafa;">'
                        html += f'<div style="background:{color};border-radius:8px;padding:10px;">'
                        html += f'<div style="font-weight:600;font-size:11px;color:#475569;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">{title}</div>'
                        for f in fields:
                            val = _hdecl_clean.get(f, '')
                            dv = str(val) if val is not None and str(val).strip() else '—'
                            if isinstance(val, (int, float)):
                                dv = str(val)
                            label = f.replace('_', ' ').title()
                            html += f'<div style="display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid rgba(0,0,0,0.05);"><span style="color:#64748b;font-size:12px;">{label}</span><span style="font-weight:600;font-size:12px;color:#0f172a;">{dv}</span></div>'
                        html += '</div></div>'
                        return html

                    _hd1, _hd2, _hd3 = st.columns(3)
                    with _hd1:
                        st.markdown(_hrender_grp("Identity & Document", _id_fields, "#f0f9ff"), unsafe_allow_html=True)
                    with _hd2:
                        st.markdown(_hrender_grp("Invoice Details", _inv_fields, "#fefce8"), unsafe_allow_html=True)
                    with _hd3:
                        st.markdown(_hrender_grp("Duties, Taxes & Fees", _fin_fields, "#f0fdf4"), unsafe_allow_html=True)

                    st.dataframe(_job_decl_df, use_container_width=True, hide_index=True)

                # Downloads + Delete
                st.markdown("---")
                dl1, dl2, dl3 = st.columns(3)
                with dl1:
                    combined_data = to_excel_2sheet(_job_items_df, _job_decl_df)
                    st.download_button(
                        label="Download Excel",
                        data=combined_data,
                        file_name=f"extraction_{pdf_name}_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True, type="primary",
                        key=f"dl_{job['job_id']}"
                    )
                with dl2:
                    _hp = _find_pdf_file(_hist_pdf_path, pdf_name)
                    if _hp and _hp.is_file():
                        with open(_hp, 'rb') as _pf:
                            st.download_button(
                                label="Download PDF",
                                data=_pf,
                                file_name=pdf_name,
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"dl_pdf_{job['job_id']}"
                            )
                with dl3:
                    if st.button("Delete Job", type="secondary", use_container_width=True, key=f"del_{job['job_id']}"):
                        database.delete_job(job['job_id'])
                        database.log_activity(
                            current_user['id'], current_user['username'],
                            "DELETE_JOB", f"Deleted job {job['job_id']} ({job['pdf_name']})"
                        )
                        ef = config.RESULTS_DIR / f"final_output_{job['job_id']}.xlsx"
                        if ef.exists():
                            ef.unlink()
                        st.toast(f"Deleted job {job['job_id'][:16]}...")
                        st.rerun()

# =============================================================================
# TAB 4: PRODUCT ITEMS
# =============================================================================

elif selected_tab == 'Product Items':
    st.header("Product Items (All Jobs)" if is_admin else "Product Items (My Jobs)")

    all_jobs = database.get_all_jobs(limit=1000) if is_admin else database.get_user_jobs(current_user['id'], limit=1000)

    if not all_jobs:
        ui.alert(title="No Data", description="Process a PDF first to see extracted data.", key="items_empty_alert")
    else:
        all_items_data = []
        total_jobs_with_items = 0
        pdf_names_set = set()

        def _fmt_num(val, decimals=2):
            """Format numeric value to consistent decimal places."""
            if val is None or val == 'N/A' or val == '':
                return 'N/A'
            try:
                return f"{float(val):.{decimals}f}"
            except (ValueError, TypeError):
                return str(val)

        def _split_num_unit(val):
            """Split a value like '69.1358THB' or 'THB 65.0025' into (number, unit)."""
            import re as _re
            if val is None or val == 'N/A' or val == '':
                return None, ''
            s = str(val).strip()
            # Pattern: unit first (e.g. 'THB 65.0025')
            m = _re.match(r'^([A-Za-z]+)\s*([\d.]+)$', s)
            if m:
                return float(m.group(2)), m.group(1).upper()
            # Pattern: number first (e.g. '69.1358THB' or '16200.00KG')
            m = _re.match(r'^([\d.]+)\s*([A-Za-z]*)$', s)
            if m:
                unit = m.group(2).upper() if m.group(2) else ''
                return float(m.group(1)), unit
            return None, s

        def _normalize_price(val):
            """Normalize unit price: NUMBER + UNIT. Fix KG→THB if it's a price field."""
            num, unit = _split_num_unit(val)
            if num is None:
                return str(val) if val else 'N/A'
            # KG on a price field is a known LLM error — should be currency
            if unit in ('KG', 'CT', 'PC', 'PCS', 'L', 'ML'):
                unit = 'THB'  # default currency for Myanmar imports
            if not unit:
                unit = 'THB'
            return f"{num:.4f}{unit}"

        def _normalize_exchange(val):
            """Normalize exchange rate: CURRENCY + NUMBER."""
            num, unit = _split_num_unit(val)
            if num is None:
                return str(val) if val else 'N/A'
            if not unit:
                unit = 'THB'
            return f"{unit} {num:.4f}"

        def _normalize_quantity(val):
            """Normalize quantity: NUMBER + UNIT, keep original unit."""
            num, unit = _split_num_unit(val)
            if num is None:
                return str(val) if val else 'N/A'
            if not unit:
                unit = 'KG'
            # Format: whole number if no decimals, else 2 decimals
            if num == int(num):
                return f"{int(num)}{unit}"
            return f"{num:.2f}{unit}"

        for job in all_jobs:
            job_details = database.get_job_details(job['job_id'])
            if job_details and job_details.get('items'):
                total_jobs_with_items += 1
                pdf_names_set.add(job['pdf_name'])
                created = job.get('created_at', '') or ''
                for item in job_details['items']:
                    qty_num, qty_unit = _split_num_unit(item.get('quantity'))
                    price_num, price_unit = _split_num_unit(item.get('invoice_unit_price'))
                    exch_num, exch_unit = _split_num_unit(item.get('exchange_rate'))

                    # Fix known LLM errors
                    if price_unit in ('KG', 'CT', 'PC', 'PCS', 'L', 'ML'):
                        price_unit = 'THB'
                    if not price_unit:
                        price_unit = 'THB'
                    if not qty_unit:
                        qty_unit = 'KG'
                    if not exch_unit:
                        exch_unit = 'THB'

                    all_items_data.append({
                        'Job ID': job['job_id'],
                        'PDF Name': job['pdf_name'],
                        'Created': created[:19],
                        'Item Name': item.get('item_name', 'N/A'),
                        'Duty Rate': _fmt_num(item.get('customs_duty_rate'), 2),
                        'Tax %': _fmt_num(item.get('commercial_tax_percent'), 2),
                        'Quantity': f"{qty_num:.2f}" if qty_num is not None and qty_num != int(qty_num) else str(int(qty_num)) if qty_num is not None else 'N/A',
                        'Unit': qty_unit,
                        'Unit Price': f"{price_num:.4f}" if price_num is not None else 'N/A',
                        'Currency': price_unit,
                        'Exchange Rate': f"{exch_num:.4f}" if exch_num is not None else 'N/A',
                        'Exch Currency': exch_unit,
                    })

        if all_items_data:
            col1, col2, col3 = st.columns(3)
            with col1:
                ui.metric_card(title="Total Jobs", content=str(total_jobs_with_items), key="items_metric_jobs")
            with col2:
                ui.metric_card(title="Total Items", content=str(len(all_items_data)), key="items_metric_total")
            with col3:
                ui.metric_card(title="Fields per Item", content="6", key="items_metric_fields")

            st.markdown("---")

            f1, f2, f3 = st.columns(3)
            with f1:
                filter_pdf = st.selectbox("Filter by PDF", options=["All PDFs"] + sorted(list(pdf_names_set)), key="items_filter_pdf")
            with f2:
                items_date_range = st.date_input("Filter by date range", value=[], key="items_date_range")
            with f3:
                search_item = st.text_input("Search item name", value="", key="items_search")

            df_all_items = pd.DataFrame(all_items_data)
            if filter_pdf and filter_pdf != "All PDFs":
                df_all_items = df_all_items[df_all_items['PDF Name'] == filter_pdf]
            if items_date_range and len(items_date_range) == 2:
                d_start, d_end = str(items_date_range[0]), str(items_date_range[1])
                df_all_items = df_all_items[(df_all_items['Created'].str[:10] >= d_start) & (df_all_items['Created'].str[:10] <= d_end)]
            if search_item:
                df_all_items = df_all_items[df_all_items['Item Name'].str.contains(search_item, case=False, na=False)]

            render_export_buttons(df_all_items, "product_items")
            st.markdown("---")
            st.dataframe(df_all_items, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(df_all_items)} of {len(all_items_data)} items")
        else:
            st.info("No product items found in any processed jobs")

# =============================================================================
# TAB 5: DECLARATION DATA
# =============================================================================

elif selected_tab == 'Declaration Data':
    st.header("Declaration Data (All Jobs)" if is_admin else "Declaration Data (My Jobs)")

    all_jobs = database.get_all_jobs(limit=1000) if is_admin else database.get_user_jobs(current_user['id'], limit=1000)

    if not all_jobs:
        ui.alert(title="No Data", description="Process a PDF first to see extracted data.", key="decl_empty_alert")
    else:
        all_declarations_data = []
        total_jobs_with_declarations = 0
        decl_pdf_names_set = set()

        def _fmt_money(val):
            """Format monetary value consistently — no decimals for whole numbers, 2 decimals otherwise."""
            if val is None or val == 'N/A' or val == '':
                return 'N/A'
            try:
                num = float(val)
                return f"{num:,.2f}"
            except (ValueError, TypeError):
                return str(val)

        def _fmt_rate(val):
            """Format rate with 4 decimal places."""
            if val is None or val == 'N/A' or val == '':
                return 'N/A'
            try:
                return f"{float(val):.4f}"
            except (ValueError, TypeError):
                return str(val)

        for job in all_jobs:
            job_details = database.get_job_details(job['job_id'])
            if job_details and job_details.get('declarations'):
                total_jobs_with_declarations += 1
                decl_pdf_names_set.add(job['pdf_name'])
                created = job.get('created_at', '') or ''
                for decl in job_details['declarations']:
                    inv_currency = decl.get('currency', 'THB') or 'THB'
                    local_currency = decl.get('currency_2', '') or decl.get('currency.1', '') or 'MMK'

                    all_declarations_data.append({
                        'Job ID': job['job_id'],
                        'PDF Name': job['pdf_name'],
                        'Created': created[:19],
                        'Declaration No': decl.get('declaration_no', 'N/A'),
                        'Declaration Date': decl.get('declaration_date', 'N/A'),
                        'Importer': decl.get('importer_name', 'N/A'),
                        'Consignor': decl.get('consignor_name', 'N/A'),
                        'Invoice No': decl.get('invoice_number', 'N/A'),
                        'Invoice Price': _fmt_money(decl.get('invoice_price')),
                        'Invoice CCY': inv_currency,
                        'Exchange Rate': _fmt_rate(decl.get('exchange_rate')),
                        'Exchange Pair': f"{inv_currency}/{local_currency}",
                        'Customs Value': _fmt_money(decl.get('total_customs_value')),
                        'Customs Value CCY': local_currency,
                        'Customs Duty': _fmt_money(decl.get('import_export_customs_duty')),
                        'Customs Duty CCY': local_currency,
                        'Commercial Tax': _fmt_money(decl.get('commercial_tax_ct')),
                        'Commercial Tax CCY': local_currency,
                        'Income Tax': _fmt_money(decl.get('advance_income_tax_at')),
                        'Income Tax CCY': local_currency,
                        'Security Fee': _fmt_money(decl.get('security_fee_sf')),
                        'Security Fee CCY': local_currency,
                        'MACCS Fee': _fmt_money(decl.get('maccs_service_fee_mf')),
                        'MACCS Fee CCY': local_currency,
                        'Exemption': _fmt_money(decl.get('exemption_reduction')),
                        'Exemption CCY': local_currency,
                    })

        if all_declarations_data:
            col1, col2, col3 = st.columns(3)
            with col1:
                ui.metric_card(title="Total Jobs", content=str(total_jobs_with_declarations), key="decl_metric_jobs")
            with col2:
                ui.metric_card(title="Total Declarations", content=str(len(all_declarations_data)), key="decl_metric_total")
            with col3:
                ui.metric_card(title="Fields per Declaration", content="16", key="decl_metric_fields")

            st.markdown("---")

            f1, f2, f3 = st.columns(3)
            with f1:
                filter_decl_pdf = st.selectbox("Filter by PDF", options=["All PDFs"] + sorted(list(decl_pdf_names_set)), key="decl_filter_pdf")
            with f2:
                decl_date_range = st.date_input("Filter by date range", value=[], key="decl_date_range")
            with f3:
                search_decl = st.text_input("Search (importer, declaration no...)", value="", key="decl_search")

            df_all_declarations = pd.DataFrame(all_declarations_data)
            if filter_decl_pdf and filter_decl_pdf != "All PDFs":
                df_all_declarations = df_all_declarations[df_all_declarations['PDF Name'] == filter_decl_pdf]
            if decl_date_range and len(decl_date_range) == 2:
                d_start, d_end = str(decl_date_range[0]), str(decl_date_range[1])
                df_all_declarations = df_all_declarations[(df_all_declarations['Created'].str[:10] >= d_start) & (df_all_declarations['Created'].str[:10] <= d_end)]
            if search_decl:
                mask = df_all_declarations.apply(lambda row: search_decl.lower() in ' '.join(str(v) for v in row.values).lower(), axis=1)
                df_all_declarations = df_all_declarations[mask]

            render_export_buttons(df_all_declarations, "declarations")
            st.markdown("---")
            st.dataframe(df_all_declarations, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(df_all_declarations)} of {len(all_declarations_data)} declarations")
        else:
            st.info("No declaration data found in any processed jobs")

# =============================================================================
# TAB 5: DOCUMENT SEARCH
# =============================================================================

elif selected_tab == 'Document Search':
    st.header("Document Search")
    st.caption("Search across all extracted page content from processed PDFs")

    # Determine user scope
    _search_uid = None if is_admin else current_user['id']

    # Stats
    pc_stats = database.get_page_content_stats(user_id=_search_uid)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        ui.metric_card(title="PDFs", content=str(pc_stats['total_pdfs']), key="ds_pdfs")
    with col2:
        ui.metric_card(title="Pages", content=str(pc_stats['total_pages']), key="ds_pages")
    with col3:
        ui.metric_card(title="Text Pages", content=str(pc_stats['text_pages']), key="ds_text")
    with col4:
        ui.metric_card(title="Image Pages", content=str(pc_stats['image_pages']), key="ds_image")
    with col5:
        chars_k = pc_stats['total_chars'] / 1000
        ui.metric_card(title="Total Chars", content=f"{chars_k:.0f}K", key="ds_chars")

    # Document overview charts
    all_pc = database.get_all_page_contents(user_id=_search_uid, limit=1000)
    if all_pc:
        ds_c1, ds_c2 = st.columns(2)

        with ds_c1:
            # Treemap — pages by PDF, size = chars, color = type
            tree_data = []
            for p in all_pc:
                tree_data.append({
                    'PDF': (p.get('pdf_name') or '')[:30],
                    'Page': f"Pg {p.get('page_number', 0)}",
                    'Type': p.get('page_type', 'TEXT'),
                    'Chars': p.get('char_count', 0) or 1
                })
            tree_df = pd.DataFrame(tree_data)
            fig_tree = px.treemap(
                tree_df, path=['PDF', 'Page'], values='Chars',
                color='Type', color_discrete_map={'TEXT': '#3b82f6', 'IMAGE': '#f59e0b'},
            )
            fig_tree.update_layout(
                title=dict(text='Pages by PDF (size = content length)', font=dict(size=13)),
                height=300, margin=dict(l=5, r=5, t=35, b=5),
                paper_bgcolor='rgba(0,0,0,0)',
            )
            fig_tree.update_traces(textinfo='label+value', textfont=dict(size=10))
            st.plotly_chart(fig_tree, use_container_width=True)

        with ds_c2:
            # Stacked bar — text vs image pages per PDF
            pdf_breakdown = {}
            for p in all_pc:
                pdf = (p.get('pdf_name') or '')[:25]
                ptype = p.get('page_type', 'TEXT')
                if pdf not in pdf_breakdown:
                    pdf_breakdown[pdf] = {'TEXT': 0, 'IMAGE': 0}
                pdf_breakdown[pdf][ptype] = pdf_breakdown[pdf].get(ptype, 0) + 1

            pdfs = list(pdf_breakdown.keys())
            fig_stack = go.Figure()
            fig_stack.add_trace(go.Bar(
                name='Text', x=pdfs,
                y=[pdf_breakdown[p]['TEXT'] for p in pdfs],
                marker_color='#3b82f6'
            ))
            fig_stack.add_trace(go.Bar(
                name='Image', x=pdfs,
                y=[pdf_breakdown[p]['IMAGE'] for p in pdfs],
                marker_color='#f59e0b'
            ))
            fig_stack.update_layout(
                title=dict(text='Page Types per PDF', font=dict(size=13)),
                barmode='stack', height=300,
                margin=dict(l=10, r=10, t=35, b=80),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9), showgrid=False),
                yaxis=dict(title='Pages', gridcolor='#f1f5f9'),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1e293b'), legend=dict(orientation='h', y=1.12)
            )
            st.plotly_chart(fig_stack, use_container_width=True)

    st.markdown("---")

    # Filters
    f1, f2, f3 = st.columns([3, 1.5, 1.5])
    with f1:
        search_query = st.text_input("Search documents...", placeholder="e.g. Whipping Cream, invoice, 100308...", key="ds_search")
    with f2:
        pdf_list = database.get_page_content_pdfs(user_id=_search_uid)
        filter_pdf = st.selectbox("PDF", options=["All PDFs"] + pdf_list, key="ds_pdf_filter")
    with f3:
        filter_type = st.selectbox("Page Type", options=["All Types", "TEXT", "IMAGE"], key="ds_type_filter")

    # Fetch results
    if search_query and search_query.strip():
        results = database.search_page_contents(
            query=search_query, user_id=_search_uid,
            pdf_name=filter_pdf, page_type=filter_type, limit=200
        )
    else:
        results = database.get_all_page_contents(
            user_id=_search_uid, pdf_name=filter_pdf,
            page_type=filter_type, limit=200
        )

    if results:
        st.caption(f"Found {len(results)} pages")

        # Build table
        table_data = []
        for r in results:
            content_preview = (r.get('content') or '')[:150].replace('\n', ' ')
            if search_query and '**' in (r.get('snippet') or ''):
                content_preview = (r.get('snippet') or '')[:150].replace('\n', ' ')

            table_data.append({
                'PDF': (r.get('pdf_name') or '')[:35],
                'Page': r.get('page_number', 0),
                'Type': r.get('page_type', ''),
                'Agent': (r.get('source_agent') or '').replace(' (text extraction)', '').replace(' (OCR)', ''),
                'Chars': r.get('char_count', 0),
                'Content Preview': content_preview,
            })

        df_pages = pd.DataFrame(table_data)
        st.dataframe(df_pages, use_container_width=True, hide_index=True)

        # Export
        st.markdown("---")
        export_data = []
        for r in results:
            export_data.append({
                'PDF Name': r.get('pdf_name', ''),
                'Job ID': r.get('job_id', ''),
                'Page': r.get('page_number', 0),
                'Type': r.get('page_type', ''),
                'Source Agent': r.get('source_agent', ''),
                'Chars': r.get('char_count', 0),
                'Content': r.get('content', ''),
            })
        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("Export All Page Content (CSV)", data=csv,
            file_name=f"page_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", type="primary")

        # Expandable full content per page
        st.markdown("---")
        st.subheader("Full Page Content")
        st.caption("Expand to read the full extracted text of each page")

        # Group by PDF
        from collections import OrderedDict
        grouped = OrderedDict()
        for r in results:
            pdf = r.get('pdf_name', 'Unknown')
            if pdf not in grouped:
                grouped[pdf] = []
            grouped[pdf].append(r)

        for pdf_name, pages in grouped.items():
            with st.expander(f"{pdf_name} ({len(pages)} pages)", expanded=False):
                for pg in pages:
                    pg_num = pg.get('page_number', 0)
                    pg_type = pg.get('page_type', '')
                    agent = pg.get('source_agent', '')
                    chars = pg.get('char_count', 0)
                    content = pg.get('content', '')

                    type_icon = "T" if pg_type == "TEXT" else "I"
                    st.markdown(f"**Page {pg_num}** `{type_icon}` | {agent} | {chars} chars")
                    if content:
                        st.code(content[:3000], language=None)
                    else:
                        st.caption("No content extracted")
                    st.markdown("---")
    else:
        if search_query:
            st.info(f"No results found for \"{search_query}\"")
        else:
            st.info("No page content stored yet. Process a PDF to populate this tab.")


# =============================================================================
# TAB 6: USER MANAGEMENT (ADMIN ONLY)
# =============================================================================

elif selected_tab == 'User Management' and is_admin:
    render_admin_user_management()
