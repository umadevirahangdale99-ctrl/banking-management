import streamlit as st
import pandas as pd

from bank import Bank
from account import SavingAccount


st.set_page_config(
    page_title="Banking Management",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded",
)

bank = Bank()


def money(value):
    return f"${value:,.2f}"


def inject_styles():
    st.markdown(
        """
        <style>
            :root {
                --ink: #172033;
                --muted: #667085;
                --line: #d9e2ef;
                --panel: #ffffff;
                --soft: #f5f8fc;
                --primary: #1f6feb;
                --accent: #10b981;
                --danger: #ef4444;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(31, 111, 235, .10), transparent 30rem),
                    linear-gradient(180deg, #f7faff 0%, #eef3f9 100%);
                color: var(--ink);
            }

            section[data-testid="stSidebar"] {
                background: #101828;
            }

            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] span,
            section[data-testid="stSidebar"] p {
                color: #f8fafc !important;
            }

            .block-container {
                padding-top: 2.2rem;
                padding-bottom: 2.5rem;
                max-width: 1180px;
            }

            .hero {
                min-height: 320px;
                display: grid;
                grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr);
                gap: 1.25rem;
                align-items: stretch;
                margin-bottom: 1.25rem;
            }

            .hero-main,
            .hero-panel,
            .metric-card,
            .form-panel,
            .success-panel,
            .error-panel {
                background: rgba(255, 255, 255, .92);
                border: 1px solid rgba(217, 226, 239, .95);
                box-shadow: 0 18px 48px rgba(16, 24, 40, .08);
                border-radius: 8px;
            }

            .hero-main {
                padding: clamp(1.5rem, 4vw, 3rem);
                display: flex;
                flex-direction: column;
                justify-content: center;
                overflow: hidden;
                position: relative;
            }

            .eyebrow {
                color: var(--primary);
                font-size: .78rem;
                font-weight: 800;
                letter-spacing: 0;
                text-transform: uppercase;
                margin-bottom: .7rem;
            }

            .hero h1 {
                font-size: clamp(2rem, 5vw, 4.2rem);
                line-height: 1;
                margin: 0;
                color: var(--ink);
                letter-spacing: 0;
            }

            .hero p {
                max-width: 620px;
                color: var(--muted);
                font-size: 1.02rem;
                line-height: 1.7;
                margin: 1rem 0 0;
            }

            .hero-panel {
                padding: 1.25rem;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                gap: 1rem;
            }

            .card-visual {
                min-height: 170px;
                border-radius: 8px;
                padding: 1.1rem;
                background:
                    linear-gradient(135deg, #12213f 0%, #1f6feb 58%, #18a999 100%);
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.24);
            }

            .card-number {
                font-size: 1rem;
                letter-spacing: 0;
                opacity: .9;
            }

            .card-balance {
                font-size: 1.9rem;
                font-weight: 800;
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 1rem;
                margin: 1rem 0 1.35rem;
            }

            .metric-card {
                padding: 1rem;
            }

            .metric-label {
                color: var(--muted);
                font-size: .84rem;
                margin-bottom: .45rem;
            }

            .metric-value {
                font-size: 1.65rem;
                font-weight: 800;
                color: var(--ink);
            }

            .form-panel,
            .success-panel,
            .error-panel {
                padding: 1.35rem;
                margin-top: .85rem;
            }

            .section-title {
                font-size: 1.55rem;
                font-weight: 800;
                color: var(--ink);
                margin-bottom: .25rem;
            }

            .section-copy {
                color: var(--muted);
                margin-bottom: 1rem;
            }

            .success-panel {
                border-color: rgba(16, 185, 129, .35);
                background: linear-gradient(180deg, rgba(236, 253, 245, .96), rgba(255,255,255,.96));
            }

            .error-panel {
                border-color: rgba(239, 68, 68, .35);
                background: linear-gradient(180deg, rgba(254, 242, 242, .96), rgba(255,255,255,.96));
            }

            .txn-stage {
                position: relative;
                height: 180px;
                overflow: hidden;
                border-radius: 8px;
                background:
                    linear-gradient(180deg, rgba(255,255,255,.92), rgba(241,245,249,.92));
                border: 1px solid var(--line);
                margin-top: .8rem;
            }

            .wallet {
                position: absolute;
                left: 50%;
                bottom: 22px;
                transform: translateX(-50%);
                width: 172px;
                height: 90px;
                border-radius: 8px;
                background: linear-gradient(135deg, #172033, #2d3a55);
                box-shadow: 0 16px 35px rgba(16, 24, 40, .22);
            }

            .wallet::after {
                content: "";
                position: absolute;
                right: 18px;
                top: 28px;
                width: 38px;
                height: 22px;
                border-radius: 6px;
                background: #f8fafc;
                opacity: .18;
            }

            .bill {
                position: absolute;
                left: calc(50% - 52px);
                width: 104px;
                height: 48px;
                border-radius: 6px;
                background: linear-gradient(135deg, #d1fae5, #34d399);
                border: 2px solid rgba(5, 150, 105, .35);
                color: #065f46;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 900;
                box-shadow: 0 12px 24px rgba(16, 185, 129, .20);
            }

            .bill::before,
            .bill::after {
                content: "";
                position: absolute;
                border: 1px solid rgba(6, 95, 70, .24);
                border-radius: 50%;
                width: 18px;
                height: 18px;
            }

            .bill::before { left: 10px; }
            .bill::after { right: 10px; }

            .deposit-pop {
                top: 100px;
                animation: depositPop 1.25s ease-out forwards;
            }

            .withdraw-out {
                top: 20px;
                animation: withdrawOut 1.35s ease-in-out forwards;
            }

            .bill-two {
                animation-delay: .12s;
                transform: rotate(-5deg);
            }

            .bill-three {
                animation-delay: .24s;
                transform: rotate(6deg);
            }

            .burst {
                position: absolute;
                left: 50%;
                top: 46%;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: var(--accent);
                transform: translate(-50%, -50%);
                animation: burst .75s ease-out forwards;
            }

            @keyframes depositPop {
                0% { transform: translateY(-90px) scale(.88) rotate(-3deg); opacity: 0; }
                48% { transform: translateY(8px) scale(1.05) rotate(2deg); opacity: 1; }
                72% { transform: translateY(-10px) scale(1.02) rotate(-1deg); opacity: 1; }
                100% { transform: translateY(42px) scale(.82) rotate(0); opacity: 0; }
            }

            @keyframes withdrawOut {
                0% { transform: translateY(92px) scale(.78) rotate(0); opacity: 0; }
                32% { transform: translateY(44px) scale(1) rotate(-2deg); opacity: 1; }
                100% { transform: translateY(-38px) scale(1.08) rotate(5deg); opacity: 0; }
            }

            @keyframes burst {
                0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, .45); opacity: .95; }
                100% { box-shadow: 0 0 0 70px rgba(16, 185, 129, 0); opacity: 0; }
            }

            @media (max-width: 820px) {
                .hero,
                .metric-grid {
                    grid-template-columns: 1fr;
                }

                .hero {
                    min-height: auto;
                }

                .hero-main,
                .hero-panel,
                .form-panel {
                    padding: 1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metrics():
    total_balance = sum(account.get_balance() for account in bank.accounts)
    largest_balance = max((account.get_balance() for account in bank.accounts), default=0)

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Accounts</div>
                <div class="metric-value">{len(bank.accounts)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Deposits</div>
                <div class="metric-value">{money(total_balance)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Highest Balance</div>
                <div class="metric-value">{money(largest_balance)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home():
    total_balance = sum(account.get_balance() for account in bank.accounts)
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-main">
                <div class="eyebrow">Modern banking dashboard</div>
                <h1>Banking Management</h1>
                <p>
                    Manage customer accounts, monitor balances, and process deposits
                    or withdrawals from a clean professional workspace.
                </p>
            </div>
            <div class="hero-panel">
                <div class="card-visual">
                    <div class="card-number">BANK / SECURE ACCOUNTING</div>
                    <div>
                        <div style="opacity:.78; font-size:.88rem;">Portfolio Balance</div>
                        <div class="card-balance">{money(total_balance)}</div>
                    </div>
                </div>
                <div style="color:#667085; line-height:1.55;">
                    Quick access is available from the sidebar for account creation,
                    account review, deposits, and withdrawals.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metrics()


def render_transaction_animation(kind, amount):
    animation_class = "deposit-pop" if kind == "deposit" else "withdraw-out"
    title = "Deposit successful" if kind == "deposit" else "Withdrawal successful"
    copy = "Money added to the account." if kind == "deposit" else "Cash withdrawn from the account."

    st.markdown(
        f"""
        <div class="success-panel">
            <div class="section-title">{title}</div>
            <div class="section-copy">{copy} Transaction amount: <strong>{money(amount)}</strong></div>
            <div class="txn-stage">
                <div class="burst"></div>
                <div class="bill {animation_class}">$</div>
                <div class="bill {animation_class} bill-two">$</div>
                <div class="bill {animation_class} bill-three">$</div>
                <div class="wallet"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_error(message):
    st.markdown(
        f"""
        <div class="error-panel">
            <div class="section-title">Action needed</div>
            <div class="section-copy">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_styles()

st.sidebar.title("Bank Console")
menu = st.sidebar.radio(
    "Menu",
    [
        "Home",
        "Create Account",
        "View Account",
        "Deposit",
        "Withdraw",
    ],
)

if menu == "Home":
    render_home()

elif menu == "Create Account":
    st.markdown('<div class="section-title">Create Account</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Open a new savings account with an initial balance.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        account_no = st.text_input("Account Number")
        name = st.text_input("Customer Name")
        balance = st.number_input("Opening Balance", min_value=0, step=100)

        if st.button("Create Account", type="primary"):
            if not account_no.strip() or not name.strip():
                render_error("Please enter both account number and customer name.")
            elif bank.find_account(account_no.strip()):
                render_error("An account with this number already exists.")
            else:
                account = SavingAccount(account_no.strip(), name.strip(), balance)
                bank.create_account(account)
                st.success("Account created successfully.")

elif menu == "View Account":
    st.markdown('<div class="section-title">Account Overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Review all registered customer accounts and balances.</div>',
        unsafe_allow_html=True,
    )
    render_metrics()

    data = [
        {
            "Account No": account.account_no,
            "Name": account.name,
            "Balance": account.get_balance(),
        }
        for account in bank.accounts
    ]

    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info("No accounts found. Create an account to get started.")

elif menu == "Deposit":
    st.markdown('<div class="section-title">Deposit Money</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Add funds to an existing customer account.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        account_no = st.text_input("Account Number")
        amount = st.number_input("Amount", min_value=1, step=100)

        if st.button("Deposit", type="primary"):
            account = bank.find_account(account_no.strip())

            if account:
                account.deposite(amount)
                bank.save_accounts()
                render_transaction_animation("deposit", amount)
                st.caption(f"Updated balance: {money(account.get_balance())}")
            else:
                render_error("Account not found. Please check the account number.")

elif menu == "Withdraw":
    st.markdown('<div class="section-title">Withdraw Money</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Withdraw available funds from a customer account.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        account_no = st.text_input("Account Number")
        amount = st.number_input("Amount", min_value=1, step=100)

        if st.button("Withdraw", type="primary"):
            account = bank.find_account(account_no.strip())

            if account:
                result = account.withdraw(amount)
                if result:
                    bank.save_accounts()
                    render_transaction_animation("withdraw", amount)
                    st.caption(f"Updated balance: {money(account.get_balance())}")
                else:
                    render_error("Insufficient balance for this withdrawal.")
            else:
                render_error("Account not found. Please check the account number.")
