
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import connect, create_table
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(
    page_title="ExpensePro",
    page_icon="💰",
    layout="wide"
)

create_table()

# DESIGN
st.markdown("""
<style>
.stApp {background:#F4F6FB;}
.block-container {padding-top:2rem;}
[data-testid="stSidebar"] {background:#172554;}
[data-testid="stSidebar"] * {color:white !important;}
[data-testid="stMetric"] {
    background:white;
    padding:18px;
    border-radius:12px;
    border:1px solid #E2E8F0;
}
</style>
""", unsafe_allow_html=True)

# SIDEBAR
st.sidebar.title("💰 ExpensePro")
st.sidebar.caption("PERSONAL FINANCE MANAGER")

page = st.sidebar.radio(
    "NAVIGATION",
    ["Dashboard", "Add Transaction", "Transactions",
     "Reports", "Monthly Budget"]
)

st.sidebar.divider()
st.sidebar.caption("Manage your money wisely!")

# LOAD DATABASE
def load_data():
    con = connect()
    data = pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY date DESC",
        con
    )
    con.close()
    return data

df = load_data()

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])

# DASHBOARD
if page == "Dashboard":

    st.title("📊 Dashboard Overview")
    st.write("Welcome to your personal finance dashboard!")

    if not df.empty:

        income = df[df.type == "Income"].amount.sum()
        expense = df[df.type == "Expense"].amount.sum()
        balance = income - expense

        c1, c2, c3 = st.columns(3)
        c1.metric("💚 Income", f"₹{income:,.2f}")
        c2.metric("❤️ Expenses", f"₹{expense:,.2f}")
        c3.metric("💙 Balance", f"₹{balance:,.2f}")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Expense by Category")
            expenses = df[df.type == "Expense"]

            if not expenses.empty:
                category = expenses.groupby("category").amount.sum()
                fig, ax = plt.subplots()
                ax.pie(category, labels=category.index,
                       autopct="%1.1f%%")
                st.pyplot(fig)
                plt.close(fig)

        with col2:
            st.subheader("Income vs Expenses")
            chart = pd.DataFrame(
                {"Amount": [income, expense]},
                index=["Income", "Expenses"]
            )
            st.bar_chart(chart)

        st.subheader("Recent Transactions")
        st.dataframe(df.head(5), use_container_width=True)

    else:
        st.info("Add transactions to view dashboard.")

# ADD TRANSACTION
elif page == "Add Transaction":

    st.title("➕ Add Transaction")

    with st.form("transaction_form"):

        d = st.date_input("Date", date.today())

        t = st.selectbox("Type", ["Expense", "Income"])

        c = st.selectbox(
            "Category",
            ["Food", "Travel", "Shopping",
             "Education", "Bills", "Salary", "Other"]
        )

        a = st.number_input("Amount (₹)", min_value=1.0)
        desc = st.text_input("Description")

        submit = st.form_submit_button("Save Transaction")

        if submit:
            con = connect()
            con.execute(
                """INSERT INTO transactions
                (date,type,category,amount,description)
                VALUES (?,?,?,?,?)""",
                (str(d), t, c, a, desc)
            )
            con.commit()
            con.close()
            st.success("Transaction saved!")
            st.rerun()

# TRANSACTIONS WITH FILTERS
elif page == "Transactions":

    st.title("📋 Transaction History")

    if not df.empty:

        search = st.text_input("🔍 Search description or category")

        col1, col2, col3 = st.columns(3)

        with col1:
            type_filter = st.selectbox(
                "Transaction Type",
                ["All", "Income", "Expense"]
            )

        with col2:
            category_filter = st.selectbox(
                "Category",
                ["All"] + sorted(df.category.dropna().unique().tolist())
            )

        with col3:
            start_date = st.date_input(
                "Start Date",
                df.date.min().date()
            )

        end_date = st.date_input(
            "End Date",
            df.date.max().date()
        )

        filtered = df.copy()

        if type_filter != "All":
            filtered = filtered[filtered.type == type_filter]

        if category_filter != "All":
            filtered = filtered[filtered.category == category_filter]

        filtered = filtered[
            (filtered.date.dt.date >= start_date) &
            (filtered.date.dt.date <= end_date)
        ]

        if search:
            filtered = filtered[
                filtered.category.str.contains(
                    search, case=False, na=False
                ) |
                filtered.description.str.contains(
                    search, case=False, na=False
                )
            ]

        st.write(f"Found {len(filtered)} transactions")

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Delete Transaction")

        selected = st.selectbox(
            "Select Transaction ID",
            df.id.tolist()
        )

        if st.button("🗑️ Delete Transaction"):
            con = connect()
            con.execute(
                "DELETE FROM transactions WHERE id=?",
                (int(selected),)
            )
            con.commit()
            con.close()
            st.success("Transaction deleted!")
            st.rerun()

    else:
        st.info("No transactions found.")

