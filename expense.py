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

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Family Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "expenses.json"
CONFIG_FILE = "config.json"
SALARY_FILE = "salary.json"
LOAN_FILE = "loans.json"
SAVINGS_FILE = "savings.json"

# ── Defaults (used only when config has no saved list yet)
DEFAULT_CATEGORIES = [
    "🛒 Groceries", "🍽️ Dining Out", "🚗 Transport", "💊 Healthcare",
    "🎓 Education", "🎮 Entertainment", "👗 Clothing", "🏠 Utilities",
    "🛠️ Home Maintenance", "📦 Shopping", "✈️ Travel", "💰 Savings/Investment",
    "🎁 Gifts", "📱 Subscriptions", "🏋️ Fitness",
    "📚 Books / Learning", "🔧 Miscellaneous", "🍖 Meat",
]
DEFAULT_MEMBERS = ["Shared", "Wife", "Parent 1", "Parent 2", "Child 1", "Child 2"]
PAYMENT_METHODS = ["Cash", "UPI / Mobile Pay", "Credit Card", "Debit Card", "Net Banking", "Other"]
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
    "Gold",
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

def load_expenses():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["amount"] = pd.to_numeric(df["amount"])
        return df
    return pd.DataFrame(
        columns=["id", "date", "category", "description", "amount", "member", "payment_method", "notes"])


def save_expenses(df):
    records = df.copy()
    records["date"] = records["date"].astype(str)
    with open(DATA_FILE, "w") as f:
        json.dump(records.to_dict("records"), f, indent=2)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        cfg.setdefault("categories", DEFAULT_CATEGORIES.copy())
        cfg.setdefault("members", DEFAULT_MEMBERS.copy())
        cfg.setdefault("saving_types", DEFAULT_SAVING_TYPES.copy())
        return cfg
    return {
        "limits": {}, "currency": "₹", "family_name": "My Family",
        "categories": DEFAULT_CATEGORIES.copy(),
        "members": DEFAULT_MEMBERS.copy(),
        "saving_types": DEFAULT_SAVING_TYPES.copy()
    }


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def next_id(df):
    return int(df["id"].max()) + 1 if not df.empty else 1


def get_categories(): return st.session_state.config.get("categories", DEFAULT_CATEGORIES)


def get_members():    return st.session_state.config.get("members", DEFAULT_MEMBERS)


def load_json(file, default=[]):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


# ─── PDF Generator ────────────────────────────────────────────────────────────

