import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date, timedelta
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER
from streamlit_cookies_manager import EncryptedCookieManager


# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Family Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Cookies ─────────────────────────────────────────────────────────────
cookies = EncryptedCookieManager(
    prefix="expense_tracker_",
    password="expense_tracker_secret_key"
)

if not cookies.ready():
    st.stop()

DATA_DIR = "user_data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = "users.json"
DATA_FILE = ""
CONFIG_FILE = ""
SALARY_FILE = ""
LOAN_FILE = ""
SAVINGS_FILE = ""

# ── Defaults (used only when config has no saved list yet)
DEFAULT_SAVING_GOAL = 60000
DEFAULT_CATEGORIES = [
    "🛒 Groceries", "🍽️ Dining Out", "🚗 Transport", "💊 Healthcare",
    "🍖 Meat", "💐 Flowers", "🥦 Vegetables", "🥛 Milk", "🍎 Fruits",
    "🎓 Education", "🎮 Entertainment", "👗 Clothing", "🏠 Utilities",
    "🛠️ Home Maintenance", "📦 Shopping", "✈️ Travel", "💰 Savings/Investment",
    "🎁 Gifts", "📱 Subscriptions", "🏋️ Fitness", "🥤 Chats/Juice",
    "📚 Books/Learning", "🔧 Miscellaneous"]
DEFAULT_MEMBERS = ["Shared", "Wife", "Parent", "Child 1", "Child 2", "Friends"]
PAYMENT_METHODS = ["UPI", "Cash", "Credit Card", "Debit Card", "Net Banking", "Other"]
CATEGORY_EMOJIS = ["🛒", "🍽️", "🚗", "💊", "🎓", "🎮", "👗", "🏠", "🛠️", "📦", "✈️", "💰", "🐾", "🎁", "📱",
                   "🏋️", "📚", "🔧", "🎯", "🌿", "🏥", "🧴", "🍕", "🍖", "☕", "🎵", "🖥️", "📷", "🧹", "🚿",
                   "💡", "🏦", "🎪", "🧪", "🪴", "🐶", "🍎", "🎂", "🚌", "🎨", "🏡", "🔑", "🪑", "🛋️"]
MEMBER_EMOJIS = ["👤", "👨", "👩", "🧒", "👧", "👦", "👴", "👵", "🧑", "👨‍💼", "👩‍💼", "🧑‍💻", "👶", "🧓"]
DEFAULT_SAVING_TYPES = [
    "Savings Account",
    "Fixed Deposit (FD)",
    "Recurring Deposit (RD)",
    "Mutual Fund",
    "Education",
    "Gold/Silver",
    "Other"
]
PAGES = [
    "🏠 Dashboard",
    "➕ Add Expense",
    "💼 Salary",
    "🤝 Loans",
    "💳 Loans Payments",
    "🏦 Savings",
    "📋 All Expenses",
    "📊 Charts",
    "🎯 Budget Limits",
    "🏷️ Manage Lists",
    "📄 Export PDF",
]

CAT_COLORS = px.colors.qualitative.Pastel + px.colors.qualitative.Bold


# ─── Data helpers ─────────────────────────────────────────────────────────────

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump([], f)

    with open(USERS_FILE, "r") as f:
        return json.load(f)


def authenticate(username, password):
    users = load_users()

    username = username.strip().lower()

    return any(
        u["username"].strip().lower() == username and
        u["password"] == password
        for u in users
    )


def get_user_dir():
    username = st.session_state.username.lower()

    user_dir = os.path.join(DATA_DIR, username)

    os.makedirs(user_dir, exist_ok=True)

    return user_dir


def get_user_file(filename):
    return os.path.join(
        get_user_dir(),
        filename
    )


def load_expenses():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        df_load = pd.DataFrame(data)
        if not df_load.empty:
            df_load["date"] = pd.to_datetime(df_load["date"]).dt.date
            df_load["amount"] = pd.to_numeric(df_load["amount"])
        return df_load
    return pd.DataFrame(
        columns=["id", "date", "category", "description", "amount", "member", "payment_method", "notes"])


def save_expenses(df_save_exp):
    records = df_save_exp.copy()
    records["date"] = records["date"].astype(str)
    with open(DATA_FILE, "w") as f:
        json.dump(records.to_dict("records"), f, indent=2)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg_load = json.load(f)
        cfg_load.setdefault("categories", DEFAULT_CATEGORIES.copy())
        cfg_load.setdefault("members", DEFAULT_MEMBERS.copy())
        cfg_load.setdefault("saving_types", DEFAULT_SAVING_TYPES.copy())
        return cfg_load
    return {
        "limits": {}, "currency": "₹", "family_name": "My Family",
        "categories": DEFAULT_CATEGORIES.copy(),
        "members": DEFAULT_MEMBERS.copy(),
        "saving_types": DEFAULT_SAVING_TYPES.copy()
    }


def save_config(cfg_save):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg_save, f, indent=2)


def next_id(df_next):
    return int(df_next["id"].max()) + 1 if not df_next.empty else 1


def get_categories(): return st.session_state.config.get("categories", DEFAULT_CATEGORIES)


def get_members():    return st.session_state.config.get("members", DEFAULT_MEMBERS)


def load_json(file, default=None):
    if default is None:
        default = []
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


# ─── PDF Generator ────────────────────────────────────────────────────────────

def generate_pdf(pdf_df, pdf_start_date, pdf_end_date, config):
    buf = BytesIO()
    d_currency = config.get("currency", "₹")
    d_fam_name = config.get("family_name", "My Family")
    d_limits = config.get("limits", {})

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("TS", parent=styles["Title"],
                                 fontSize=20, textColor=colors.HexColor("#1e3a5f"), spaceAfter=4)
    sub_style = ParagraphStyle("SS", parent=styles["Normal"],
                               fontSize=11, textColor=colors.HexColor("#5a5a5a"),
                               alignment=TA_CENTER, spaceAfter=2)

    story.append(Paragraph(f"{d_fam_name} — Expense Report", title_style))
    story.append(
        Paragraph(f"Period: {pdf_start_date.strftime('%d %b %Y')} to {pdf_end_date.strftime('%d %b %Y')}", sub_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a5f"), spaceAfter=10))

    total = pdf_df["amount"].sum()
    daily_avg = total / max((pdf_end_date - pdf_start_date).days + 1, 1)
    top_cat = pdf_df.groupby("category")["amount"].sum().idxmax() if not pdf_df.empty else "—"

    summary_data = [
        ["Total Spending", f"{d_currency} {total:,.2f}"],
        ["Daily Average", f"{d_currency} {daily_avg:,.2f}"],
        ["Transactions", str(len(pdf_df))],
        ["Top Category", top_cat],
    ]
    st_ = Table(summary_data, hAlign="LEFT")
    st_.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#dce8f5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c5d8ec")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f0f7ff"), colors.white]),
    ]))
    story.append(st_)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Category Breakdown", styles["Heading2"]))
    cat_df = pdf_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    cat_data = [["Category", f"Amount ({d_currency})", "% of Total", "Limit", "Status"]]
    for _, cat_row in cat_df.iterrows():
        cat_pct = (cat_row["amount"] / total * 100) if total else 0
        limit = d_limits.get(cat_row["category"], 0)
        cat_data.append([
            cat_row["category"],
            f"{d_currency} {cat_row['amount']:,.2f}",
            f"{cat_pct:.1f}%",
            f"{d_currency} {limit:,.2f}" if limit else "—",
            ("OK" if cat_row["amount"] <= limit else "Over") if limit else "",
        ])
    ct_ = Table(cat_data, colWidths=[5.5 * cm, 3 * cm, 2.2 * cm, 3 * cm, 1.8 * cm])
    ct_.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f9ff"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5d8ec")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(ct_)
    story.append(Spacer(1, 14))

    story.append(Paragraph("All Transactions", styles["Heading2"]))
    txn_data = [["Date", "Category", "Description", "Member", "Payment", f"Amount ({d_currency})"]]
    for _, txn_row in pdf_df.sort_values("date").iterrows():
        txn_data.append([
            str(txn_row["date"]), txn_row["category"],
            str(txn_row.get("description", ""))[:35],
            txn_row.get("member", ""), txn_row.get("payment_method", ""),
            f"{txn_row['amount']:,.2f}",
        ])
    txn_data.append(["", "", "", "", "TOTAL", f"{total:,.2f}"])

    tt_ = Table(txn_data,
                colWidths=[2.2 * cm, 4 * cm, 4.2 * cm, 2.2 * cm, 2.5 * cm, 2.3 * cm],
                repeatRows=1)
    tt_.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f5f9ff"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dce8f5")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c5d8ec")),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tt_)
    doc.build(story)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "page" not in st.session_state:
    st.session_state.page = PAGES[0]

# ─────────────────────────────────────────────────────────────
# RESTORE LOGIN FROM COOKIE
# ─────────────────────────────────────────────────────────────
if not st.session_state.logged_in:

    saved_user = cookies.get("username")

    if saved_user:

        saved_user = saved_user.strip().lower()

        st.session_state.logged_in = True
        st.session_state.username = saved_user