# REPORTS AND DOWNLOADS
elif page == "Reports":

    st.title("📈 Financial Reports")

    if not df.empty:

        income = df[df.type == "Income"].amount.sum()
        expense = df[df.type == "Expense"].amount.sum()

        st.subheader("Financial Summary")

        c1, c2, c3 = st.columns(3)
        c1.metric("Income", f"₹{income:,.2f}")
        c2.metric("Expenses", f"₹{expense:,.2f}")
        c3.metric("Balance", f"₹{income-expense:,.2f}")

        st.subheader("Monthly Expense Analysis")

        expenses = df[df.type == "Expense"].copy()

        if not expenses.empty:
            expenses["Month"] = expenses.date.dt.strftime("%Y-%m")
            monthly = expenses.groupby("Month").amount.sum()
            st.bar_chart(monthly)

            st.subheader("Category Analysis")
            st.dataframe(
                expenses.groupby("category").amount.sum()
                .reset_index(),
                use_container_width=True
            )

        st.divider()
        st.subheader("📥 Download Reports")

        # EXCEL DOWNLOAD
        excel_buffer = BytesIO()

        with pd.ExcelWriter(
            excel_buffer, engine="openpyxl"
        ) as writer:
            df.to_excel(
                writer, sheet_name="Transactions", index=False
            )

            summary = pd.DataFrame({
                "Type": ["Income", "Expenses", "Balance"],
                "Amount": [income, expense, income-expense]
            })

            summary.to_excel(
                writer, sheet_name="Summary", index=False
            )

        st.download_button(
            "📗 Download Excel Report",
            data=excel_buffer.getvalue(),
            file_name="Expense_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # PDF DOWNLOAD
        pdf_buffer = BytesIO()

        doc = SimpleDocTemplate(
            pdf_buffer, pagesize=A4
        )

        styles = getSampleStyleSheet()

        elements = [
            Paragraph("Daily Expense Tracker Report", styles["Title"]),
            Spacer(1, 20),
            Paragraph(
                f"Total Income: Rs. {income:.2f}",
                styles["Normal"]
            ),
            Paragraph(
                f"Total Expenses: Rs. {expense:.2f}",
                styles["Normal"]
            ),
            Paragraph(
                f"Remaining Balance: Rs. {income-expense:.2f}",
                styles["Normal"]
            ),
            Spacer(1, 20)
        ]

        table_data = [[
            "Date", "Type", "Category", "Amount"
        ]]

        for _, row in df.iterrows():
            table_data.append([
                row["date"].strftime("%Y-%m-%d"),
                str(row["type"]),
                str(row["category"]),
                f"{row['amount']:.2f}"
            ])

        elements.append(Table(table_data))
        doc.build(elements)

        st.download_button(
            "📕 Download PDF Report",
            data=pdf_buffer.getvalue(),
            file_name="Expense_Report.pdf",
            mime="application/pdf"
        )

    else:
        st.info("Add transactions to generate reports.")

# MONTHLY BUDGET
elif page == "Monthly Budget":

    st.title("💰 Monthly Budget Management")

    month = date.today().strftime("%Y-%m")

    budget = st.number_input(
        "Set Monthly Budget (₹)",
        min_value=0.0,
        value=5000.0,
        step=500.0
    )

    if st.button("Save Budget"):
        con = connect()
        con.execute("""
            INSERT INTO budgets (month, amount)
            VALUES (?, ?)
            ON CONFLICT(month)
            DO UPDATE SET amount=excluded.amount
        """, (month, budget))
        con.commit()
        con.close()
        st.success("Budget saved!")
        st.rerun()

    con = connect()
    result = con.execute(
        "SELECT amount FROM budgets WHERE month=?",
        (month,)
    ).fetchone()
    con.close()

    if result:

        monthly_budget = result[0]

        if not df.empty:
            monthly_expenses = df[
                (df.type == "Expense") &
                (df.date.dt.strftime("%Y-%m") == month)
            ].amount.sum()
        else:
            monthly_expenses = 0

        remaining = monthly_budget - monthly_expenses

        c1, c2, c3 = st.columns(3)
        c1.metric("Budget", f"₹{monthly_budget:,.2f}")
        c2.metric("Spent", f"₹{monthly_expenses:,.2f}")
        c3.metric("Remaining", f"₹{remaining:,.2f}")

        progress = min(
            monthly_expenses / monthly_budget, 1.0
        ) if monthly_budget > 0 else 0

        st.subheader("Budget Progress")
        st.progress(progress)

        st.write(f"{progress*100:.1f}% used")

        if monthly_expenses > monthly_budget:
            st.error("You exceeded your monthly budget!")
        else:
            st.success("You are within your budget!")

    else:
        st.info("Please save your monthly budget first.")

st.sidebar.divider()
st.sidebar.caption("ExpensePro © 2026")