def generate_pdf(df, start_date, end_date, config):
    buf = BytesIO()
    currency = config.get("currency", "₹")
    fname = config.get("family_name", "My Family")
    limits = config.get("limits", {})

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

    story.append(Paragraph(f"{fname} — Expense Report", title_style))
    story.append(Paragraph(f"Period: {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}", sub_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a5f"), spaceAfter=10))

    total = df["amount"].sum()
    daily_avg = total / max((end_date - start_date).days + 1, 1)
    top_cat = df.groupby("category")["amount"].sum().idxmax() if not df.empty else "—"

    summary_data = [
        ["Total Spending", f"{currency} {total:,.2f}"],
        ["Daily Average", f"{currency} {daily_avg:,.2f}"],
        ["Transactions", str(len(df))],
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
    cat_df = df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    cat_data = [["Category", f"Amount ({currency})", "% of Total", "Limit", "Status"]]
    for _, row in cat_df.iterrows():
        pct = (row["amount"] / total * 100) if total else 0
        limit = limits.get(row["category"], 0)
        cat_data.append([
            row["category"],
            f"{currency} {row['amount']:,.2f}",
            f"{pct:.1f}%",
            f"{currency} {limit:,.2f}" if limit else "—",
            ("OK" if row["amount"] <= limit else "Over") if limit else "",
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
    txn_data = [["Date", "Category", "Description", "Member", "Payment", f"Amount ({currency})"]]
    for _, row in df.sort_values("date").iterrows():
        txn_data.append([
            str(row["date"]), row["category"],
            str(row.get("description", ""))[:35],
            row.get("member", ""), row.get("payment_method", ""),
            f"{row['amount']:,.2f}",
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


# ─── Session state bootstrap ──────────────────────────────────────────────────
if "df" not in st.session_state: st.session_state.df = load_expenses()
if "config" not in st.session_state: st.session_state.config = load_config()
if "salary" not in st.session_state:
    st.session_state.salary = load_json(SALARY_FILE)

if "loans" not in st.session_state:
    st.session_state.loans = load_json(LOAN_FILE)

if "savings" not in st.session_state:
    st.session_state.savings = load_json(SAVINGS_FILE)

if "page" not in st.session_state:
    st.session_state.page = PAGES[0]

if st.session_state.page not in PAGES:
    st.session_state.page = PAGES[0]

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 Family Expenses")
    st.caption(f"👨‍👩‍👧‍👦 {st.session_state.config.get('family_name', 'My Family')}")
    st.divider()

    page = st.radio(
        "Navigate",
        PAGES,
        index=PAGES.index(st.session_state.page),
        key="page_radio"   # ✅ IMPORTANT FIX
    )

    st.session_state.page = page
    st.divider()
    currency = st.session_state.config.get("currency", "₹")
    df_side = st.session_state.df
    today = date.today()

    month_total = 0
    if not df_side.empty:
        ms = date(today.year, today.month, 1)
        month_total = df_side[
            (df_side["date"] >= ms) & (df_side["date"] <= today)
        ]["amount"].sum()

    st.metric("This Month", f"{currency} {month_total:,.0f}")
    st.caption(f"{len(get_categories())} categories · {len(get_members())} members")

# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "🏠 Dashboard":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    df = st.session_state.df
    today = date.today()

    st.title("🏠 Dashboard")
    st.caption(f"Today is {today.strftime('%A, %d %B %Y')}")

    today_total = df[df["date"] == today]["amount"].sum() if not df.empty else 0
    week_start = today - timedelta(days=today.weekday())
    week_total = df[(df["date"] >= week_start) & (df["date"] <= today)]["amount"].sum() if not df.empty else 0
    ms = date(today.year, today.month, 1)
    month_df = df[(df["date"] >= ms) & (df["date"] <= today)] if not df.empty else pd.DataFrame()
    month_total = month_df["amount"].sum() if not month_df.empty else 0
    lme = ms - timedelta(days=1)
    lms = date(lme.year, lme.month, 1)
    last_month = df[(df["date"] >= lms) & (df["date"] <= lme)]["amount"].sum() if not df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Today", f"{currency} {today_total:,.0f}")
    c2.metric("This Week", f"{currency} {week_total:,.0f}")
    c3.metric("This Month", f"{currency} {month_total:,.0f}",
              delta=f"{month_total - last_month:+,.0f} vs last month", delta_color="inverse")
    c4.metric("Transactions", len(month_df) if not month_df.empty else 0)

    st.divider()
    if df.empty:
        st.info("No expenses yet. Head to **➕ Add Expense** to get started!")
        st.stop()

    limits = cfg.get("limits", {})
    if limits and not month_df.empty:
        over = [(c, month_df[month_df["category"] == c]["amount"].sum(), l)
                for c, l in limits.items()
                if month_df[month_df["category"] == c]["amount"].sum() > l]
        if over:
            with st.expander("⚠️ Budget Alerts", expanded=True):
                for c_, sp, lim in over:
                    st.error(
                        f"**{c_}** — {currency} {sp:,.0f} spent of {currency} {lim:,.0f} (+{currency} {sp - lim:,.0f})")

    ca, cb = st.columns([1.2, 1])
    with ca:
        st.subheader("📈 Monthly Spending Trend")
        df2 = df.copy()
        df2["month"] = pd.to_datetime(df2["date"].astype(str)).dt.to_period("M")
        monthly = df2.groupby("month")["amount"].sum().reset_index()
        monthly["month_str"] = monthly["month"].astype(str)
        fig = px.bar(monthly.tail(7), x="month_str", y="amount",
                     color="amount", color_continuous_scale="Blues", text_auto=".2s",
                     labels={"month_str": "Month", "amount": f"Amount ({currency})"})
        fig.update_layout(showlegend=False, coloraxis_showscale=False,
                          margin=dict(t=10, b=10), height=280)
        st.plotly_chart(fig, width='stretch')

    with cb:
        st.subheader("🍩 This Month by Category")
        if not month_df.empty:
            cs = month_df.groupby("category")["amount"].sum().reset_index()
            fig2 = px.pie(cs, names="category", values="amount",
                          hole=0.45, color_discrete_sequence=CAT_COLORS)
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            fig2.update_layout(showlegend=False, margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig2, width='stretch')
        else:
            st.info("No data for current month.")

    if limits and not month_df.empty:
        st.subheader("🎯 Budget Progress — This Month")
        bcols = st.columns(3)
        for i, (cat, lim) in enumerate(limits.items()):
            spent = month_df[month_df["category"] == cat]["amount"].sum()
            pct = min(spent / lim, 1.0) if lim else 0
            icon = "🔴" if pct >= 1 else ("🟡" if pct >= 0.8 else "🟢")
            with bcols[i % 3]:
                st.markdown(f"**{cat}** {icon}")
                st.progress(pct)
                st.caption(f"{currency} {spent:,.0f} / {currency} {lim:,.0f}")

    st.subheader("🕐 Recent Transactions")
    recent = df.sort_values("date", ascending=False).head(10)[
        ["date", "category", "description", "member", "amount"]].copy()
    recent["amount"] = recent["amount"].apply(lambda x: f"{currency} {x:,.2f}")
    st.dataframe(recent, width='stretch', hide_index=True)

    today = date.today()

    salary = next(
        (s["amount"] for s in st.session_state.salary
         if s["month"] == today.month and s["year"] == today.year),
        0
    )
    expenses_total = df["amount"].sum() if not df.empty else 0
    loan_taken = sum([l["amount"] for l in st.session_state.loans])
    loan_remaining = sum([l["remaining"] for l in st.session_state.loans])
    savings_total = sum([s["amount"] for s in st.session_state.savings])

    balance = salary - expenses_total - savings_total
    liability = sum([l["remaining"] for l in st.session_state.loans])
    net_worth = balance - liability
    next_month_available = salary - loan_remaining

    st.divider()
    st.subheader("💰 Financial Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Salary", f"₹ {salary}")
    c2.metric("Expenses", f"₹ {expenses_total}")
    c3.metric("Savings", f"₹ {savings_total}")
    c4.metric("Balance", f"₹ {balance}")

    st.metric("💳 Total Loan Liability", f"₹ {liability}")
    st.metric("📊 Net Position", f"₹ {net_worth}")

    if balance < 0:
        st.error(f"⚠️ You are over budget by ₹ {abs(balance):,.0f}")

        st.info("💡 Suggestion: Take a loan or reduce expenses.")

        if st.button("➡️ Go to Loans Page"):
            st.session_state.page = "🤝 Loans"
            st.session_state.page_radio = "🤝 Loans"  # sync radio
            st.rerun()

    st.subheader("📅 Next Month Projection")
    st.info(f"Available after clearing loans: ₹ {next_month_available}")

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
            exp_date = st.date_input("Date", value=date.today())
            category = st.selectbox("Category", CATS)
            description = st.text_input("Description", placeholder="e.g. Weekly groceries")
        with c2:
            amount = st.number_input(f"Amount ({currency})", min_value=0.0, step=10.0, format="%.0f")
            member = st.selectbox("Family Member", MEMS)
            payment = st.selectbox("Payment Method", PAYMENT_METHODS)
        notes = st.text_area("Notes (optional)", height=80)
        submitted = st.form_submit_button("💾 Save Expense", width='stretch', type="primary")

        if submitted:
            df = st.session_state.df
            nr = {"id": next_id(df), "date": exp_date, "category": category,
                  "description": description, "amount": amount,
                  "member": member, "payment_method": payment, "notes": notes}
            st.session_state.df = pd.concat([df, pd.DataFrame([nr])], ignore_index=True)
            save_expenses(st.session_state.df)
            st.success(f"✅ Saved {currency} {amount:,.2f} for **{category}**")

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
            list(range(1, 13)),
            format_func=lambda x: datetime(2000, x, 1).strftime("%B")
        )

    with c2:
        current_year = date.today().year
        years = list(range(2022, current_year + 1))

        year = st.selectbox(
            "Year",
            years,
            index=years.index(current_year)
        )

    amount = st.number_input("Salary Amount", min_value=0.0, format="%.0f")

    # 🔍 Check duplicate
    exists = any(s["month"] == month and s["year"] == year for s in salaries)

    if exists:
        st.warning("⚠️ Salary already exists for this month & year")

    if st.button("Save Salary", disabled=exists):
        salaries.append({
            "month": month,
            "year": year,
            "amount": amount
        })

        save_json(SALARY_FILE, salaries)
        st.session_state.salary = salaries

        st.success("✅ Salary saved!")

    # 📊 Display table
    if salaries:
        df_sal = pd.DataFrame(salaries)

        df_sal["month"] = df_sal["month"].apply(lambda x: datetime(2000, x, 1).strftime("%B"))

        st.subheader("📊 Salary History")
        st.dataframe(
            df_sal[["month", "year", "amount"]]
            .sort_values(["year", "month"], ascending=False),
            width='stretch',
            hide_index=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# 🤝 Loans
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "🤝 Loans":
    st.title("🤝 Borrow Loan")

    members = get_members() + ["Friend"]

    loan_name = st.text_input("Loan Name (e.g. Bike Loan)")
    lender = st.selectbox("Borrow From", members)
    amount = st.number_input("Loan Amount", min_value=0.0, format="%.0f")
    note = st.text_input("Reason")

    if st.button("Take Loan"):
        loan = {
            "loan_name": loan_name,
            "lender": lender,
            "amount": amount,
            "remaining": amount,
            "date": str(date.today()),
            "note": note,
            "status": "Active",
            "payments": []
        }
        st.session_state.loans.append(loan)
        save_json(LOAN_FILE, st.session_state.loans)
        st.success("Loan added!")

    st.subheader("Active Loans")

    if st.session_state.loans:
        active_loans = [l for l in st.session_state.loans if l.get("status") == "Active"]

        if active_loans:
            df_loans = pd.DataFrame(active_loans)

            st.dataframe(
                df_loans[["loan_name", "lender", "amount", "remaining", "date", "note"]],
                width='stretch'
            )
        else:
            st.info("No active loans 🎉")
    else:
        st.info("No loans available")

    completed_loans = [l for l in st.session_state.loans if l.get("status") == "Completed"]

    if completed_loans:
        st.subheader("✅ Completed Loans")
        st.dataframe(pd.DataFrame(completed_loans), width='stretch')

# ══════════════════════════════════════════════════════════════════════════════
# 💳 EMIs
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "💳 Loans Payments":
    st.title("💳 Loan Repayments & Summary")

    loans = st.session_state.loans

    if not loans:
        st.info("No loans available")
    else:
        df_loans = pd.DataFrame(loans)

        st.subheader("📊 Loan Summary")

        df_loans["paid"] = df_loans["amount"] - df_loans["remaining"]

        st.dataframe(
            df_loans[["loan_name", "lender", "amount", "paid", "remaining", "status"]],
            width='stretch'
        )

        st.divider()

        selected_loan = st.selectbox("Select Loan", df_loans["loan_name"])

        loan = next(l for l in loans if l["loan_name"] == selected_loan)

        st.write(f"Remaining: ₹ {loan['remaining']}")

        pay_amount = st.number_input("Pay Amount", min_value=0.0)

        payment_type = st.selectbox(
            "Payment Type",
            PAYMENT_METHODS,
            help="Select how the EMI was paid"
        )

        desc = st.text_input("Payment Note")

        if st.button("Pay EMI"):
            loan["remaining"] -= pay_amount

            payment = {
                "amount": pay_amount,
                "date": str(date.today()),
                "payment_type": payment_type,
                "note": desc
            }

            loan["payments"].append(payment)

            # ✅ Update status automatically
            if loan["remaining"] <= 0:
                loan["remaining"] = 0
                loan["status"] = "Completed"
            else:
                loan["status"] = "Active"

            save_json(LOAN_FILE, loans)
            st.success("Payment updated!")
            st.rerun()

        # 📅 Payment history
        if loan.get("payments"):
            st.subheader("📅 Payment History")

            df_pay = pd.DataFrame(loan["payments"])

            st.dataframe(
                df_pay[["date", "amount", "payment_type", "note"]],
                width='stretch'
            )

# ══════════════════════════════════════════════════════════════════════════════
# 🏦 Savings
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "🏦 Savings":
    st.title("🏦 Savings / Bank Deposit")

    bank = st.text_input("Bank Name (e.g. HDFC, SBI)")
    cfg = st.session_state.config
    amount = st.number_input("Amount", min_value=0.0, format="%.0f")
    saving_type = st.selectbox("Saving Type", cfg.get("saving_types", DEFAULT_SAVING_TYPES))

    source = st.selectbox("Source", ["Wife", "Kumar", "Other"])

    if st.button("Add Savings"):
        entry = {
            "amount": amount,
            "bank": bank,
            "type": saving_type,
            "source": source,
            "date": str(date.today())
        }
        st.session_state.savings.append(entry)
        save_json(SAVINGS_FILE, st.session_state.savings)
        st.success("Saved!")

    # 📊 Show Table instead of JSON
    if st.session_state.savings:
        df_sav = pd.DataFrame(st.session_state.savings)
        st.dataframe(df_sav, width='stretch')

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
    disp = filtered[["date", "category", "description", "member", "payment_method", "amount", "notes"]].copy()
    disp["amount"] = disp["amount"].apply(lambda x: f"{currency} {x:,.2f}")
    st.dataframe(disp, width='stretch', hide_index=True)

    st.divider()
    st.subheader("✏️ Edit / Delete Expense")
    if not filtered.empty:
        sel_id = st.selectbox("Select Expense",
                              options=filtered["id"].tolist(),
                              format_func=lambda x: (
                                  f"#{x} — "
                                  f"{filtered[filtered['id'] == x]['description'].values[0]} "
                                  f"({currency} {filtered[filtered['id'] == x]['amount'].values[0]:,.2f})"
                              ))
        row = df[df["id"] == sel_id].iloc[0]
        ec1, ec2 = st.columns(2)
        with ec1:
            new_desc = st.text_input("Description", value=row["description"], key="ed")
            new_cat = st.selectbox("Category", CATS,
                                   index=CATS.index(row["category"]) if row["category"] in CATS else 0, key="ec")
            new_amount = st.number_input("Amount", value=float(row["amount"]), step=10.0, key="ea")
        with ec2:
            new_mem = st.selectbox("Member", MEMBER,
                                   index=MEMBER.index(row["member"]) if row["member"] in MEMBER else 0, key="em")
            new_pay = st.selectbox("Payment", PAYMENT_METHODS,
                                   index=PAYMENT_METHODS.index(row["payment_method"]) if row[
                                                                                             "payment_method"] in PAYMENT_METHODS else 0,
                                   key="ep")
            new_notes = st.text_area("Notes", value=row.get("notes", ""), key="en", height=68)

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("💾 Update", width='stretch', type="primary"):
                df.loc[df["id"] == sel_id,
                ["description", "category", "amount", "member", "payment_method", "notes"]] = \
                    [new_desc, new_cat, new_amount, new_mem, new_pay, new_notes]
                st.session_state.df = df
                save_expenses(df)
                st.success("Updated!")
                st.rerun()
        with bc2:
            if st.button("🗑️ Delete", width='stretch', type="secondary"):
                df = df[df["id"] != sel_id].reset_index(drop=True)
                st.session_state.df = df
                save_expenses(df)
                st.success("Deleted!")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 📊 CHARTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "📊 Charts":
    cfg = st.session_state.config
    currency = cfg.get("currency", "₹")
    df = st.session_state.df.copy()

    st.title("📊 Expense Charts")
    if df.empty:
        st.info("No data to chart yet.")
        st.stop()

    period = st.radio("Period", ["This Month", "Last 3 Months", "Last 6 Months", "This Year", "All Time", "Custom"],
                      horizontal=True)
    today = date.today()
    if period == "This Month":
        s, e = date(today.year, today.month, 1), today
    elif period == "Last 3 Months":
        s, e = today - timedelta(days=90), today
    elif period == "Last 6 Months":
        s, e = today - timedelta(days=180), today
    elif period == "This Year":
        s, e = date(today.year, 1, 1), today
    elif period == "All Time":
        s, e = df["date"].min(), df["date"].max()
    else:
        cr = st.date_input("Custom Range", value=(today - timedelta(days=30), today))
        s, e = (cr[0], cr[1]) if len(cr) == 2 else (today - timedelta(days=30), today)

    plot_df = df[(df["date"] >= s) & (df["date"] <= e)]
    if plot_df.empty:
        st.warning("No data for the selected period.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Category Distribution")
        cs = plot_df.groupby("category")["amount"].sum().reset_index()
        fig = px.pie(cs, names="category", values="amount",
                     hole=0.4, color_discrete_sequence=CAT_COLORS)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=True, height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    with c2:
        st.subheader("Spending by Member")
        ms2 = plot_df.groupby("member")["amount"].sum().reset_index().sort_values("amount", ascending=True)
        fig2 = px.bar(ms2, x="amount", y="member", orientation="h",
                      color="amount", color_continuous_scale="Teal", text_auto=".2s",
                      labels={"amount": f"Amount ({currency})", "member": "Member"})
        fig2.update_layout(showlegend=False, coloraxis_showscale=False, height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, width='stretch')

    st.subheader("Daily Spending Trend")
    daily = plot_df.groupby("date")["amount"].sum().reset_index()
    fig3 = px.area(daily, x="date", y="amount",
                   labels={"date": "Date", "amount": f"Amount ({currency})"},
                   color_discrete_sequence=["#2c7bb6"])
    fig3.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(fig3, width='stretch')

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Spending by Day of Week")
        pf2 = plot_df.copy()
        pf2["dow"] = pd.to_datetime(pf2["date"].astype(str)).dt.day_name()
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_sum = pf2.groupby("dow")["amount"].sum().reindex(dow_order).reset_index()
        fig4 = px.bar(dow_sum, x="dow", y="amount",
                      color="amount", color_continuous_scale="Oranges", text_auto=".2s",
                      labels={"dow": "Day", "amount": f"Amount ({currency})"})
        fig4.update_layout(coloraxis_showscale=False, height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig4, width='stretch')

    with c4:
        st.subheader("Payment Method Breakdown")
        pay_sum = plot_df.groupby("payment_method")["amount"].sum().reset_index()
        fig5 = px.pie(pay_sum, names="payment_method", values="amount",
                      color_discrete_sequence=px.colors.qualitative.Set3)
        fig5.update_traces(textposition="inside", textinfo="percent+label")
        fig5.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig5, width='stretch')

    limits = cfg.get("limits", {})
    if limits:
        st.subheader("🎯 Budget vs. Actual")
        bv = [{"Category": c, "Spent": plot_df[plot_df["category"] == c]["amount"].sum(), "Budget": l}
              for c, l in limits.items()]
        bvdf = pd.DataFrame(bv)
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(name="Spent", x=bvdf["Category"], y=bvdf["Spent"],
                              marker_color="#2c7bb6",
                              text=bvdf["Spent"].apply(lambda x: f"{currency}{x:,.0f}"),
                              textposition="outside"))
        fig6.add_trace(go.Bar(name="Budget", x=bvdf["Category"], y=bvdf["Budget"],
                              marker_color="#d9534f", opacity=0.5,
                              text=bvdf["Budget"].apply(lambda x: f"{currency}{x:,.0f}"),
                              textposition="outside"))
        fig6.update_layout(barmode="group", height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig6, width='stretch')

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
        st.markdown("Set a monthly spending limit per category. Alerts fire at 80% and when exceeded.")
        limits = cfg.get("limits", {})

        with st.form("limits_form"):
            new_limits = {}
            cols = st.columns(2)
            for i, cat in enumerate(CATS):
                with cols[i % 2]:
                    val = st.number_input(cat, min_value=0.0,
                                          value=float(limits.get(cat, 0)),
                                          step=100.0, format="%.0f", key=f"lim_{i}",
                                          help="0 = no limit")
                    if val > 0:
                        new_limits[cat] = val
            if st.form_submit_button("💾 Save Limits", width='stretch', type="primary"):
                cfg["limits"] = new_limits
                save_config(cfg)
                st.session_state.config = cfg
                st.success("✅ Budget limits saved!")

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
            if st.button("Delete All Data", disabled=not confirm, type="secondary"):
                st.session_state.df = pd.DataFrame(
                    columns=["id", "date", "category", "description", "amount", "member", "payment_method", "notes"])
                save_expenses(st.session_state.df)
                st.success("All data deleted.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 🏷️ MANAGE LISTS  ← NEW PAGE
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