# ─────────────────────────────────────────────────────────────
# LOAD USER FILES AFTER LOGIN
# ─────────────────────────────────────────────────────────────
if st.session_state.logged_in:

    DATA_FILE = get_user_file("expenses.json")
    CONFIG_FILE = get_user_file("config.json")
    SALARY_FILE = get_user_file("salary.json")
    LOAN_FILE = get_user_file("loans.json")
    SAVINGS_FILE = get_user_file("savings.json")

    # Load only once
    if "df" not in st.session_state:
        st.session_state.df = load_expenses()

    if "config" not in st.session_state:
        st.session_state.config = load_config()

    if "salary" not in st.session_state:
        st.session_state.salary = load_json(SALARY_FILE)

    if "loans" not in st.session_state:
        st.session_state.loans = load_json(LOAN_FILE)

    if "savings" not in st.session_state:
        st.session_state.savings = load_json(SAVINGS_FILE)

    # Validate page
    if st.session_state.page not in PAGES:
        st.session_state.page = PAGES[0]

    cfg = st.session_state.config

    if "saving_goal" not in cfg:
        cfg["saving_goal"] = DEFAULT_SAVING_GOAL

# ═══════════════════════════════════════
# LOGIN SCREEN
# ═══════════════════════════════════════
if not st.session_state.logged_in:

    st.markdown(
        """
        <style>
        .login-card {
            padding: 30px;
            border-radius: 30px;
            background: linear-gradient(135deg,#111827,#1f2937);
            color: white;
            max-width: 420px;
            margin: auto;
            margin-top: 100px;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="login-card">
            <h1 style="text-align:center;">
                💰 Family Expense Tracker
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    username = st.text_input(
        "Username",
        placeholder="Enter username"
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter password"
    )

    if st.button(
            "🔐 Login",
            width='stretch',
            type="primary"
    ):

        if authenticate(username, password):

            username = username.strip().lower()

            st.session_state.logged_in = True
            st.session_state.username = username

            # Save cookie
            cookies["username"] = username
            cookies.save()

            # Reset cached state
            for key in ["df", "config", "salary", "loans", "savings"]:
                if key in st.session_state:
                    del st.session_state[key]

            st.success("✅ Login successful")

            st.rerun()

        else:
            st.error("❌ Invalid username or password")

    st.stop()

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <style>
        .sidebar-title {
            padding: 16px;
            border-radius: 16px;
            background: linear-gradient(135deg, #111827, #1f2937);
            color: white;
            text-align: center;
            margin-bottom: 15px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="sidebar-title">
            <h2 style="margin-bottom:0;">💰 {st.session_state.config.get('family_name', 'My Family')} Expenses</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────
    # NAVIGATION
    # ─────────────────────────────────────────────
    page = st.radio(
        "📌 Navigate",
        PAGES,
        index=PAGES.index(st.session_state.page),
        key="page_radio"
    )

    st.session_state.page = page

    st.divider()

    currency = st.session_state.config.get("currency", "₹")
    df_side = st.session_state.df
    today = date.today()

    # ─────────────────────────────────────────────
    # MONTHLY SALARY
    # ─────────────────────────────────────────────
    salary_list = (
        st.session_state.salary
        if "salary" in st.session_state
        else []
    )

    current_salary = next(
        (
            s["amount"]
            for s in salary_list
            if s["month"] == today.month
               and s["year"] == today.year
        ),
        0
    )

    st.metric(
        "💼 This Month Salary",
        f"{currency} {current_salary:,.0f}"
    )

    # ─────────────────────────────────────────────
    # MONTHLY EXPENSE
    # ─────────────────────────────────────────────
    month_total = 0

    if not df_side.empty:
        ms = date(today.year, today.month, 1)

        month_total = df_side[
            (df_side["date"] >= ms)
            & (df_side["date"] <= today)
            ]["amount"].sum()

    st.metric(
        "💸 This Month Expense",
        f"{currency} {month_total:,.0f}"
    )

    # ─────────────────────────────────────────────
    # REMAINING BALANCE
    # ─────────────────────────────────────────────
    remaining = current_salary - month_total

    st.metric(
        "💰 Total Balance",
        f"{currency} {remaining:,.0f}"
    )

    # ─────────────────────────────────────────────
    # ACTIVE LOAN LIABILITY
    # ─────────────────────────────────────────────
    active_loans = [
        l for l in st.session_state.loans
        if l.get("status") == "Active"
    ]

    loan_liability = sum(
        l.get("remaining", 0)
        for l in active_loans
    )

    # ─────────────────────────────────────────────
    # TOTAL SAVINGS (ASSET)
    # ─────────────────────────────────────────────
    total_savings = sum(
        s.get("amount", 0)
        for s in st.session_state.savings
    )

    # ─────────────────────────────────────────────
    # SAVINGS BREAKDOWN (NEW)
    # ─────────────────────────────────────────────

    kumar_savings = sum(
        s.get("amount", 0)
        for s in st.session_state.savings
        if s.get("source") == "Kumar"
    )

    other_savings = total_savings - kumar_savings

    st.metric(
        "🏦 Kumar Savings",
        f"{currency} {kumar_savings:,.0f}"
    )

    st.metric(
        "🏛️ Other Savings",
        f"{currency} {other_savings:,.0f}"
    )

    # ─────────────────────────────────────────────
    # AVAILABLE CASH
    # Salary - Expenses - Loan Liability
    # Savings NOT deducted because it is your asset
    # ─────────────────────────────────────────────
    available_cash = (
            remaining - kumar_savings - loan_liability
    )

    # ─────────────────────────────────────────────
    # AVAILABLE CASH CARD
    # ─────────────────────────────────────────────
    st.metric(
        "💵 Available Cash",
        f"{currency} {available_cash:,.0f}",
        delta=f"Loan Liability: {currency} {loan_liability:,.0f}",
        delta_color="inverse"
    )

    # ─────────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────────
    if available_cash < 0:
        st.error(
            f"⚠️ Cash Flow Negative "
            f"({currency} {abs(available_cash):,.0f})"
        )

    else:

        st.success(
            f"✅ Safe Available Cash: "
            f"{currency} {available_cash:,.0f}"
        )

    st.divider()

    st.caption(
        f"👤 Logged in as: "
        f"{st.session_state.username}"
    )
    if st.button(
            "🚪 Logout",
            width='stretch',
            type="secondary"
    ):
        cookies["username"] = ""
        cookies.save()

        # Clear session
        for key in [
            "logged_in",
            "username",
            "df",
            "config",
            "salary",
            "loans",
            "savings"
        ]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "🏠 Dashboard":

    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    df = st.session_state.df.copy()

    st.title("🏠 Smart Financial Dashboard")

    # ════════════════════════════════════════════
    # FILTER BAR
    # ════════════════════════════════════════════
    with st.container(border=True):

        st.subheader("📅 Analytics Filter")

        fc1, fc2, fc3 = st.columns([1, 1, 1])

        today = date.today()

        with fc1:

            filter_type = st.selectbox(
                "View",
                [
                    "Current Month",
                    "Last 30 Days",
                    "Custom Range"
                ]
            )

        if filter_type == "Current Month":

            start_date = date(
                today.year,
                today.month,
                1
            )

            end_date = today

        elif filter_type == "Last 30 Days":

            start_date = today - timedelta(days=30)
            end_date = today

        else:

            with fc2:
                start_date = st.date_input(
                    "Start Date",
                    value=today.replace(day=1),
                    max_value=today
                )

            with fc3:
                end_date = st.date_input(
                    "End Date",
                    value=today,
                    max_value=today
                )

        st.caption(
            f"📌 "
            f"{start_date.strftime('%d %b %Y')} "
            f"→ "
            f"{end_date.strftime('%d %b %Y')}"
        )

    # ════════════════════════════════════════════
    # FILTER DATA
    # ════════════════════════════════════════════
    if not df.empty:

        filtered_df = df[
            (df["date"] >= start_date) &
            (df["date"] <= end_date)
            ].copy()

    else:
        filtered_df = pd.DataFrame()

    if filtered_df.empty:
        st.info("No expenses found.")
        st.stop()

    # ════════════════════════════════════════════
    # CORE CALCULATIONS
    # ════════════════════════════════════════════
    total_spent = filtered_df["amount"].sum()

    highest_spend = filtered_df["amount"].max()

    avg_daily = (
            total_spent /
            max((end_date - start_date).days + 1, 1)
    )

    txns = len(filtered_df)

    current_salary = next(
        (
            s["amount"]
            for s in st.session_state.salary
            if s["month"] == end_date.month
               and s["year"] == end_date.year
        ),
        0
    )

    savings_total = sum(
        s["amount"]
        for s in st.session_state.savings
    )

    kumar_savings = sum(
        s["amount"]
        for s in st.session_state.savings
        if s.get("source") == "Kumar"
    )

    other_savings = savings_total - kumar_savings

    active_loans = [
        l for l in st.session_state.loans
        if l.get("status") == "Active"
    ]

    loan_due = sum(
        l["remaining"]
        for l in active_loans
    )

    available_cash = (
            current_salary
            - total_spent
            - loan_due
    )

    expense_ratio = (
        (total_spent / current_salary) * 100
        if current_salary else 0
    )

    savings_ratio = (
        (savings_total / current_salary) * 100
        if current_salary else 0
    )

    # ════════════════════════════════════════════
    # HERO METRICS
    # ════════════════════════════════════════════
    st.subheader("📌 Financial Snapshot")

    h1, h2, h3, h4 = st.columns(4)

    h1.metric(
        "💸 Total Spent",
        f"{currency} {total_spent:,.0f}"
    )

    h2.metric(
        "🧾 Transactions",
        txns
    )

    h3.metric(
        "📅 Daily Average",
        f"{currency} {avg_daily:,.0f}"
    )

    h4.metric(
        "🔥 Highest Expense",
        f"{currency} {highest_spend:,.0f}"
    )

    # ════════════════════════════════════════════
    # WEALTH CARDS
    # ════════════════════════════════════════════
    st.divider()

    st.subheader("💰 Wealth Overview")

    w1, w2, w3, w4 = st.columns(4)

    w1.metric(
        "💼 Salary",
        f"{currency} {current_salary:,.0f}"
    )

    w2a, w2b = st.columns(2)

    w2a.metric(
        "🏦 Kumar Savings",
        f"{currency} {kumar_savings:,.0f}"
    )

    w2b.metric(
        "🏛️ Other Savings",
        f"{currency} {other_savings:,.0f}"
    )

    w3.metric(
        "💳 Loan Due",
        f"{currency} {loan_due:,.0f}"
    )

    w4.metric(
        "💵 Available Cash",
        f"{currency} {available_cash:,.0f}"
    )

    savings_df = pd.DataFrame(st.session_state.savings)

    if not savings_df.empty:
        savings_df["amount"] = pd.to_numeric(savings_df["amount"], errors="coerce")
    else:
        savings_df = pd.DataFrame(columns=["amount", "source"])

    st.divider()
    st.subheader("🔥 Savings Analytics Panel")

    source_summary = (
        savings_df.groupby("source")["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    total_savings = source_summary["amount"].sum()

    source_summary["contribution_%"] = (
            source_summary["amount"] / total_savings * 100
    )

    top_source = source_summary.iloc[0]

    insights = []

    insights.append(
        f"🏆 **{top_source['source']}** contributes the highest savings at "
        f"{top_source['contribution_%']:.1f}%"
    )

    for _, row in source_summary.iterrows():
        insights.append(
            f"👤 {row['source']} contributes {row['contribution_%']:.1f}% "
            f"({currency} {row['amount']:,.0f})"
        )

    # Dominance rule
    if top_source["contribution_%"] >= 70:
        insights.append(
            f"🔥 **{top_source['source']} dominates savings with "
            f"{top_source['contribution_%']:.1f}% contribution**"
        )
    elif top_source["contribution_%"] >= 50:
        insights.append(
            f"⚖️ Savings are moderately concentrated in {top_source['source']}."
        )
    else:
        insights.append(
            "📊 Savings are well distributed across members."
        )

    col1, col2 = st.columns([1, 1])

    with col1:

        fig2 = px.pie(
            source_summary,
            names="source",
            values="amount",
            hole=0.5
        )

        fig2.update_traces(textposition="inside", textinfo="percent+label")

        st.plotly_chart(fig2, use_container_width=True)

    with col2:

        st.subheader("🧠 Insights")

        for i, text in enumerate(insights):
            st.write(f"{i + 1}. {text}")

    # ════════════════════════════════════════════
    # FINANCIAL SCORE + PERSONALITY
    # ════════════════════════════════════════════
    st.divider()

    c1, c2 = st.columns([1, 1])

    score = 100

    if expense_ratio > 80:
        score -= 25

    if loan_due > current_salary:
        score -= 30

    if savings_ratio > 30:
        score += 10

    score = max(0, min(score, 100))

    with c1:

        st.subheader("🏅 Financial Score")

        st.progress(score / 100)

        st.metric(
            "Overall Score",
            f"{score}/100"
        )

    with c2:

        st.subheader("🧠 Spending Personality")

        if expense_ratio < 40:
            personality = "Excellent Saver 🟢"

        elif expense_ratio < 70:
            personality = "Balanced Spender 🟡"

        else:
            personality = "Aggressive Spender 🔴"

        st.success(
            f"""
            ### {personality}

            - Expense Usage: {expense_ratio:.1f}%
            - Savings Rate: {savings_ratio:.1f}%
            """
        )

    # ════════════════════════════════════════════
    # SAVINGS INSIGHT + CASH RUNWAY
    # ════════════════════════════════════════════
    st.divider()

    i1, i2 = st.columns(2)

    top_category = (
        filtered_df.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    highest_cat = top_category.index[0]
    highest_amt = top_category.iloc[0]

    potential_save = highest_amt * 0.20

    with i1:

        st.info(
            f"""
            ### 💡 Savings Insight

            Highest Spending:
            **{highest_cat}**

            Current Spend:
            {currency} {highest_amt:,.0f}

            Possible Savings:
            {currency} {potential_save:,.0f}
            """
        )

    burn_rate = avg_daily

    days_left = (
        available_cash / burn_rate
        if burn_rate else 0
    )

    with i2:

        st.warning(
            f"""
            ### 🔥 Cash Runway

            Your current cash can sustain for: 
            ## {days_left:.0f} Days
            Based on average daily spending.
            """
        )

    # ════════════════════════════════════════════
    # SAVINGS GOAL
    # ════════════════════════════════════════════
    st.divider()

    goal = cfg.get("saving_goal", 60000)

    progress = (
        (savings_total / goal) * 100
        if goal else 0
    )

    st.subheader("🎯 Savings Goal")

    st.progress(min(progress / 100, 1.0))

    sg1, sg2, sg3 = st.columns(3)

    sg1.metric(
        "Goal Amount",
        f"{currency} {goal:,.0f}"
    )

    sg2.metric(
        "Saved",
        f"{currency} {savings_total:,.0f}"
    )

    sg3.metric(
        "Completion",
        f"{progress:.1f}%"
    )

    remaining_goal = goal - savings_total

    if remaining_goal > 0:
        st.info(
            f"💰 You need {currency} {remaining_goal:,.0f} more to reach your goal."
        )
    else:
        st.success("🎉 Savings goal achieved!")

    # ════════════════════════════════════════════
    # MONTHLY COMPARISON
    # ════════════════════════════════════════════
    st.divider()

    previous_month = today.month - 1 or 12

    previous_year = (
        today.year
        if today.month != 1
        else today.year - 1
    )

    prev_df = df[
        (
                pd.to_datetime(df["date"]).dt.month
                == previous_month
        ) &
        (
                pd.to_datetime(df["date"]).dt.year
                == previous_year
        )
        ]

    prev_total = prev_df["amount"].sum()

    change = total_spent - prev_total

    change_pct = (
        (change / prev_total) * 100
        if prev_total else 0
    )

    st.subheader("📊 Monthly Comparison")

    mc1, mc2 = st.columns(2)

    mc1.metric(
        "Current Spending",
        f"{currency} {total_spent:,.0f}"
    )

    mc2.metric(
        "Monthly Change",
        f"{change_pct:.1f}%",
        delta=f"{currency} {change:,.0f}"
    )

    # ════════════════════════════════════════════
    # UNUSUAL EXPENSES
    # ════════════════════════════════════════════
    threshold = (
            filtered_df["amount"].mean() * 2
    )

    unusual = filtered_df[
        filtered_df["amount"] > threshold
        ]

    if not unusual.empty:
        st.divider()

        st.subheader("🚨 Unusual Expenses")

        st.dataframe(
            unusual[
                [
                    "date",
                    "category",
                    "amount"
                ]
            ],
            width='stretch',
            hide_index=True
        )

    # ════════════════════════════════════════════
    # CHARTS
    # ════════════════════════════════════════════
    st.divider()

    vc1, vc2 = st.columns([1.4, 1])

    with vc1:

        st.subheader("📈 Spending Trend")

        chart_df = filtered_df.copy()

        chart_df["day"] = pd.to_datetime(
            chart_df["date"]
        ).dt.strftime("%d-%b")

        daily = (
            chart_df.groupby("day")["amount"]
            .sum()
            .reset_index()
        )

        fig = px.area(
            daily,
            x="day",
            y="amount",
            markers=True,
            line_shape="spline"
        )

        fig.update_traces(
            mode="lines+markers",
            fill="tozeroy"
        )

        fig.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(t=10, b=10),
            xaxis_title=None,
            yaxis_title=None
        )

        st.plotly_chart(
            fig,
            width='stretch'
        )

    with vc2:

        st.subheader("🍩 Expense Split")

        cat = (
            filtered_df.groupby("category")["amount"]
            .sum()
            .reset_index()
        )

        fig2 = px.pie(
            cat,
            names="category",
            values="amount",
            hole=0.60,
            color_discrete_sequence=CAT_COLORS
        )

        fig2.update_traces(
            textposition="inside",
            textinfo="percent"
        )

        fig2.update_layout(
            height=380,
            margin=dict(t=10, b=10)
        )

        st.plotly_chart(
            fig2,
            width='stretch'
        )

    # ════════════════════════════════════════════
    # WARNINGS
    # ════════════════════════════════════════════
    st.divider()

    if expense_ratio >= 80:
        st.warning(
            "⚠️ Expenses are above 80% of salary."
        )

    if loan_due > current_salary > 0:
        st.warning(
            "⚠️ Loan dues exceed salary."
        )

    if available_cash < 0:
        st.error(
            "🚨 Negative available balance detected."
        )

# ══════════════════════════════════════════════════════════════════════════════
# ➕ ADD EXPENSE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "➕ Add Expense":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    CATS = get_categories()
    MEMS = get_members()

    st.title("➕ Add New Expense")

    with st.form("add_expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            exp_date = st.date_input(
                "Date",
                value=date.today(),
                max_value=date.today()
            )
            category = st.selectbox("Category", CATS)
            description = st.text_input("Description", placeholder="e.g. Weekly groceries")
        with c2:
            amount = st.number_input(
                f"Amount ({currency})",
                min_value=0.0,
                step=10.0,
                placeholder="Enter amount",
                format="%.0f"
            )
            member = st.selectbox("Family Member", MEMS)
            payment = st.selectbox("Payment Method", PAYMENT_METHODS)
        notes = st.text_area("Notes (optional)", height=80)
        submitted = st.form_submit_button(
            "💾 Save Expense",
            width='stretch',
            type="primary"
        )

        if submitted:
            if amount is None or amount <= 0:
                st.warning(
                    "⚠️ Please enter a valid amount greater than 0."
                )
                st.stop()

            df = st.session_state.df
            nr = {"id": next_id(df), "date": exp_date, "category": category,
                  "description": description, "amount": amount,
                  "member": member, "payment_method": payment, "notes": notes}
            st.session_state.df = pd.concat([df, pd.DataFrame([nr])], ignore_index=True)
            save_expenses(st.session_state.df)
            st.success(f"✅ Expense {currency} {amount:,.2f} for **{category}**")

            limits = cfg.get("limits", {})
            if category in limits:
                today = date.today()
                ms = date(today.year, today.month, 1)
                spent = st.session_state.df[
                    (st.session_state.df["category"] == category) &
                    (st.session_state.df["date"] >= ms) &
                    (st.session_state.df["date"] <= today)]["amount"].sum()
                lim = limits[category]
                if spent > lim:
                    st.warning(f"⚠️ Over budget for **{category}**! {currency} {spent:,.0f} / {currency} {lim:,.0f}")
                elif spent / lim >= 0.8:
                    st.info(f"ℹ️ {spent / lim * 100:.0f}% of {currency} {lim:,.0f} budget used for **{category}**.")

    st.divider()
    st.subheader("⚡ Quick Add — Today")
    quick = CATS[:4]
    qcols = st.columns(len(quick))
    for i, qcat in enumerate(quick):
        with qcols[i]:
            with st.expander(qcat):
                qa = st.number_input(currency, min_value=0.01, step=10.0, key=f"q_{i}", format="%.2f")
                qdesc = st.text_input("Note", key=f"qd_{i}")
                if st.button("Add", key=f"qb_{i}", width='stretch'):
                    df = st.session_state.df
                    nr = {"id": next_id(df), "date": date.today(), "category": qcat,
                          "description": qdesc, "amount": qa, "member": MEMS[0],
                          "payment_method": "Cash", "notes": ""}
                    st.session_state.df = pd.concat([df, pd.DataFrame([nr])], ignore_index=True)
                    save_expenses(st.session_state.df)
                    st.success("Saved!")

# ══════════════════════════════════════════════════════════════════════════════
# 💼 Salary
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "💼 Salary":
    st.title("💼 Salary Management")

    salaries = st.session_state.salary

    c1, c2 = st.columns(2)

    with c1:
        month = st.selectbox(
            "Select Month",
            ["Select Month"] + list(range(1, 13)),
            index=0,
            format_func=lambda x: x if isinstance(x, str)
            else datetime(2000, x, 1).strftime("%B")
        )

    with c2:
        current_year = date.today().year
        years = list(range(2022, current_year + 1))

        year = st.selectbox(
            "Select Year",
            ["Select Year"] + years,
            index=0
        )

    amount = st.number_input(
        "Salary Amount",
        min_value=0.0,
        format="%.0f"
    )

    # 🔍 Check duplicate
    exists = any(
        s["month"] == month and
        s["year"] == year
        for s in salaries
    )

    if exists:
        st.warning(
            "⚠️ Salary already exists "
            "for this month & year"
        )

    if st.button(
            "Save Salary",
            disabled=(exists or amount <= 0)
    ):
        salaries.append({
            "month": month,
            "year": year,
            "amount": amount
        })

        save_json(
            SALARY_FILE,
            salaries
        )

        st.session_state.salary = salaries

        st.success("✅ Salary saved!")

    # 📊 DISPLAY SALARY HISTORY
    if salaries:

        st.divider()
        st.subheader("📊 Salary History")

        df_sal = pd.DataFrame(salaries)

        # Create Month-Year column
        df_sal["salary_period"] = df_sal.apply(
            lambda row: (
                f"{datetime(2000, int(row['month']), 1).strftime('%B')} "
                f"{int(row['year'])}"
            ),
            axis=1
        )

        # Sort latest first
        df_sal = df_sal.sort_values(
            ["year", "month"],
            ascending=False
        ).reset_index(drop=True)

        # Serial number
        df_sal.insert(0, "Sl.No", range(1, len(df_sal) + 1))

        # Display
        st.dataframe(
            df_sal[
                ["Sl.No", "salary_period", "amount"]
            ].rename(
                columns={
                    "salary_period": "Salary Month",
                    "amount": "Salary Amount"
                }
            ),
            width='stretch',
            hide_index=True
        )

        # ─────────────────────────────────────────────
        # EDIT / DELETE SALARY
        # ─────────────────────────────────────────────
        st.divider()
        st.subheader("✏️ Edit Salary")

        # Create display list
        salary_options = [
            f"{datetime(2000, int(s['month']), 1).strftime('%B')} {int(s['year'])}"
            for s in salaries
        ]

        selected_salary_label = st.selectbox(
            "Select Salary Month",
            options=["Select"] + salary_options
        )

        # Show edit section only after selection
        if selected_salary_label != "Select":

            selected_salary = salary_options.index(
                selected_salary_label
            )

            salary_row = salaries[selected_salary]

            e1, e2, e3 = st.columns(3)

            with e1:
                edit_month = st.selectbox(
                    "Month",
                    options=list(range(1, 13)),
                    index=int(salary_row["month"]) - 1,
                    format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
                    key="edit_salary_month"
                )

            with e2:
                edit_year = st.selectbox(
                    "Year",
                    options=years,
                    index=years.index(int(salary_row["year"])),
                    key="edit_salary_year"
                )

            with e3:
                edit_amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    value=float(salary_row["amount"]),
                    format="%.0f",
                    key="edit_salary_amount"
                )

            c1, c2 = st.columns(2)

            # UPDATE
            with c1:

                if st.button(
                        "💾 Update Salary",
                        width='stretch'
                ):

                    duplicate = any(
                        s["month"] == edit_month and
                        s["year"] == edit_year and
                        i != selected_salary
                        for i, s in enumerate(salaries)
                    )

                    if duplicate:

                        st.error(
                            "Salary already exists "
                            "for selected month & year"
                        )

                    else:

                        salaries[selected_salary] = {
                            "month": edit_month,
                            "year": edit_year,
                            "amount": edit_amount
                        }

                        save_json(
                            SALARY_FILE,
                            salaries
                        )

                        st.session_state.salary = salaries

                        st.success("✅ Salary updated!")
                        st.rerun()

            # DELETE
            with c2:

                if st.button(
                        "🗑️ Delete Salary",
                        width='stretch',
                        type="secondary"
                ):
                    salaries.pop(selected_salary)

                    save_json(
                        SALARY_FILE,
                        salaries
                    )

                    st.session_state.salary = salaries

                    st.success("✅ Salary deleted!")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 🤝 Loans
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "🤝 Loans":

    st.title("🤝 Borrow Loan")
    if "loan_added" not in st.session_state:
        st.session_state.loan_added = False

    members = get_members() + ["Friend"]

    # ─────────────────────────────────────────────
    # ➕ ADD NEW LOAN
    # ─────────────────────────────────────────────
    st.subheader("➕ Add New Loan")

    c1, c2 = st.columns(2)

    with c1:
        loan_name = st.text_input(
            "Loan Name",
            placeholder="e.g. Bike Loan"
        )

        lender = st.selectbox(
            "Borrow From",
            members,
            key="loan_lender"
        )

        note = st.text_input("Reason")

    with c2:
        amount = st.number_input(
            "Loan Amount",
            min_value=0.0,
            format="%.0f"
        )

        loan_date = st.date_input(
            "Borrowed Date",
            value=date.today(),
            max_value=date.today()
        )

    # ✅ Duplicate validation
    duplicate_loan = False

    if loan_name.strip():
        duplicate_loan = any(
            l["loan_name"].strip().lower() == loan_name.strip().lower()
            and l.get("status") == "Active"
            for l in st.session_state.loans
        )

    # Show warning only before clicking button
    if duplicate_loan and not st.session_state.get("loan_added", False):
        st.warning("⚠️ Loan name already exists")

    if st.button(
            "Take Loan",
            disabled=duplicate_loan or not loan_name.strip() or amount <= 0,
            type="primary",
            width='stretch'
    ):
        loan = {
            "loan_name": loan_name.strip(),
            "lender": lender,
            "amount": amount,
            "remaining": amount,
            "borrowed_date": str(loan_date),
            "note": note,
            "status": "Active",
            "payments": []
        }

        st.session_state.loans.append(loan)

        save_json(LOAN_FILE, st.session_state.loans)
        st.session_state.loan_added = True

        st.success("✅ Loan added!")
        st.rerun()

    st.divider()

    # ─────────────────────────────────────────────────────────
    # ACTIVE LOANS
    # ─────────────────────────────────────────────────────────
    st.subheader("📋 Active Loans")

    active_loans = [
        l for l in st.session_state.loans
        if l.get("status") == "Active"
    ]

    if active_loans:

        df_loans = pd.DataFrame(active_loans)

        df_loans.insert(
            0,
            "Sl.No",
            range(1, len(df_loans) + 1)
        )

        st.dataframe(
            df_loans[
                [
                    "Sl.No",
                    "loan_name",
                    "lender",
                    "amount",
                    "remaining",
                    "borrowed_date",
                    "note"
                ]
            ].rename(
                columns={
                    "loan_name": "Loan Name",
                    "lender": "Borrowed From",
                    "amount": "Loan Amount",
                    "borrowed_date": "Borrowed Date",
                    "remaining": "Remaining Amount",
                    "note": "Reason"
                }
            ),
            width='stretch',
            hide_index=True
        )

        st.divider()

        # ✅ Select loan to edit
        selected_loan_name = st.selectbox(
            "Select Loan to Edit",
            ["-- Select Loan --"] +
            [l["loan_name"] for l in active_loans]
        )

        # ✅ Open edit section only after selection
        if selected_loan_name != "-- Select Loan --":

            loan = next(
                l for l in active_loans
                if l["loan_name"] == selected_loan_name
            )

            st.subheader("✏️ Edit Loan")

            ec1, ec2 = st.columns(2)

            with ec1:

                edit_name = st.text_input(
                    "Loan Name",
                    value=loan["loan_name"]
                )

                edit_lender = st.selectbox(
                    "Lender",
                    members,
                    index=members.index(loan["lender"])
                    if loan["lender"] in members else 0
                )

            with ec2:

                edit_borrowed_date = st.date_input(
                    "Borrowed Date",
                    value=pd.to_datetime(
                        loan["borrowed_date"]
                    ).date(),
                    max_value=date.today()
                )

                edit_note = st.text_input(
                    "Note",
                    value=loan.get("note", "")
                )

                topup_amount = st.number_input(
                    "Top-up Amount",
                    min_value=0.0,
                    format="%.0f"
                )

            c1, c2, c3 = st.columns(3)

            # ✅ UPDATE
            with c1:

                if st.button(
                        "💾 Update Loan",
                        width='stretch'
                ):

                    duplicate = any(
                        l["loan_name"].lower() == edit_name.lower()
                        and l != loan
                        for l in st.session_state.loans
                    )

                    if duplicate:
                        st.error(
                            "Loan name already exists"
                        )

                    else:
                        loan["loan_name"] = edit_name
                        loan["lender"] = edit_lender
                        loan["borrowed_date"] = str(edit_borrowed_date)
                        loan["note"] = edit_note

                        save_json(
                            LOAN_FILE,
                            st.session_state.loans
                        )

                        st.success("✅ Loan updated!")
                        st.rerun()

            # ✅ TOP-UP
            with c2:

                if st.button(
                        "➕ Add Top-up",
                        width='stretch'
                ):

                    if topup_amount <= 0:
                        st.warning(
                            "Enter valid top-up amount"
                        )

                    else:

                        loan["amount"] += topup_amount
                        loan["remaining"] += topup_amount

                        save_json(
                            LOAN_FILE,
                            st.session_state.loans
                        )

                        st.success(
                            f"✅ ₹ {topup_amount:,.0f} added to loan"
                        )

                        st.rerun()

            # ✅ DELETE
            with c3:

                if st.button(
                        "🗑️ Delete Loan",
                        width='stretch',
                        type="secondary"
                ):
                    st.session_state.loans.remove(loan)

                    save_json(
                        LOAN_FILE,
                        st.session_state.loans
                    )

                    st.success("✅ Loan deleted!")
                    st.rerun()

    else:
        st.info("No active loans 🎉")

    # ─────────────────────────────────────────────
    # COMPLETED LOANS
    # ─────────────────────────────────────────────
    completed_loans = [
        l for l in st.session_state.loans
        if l.get("status") == "Completed"
    ]

    if completed_loans:
        st.divider()

        st.subheader("✅ Completed Loans")
        for loan in completed_loans:

            payments = loan.get("payments", [])

            if payments:

                loan["paid_date"] = payments[-1].get(
                    "paid_date",
                    ""
                )

            else:
                loan["paid_date"] = ""

        df_completed = pd.DataFrame(
            completed_loans
        )

        df_completed.insert(
            0,
            "Sl.No",
            range(1, len(df_completed) + 1)
        )

        st.dataframe(
            df_completed[
                [
                    "Sl.No",
                    "loan_name",
                    "lender",
                    "amount",
                    "borrowed_date",
                    "paid_date",
                    "note"
                ]
            ].rename(
                columns={
                    "loan_name": "Loan Name",
                    "lender": "Borrowed From",
                    "amount": "Loan Amount",
                    "borrowed_date": "Borrowed Date",
                    "paid_date": "Loan Paid Date",
                    "note": "Reason"
                }
            ),
            width='stretch',
            hide_index=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# 💳 LOAN PAYMENTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "💳 Loans Payments":

    st.title("💳 Loan Repayments & Summary")

    loans = st.session_state.loans

    if not loans:
        st.info("No loans available")

    else:

        df_loans = pd.DataFrame(loans)

        df_loans["paid"] = (
                df_loans["amount"] - df_loans["remaining"]
        )

        st.subheader("📊 Loan Summary")

        st.dataframe(
            df_loans[
                [
                    "loan_name",
                    "lender",
                    "amount",
                    "paid",
                    "remaining",
                    "status"
                ]
            ].rename(
                columns={
                    "loan_name": "Loan Name",
                    "lender": "Borrowed From",
                    "amount": "Loan Amount",
                    "paid": "Loan Amount Paid",
                    "remaining": "Loan Remaining",
                    "status": "Status"
                }
            ),
            width='stretch',
            hide_index=True
        )

        st.divider()

        # ✅ ONLY ACTIVE LOANS
        active_loans = [
            l for l in loans
            if l.get("status") == "Active"
        ]

        if not active_loans:
            st.success("🎉 All loans are completed")
            st.stop()

        loan_names = ["Select Loan"] + [l["loan_name"] for l in active_loans]

        # ✅ Select only active loans
        selected_loan = st.selectbox(
            "Select Active Loan",
            loan_names, index=0
        )

        if selected_loan == "Select Loan":
            st.info("Please select a loan to continue")
            st.stop()

        loan = next(
            l for l in active_loans
            if l["loan_name"] == selected_loan
        )

        st.info(
            f"Remaining Amount: ₹ {loan['remaining']:,.0f}"
        )

        c1, c2 = st.columns(2)

        with c1:
            pay_amount = st.number_input(
                "Pay Amount",
                min_value=0.0,
                step=10.0,
                format="%.0f"
            )

            payment_date = st.date_input(
                "Payment Date",
                value=date.today(),
                max_value=date.today()
            )

        with c2:
            payment_type = st.selectbox(
                "Payment Type",
                PAYMENT_METHODS
            )

            desc = st.text_input(
                "Payment Note"
            )

        # ✅ PAY BUTTON
        if st.button("💰 Pay Loan", width='stretch'):

            if pay_amount <= 0:
                st.warning("Enter valid amount")

            elif pay_amount > loan["remaining"]:
                st.warning(
                    "Payment cannot exceed remaining loan amount"
                )

            else:

                loan["remaining"] -= pay_amount

                payment = {
                    "amount": pay_amount,
                    "paid_date": str(payment_date),
                    "payment_type": payment_type,
                    "note": desc
                }

                loan.setdefault("payments", []).append(payment)

                # ✅ Auto complete
                if loan["remaining"] <= 0:
                    loan["remaining"] = 0
                    loan["status"] = "Completed"

                save_json(
                    LOAN_FILE,
                    st.session_state.loans
                )

                st.success("✅ EMI payment added!")
                st.rerun()

        # ─────────────────────────────────────────────
        # PAYMENT HISTORY
        # ─────────────────────────────────────────────
        if loan.get("payments"):
            st.divider()
            st.subheader("📅 Payment History")

            df_pay = pd.DataFrame(
                loan["payments"]
            )

            df_pay.insert(
                0,
                "Sl.No",
                range(1, len(df_pay) + 1)
            )

            st.dataframe(
                df_pay[
                    [
                        "Sl.No",
                        "paid_date",
                        "amount",
                        "payment_type",
                        "note"
                    ]
                ],
                width='stretch',
                hide_index=True
            )

# ══════════════════════════════════════════════════════════════════════════════
# 🏦 Savings
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "🏦 Savings":

    st.title("🏦 Savings / Bank Deposit")

    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")

    # ─────────────────────────────────────────────
    # ADD SAVINGS
    # ─────────────────────────────────────────────
    st.subheader("➕ Add Savings")

    c1, c2 = st.columns(2)

    with c1:

        bank = st.text_input(
            "Bank Name",
            placeholder="e.g. HDFC, SBI"
        )

        saving_type = st.selectbox(
            "Saving Type",
            cfg.get(
                "saving_types",
                DEFAULT_SAVING_TYPES
            )
        )

    with c2:

        amount = st.number_input(
            "Amount",
            min_value=0.0,
            format="%.0f"
        )

        source = st.selectbox(
            "Source",
            ["Wife", "Kumar", "Other"]
        )

    saving_date = st.date_input(
        "Deposit Date",
        value=date.today(),
        max_value=date.today()
    )

    if st.button(
            "💾 Add Savings",
            width='stretch',
            type="primary"
    ):

        if amount <= 0:

            st.warning("Enter valid amount")

        else:

            entry = {
                "amount": amount,
                "bank": bank,
                "type": saving_type,
                "source": source,
                "date": str(saving_date)
            }

            st.session_state.savings.append(entry)

            save_json(
                SAVINGS_FILE,
                st.session_state.savings
            )

            st.success("✅ Savings added!")
            st.rerun()

    # ─────────────────────────────────────────────
    # SAVINGS TABLE
    # ─────────────────────────────────────────────
    if st.session_state.savings:

        st.divider()

        st.subheader("📊 Savings History")

        df_sav = pd.DataFrame(
            st.session_state.savings
        )

        df_sav.insert(
            0,
            "Sl.No",
            range(1, len(df_sav) + 1)
        )

        st.dataframe(
            df_sav[
                [
                    "Sl.No",
                    "bank",
                    "type",
                    "source",
                    "amount",
                    "date"
                ]
            ].rename(
                columns={
                    "bank": "Bank",
                    "type": "Type",
                    "source": "Source",
                    "amount": f"Amount ({currency})",
                    "date": "Deposit Date"
                }
            ),
            width='stretch',
            hide_index=True
        )

        # ─────────────────────────────────────────
        # EDIT SAVINGS
        # ─────────────────────────────────────────
        st.divider()

        selected_saving = st.selectbox(
            "Select Savings to Edit",
            ["-- Select Savings --"] +
            [
                f"{s['bank']} - {currency} {s['amount']:,.0f}"
                for s in st.session_state.savings
            ]
        )

        if selected_saving != "-- Select Savings --":

            saving_index = (
                [
                    f"{s['bank']} - {currency} {s['amount']:,.0f}"
                    for s in st.session_state.savings
                ].index(selected_saving)
            )

            saving = st.session_state.savings[
                saving_index
            ]

            st.subheader("✏️ Edit Savings")

            e1, e2 = st.columns(2)

            with e1:

                edit_bank = st.text_input(
                    "Bank",
                    value=saving["bank"]
                )

                edit_type = st.selectbox(
                    "Saving Type",
                    cfg.get(
                        "saving_types",
                        DEFAULT_SAVING_TYPES
                    ),
                    index=cfg.get(
                        "saving_types",
                        DEFAULT_SAVING_TYPES
                    ).index(saving["type"])
                    if saving["type"] in cfg.get(
                        "saving_types",
                        DEFAULT_SAVING_TYPES
                    ) else 0
                )

                edit_saving_date = st.date_input(
                    "Deposit Date",
                    value=pd.to_datetime(
                        saving["date"]
                    ).date(),
                    max_value=date.today(),
                    key=f"edit_saving_date_{saving_index}"
                )

            with e2:

                edit_amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    value=float(saving["amount"]),
                    format="%.0f"
                )

                source_options = [
                    "Wife",
                    "Kumar",
                    "Other"
                ]

                edit_source = st.selectbox(
                    "Source",
                    source_options,
                    index=source_options.index(
                        saving["source"]
                    )
                    if saving["source"] in source_options
                    else 0
                )

            c1, c2 = st.columns(2)

            # UPDATE
            with c1:

                if st.button(
                        "💾 Update Savings",
                        width='stretch'
                ):

                    if edit_amount <= 0:

                        st.warning(
                            "Amount should be greater than 0"
                        )

                    else:

                        st.session_state.savings[
                            saving_index
                        ] = {
                            "amount": edit_amount,
                            "bank": edit_bank,
                            "type": edit_type,
                            "source": edit_source,
                            "date": str(edit_saving_date)
                        }

                        save_json(
                            SAVINGS_FILE,
                            st.session_state.savings
                        )

                        st.success(
                            "✅ Savings updated!"
                        )

                        st.rerun()

            # DELETE
            with c2:

                if st.button(
                        "🗑️ Delete Savings",
                        width='stretch',
                        type="secondary"
                ):
                    st.session_state.savings.pop(
                        saving_index
                    )

                    save_json(
                        SAVINGS_FILE,
                        st.session_state.savings
                    )

                    st.success(
                        "✅ Savings deleted!"
                    )

                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 📋 ALL EXPENSES
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "📋 All Expenses":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    CATS = get_categories()
    MEMBER = get_members()
    df = st.session_state.df.copy()

    st.title("📋 All Expenses")
    if df.empty:
        st.info("No expenses recorded yet.")
        st.stop()

    with st.expander("🔍 Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            dr = st.date_input("Date Range", value=(df["date"].min(), df["date"].max()))
        with fc2:
            sel_cats = st.multiselect("Categories", CATS)
        with fc3:
            sel_mems = st.multiselect("Members", MEMBER)
        with fc4:
            sel_pay = st.multiselect("Payment", PAYMENT_METHODS)

    mask = pd.Series([True] * len(df))
    if len(dr) == 2:      mask &= (df["date"] >= dr[0]) & (df["date"] <= dr[1])
    if sel_cats:        mask &= df["category"].isin(sel_cats)
    if sel_mems:        mask &= df["member"].isin(sel_mems)
    if sel_pay:         mask &= df["payment_method"].isin(sel_pay)

    filtered = df[mask].sort_values("date", ascending=False).copy()
    st.markdown(f"**{len(filtered)} transactions** — Total: **{currency} {filtered['amount'].sum():,.2f}**")

    if not filtered.empty:
        filtered = filtered.reset_index(drop=True)
        filtered["Sl.No"] = range(1, len(filtered) + 1)

        disp = filtered[
            ["Sl.No", "date", "category", "description",
             "member", "payment_method", "amount", "notes"]
        ].copy()

        disp["amount"] = disp["amount"].apply(
            lambda x: f"{currency} {x:,.2f}"
        )

        st.dataframe(
            disp.rename(columns={
                    "date": "Date",
                    "category": "Category",
                    "description": "Description",
                    "member": "Member",
                    "payment_method": "Payment Method",
                    "amount": f"Amount ({currency})",
                    "notes": "Reason"
                }),
            width='stretch',
            hide_index=True
        )

        st.divider()
        st.subheader("✏️ Edit / Delete Expense")

        # ✅ Select using serial number
        selected_sl = st.selectbox(
            "Select Expense",
            ["-- Select Expense --"] + filtered["Sl.No"].astype(str).tolist()
        )

        # ✅ Open only when selected
        if selected_sl != "-- Select Expense --":

            selected_sl = int(selected_sl)

            selected_row = filtered[
                filtered["Sl.No"] == selected_sl
                ].iloc[0]

            sel_id = selected_row["id"]

            row = df[df["id"] == sel_id].iloc[0]

            ec1, ec2 = st.columns(2)

            # ─────────────────────────────────────────
            # LEFT
            # ─────────────────────────────────────────
            with ec1:

                new_desc = st.text_input(
                    "Description",
                    value=row["description"],
                    key=f"ed_{sel_id}"
                )

                new_cat = st.selectbox(
                    "Category",
                    CATS,
                    index=CATS.index(row["category"])
                    if row["category"] in CATS else 0,
                    key=f"ec_{sel_id}"
                )

                new_amount = st.number_input(
                    "Amount",
                    value=float(row["amount"]),
                    step=10.0,
                    key=f"ea_{sel_id}"
                )

            # ─────────────────────────────────────────
            # RIGHT
            # ─────────────────────────────────────────
            with ec2:

                new_mem = st.selectbox(
                    "Member",
                    MEMBER,
                    index=MEMBER.index(row["member"])
                    if row["member"] in MEMBER else 0,
                    key=f"em_{sel_id}"
                )

                new_pay = st.selectbox(
                    "Payment",
                    PAYMENT_METHODS,
                    index=PAYMENT_METHODS.index(
                        row["payment_method"]
                    )
                    if row["payment_method"] in PAYMENT_METHODS else 0,
                    key=f"ep_{sel_id}"
                )

                new_notes = st.text_area(
                    "Notes",
                    value=row.get("notes", ""),
                    height=80,
                    key=f"en_{sel_id}"
                )

            bc1, bc2 = st.columns(2)

            # ✅ UPDATE
            with bc1:

                if st.button(
                        "💾 Update Expense",
                        width='stretch',
                        key=f"update_{sel_id}"
                ):
                    df.loc[
                        df["id"] == sel_id,
                        [
                            "description",
                            "category",
                            "amount",
                            "member",
                            "payment_method",
                            "notes"
                        ]
                    ] = [
                        new_desc,
                        new_cat,
                        new_amount,
                        new_mem,
                        new_pay,
                        new_notes
                    ]

                    st.session_state.df = df

                    save_expenses(df)

                    st.success("✅ Expense updated!")

                    st.rerun()

            # ✅ DELETE
            with bc2:

                if st.button(
                        "🗑️ Delete Expense",
                        width='stretch',
                        type="secondary",
                        key=f"delete_{sel_id}"
                ):
                    df = df[
                        df["id"] != sel_id
                        ].reset_index(drop=True)

                    st.session_state.df = df

                    save_expenses(df)

                    st.success("✅ Expense deleted!")

                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 📊 CHARTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "📊 Charts":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    df = st.session_state.df.copy()

    st.title("📊 Expense Analytics Dashboard")

    if df.empty:
        st.info("No data to chart yet.")
        st.stop()

    # ---------------------------
    # 🔷 KPI SECTION
    # ---------------------------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Spend", f"{currency}{df['amount'].sum():,.0f}")
    c2.metric("Avg Expense", f"{currency}{df['amount'].mean():,.0f}")
    c3.metric("Max Expense", f"{currency}{df['amount'].max():,.0f}")
    c4.metric("Transactions", len(df))

    st.divider()

    # ---------------------------
    # 🔷 CATEGORY ANALYSIS
    # ---------------------------
    st.subheader("📂 Category Wise Spending")

    cat_df = df.groupby("category")["amount"].sum().sort_values(ascending=True).reset_index()

    fig1 = px.bar(
        cat_df,
        x="amount",
        y="category",
        orientation="h",
        text_auto=".2s",
        color="amount",
        color_continuous_scale="Blues"
    )
    fig1.update_layout(height=400, margin=dict(t=10, b=10))
    st.plotly_chart(fig1, width='stretch')

    # ---------------------------
    # 🔷 MEMBER ANALYSIS
    # ---------------------------
    st.subheader("👥 Member Wise Spending")

    mem_df = df.groupby("member")["amount"].sum().sort_values(ascending=True).reset_index()

    fig2 = px.bar(
        mem_df,
        x="amount",
        y="member",
        orientation="h",
        text_auto=".2s",
        color="amount",
        color_continuous_scale="Teal"
    )
    fig2.update_layout(height=350, margin=dict(t=10, b=10))
    st.plotly_chart(fig2, width='stretch')

    # ---------------------------
    # 🔷 PAYMENT METHOD
    # ---------------------------
    st.subheader("💳 Payment Method Breakdown")

    pay_df = df.groupby("payment_method")["amount"].sum().reset_index()

    fig3 = px.pie(
        pay_df,
        names="payment_method",
        values="amount",
        hole=0.4
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig3, width='stretch')

    # ---------------------------
    # 🔷 HEATMAP (NEW INSIGHT)
    # ---------------------------
    st.subheader("🔥 Member vs Category Heatmap")

    heatmap_df = df.pivot_table(
        index="member",
        columns="category",
        values="amount",
        aggfunc="sum",
        fill_value=0
    )

    fig4 = px.imshow(
        heatmap_df,
        text_auto=True,
        aspect="auto"
    )
    st.plotly_chart(fig4, width='stretch')

    # ---------------------------
    # 🔷 EXPENSE DISTRIBUTION
    # ---------------------------
    st.subheader("📊 Expense Distribution")

    fig5 = px.histogram(
        df,
        x="amount",
        nbins=20
    )
    st.plotly_chart(fig5, width='stretch')

    # ---------------------------
    # 🧠 AI INSIGHTS
    # ---------------------------
    st.subheader("🧠 AI Insights Summary")

    total = df["amount"].sum()
    avg = df["amount"].mean()

    top_category = df.groupby("category")["amount"].sum().idxmax()
    top_category_val = df.groupby("category")["amount"].sum().max()

    top_member = df.groupby("member")["amount"].sum().idxmax()
    top_member_val = df.groupby("member")["amount"].sum().max()

    top_payment = df.groupby("payment_method")["amount"].sum().idxmax()

    insights = []

    # Category dominance
    cat_share = (top_category_val / total) * 100
    if cat_share > 50:
        insights.append(f"⚠️ Heavy spending in **{top_category}** ({cat_share:.1f}%).")
    else:
        insights.append(f"📊 Top category is **{top_category}** ({cat_share:.1f}%).")

    # Member dominance
    mem_share = (top_member_val / total) * 100
    insights.append(f"👤 Highest spender: **{top_member}** ({mem_share:.1f}%).")

    # Payment behavior
    insights.append(f"💳 Most used payment method: **{top_payment}**.")

    # Spending level
    if avg > 5000:
        insights.append("🔥 High average spending detected.")
    elif avg > 2000:
        insights.append("⚖️ Moderate spending pattern.")
    else:
        insights.append("✅ Controlled spending pattern.")

    # Stability
    std = df["amount"].std()
    if std > avg:
        insights.append("⚠️ Highly inconsistent spending pattern.")
    else:
        insights.append("📈 Stable spending behavior.")

    for i, ins in enumerate(insights, 1):
        st.write(f"{i}. {ins}")

# ══════════════════════════════════════════════════════════════════════════════
# 🎯 BUDGET LIMITS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "🎯 Budget Limits":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    CATS = get_categories()

    st.title("🎯 Budget Limits & Settings")
    tab1, tab2 = st.tabs(["💸 Category Limits", "⚙️ App Settings"])

    with tab1:

        st.markdown(
            "Set monthly spending limits only for categories you want to track."
        )

        limits = cfg.get("limits", {})

        # Existing limited categories
        existing_limit_categories = list(limits.keys())

        # Multi select categories
        selected_limit_categories = st.multiselect(
            "Select Categories for Budget Limits",
            options=CATS,
            default=existing_limit_categories
        )

        with st.form("limits_form"):

            new_limits = {}

            cols = st.columns(2)

            for i, cat in enumerate(selected_limit_categories):

                with cols[i % 2]:

                    val = st.number_input(
                        f"{cat} Limit",
                        min_value=0.0,
                        value=float(limits.get(cat, 0)),
                        step=100.0,
                        format="%.0f",
                        key=f"lim_{cat}"
                    )

                    if val > 0:
                        new_limits[cat] = val

            submitted = st.form_submit_button(
                "💾 Save Limits",
                width='stretch',
                type="primary"
            )

            if submitted:
                cfg["limits"] = new_limits

                save_config(cfg)

                st.session_state.config = cfg

                st.success("✅ Budget limits updated!")

        st.subheader("🎯 Savings Goal")

        saving_goal = st.number_input(
            "Target Savings Amount",
            min_value=0.0,
            value=float(cfg.get("saving_goal", 60000)),
            step=1000.0,
            format="%.0f"
        )

        if st.button(
                "💾 Save Savings Goal",
                width='stretch',
                type="primary"
        ):
            cfg["saving_goal"] = saving_goal

            save_config(cfg)

            st.session_state.config = cfg

            st.success("✅ Savings goal updated!")

    with tab2:
        st.subheader("App Settings")
        with st.form("settings_form"):
            family_name = st.text_input("Family Name", value=cfg.get("family_name", "My Family"))
            cur_opts = ["₹", "$", "€", "£", "¥", "AED", "SGD"]
            currency_opt = st.selectbox("Currency Symbol", cur_opts,
                                        index=cur_opts.index(cfg.get("currency", "₹")))
            if st.form_submit_button("💾 Save Settings", type="primary"):
                cfg["family_name"] = family_name
                cfg["currency"] = currency_opt
                save_config(cfg)
                st.session_state.config = cfg
                st.success("✅ Settings saved!")

        st.divider()
        st.subheader("🗑️ Data Management")
        with st.expander("⚠️ Danger Zone"):
            st.warning("This will permanently delete all expense data.")
            confirm = st.checkbox("I understand this action cannot be undone")

            delete_password = st.text_input(
                "Enter account password to confirm",
                type="password",
                placeholder="Enter your password"
            )

            # Validate password
            valid_password = authenticate(
                st.session_state.username,
                delete_password
            )

            if delete_password and not valid_password:
                st.error("❌ Incorrect password")

            if st.button(
                    "Delete All Data",
                    disabled=(
                            not confirm
                            or not delete_password
                            or not valid_password
                    ),
                    type="secondary"):
                st.session_state.df = pd.DataFrame(
                    columns=["id", "date", "category", "description", "amount", "member", "payment_method", "notes"])
                save_expenses(st.session_state.df)
                st.session_state.loans = []
                save_json(LOAN_FILE,[])

                st.session_state.savings = []
                save_json(SAVINGS_FILE,[])

                st.session_state.salary = []
                save_json(SALARY_FILE,[])

                cfg = st.session_state.config
                cfg["limits"] = {}
                cfg["saving_goal"] = DEFAULT_SAVING_GOAL
                save_config(cfg)
                st.session_state.config = cfg

                st.success(
                    "✅ All financial data deleted successfully."
                )
                # st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 🏷️ MANAGE LISTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "🏷️ Manage Lists":
    cfg = st.session_state.config
    st.title("🏷️ Manage Categories & Members")

    tab_cat, tab_mem, tab_sav = st.tabs(["📂 Categories", "👨‍👩‍👧 Family Members", "🏦 Saving Types"])

    # ─────────────────────────────────────────────────────────────────────────
    # 📂 CATEGORIES TAB
    # ─────────────────────────────────────────────────────────────────────────
    with tab_cat:
        CATS = cfg.get("categories", DEFAULT_CATEGORIES.copy())
        st.markdown(
            "Add new categories, rename existing ones, or remove ones you don't use. "
            "Existing expenses keep their original category name even after a rename."
        )

        # ── Add new
        st.subheader("➕ Add Category")
        with st.form("add_cat_form", clear_on_submit=True):
            col_e, col_n, col_b = st.columns([1.2, 4, 1.5])
            with col_e:
                emoji = st.selectbox("Emoji", CATEGORY_EMOJIS, label_visibility="collapsed")
            with col_n:
                new_cat_name = st.text_input("Name", placeholder="e.g. Car Insurance",
                                             label_visibility="collapsed")
            with col_b:
                add_cat = st.form_submit_button("➕ Add Category", width='stretch', type="primary")

            if add_cat:
                name = new_cat_name.strip()
                if not name:
                    st.warning("Please enter a category name.")
                else:
                    full = f"{emoji} {name}"
                    if full in CATS:
                        st.warning(f"**{full}** already exists.")
                    else:
                        CATS.append(full)
                        cfg["categories"] = CATS
                        save_config(cfg)
                        st.session_state.config = cfg
                        st.success(f"✅ **{full}** added!")
                        st.rerun()

        st.divider()

        # ── Current list
        col_head, col_reset = st.columns([3, 1])
        col_head.subheader(f"📋 All Categories ({len(CATS)})")
        if col_reset.button("↩️ Reset Defaults", key="reset_cats", width='stretch'):
            cfg["categories"] = DEFAULT_CATEGORIES.copy()
            save_config(cfg)
            st.session_state.config = cfg
            st.success("Reset to defaults.")
            st.rerun()

        df_check = st.session_state.df
        for i, cat in enumerate(CATS):
            in_use = not df_check.empty and cat in df_check["category"].values
            row_c = st.columns([3, 2, 1, 1])

            with row_c[0]:
                st.markdown(f"**{cat}**" + (f" *(in use)*" if in_use else ""))

            with row_c[1]:
                new_name = st.text_input("Rename", value=cat, key=f"cat_rename_{i}",
                                         label_visibility="collapsed",
                                         placeholder="New name…")

            with row_c[2]:
                if st.button("✔ Rename", key=f"cat_save_{i}", width='stretch',
                             disabled=(new_name.strip() == cat or not new_name.strip())):
                    renamed = new_name.strip()
                    if renamed in CATS and renamed != cat:
                        st.error("That name already exists.")
                    else:
                        CATS[i] = renamed
                        # propagate rename to existing expenses
                        if not df_check.empty:
                            df_check.loc[df_check["category"] == cat, "category"] = renamed
                            st.session_state.df = df_check
                            save_expenses(df_check)
                        # propagate in limits
                        if cat in cfg.get("limits", {}):
                            cfg["limits"][renamed] = cfg["limits"].pop(cat)
                        cfg["categories"] = CATS
                        save_config(cfg)
                        st.session_state.config = cfg
                        st.success(f"Renamed to **{renamed}**")
                        st.rerun()

            with row_c[3]:
                if st.button("🗑️ Delete", key=f"cat_del_{i}", width='stretch',
                             type="secondary", disabled=in_use or len(CATS) <= 1):
                    CATS.pop(i)
                    cfg.get("limits", {}).pop(cat, None)
                    cfg["categories"] = CATS
                    save_config(cfg)
                    st.session_state.config = cfg
                    st.success(f"Deleted **{cat}**")
                    st.rerun()
                if in_use:
                    st.caption("🔒 in use")

        st.info("💡 Categories in use by existing expenses cannot be deleted. Rename them instead.")

    # ─────────────────────────────────────────────────────────────────────────
    # 👨‍👩‍👧 MEMBERS TAB
    # ─────────────────────────────────────────────────────────────────────────
    with tab_mem:
        MEMS = cfg.get("members", DEFAULT_MEMBERS.copy())
        st.markdown(
            "Add, rename, or remove family members. "
            "Members in use by existing expenses are protected from deletion."
        )

        # ── Add new
        st.subheader("➕ Add Member")
        with st.form("add_mem_form", clear_on_submit=True):
            col_e2, col_n2, col_b2 = st.columns([1.2, 4, 1.5])
            with col_e2:
                mem_emoji = st.selectbox("Emoji", MEMBER_EMOJIS, label_visibility="collapsed")
            with col_n2:
                new_mem_name = st.text_input("Name", placeholder="e.g. Grandma",
                                             label_visibility="collapsed")
            with col_b2:
                add_mem = st.form_submit_button("➕ Add Member", width='stretch', type="primary")

            if add_mem:
                name = new_mem_name.strip()
                if not name:
                    st.warning("Please enter a name.")
                else:
                    full_mem = f"{mem_emoji} {name}"
                    if full_mem in MEMS:
                        st.warning(f"**{full_mem}** already exists.")
                    else:
                        MEMS.append(full_mem)
                        cfg["members"] = MEMS
                        save_config(cfg)
                        st.session_state.config = cfg
                        st.success(f"✅ **{full_mem}** added!")
                        st.rerun()

        st.divider()

        col_head2, col_reset2 = st.columns([3, 1])
        col_head2.subheader(f"👨‍👩‍👧 All Members ({len(MEMS)})")
        if col_reset2.button("↩️ Reset Defaults", key="reset_mems", width='stretch'):
            cfg["members"] = DEFAULT_MEMBERS.copy()
            save_config(cfg)
            st.session_state.config = cfg
            st.success("Reset to defaults.")
            st.rerun()

        df_check2 = st.session_state.df
        for j, mem in enumerate(MEMS):
            in_use_m = not df_check2.empty and mem in df_check2["member"].values
            row_m = st.columns([3, 2, 1, 1])

            with row_m[0]:
                st.markdown(f"**{mem}**" + (" *(in use)*" if in_use_m else ""))

            with row_m[1]:
                new_mem_val = st.text_input("Rename", value=mem, key=f"mem_rename_{j}",
                                            label_visibility="collapsed",
                                            placeholder="New name…")

            with row_m[2]:
                if st.button("✔ Rename", key=f"mem_save_{j}", width='stretch',
                             disabled=(new_mem_val.strip() == mem or not new_mem_val.strip())):
                    renamed_m = new_mem_val.strip()
                    if renamed_m in MEMS and renamed_m != mem:
                        st.error("That name already exists.")
                    else:
                        MEMS[j] = renamed_m
                        if not df_check2.empty:
                            df_check2.loc[df_check2["member"] == mem, "member"] = renamed_m
                            st.session_state.df = df_check2
                            save_expenses(df_check2)
                        cfg["members"] = MEMS
                        save_config(cfg)
                        st.session_state.config = cfg
                        st.success(f"Renamed to **{renamed_m}**")
                        st.rerun()

            with row_m[3]:
                if st.button("🗑️ Delete", key=f"mem_del_{j}", width='stretch',
                             type="secondary", disabled=in_use_m or len(MEMS) <= 1):
                    MEMS.pop(j)
                    cfg["members"] = MEMS
                    save_config(cfg)
                    st.session_state.config = cfg
                    st.success(f"Deleted **{mem}**")
                    st.rerun()
                if in_use_m:
                    st.caption("🔒 in use")

        st.info("💡 Members in use by existing expenses cannot be deleted. Rename them instead.")

    # ─────────────────────────────────────────────────────────────────────────
    # 👨‍👩‍👧 SAVINGS TYPE TAB
    # ─────────────────────────────────────────────────────────────────────────
    with tab_sav:
        st.subheader("🏦 Saving Types")

        SAV_TYPES = cfg.get("saving_types", DEFAULT_SAVING_TYPES.copy())

        # ➕ Add
        with st.form("add_sav_type", clear_on_submit=True):
            new_type = st.text_input("New Saving Type (e.g. Crypto)")
            if st.form_submit_button("➕ Add"):
                if new_type.strip() and new_type not in SAV_TYPES:
                    SAV_TYPES.append(new_type.strip())
                    cfg["saving_types"] = SAV_TYPES
                    save_config(cfg)
                    st.session_state.config = cfg
                    st.success("Added!")
                    st.rerun()

        st.divider()

        # 📋 List + Delete
        for i, stype in enumerate(SAV_TYPES):
            col1, col2 = st.columns([4, 1])

            col1.write(stype)

            if col2.button("🗑️", key=f"del_sav_{i}"):
                SAV_TYPES.pop(i)
                cfg["saving_types"] = SAV_TYPES
                save_config(cfg)
                st.session_state.config = cfg
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 📄 EXPORT PDF
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "📄 Export PDF":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    df = st.session_state.df.copy()

    st.title("📄 Export Expense Report (PDF)")
    if df.empty:
        st.info("No expenses to export yet.")
        st.stop()

    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("From Date", value=date(today.year, today.month, 1))
    with c2:
        end_date = st.date_input("To Date", value=today)

    filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    if filtered.empty:
        st.warning("No expenses found in the selected range.")
        st.stop()

    st.markdown(f"**{len(filtered)} transactions** totalling **{currency} {filtered['amount'].sum():,.2f}**")

    ca, cb = st.columns(2)
    with ca:
        cp = filtered.groupby("category")["amount"].sum().sort_values(ascending=False)
        st.dataframe(cp.reset_index().rename(columns={"amount": f"Amount ({currency})"}),
                     width='stretch', hide_index=True)
    with cb:
        fig = px.pie(filtered.groupby("category")["amount"].sum().reset_index(),
                     names="category", values="amount",
                     hole=0.45, color_discrete_sequence=CAT_COLORS)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, height=300, margin=dict(t=5, b=5))
        st.plotly_chart(fig, width='stretch')

    if st.button("📥 Generate & Download PDF", type="primary", width='stretch'):
        with st.spinner("Generating PDF…"):
            pdf_buf = generate_pdf(filtered, start_date, end_date, cfg)
        st.download_button(
            label="⬇️ Click here to download PDF",
            data=pdf_buf,
            file_name=f"expense_report_{start_date}_{end_date}.pdf",
            mime="application/pdf",
            width='stretch',
        )
        st.success("✅ PDF ready!")
