import os
import os
from datetime import date

import streamlit as st
import pandas as pd

try:
    import qrcode
except ImportError as exc:
    qrcode = None
    QRCODE_IMPORT_ERROR = exc
else:
    QRCODE_IMPORT_ERROR = None

from auth import Auth
from bank import Bank
from account import SavingAccount
from deposit import DepositManager
from credit_card import CreditCardManager
from fixed_deposit import FixedDepositManager
from admin_panel import AdminPanelManager
from payments import PaymentManager
from recurring_deposit import RecurringDepositManager
from loan import EMICalculator, LoanManager
from kyc import KYCManager
from statement import BankStatement


st.set_page_config(
    page_title="Banking Management",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded",
)

bank = Bank()
deposit_manager = DepositManager(bank)
credit_card_manager = CreditCardManager()
loan_manager = LoanManager()
fd_manager = FixedDepositManager(bank)
admin_manager = AdminPanelManager()
payment_manager = PaymentManager(bank)
rd_manager = RecurringDepositManager(bank)
kyc_manager = KYCManager()

PHOTO_DIR = "customer_photos"


def ensure_photo_dir():
    os.makedirs(PHOTO_DIR, exist_ok=True)


def save_customer_photo(account_no, uploaded_file):
    if not uploaded_file:
        return ""

    ensure_photo_dir()
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower() if ext else ".png"
    photo_path = os.path.join(PHOTO_DIR, f"{account_no}{ext}")

    with open(photo_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    return photo_path


def render_customer_photo(account):
    photo_path = getattr(account, "photo_path", "") or ""
    if photo_path and os.path.exists(photo_path):
        st.image(photo_path, caption="Customer Photo", width=180)
    else:
        st.info("No customer photo uploaded for this account.")


def money(value):
    return f"${value:,.2f}"


def is_admin_user():
    return bool(st.session_state.get("is_admin")) or st.session_state.get("current_user", "").strip().lower() == "admin"


def build_qr_image(payload):
    if QRCODE_IMPORT_ERROR:
        raise ImportError(
            "qrcode is required for QR Code Payments. Install it with: pip install qrcode[pil]"
        ) from QRCODE_IMPORT_ERROR

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


def render_admin_dashboard():
    admin_manager.load()
    metrics = admin_manager.get_dashboard_metrics(bank, loan_manager, fd_manager, rd_manager, credit_card_manager)

    st.markdown('<div class="section-title">Admin Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Overview of users, accounts, deposits, loans, branches, and system settings.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Users", metrics["total_users"])
        st.metric("Accounts", metrics["total_accounts"])
    with c2:
        st.metric("Loans", metrics["total_loans"])
        st.metric("Branches", metrics["branches"])
    with c3:
        st.metric("FDs", metrics["total_fds"])
        st.metric("RDs", metrics["total_rds"])

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Credit Cards", metrics["total_cards"])
        st.metric("Active Branches", metrics["active_branches"])
    with c5:
        cfg = metrics["system_config"]
        st.markdown(
            f"""
            **System Snapshot**
            - Bank Name: {cfg.get("bank_name", "")}
            - Support Email: {cfg.get("support_email", "")}
            - Maintenance Mode: {"On" if cfg.get("maintenance_mode") else "Off"}
            - Currency: {cfg.get("currency_symbol", "$")}
            - Last Updated: {admin_manager.data.get("updated_at") or "Never"}
            """,
            unsafe_allow_html=True,
        )

    users = admin_manager.get_users()
    if users:
        st.subheader("Recent Users")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Username": user.get("username", ""),
                        "Full Name": user.get("full_name", ""),
                    }
                    for user in users[:10]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


def render_user_management():
    st.markdown('<div class="section-title">User Management</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">View users, create new users, update passwords, or remove non-admin accounts.</div>',
        unsafe_allow_html=True,
    )

    users = admin_manager.get_users()
    if users:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Username": user.get("username", ""),
                        "Full Name": user.get("full_name", ""),
                    }
                    for user in users
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No users found.")

    tab_create, tab_update_delete = st.tabs(["Create User", "Update / Delete User"])

    with tab_create:
        with st.form("admin_create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_full_name = st.text_input("Full Name")
            with col2:
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button("Create User", type="primary")
            if submitted:
                if not new_username.strip() or not new_password.strip():
                    render_error("Please enter username and password.")
                elif new_password.strip() != confirm_password.strip():
                    render_error("Passwords do not match.")
                elif admin_manager.create_user(new_username.strip(), new_full_name.strip(), new_password.strip()):
                    st.success("User created successfully.")
                    st.rerun()
                else:
                    render_error("Username already exists or is invalid.")

    with tab_update_delete:
        with st.form("admin_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                target_user = st.text_input("Username")
                new_password = st.text_input("New Password", type="password")
            with col2:
                action = st.radio("Action", ["Update Password", "Delete User"], horizontal=True)
                st.caption("Admin account cannot be deleted.")

            submitted = st.form_submit_button("Apply User Action", type="primary")
            if submitted:
                if not target_user.strip():
                    render_error("Please enter a username.")
                elif target_user.strip().lower() == "admin" and action == "Delete User":
                    render_error("Admin account cannot be deleted.")
                elif action == "Update Password" and not new_password.strip():
                    render_error("Please enter a new password.")
                else:
                    if action == "Update Password":
                        if admin_manager.update_user_password(target_user.strip(), new_password.strip()):
                            st.success("User password updated successfully.")
                            st.rerun()
                        else:
                            render_error("User not found.")
                    else:
                        if admin_manager.delete_user(target_user.strip()):
                            st.success("User deleted successfully.")
                            st.rerun()
                        else:
                            render_error("User not found.")


def render_branch_management():
    st.markdown('<div class="section-title">Branch Management</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Create, edit, or remove branch records.</div>',
        unsafe_allow_html=True,
    )

    branches = admin_manager.data.get("branches", [])
    if branches:
        st.dataframe(pd.DataFrame(branches), use_container_width=True, hide_index=True)
    else:
        st.info("No branches found.")

    tab_add, tab_edit, tab_delete = st.tabs(["Add Branch", "Edit Branch", "Delete Branch"])

    with tab_add:
        with st.form("add_branch_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Branch Name")
                city = st.text_input("City")
            with col2:
                state = st.text_input("State")
                manager_name = st.text_input("Branch Manager")

            status = st.selectbox("Status", ["Active", "Inactive"])
            submitted = st.form_submit_button("Add Branch", type="primary")
            if submitted:
                if admin_manager.add_branch(name, city, state, manager_name, status):
                    st.success("Branch added successfully.")
                    st.rerun()
                else:
                    render_error("Please fill branch name, city, and state.")

    with tab_edit:
        with st.form("edit_branch_form"):
            branch_ids = [branch.get("branch_id", "") for branch in branches] or [""]
            branch_id = st.selectbox("Branch ID", branch_ids)
            selected_branch = next((b for b in branches if b.get("branch_id") == branch_id), {})

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Branch Name", value=selected_branch.get("name", ""))
                city = st.text_input("City", value=selected_branch.get("city", ""))
            with col2:
                state = st.text_input("State", value=selected_branch.get("state", ""))
                manager_name = st.text_input("Branch Manager", value=selected_branch.get("manager", ""))

            status = st.selectbox("Status", ["Active", "Inactive"], index=0 if selected_branch.get("status", "Active") == "Active" else 1)
            submitted = st.form_submit_button("Update Branch", type="primary")
            if submitted:
                if admin_manager.update_branch(branch_id, name, city, state, manager_name, status):
                    st.success("Branch updated successfully.")
                    st.rerun()
                else:
                    render_error("Branch not found.")

    with tab_delete:
        with st.form("delete_branch_form"):
            branch_ids = [branch.get("branch_id", "") for branch in branches] or [""]
            branch_id = st.selectbox("Branch ID to delete", branch_ids)
            submitted = st.form_submit_button("Delete Branch", type="primary")
            if submitted:
                if admin_manager.delete_branch(branch_id):
                    st.success("Branch deleted successfully.")
                    st.rerun()
                else:
                    render_error("Branch not found.")


def render_interest_rate_settings():
    st.markdown('<div class="section-title">Interest Rate Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Update interest rates used by the banking modules.</div>',
        unsafe_allow_html=True,
    )

    rates = admin_manager.data.get("interest_rates", {})
    with st.form("interest_rate_form"):
        col1, col2 = st.columns(2)
        with col1:
            savings = st.number_input("Savings Rate (%)", value=float(rates.get("savings", 3.5)), step=0.1)
            loan_rate = st.number_input("Loan Rate (%)", value=float(rates.get("loan", 11.5)), step=0.1)
            fd_rate = st.number_input("FD Rate (%)", value=float(rates.get("fd", 7.0)), step=0.1)
        with col2:
            rd_rate = st.number_input("RD Rate (%)", value=float(rates.get("rd", 6.5)), step=0.1)
            cc_rate = st.number_input("Credit Card Rate (%)", value=float(rates.get("credit_card", 24.0)), step=0.1)
            st.caption("Rates are stored in `admin_panel.json` and can be referenced by your modules.")

        submitted = st.form_submit_button("Save Interest Rates", type="primary")
        if submitted:
            if admin_manager.update_interest_rates(savings, loan_rate, fd_rate, rd_rate, cc_rate):
                st.success("Interest rates updated successfully.")
                st.rerun()
            else:
                render_error("Unable to update interest rates.")


def render_system_configuration():
    st.markdown('<div class="section-title">System Configuration</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Manage bank-wide system settings and contact details.</div>',
        unsafe_allow_html=True,
    )

    cfg = admin_manager.data.get("system_config", {})
    with st.form("system_config_form"):
        bank_name = st.text_input("Bank Name", value=cfg.get("bank_name", "Banking Management System"))
        support_email = st.text_input("Support Email", value=cfg.get("support_email", "support@bank.local"))
        currency_symbol = st.text_input("Currency Symbol", value=cfg.get("currency_symbol", "$"), max_chars=4)
        maintenance_mode = st.checkbox("Maintenance Mode", value=bool(cfg.get("maintenance_mode", False)))

        submitted = st.form_submit_button("Save System Configuration", type="primary")
        if submitted:
            if admin_manager.update_system_config(bank_name, support_email, maintenance_mode, currency_symbol):
                st.success("System configuration updated successfully.")
                st.rerun()
            else:
                render_error("Unable to save system configuration.")


def inject_styles():
    st.markdown(
        """
        <style>
            :root {
                --ink: #0b2545;
                --muted: #536a8a;
                --line: #dce8fb;
                --panel: #ffffff;
                --soft: #f3f8ff;
                --primary: #0b61ff;
                --accent: #1e40ff;
                --danger: #ef4444;
            }

            .stApp {
                background: linear-gradient(180deg, #e6f0ff 0%, #ffffff 100%);
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
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(243,248,255,0.96));
                border: 1px solid var(--line);
            }

            .card-visual {
                min-height: 170px;
                border-radius: 8px;
                padding: 1.1rem;
                background: linear-gradient(135deg, #0b61ff 0%, #3b82f6 70%);
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.18);
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

            .login-background {
                background: transparent;
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
            }

            .auth-shell {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                padding: 2rem 1rem;
            }

            .auth-card {
                width: min(500px, 100%);
                max-width: 520px;
                background: white;
                border-radius: 24px;
                padding: 2rem;
                box-shadow: 0 22px 55px rgba(47, 87, 47, .14);
                border: 1px solid rgba(121, 182, 94, .25);
                margin: 0 auto;
            }

            .auth-card h3 {
                margin-top: 0;
                margin-bottom: 0.5rem;
                color: #2f6d3a;
            }

            .auth-card .stMarkdown {
                margin-bottom: 1rem;
            }

            .auth-card .stButton>button {
                border-radius: 999px;
                padding: .95rem 1.4rem;
                font-weight: 700;
                background: #3f7a3b;
                color: white;
                border: none;
            }

            .auth-card .stButton>button:hover {
                background: #346b34;
            }

            .auth-card input,
            .auth-card textarea {
                border-radius: 12px !important;
                border: 1px solid #cce5b9 !important;
                background: #f7ffed !important;
                padding: .95rem !important;
                color: #1f3f21 !important;
            }

            .auth-card .stExpander {
                background: #f3ffeb !important;
                border-radius: 16px;
                border: 1px solid rgba(92, 140, 76, .22);
            }

            .auth-footer {
                margin-top: 1.3rem;
                font-size: .93rem;
                color: #4b6e47;
                text-align: center;
            }

            .auth-card .stTextInput>div>div>input,
            .auth-card .stTextInput>div>div>textarea {
                border-radius: 14px !important;
                border: 1px solid #c4e0aa !important;
                background: #f8fff1 !important;
                padding: 1rem !important;
            }

            .auth-card .css-1siy2j7 {
                background: transparent !important;
            }

            .auth-footer {
                margin-top: 1.5rem;
                font-size: .94rem;
                color: #486545;
            }

            .auth-footer a {
                color: #0b61ff;
                text-decoration: none;
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
    if kind == "deposit":
        animation_class = "deposit-pop"
        title = "Deposit successful"
        copy = "Money added to the account."
    elif kind == "withdraw":
        animation_class = "withdraw-out"
        title = "Withdrawal successful"
        copy = "Cash withdrawn from the account."
    else:
        animation_class = "deposit-pop"
        title = "Transfer successful"
        copy = "Money moved between accounts."

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


def render_credit_card_details(card):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Card Number", card.card_no)
        st.metric("Holder Name", card.holder_name)

    with col2:
        st.metric("Credit Limit", money(card.credit_limit))
        st.metric("Outstanding", money(card.outstanding_amount))

    with col3:
        st.metric("Available Limit", money(card.available_limit()))
        st.metric("Minimum Due", money(card.minimum_due()))

    st.markdown(
        f"""
        <div class="success-panel">
            <div class="section-title">Card Profile</div>
            <div class="section-copy">
                Linked Account: <strong>{card.account_no}</strong> |
                Status: <strong>{card.status}</strong> |
                Created: <strong>{card.created_date}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if card.transactions:
        transaction_rows = []
        for transaction in card.transactions:
            transaction_rows.append(
                {
                    "Date": transaction.get("date", ""),
                    "Type": transaction.get("type", ""),
                    "Merchant": transaction.get("merchant", ""),
                    "Amount": money(transaction.get("amount", 0)),
                    "Outstanding": money(transaction.get("outstanding", 0)),
                }
            )
        st.subheader("Card Transactions")
        st.dataframe(pd.DataFrame(transaction_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No credit card transactions found yet.")


inject_styles()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_user = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"


def render_login_page():
    """Render a simple centered login page"""
    st.markdown(
        """
        <style>
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(180deg, #e6f0ff 0%, #ffffff 100%);
        }
        .login-form-box {
            background: white;
            padding: 50px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .login-title {
            font-size: 32px;
            font-weight: bold;
            color: #0b2545;
            margin-bottom: 10px;
        }
        .login-subtitle {
            color: #536a8a;
            font-size: 14px;
            margin-bottom: 30px;
        }
        .link-button {
            color: #0b61ff;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
            margin-top: 15px;
        }
        .link-button:hover {
            text-decoration: underline;
        }
        .black-button button {
            background-color: #000000 !important;
            color: white !important;
            border: none !important;
        }
        .black-button button:hover {
            background-color: #333333 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">🏦 Banking Login</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Enter your credentials</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
            
            login_button = st.form_submit_button("Login", use_container_width=True)

            if login_button:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                else:
                    user = Auth.get_user(username.strip())
                    if user and user.get("password") == password.strip():
                        st.session_state.authenticated = True
                        st.session_state.current_user = username.strip()
                        st.session_state.is_admin = username.strip().lower() == "admin"
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
        
        # Links for forgot password and change password
        st.markdown('<div class="black-button">', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("🔑 Forgot Password?", use_container_width=True):
                st.session_state.auth_page = "forgot_password"
                st.rerun()
        with col_b:
            if st.button("🔄 Change Password?", use_container_width=True):
                st.session_state.auth_page = "change_password"
                st.rerun()
        with col_c:
            if st.button("📝 Sign Up", use_container_width=True):
                st.session_state.auth_page = "register"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_forgot_password_page():
    """Render forgot password page"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">🔑 Forgot Password</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Reset your password</div>', unsafe_allow_html=True)
        
        with st.form("forgot_password_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            full_name = st.text_input("👨‍💼 Full Name", placeholder="Enter your full name")
            new_password = st.text_input("🔐 New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("🔐 Confirm Password", type="password", placeholder="Confirm new password")
            
            submit_button = st.form_submit_button("Reset Password", use_container_width=True)

            if submit_button:
                if not username or not full_name or not new_password or not confirm_password:
                    st.error("❌ Please fill all fields")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    if Auth.reset_password(username.strip(), full_name.strip(), new_password.strip()):
                        st.success("✅ Password reset successful! Please login with your new password.")
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error("❌ Username or Full Name not found")
        
        st.markdown('<div class="black-button">', unsafe_allow_html=True)
        if st.button("🔙 Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_change_password_page():
    """Render change password page (for logged-in users)"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">🔄 Change Password</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Update your password</div>', unsafe_allow_html=True)
        
        with st.form("change_password_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            current_password = st.text_input("🔐 Current Password", type="password", placeholder="Enter current password")
            new_password = st.text_input("🔐 New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("🔐 Confirm New Password", type="password", placeholder="Confirm new password")
            
            submit_button = st.form_submit_button("Change Password", use_container_width=True)

            if submit_button:
                if not username or not current_password or not new_password or not confirm_password:
                    st.error("❌ Please fill all fields")
                elif new_password != confirm_password:
                    st.error("❌ New passwords do not match")
                else:
                    if Auth.change_password(username.strip(), current_password.strip(), new_password.strip()):
                        st.success("✅ Password changed successfully! Please login with your new password.")
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or current password")
        
        st.markdown('<div class="black-button">', unsafe_allow_html=True)
        if st.button("🔙 Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_register_page():
    """Render registration/sign-up page"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">📝 Create Account</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Join our banking system</div>', unsafe_allow_html=True)
        
        with st.form("register_form"):
            full_name = st.text_input("👨‍💼 Full Name", placeholder="Enter your full name")
            username = st.text_input("👤 Username", placeholder="Choose a username")
            password = st.text_input("🔐 Password", type="password", placeholder="Create a strong password")
            confirm_password = st.text_input("🔐 Confirm Password", type="password", placeholder="Confirm your password")
            
            submit_button = st.form_submit_button("Create Account", use_container_width=True)

            if submit_button:
                if not full_name or not username or not password or not confirm_password:
                    st.error("❌ Please fill all fields")
                elif len(username) < 3:
                    st.error("❌ Username must be at least 3 characters long")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters long")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    if Auth.register(username.strip(), password.strip(), full_name.strip()):
                        st.success("✅ Account created successfully! Please login with your new credentials.")
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error("❌ Username already exists. Please choose a different username.")
        
        st.markdown('<div class="black-button">', unsafe_allow_html=True)
        if st.button("🔙 Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
if st.session_state.authenticated:
    st.sidebar.title("Bank Console")
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.current_user}")

    if st.sidebar.button("🚪 Log Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = ""
        st.session_state.is_admin = False
        st.rerun()

    st.sidebar.divider()

    if is_admin_user():
        menu_options = [
            "Admin Panel",
            "Dashboard",
            "User Management",
            "Branch Management",
            "Interest Rate Settings",
            "System Configuration",
            "------- CUSTOMER BANKING -------",
            "Home",
            "Create Account",
            "View Account",
            "Search Account",
            "Deposit",
            "Withdraw",
            "Transfer",
            "Change Password",
            "Delete Account",
            "Transaction History",
            "------- STATEMENTS -------",
            "Download Bank Statement",
            "------- KYC -------",
            "Submit KYC",
            "View KYC Status",
            "My KYC Details",
            "------- LOANS -------",
            "EMI Calculator",
            "Apply for Loan",
            "View My Loans",
            "Make Loan Payment",
            "Loan Details",
            "------- FDS -------",
            "Open Fixed Deposit",
            "View My FDs",
            "Close Fixed Deposit",
            "------- RDS -------",
            "Open Recurring Deposit",
            "View My RDs",
            "Pay RD Installment",
            "Close Recurring Deposit",
            "------- PAYMENTS -------",
            "QR Code Payments",
            "UPI Integration",
            "Bill Payments",
            "Recharge",
            "------- CARDS -------",
            "Issue Credit Card",
            "My Credit Cards",
            "Credit Card Purchase",
            "Credit Card Payment",
            "Credit Card Details",
            "Update Card Status",
        ]
    else:
        menu_options = [
            "Home",
            "Create Account",
            "View Account",
            "Search Account",
            "Deposit",
            "Withdraw",
            "Transfer",
            "Change Password",
            "Delete Account",
            "Transaction History",
            "------- STATEMENTS -------",
            "Download Bank Statement",
            "------- KYC -------",
            "Submit KYC",
            "View KYC Status",
            "My KYC Details",
            "------- LOANS -------",
            "EMI Calculator",
            "Apply for Loan",
            "View My Loans",
            "Make Loan Payment",
            "Loan Details",
            "------- FDS -------",
            "Open Fixed Deposit",
            "View My FDs",
            "Close Fixed Deposit",
            "------- RDS -------",
            "Open Recurring Deposit",
            "View My RDs",
            "Pay RD Installment",
            "Close Recurring Deposit",
            "------- PAYMENTS -------",
            "QR Code Payments",
            "UPI Integration",
            "Bill Payments",
            "Recharge",
            "------- CARDS -------",
            "Issue Credit Card",
            "My Credit Cards",
            "Credit Card Purchase",
            "Credit Card Payment",
            "Credit Card Details",
            "Update Card Status",
        ]

    menu = st.sidebar.radio("Menu", menu_options)
else:
    menu = None

if not st.session_state.authenticated:
    if st.session_state.auth_page == "login":
        render_login_page()
    elif st.session_state.auth_page == "forgot_password":
        render_forgot_password_page()
    elif st.session_state.auth_page == "change_password":
        render_change_password_page()
    elif st.session_state.auth_page == "register":
        render_register_page()
else:
    if st.session_state.get("current_user", "").strip().lower() == "admin":
        st.sidebar.success("Admin access enabled")

    if menu == "Admin Panel":
        render_admin_dashboard()

    elif menu == "Dashboard":
        render_admin_dashboard()

    elif menu == "User Management":
        render_user_management()

    elif menu == "Branch Management":
        render_branch_management()

    elif menu == "Interest Rate Settings":
        render_interest_rate_settings()

    elif menu == "System Configuration":
        render_system_configuration()

    if menu == "Home":
        render_home()

    elif menu == "Create Account":
        st.markdown('<div class="section-title">Create Account</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Open a new savings account. The account number will be generated automatically.</div>',
            unsafe_allow_html=True,
        )

        with st.form("create_account_form", clear_on_submit=False):
            name = st.text_input("Customer Name")
            balance = st.number_input("Opening Balance", min_value=0, step=100)
            photo_file = st.file_uploader(
                "Customer Photo",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=False,
            )

            if st.form_submit_button("Create Account", type="primary"):
                if not name.strip():
                    render_error("Please enter a customer name.")
                else:
                    temp_account_no = bank.get_next_account_no()
                    photo_path = save_customer_photo(temp_account_no, photo_file)
                    account = bank.create_account_auto(
                        name.strip(),
                        balance,
                        photo_path,
                        account_no=temp_account_no,
                    )
                    st.success("Account created successfully.")
                    st.markdown(
                        f"**Generated Account Number:** `{account.account_no}`",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"**Generated Account PIN:** `{account.pin}`",
                        unsafe_allow_html=True,
                    )
                    render_customer_photo(account)

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
                "Photo": "Yes" if getattr(account, "photo_path", "") else "No",
            }
            for account in bank.accounts
        ]

        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            selected_account_no = st.selectbox(
                "View customer photo",
                [account.account_no for account in bank.accounts],
                index=0,
            )
            selected_account = bank.find_account(selected_account_no)
            if selected_account:
                render_customer_photo(selected_account)
        else:
            st.info("No accounts found. Create an account to get started.")

    elif menu == "Deposit":
        st.markdown('<div class="section-title">Deposit Money</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Add funds to an existing customer account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("deposit_form", clear_on_submit=False):
            account_no = st.text_input("Account Number")
            amount = st.number_input("Amount", min_value=1, step=100)

            if st.form_submit_button("Deposit", type="primary"):
                if not account_no.strip():
                    render_error("Please enter an account number.")
                else:
                    account = deposit_manager.deposit(account_no.strip(), amount)

                    if account:
                        render_transaction_animation("deposit", amount)
                        st.caption(f"Updated balance: {money(account.get_balance())}")
                    else:
                        render_error("Deposit failed. Please check the account number and amount.")

    elif menu == "Transaction History":
        st.header("Transaction History")
        account_no = st.text_input("Enter Account Number:")

        if st.button("View History"):
            account = bank.find_account(account_no.strip())

            if account:
                data = []

                for transaction in account.transactions:
                    if isinstance(transaction, dict):
                        data.append({
                            "Type": transaction["type"],
                            "Amount": transaction["amount"],
                            "Date": transaction["date"],
                        })
                    else:
                        data.append({
                            "Type": transaction.transaction_type,
                            "Amount": transaction.amount,
                            "Date": transaction.date,
                        })

                if data:
                    st.dataframe(data)
                else:
                    st.warning("No transactions found")
            else:
                st.error("Account not found")

    elif menu == "Download Bank Statement":
        st.markdown('<div class="section-title">Download Bank Statement</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Generate and download your bank statement as PDF.</div>', unsafe_allow_html=True)

        with st.form("statement_form", clear_on_submit=False):
            col1, col2 = st.columns(2)

            with col1:
                account_no = st.text_input("Account Number")

            with col2:
                statement_type = st.radio("Statement Type", ["Full Statement", "Custom Period"])

            if statement_type == "Custom Period":
                col3, col4 = st.columns(2)
                with col3:
                    start_date = st.date_input("Start Date")
                with col4:
                    end_date = st.date_input("End Date")
            else:
                start_date = None
                end_date = None

            if st.form_submit_button("Generate PDF Statement", type="primary"):
                if not account_no.strip():
                    st.error("Please enter account number.")
                elif statement_type == "Custom Period" and start_date and end_date and start_date > end_date:
                    st.error("Start Date cannot be later than End Date.")
                else:
                    account = bank.find_account(account_no.strip())

                    if not account:
                        st.error("Account not found.")
                    else:
                        try:
                            import time

                            timestamp = int(time.time())
                            filename = f"statement_{account_no.strip()}_{timestamp}.pdf"

                            statement = BankStatement(account)
                            pdf_file = statement.generate_pdf(filename, start_date, end_date)

                            with open(pdf_file, "rb") as file:
                                st.session_state.statement_pdf_data = file.read()
                            st.session_state.statement_pdf_name = filename

                            st.success("Statement generated successfully!")
                            st.markdown(f"""
                            **Statement Summary:**
                            - Account Number: {account.account_no}
                            - Account Holder: {account.name}
                            - Current Balance: {money(account.get_balance())}
                            - Total Transactions: {len(account.transactions)}
                            """)

                            st.download_button(
                                label="Download PDF Statement",
                                data=st.session_state.statement_pdf_data,
                                file_name=st.session_state.statement_pdf_name,
                                mime="application/pdf",
                                use_container_width=True,
                                key="statement_download_button",
                            )

                            if os.path.exists(pdf_file):
                                os.remove(pdf_file)

                        except ImportError:
                            st.error("ReportLab library not installed. Please install it first.")
                            st.info("Run: pip install reportlab")
                        except Exception as e:
                            st.error(f"Error generating statement: {str(e)}")

        if st.session_state.get("statement_pdf_data") and st.session_state.get("statement_pdf_name"):
            st.download_button(
                label="Download Last Generated PDF",
                data=st.session_state.statement_pdf_data,
                file_name=st.session_state.statement_pdf_name,
                mime="application/pdf",
                use_container_width=True,
                key="statement_download_button_persist",
            )
    elif menu == "Search Account":
        st.markdown('<div class="section-title">Search Accounts</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Search by account number or customer name.</div>', unsafe_allow_html=True)

        query = st.text_input("Search by account number or name")

        if st.button("Search"):
            q = query.strip()
            if not q:
                st.info("Please enter a search term.")
            else:
                results = []
                # exact account number match
                acc = bank.find_account(q)
                if acc:
                    results.append(acc)
                else:
                    # name or partial account number match
                    for a in bank.accounts:
                        if q.lower() in a.name.lower() or q in a.account_no:
                            results.append(a)

                if results:
                    data = [
                        {"Account No": a.account_no, "Name": a.name, "Balance": a.get_balance()}
                        for a in results
                    ]
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                    sel_label = [f"{a.account_no} - {a.name}" for a in results]
                    sel = st.selectbox("Select account to view", sel_label)
                    if st.button("View Selected"):
                        idx = sel_label.index(sel)
                        a = results[idx]
                        st.markdown(f"**Account No:** {a.account_no}")
                        st.markdown(f"**Name:** {a.name}")
                        st.markdown(f"**Balance:** {money(a.get_balance())}")
                        render_customer_photo(a)
                else:
                    st.warning("No accounts found.")
                    with st.expander("Create account with this info"):
                        name = st.text_input("Customer Name", value=query if query and not (query.isdigit()) else "")
                        balance = st.number_input("Opening Balance", min_value=0, step=100)
                        photo_file = st.file_uploader(
                            "Customer Photo",
                            type=["png", "jpg", "jpeg", "webp"],
                            key="search_customer_photo",
                        )
                        if st.button("Create Account (from search)"):
                            if not name.strip():
                                st.error("Please provide a customer name.")
                            else:
                                temp_account_no = bank.get_next_account_no()
                                photo_path = save_customer_photo(temp_account_no, photo_file)
                                account = bank.create_account_auto(
                                    name.strip(),
                                    balance,
                                    photo_path,
                                    account_no=temp_account_no,
                                )
                                st.success(f"Account created successfully. Generated Account Number: {account.account_no}")
                                st.rerun()

    elif menu == "Withdraw":
        st.markdown('<div class="section-title">Withdraw Money</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Withdraw available funds from a customer account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("withdraw_form", clear_on_submit=False):
            account_no = st.text_input("Account Number")
            amount = st.number_input("Amount", min_value=1, step=100)

            if st.form_submit_button("Withdraw", type="primary"):
                if not account_no.strip():
                    render_error("Please enter an account number.")
                else:
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
    
    elif menu == "Transfer":
        st.markdown('<div class="section-title">Transfer Money</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Move funds from one customer account to another.</div>',
            unsafe_allow_html=True,
        )

        with st.container():
            from_account_no = st.text_input("From Account Number")
            to_account_no = st.text_input("To Account Number")
            amount = st.number_input("Amount", min_value=1, step=100)

            if st.button("Transfer", type="primary"):
                if from_account_no.strip() == to_account_no.strip():
                    render_error("Source and destination accounts must be different.")
                else:
                    success = bank.transfer(from_account_no.strip(), to_account_no.strip(), amount)
                    if success:
                        render_transaction_animation("transfer", amount)
                        from_acc = bank.find_account(from_account_no.strip())
                        to_acc = bank.find_account(to_account_no.strip())
                        if from_acc:
                            st.caption(f"From Updated balance: {money(from_acc.get_balance())}")
                        if to_acc:
                            st.caption(f"To Updated balance: {money(to_acc.get_balance())}")
                    else:
                        render_error("Transfer failed. Check account numbers and available balance.")

    elif menu == "Change Password":
        st.markdown('<div class="section-title">Change Password</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Update your login password for your user account.</div>',
            unsafe_allow_html=True,
        )

        current_password = st.text_input("Current Password", type="password", key="current_password")
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

        if st.button("Update Password", type="primary"):
            if not current_password.strip() or not new_password.strip() or not confirm_password.strip():
                render_error("Please fill in all password fields.")
            elif new_password.strip() != confirm_password.strip():
                render_error("New passwords do not match.")
            elif Auth.change_password(st.session_state.current_user, current_password.strip(), new_password.strip()):
                st.success("✅ Password changed successfully.")
            else:
                render_error("Current password is incorrect. Password not changed.")

    elif menu == "Delete Account":
        st.markdown('<div class="section-title">Delete Account</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Permanently remove a customer account.</div>',
            unsafe_allow_html=True,
        )

        with st.container():
            account_no = st.text_input("Account Number to delete")
            confirm = st.checkbox("I understand this will permanently delete the account")

            if st.button("Delete Account", type="primary"):
                if not account_no.strip():
                    render_error("Please enter an account number.")
                elif not confirm:
                    render_error("Please confirm deletion by checking the box.")
                else:
                    deleted = bank.delete_account(account_no.strip())
                    if deleted:
                        st.success("Account deleted successfully.")
                        st.rerun()
                    else:
                        render_error("Account not found. Please check the account number.")

    elif menu == "Submit KYC":
        st.markdown('<div class="section-title">📋 Submit KYC Verification</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Complete your Know Your Customer (KYC) verification for banking compliance.</div>', unsafe_allow_html=True)

        with st.form("kyc_submission_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                account_no = st.text_input("Account Number")
                full_name = st.text_input("Full Name")
                email = st.text_input("Email Address")
                phone = st.text_input("Phone Number")
            
            with col2:
                address = st.text_area("Address", height=100)
                city = st.text_input("City")
                state = st.text_input("State")
                pincode = st.text_input("Pincode")
            
            col3, col4 = st.columns(2)
            
            with col3:
                id_type = st.selectbox("ID Type", ["Aadhar", "PAN", "Passport", "Driving License"])
                id_number = st.text_input("ID Number")
            
            with col4:
                dob = st.date_input(
                    "Date of Birth",
                    min_value=date(2000, 1, 1),
                    max_value=date.today(),
                )

            photo_file = st.file_uploader(
                "Customer Photo",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=False,
                key="kyc_customer_photo",
            )
            
            submitted = st.form_submit_button("Submit KYC", type="primary")
            if submitted:
                required_fields = {
                    "Account Number": account_no.strip(),
                    "Full Name": full_name.strip(),
                    "Email Address": email.strip(),
                    "Phone Number": phone.strip(),
                    "Address": address.strip(),
                    "City": city.strip(),
                    "State": state.strip(),
                    "Pincode": pincode.strip(),
                    "ID Type": id_type.strip(),
                    "ID Number": id_number.strip(),
                    "Date of Birth": dob.isoformat() if hasattr(dob, "isoformat") else str(dob),
                }
                missing_fields = [label for label, value in required_fields.items() if not value]
                if missing_fields:
                    st.error(f"Please fill all fields: {', '.join(missing_fields)}")
                else:
                    # Verify account exists
                    kyc_manager.load_kyc()
                    account = bank.find_account(account_no.strip())
                    if not account:
                        st.error("Account not found")
                    else:
                        photo_path = save_customer_photo(account_no.strip(), photo_file)
                        saved = kyc_manager.submit_kyc(
                            account_no.strip(),
                            full_name.strip(),
                            email.strip(),
                            phone.strip(),
                            address.strip(),
                            city.strip(),
                            state.strip(),
                            pincode.strip(),
                            id_type.strip(),
                            id_number.strip(),
                            dob.isoformat() if hasattr(dob, "isoformat") else str(dob),
                            photo_path,
                        )
                        if saved:
                            st.success("KYC submitted successfully!")
                            st.markdown("""
                            **Your KYC Status:** Pending

                            Your KYC application is under review. You will receive approval notification within 2-3 business days.
                            """)
                            st.rerun()
                        else:
                            st.error("KYC submission failed. Please check the details and try again.")
    elif menu == "View KYC Status":
        st.markdown('<div class="section-title">📊 KYC Status</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Check your KYC verification status.</div>', unsafe_allow_html=True)

        account_no = st.text_input("Enter Account Number")

        if st.button("Check Status"):
            if not account_no.strip():
                st.error("❌ Please enter account number")
            else:
                kyc_manager.load_kyc()  # Reload KYC data
                status = kyc_manager.get_kyc_status(account_no.strip())
                
                if status == "Not Submitted":
                    st.warning("⚠️ KYC Not Submitted")
                    st.info("Please submit your KYC details using 'Submit KYC' option.")
                elif status == "Pending":
                    st.info("⏳ KYC Verification Pending")
                    st.markdown("Your KYC is under review. Please wait for approval (2-3 business days).")
                elif status == "Approved":
                    st.success("✅ KYC Approved")
                    st.balloons()
                    st.markdown("Your KYC verification is complete and approved!")
                elif status == "Rejected":
                    kyc = kyc_manager.find_kyc_by_account(account_no.strip())
                    st.error("❌ KYC Rejected")
                    if kyc.rejection_reason:
                        st.markdown(f"**Reason:** {kyc.rejection_reason}")
                    st.info("Please contact support for more information.")

    elif menu == "My KYC Details":
        st.markdown('<div class="section-title">📄 My KYC Details</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">View your submitted KYC information.</div>', unsafe_allow_html=True)

        account_no = st.text_input("Enter Account Number")

        if st.button("View Details"):
            if not account_no.strip():
                st.error("❌ Please enter account number")
            else:
                kyc_manager.load_kyc()  # Reload KYC data
                kyc = kyc_manager.find_kyc_by_account(account_no.strip())
                
                if not kyc:
                    st.warning("No KYC details found. Please submit KYC first.")
                else:
                    render_customer_photo(kyc)
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("KYC Status", kyc.status)
                        st.metric("ID Type", kyc.id_type)
                    
                    with col2:
                        st.metric("Email", kyc.email)
                        st.metric("Phone", kyc.phone)
                    
                    with col3:
                        st.metric("Date of Birth", kyc.dob)
                        st.metric("Submitted Date", kyc.created_date.split()[0])
                    
                    with st.expander("Full Details"):
                        st.markdown(f"""
                        **Personal Information:**
                        - Full Name: {kyc.full_name}
                        - Email: {kyc.email}
                        - Phone: {kyc.phone}
                        - Date of Birth: {kyc.dob}
                        
                        **Address:**
                        - Address: {kyc.address}
                        - City: {kyc.city}
                        - State: {kyc.state}
                        - Pincode: {kyc.pincode}
                        
                        **Identification:**
                        - ID Type: {kyc.id_type}
                        - ID Number: {kyc.id_number}
                        
                        **Status:**
                        - Current Status: {kyc.status}
                        - Submitted On: {kyc.created_date}
                        """)
                        
                        if kyc.approved_date:
                            st.markdown(f"- Approved On: {kyc.approved_date}")
                        
                        if kyc.rejection_reason:
                            st.markdown(f"- Rejection Reason: {kyc.rejection_reason}")

    elif menu == "EMI Calculator":
        st.markdown('<div class="section-title">EMI Calculator</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Calculate monthly EMI and repayment schedule before applying for a loan.</div>',
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            principal = st.number_input("Loan Amount", min_value=1000, step=1000, key="emi_principal")

        with col2:
            rate = st.number_input(
                "Interest Rate (% per annum)",
                min_value=0.0,
                max_value=30.0,
                step=0.5,
                key="emi_rate",
            )

        with col3:
            tenure_months = st.slider(
                "Tenure (Months)",
                min_value=1,
                max_value=120,
                step=1,
                key="emi_tenure",
            )

        summary = EMICalculator.calculate_summary(principal, rate, tenure_months)

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Monthly EMI", money(summary["monthly_emi"]))
        with metric_col2:
            st.metric("Total Interest", money(summary["total_interest"]))
        with metric_col3:
            st.metric("Total Payable", money(summary["total_payable"]))

        schedule = EMICalculator.generate_schedule(principal, rate, tenure_months)
        schedule_data = [
            {
                "Month": row["Month"],
                "EMI": money(row["EMI"]),
                "Principal": money(row["Principal"]),
                "Interest": money(row["Interest"]),
                "Balance": money(row["Balance"]),
            }
            for row in schedule
        ]
        st.dataframe(pd.DataFrame(schedule_data), use_container_width=True, hide_index=True)

    elif menu == "Apply for Loan":
        st.markdown('<div class="section-title">💳 Apply for Loan</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Apply for a new loan with flexible terms.</div>', unsafe_allow_html=True)

        with st.container():
            col1, col2 = st.columns(2)
            
            with col1:
                account_no = st.text_input("Account Number")
                principal = st.number_input("Loan Amount (Principal)", min_value=1000, step=1000)
            
            with col2:
                customer_name = st.text_input("Customer Name")
                rate = st.number_input("Interest Rate (% per annum)", min_value=1.0, max_value=30.0, step=0.5)
            
            tenure_months = st.slider("Loan Tenure (Months)", min_value=6, max_value=60, step=1)
            loan_summary = EMICalculator.calculate_summary(principal, rate, tenure_months)

            preview_col1, preview_col2, preview_col3 = st.columns(3)
            with preview_col1:
                st.metric("Estimated EMI", money(loan_summary["monthly_emi"]))
            with preview_col2:
                st.metric("Total Interest", money(loan_summary["total_interest"]))
            with preview_col3:
                st.metric("Total Payable", money(loan_summary["total_payable"]))

            if st.button("Apply for Loan", type="primary"):
                if not account_no.strip() or not customer_name.strip():
                    st.error("❌ Please enter account number and customer name")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        st.error("❌ Account not found")
                    else:
                        loan = loan_manager.create_loan(
                            account_no.strip(),
                            customer_name.strip(),
                            principal,
                            rate,
                            tenure_months
                        )
                        st.success(f"✅ Loan approved successfully!")
                        st.markdown(f"""
                        **Loan Details:**
                        - **Loan ID:** `{loan.loan_id}` (Copy this for future reference)
                        - Principal: {money(loan.principal)}
                        - Monthly EMI: {money(loan.monthly_emi)}
                        - Total Interest: {money(loan.get_total_interest())}
                        - Total Payable: {money(loan.get_total_payable())}
                        - Tenure: {loan.tenure_months} months
                        - Interest Rate: {loan.rate}% p.a.
                        """)
                        loan_manager.load_loans()  # Reload loans to ensure persistence

    elif menu == "View My Loans":
        st.markdown('<div class="section-title">📊 View My Loans</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Check all your active and closed loans.</div>', unsafe_allow_html=True)

        account_no = st.text_input("Enter Account Number")

        if st.button("View Loans"):
            if not account_no.strip():
                st.error("❌ Please enter account number")
            else:
                loan_manager.load_loans()  # Reload loans
                loans = loan_manager.get_loans_by_account(account_no.strip())
                
                if loans:
                    data = []
                    for loan in loans:
                        data.append({
                            "Loan ID": loan.loan_id,
                            "Status": loan.status,
                            "Principal": money(loan.principal),
                            "Outstanding": money(loan.outstanding_amount),
                            "Monthly EMI": money(loan.monthly_emi),
                            "Total Payable": money(loan.get_total_payable()),
                            "Tenure": f"{loan.tenure_months} months"
                        })
                    
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    st.info(f"💡 Copy any Loan ID from above and use it in 'Make Loan Payment' or 'Loan Details'")
                else:
                    st.info("No loans found for this account")

    elif menu == "Make Loan Payment":
        st.markdown('<div class="section-title">💰 Make Loan Payment</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Pay your monthly EMI or lump sum amount.</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        
        with col1:
            loan_id = st.text_input("Loan ID")
        
        with col2:
            payment_amount = st.number_input("Payment Amount", min_value=1, step=100)

        if st.button("Make Payment", type="primary"):
            if not loan_id.strip():
                st.error("❌ Please enter loan ID")
            else:
                loan_manager.load_loans()  # Reload loans
                loan = loan_manager.find_loan(loan_id.strip())
                
                if not loan:
                    st.error("❌ Loan not found. Please check the Loan ID.")
                    st.info("💡 Tip: Go to 'View My Loans' to see your loan IDs")
                elif loan.status == "Closed":
                    st.error("❌ This loan is already closed")
                elif payment_amount > loan.outstanding_amount:
                    st.error(f"❌ Payment amount cannot exceed outstanding amount: {money(loan.outstanding_amount)}")
                else:
                    if loan_manager.make_loan_payment(loan_id.strip(), payment_amount):
                        loan_manager.load_loans()  # Reload to get updated loan
                        updated_loan = loan_manager.find_loan(loan_id.strip())
                        st.success("✅ Payment received successfully!")
                        st.markdown(f"""
                        **Payment Details:**
                        - Amount Paid: {money(payment_amount)}
                        - Outstanding Amount: {money(updated_loan.outstanding_amount)}
                        - Remaining EMIs: {updated_loan.get_remaining_payments()}
                        - Status: {updated_loan.status}
                        """)
                    else:
                        st.error("❌ Payment failed")

    elif menu == "Loan Details":
        st.markdown('<div class="section-title">📋 Loan Details</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">View detailed information about a specific loan.</div>', unsafe_allow_html=True)

        loan_id = st.text_input("Enter Loan ID")

        if st.button("View Details"):
            if not loan_id.strip():
                st.error("❌ Please enter loan ID")
            else:
                loan_manager.load_loans()  # Reload loans
                loan = loan_manager.find_loan(loan_id.strip())
                
                if not loan:
                    st.error("❌ Loan not found. Please check the Loan ID.")
                    st.info("💡 Tip: Go to 'View My Loans' to see your loan IDs")
                else:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Loan ID", loan.loan_id)
                        st.metric("Principal Amount", money(loan.principal))
                        st.metric("Interest Rate", f"{loan.rate}%")
                    
                    with col2:
                        st.metric("Status", loan.status)
                        st.metric("Monthly EMI", money(loan.monthly_emi))
                        st.metric("Total Payable", money(loan.get_total_payable()))
                        st.metric("Tenure", f"{loan.tenure_months} months")
                    
                    with col3:
                        st.metric("Outstanding", money(loan.outstanding_amount))
                        st.metric("Amount Paid", money(loan.paid_amount))
                        st.metric("Total Interest", money(loan.get_total_interest()))
                        st.metric("Remaining EMIs", loan.get_remaining_payments())
                    
                    if loan.payments:
                        st.subheader("Payment History")
                        payment_data = []
                        for payment in loan.payments:
                            payment_data.append({
                                "Date": payment["date"],
                                "Amount": money(payment["amount"]),
                                "Outstanding": money(payment["outstanding"])
                            })
                        st.dataframe(pd.DataFrame(payment_data), use_container_width=True, hide_index=True)
                    else:
                        st.info("No payments made yet")

    elif menu == "Open Fixed Deposit":
        st.markdown('<div class="section-title">Open Fixed Deposit</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Lock funds into a fixed deposit and earn interest over time.</div>',
            unsafe_allow_html=True,
        )

        with st.form("fd_open_form"):
            col1, col2 = st.columns(2)

            with col1:
                account_no = st.text_input("Account Number")
                principal = st.number_input("FD Amount", min_value=1000, step=1000)
                tenure_months = st.slider("Tenure (Months)", min_value=3, max_value=120, step=1)

            with col2:
                holder_name = st.text_input("Holder Name")
                rate = st.number_input("Interest Rate (% p.a.)", min_value=1.0, max_value=20.0, step=0.5)
                st.caption("Funds will be deducted from the linked account when the FD is opened.")

            submitted = st.form_submit_button("Open Fixed Deposit", type="primary")
            if submitted:
                if not account_no.strip():
                    render_error("Please enter an account number.")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        render_error("Account not found. Please check the account number.")
                    elif principal <= 0:
                        render_error("Please enter a valid FD amount.")
                    elif account.get_balance() < principal:
                        render_error("Insufficient balance to open this FD.")
                    else:
                        final_holder = holder_name.strip() or account.name
                        fd = fd_manager.open_fd(
                            account_no.strip(),
                            final_holder,
                            principal,
                            rate,
                            tenure_months,
                        )
                        if fd:
                            st.success("Fixed deposit opened successfully.")
                            st.markdown(
                                f"""
                                **FD Details**
                                - FD ID: `{fd.fd_id}`
                                - Linked Account: `{fd.account_no}`
                                - Principal: {money(fd.principal)}
                                - Interest Rate: {fd.rate}% p.a.
                                - Tenure: {fd.tenure_months} months
                                - Interest Amount: {money(fd.interest_amount)}
                                - Maturity Amount: {money(fd.maturity_amount)}
                                - Maturity Date: {fd.maturity_date}
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            render_error("Unable to open FD. Please check the details and try again.")

    elif menu == "View My FDs":
        st.markdown('<div class="section-title">View My FDs</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">See all fixed deposits linked to an account.</div>',
            unsafe_allow_html=True,
        )

        account_no = st.text_input("Enter Account Number")

        if st.button("View Fixed Deposits"):
            if not account_no.strip():
                render_error("Please enter an account number.")
            else:
                fd_manager.load_fds()
                fds = fd_manager.get_fds_by_account(account_no.strip())

                if fds:
                    data = []
                    for fd in fds:
                        data.append({
                            "FD ID": fd.fd_id,
                            "Status": fd.status,
                            "Principal": money(fd.principal),
                            "Interest Rate": f"{fd.rate}%",
                            "Tenure": f"{fd.tenure_months} months",
                            "Interest": money(fd.interest_amount),
                            "Maturity Amount": money(fd.maturity_amount),
                            "Maturity Date": fd.maturity_date,
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                else:
                    st.info("No fixed deposits found for this account.")

    elif menu == "Close Fixed Deposit":
        st.markdown('<div class="section-title">Close Fixed Deposit</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Close an FD and credit the maturity amount back to the linked account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("fd_close_form"):
            fd_id = st.text_input("FD ID")
            submitted = st.form_submit_button("Close Fixed Deposit", type="primary")

            if submitted:
                if not fd_id.strip():
                    render_error("Please enter an FD ID.")
                else:
                    fd_manager.load_fds()
                    fd = fd_manager.find_fd(fd_id.strip())
                    if not fd:
                        render_error("FD not found. Please check the FD ID.")
                    elif fd.status != "Active":
                        render_error("This FD is already closed.")
                    else:
                        closed_fd = fd_manager.close_fd(fd_id.strip())
                        if closed_fd:
                            st.success("Fixed deposit closed successfully.")
                            st.markdown(
                                f"""
                                **Closure Details**
                                - FD ID: `{closed_fd.fd_id}`
                                - Account Number: `{closed_fd.account_no}`
                                - Maturity Amount Credited: {money(closed_fd.maturity_amount)}
                                - Closed Date: {closed_fd.closed_date}
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            render_error("Unable to close FD. Please try again.")
    elif menu == "Open Recurring Deposit":
        st.markdown('<div class="section-title">Open Recurring Deposit</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Start a recurring deposit with monthly installments from your linked account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("rd_open_form"):
            col1, col2 = st.columns(2)

            with col1:
                account_no = st.text_input("Account Number")
                monthly_installment = st.number_input("Monthly Installment", min_value=500, step=500)
                tenure_months = st.slider("Tenure (Months)", min_value=6, max_value=120, step=1)

            with col2:
                holder_name = st.text_input("Holder Name")
                rate = st.number_input("Interest Rate (% p.a.)", min_value=1.0, max_value=20.0, step=0.5)
                st.caption("You will deposit the installment every month until maturity.")

            submitted = st.form_submit_button("Open Recurring Deposit", type="primary")
            if submitted:
                if not account_no.strip():
                    render_error("Please enter an account number.")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        render_error("Account not found. Please check the account number.")
                    elif monthly_installment <= 0:
                        render_error("Please enter a valid monthly installment.")
                    else:
                        final_holder = holder_name.strip() or account.name
                        rd = rd_manager.open_rd(
                            account_no.strip(),
                            final_holder,
                            monthly_installment,
                            rate,
                            tenure_months,
                        )
                        if rd:
                            st.success("Recurring deposit opened successfully.")
                            st.markdown(
                                f"""
                                **RD Details**
                                - RD ID: `{rd.rd_id}`
                                - Linked Account: `{rd.account_no}`
                                - Monthly Installment: {money(rd.monthly_installment)}
                                - Interest Rate: {rd.rate}% p.a.
                                - Tenure: {rd.tenure_months} months
                                - Expected Interest: {money(rd.interest_amount)}
                                - Expected Maturity Amount: {money(rd.maturity_amount)}
                                - Maturity Date: {rd.maturity_date}
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            render_error("Unable to open RD. Please check the details and try again.")

    elif menu == "View My RDs":
        st.markdown('<div class="section-title">View My RDs</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">See all recurring deposits linked to an account.</div>',
            unsafe_allow_html=True,
        )

        account_no = st.text_input("Enter Account Number")

        if st.button("View Recurring Deposits"):
            if not account_no.strip():
                render_error("Please enter an account number.")
            else:
                rd_manager.load_rds()
                rds = rd_manager.get_rds_by_account(account_no.strip())

                if rds:
                    data = []
                    for rd in rds:
                        data.append({
                            "RD ID": rd.rd_id,
                            "Status": rd.status,
                            "Monthly Installment": money(rd.monthly_installment),
                            "Interest Rate": f"{rd.rate}%",
                            "Tenure": f"{rd.tenure_months} months",
                            "Installments Paid": f"{rd.installments_paid}/{rd.tenure_months}",
                            "Deposited": money(rd.total_deposited),
                            "Interest": money(rd.interest_amount),
                            "Maturity Amount": money(rd.maturity_amount),
                            "Maturity Date": rd.maturity_date,
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                else:
                    st.info("No recurring deposits found for this account.")

    elif menu == "Pay RD Installment":
        st.markdown('<div class="section-title">Pay RD Installment</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Pay one installment toward an active recurring deposit.</div>',
            unsafe_allow_html=True,
        )

        with st.form("rd_payment_form"):
            rd_id = st.text_input("RD ID")
            submitted = st.form_submit_button("Pay Installment", type="primary")

            if submitted:
                if not rd_id.strip():
                    render_error("Please enter an RD ID.")
                else:
                    rd_manager.load_rds()
                    rd = rd_manager.find_rd(rd_id.strip())
                    if not rd:
                        render_error("RD not found. Please check the RD ID.")
                    elif rd.status != "Active":
                        render_error("This RD is already closed.")
                    elif rd.installments_paid >= rd.tenure_months:
                        render_error("All installments are already paid.")
                    else:
                        paid_rd = rd_manager.pay_installment(rd_id.strip())
                        if paid_rd:
                            st.success("Installment paid successfully.")
                            st.markdown(
                                f"""
                                **Payment Details**
                                - RD ID: `{paid_rd.rd_id}`
                                - Installments Paid: {paid_rd.installments_paid}/{paid_rd.tenure_months}
                                - Total Deposited: {money(paid_rd.total_deposited)}
                                - Current Expected Maturity: {money(paid_rd.maturity_amount)}
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            render_error("Unable to pay installment. Check the linked account balance.")

    elif menu == "Close Recurring Deposit":
        st.markdown('<div class="section-title">Close Recurring Deposit</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Close a matured RD and credit the maturity amount back to the linked account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("rd_close_form"):
            rd_id = st.text_input("RD ID")
            submitted = st.form_submit_button("Close Recurring Deposit", type="primary")

            if submitted:
                if not rd_id.strip():
                    render_error("Please enter an RD ID.")
                else:
                    rd_manager.load_rds()
                    rd = rd_manager.find_rd(rd_id.strip())
                    if not rd:
                        render_error("RD not found. Please check the RD ID.")
                    elif rd.status != "Active":
                        render_error("This RD is already closed.")
                    elif rd.installments_paid < rd.tenure_months:
                        render_error("RD is not fully matured yet.")
                    else:
                        closed_rd = rd_manager.close_rd(rd_id.strip())
                        if closed_rd:
                            st.success("Recurring deposit closed successfully.")
                            st.markdown(
                                f"""
                                **Closure Details**
                                - RD ID: `{closed_rd.rd_id}`
                                - Account Number: `{closed_rd.account_no}`
                                - Maturity Amount Credited: {money(closed_rd.maturity_amount)}
                                - Closed Date: {closed_rd.closed_date}
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            render_error("Unable to close RD. Please try again.")
    elif menu == "QR Code Payments":
        st.markdown('<div class="section-title">QR Code Payments</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Generate a QR payment request and pay a merchant from your bank account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("qr_payment_form"):
            col1, col2 = st.columns(2)
            with col1:
                account_no = st.text_input("Account Number")
                merchant_name = st.text_input("Merchant Name")
                upi_id = st.text_input("Merchant UPI ID")
            with col2:
                amount = st.number_input("Amount", min_value=1, step=1)
                note = st.text_input("Payment Note")
                st.caption("A QR payload will be generated for the entered merchant details.")

            submitted = st.form_submit_button("Pay via QR", type="primary")
            if submitted:
                if not account_no.strip():
                    render_error("Please enter an account number.")
                elif not merchant_name.strip() or not upi_id.strip():
                    render_error("Please enter merchant name and UPI ID.")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        render_error("Account not found. Please check the account number.")
                    else:
                        qr_payload = payment_manager.build_qr_payload(merchant_name.strip(), upi_id.strip(), amount, note.strip())
                        result = payment_manager.pay_via_qr(account_no.strip(), merchant_name.strip(), upi_id.strip(), amount, note.strip())
                        if result:
                            st.success("QR payment completed successfully.")
                            st.code(qr_payload)
                            try:
                                qr_image = build_qr_image(qr_payload)
                            except ImportError:
                                st.warning("QR preview is unavailable because the `qrcode` package is not installed.")
                            else:
                                st.image(qr_image, caption="Scan QR Payment Request", width=240)
                            st.caption(f"Updated balance: {money(result.get_balance())}")
                        else:
                            render_error("Payment failed. Please check your balance and details.")

    elif menu == "UPI Integration":
        st.markdown('<div class="section-title">UPI Integration</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Send money directly to a UPI ID from your account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("upi_payment_form"):
            col1, col2 = st.columns(2)
            with col1:
                account_no = st.text_input("Account Number")
                payee_upi = st.text_input("Payee UPI ID")
            with col2:
                amount = st.number_input("Amount", min_value=1, step=1)
                note = st.text_input("Payment Note")

            submitted = st.form_submit_button("Pay via UPI", type="primary")
            if submitted:
                if not account_no.strip() or not payee_upi.strip():
                    render_error("Please enter account number and UPI ID.")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        render_error("Account not found. Please check the account number.")
                    else:
                        upi_uri = payment_manager.build_upi_uri(payee_upi.strip(), "UPI Recipient", amount, note.strip())
                        result = payment_manager.pay_via_upi(account_no.strip(), payee_upi.strip(), amount, note.strip())
                        if result:
                            st.success("UPI payment completed successfully.")
                            st.code(upi_uri)
                            st.caption(f"Updated balance: {money(result.get_balance())}")
                        else:
                            render_error("Payment failed. Please check your balance and details.")

    elif menu == "Bill Payments":
        st.markdown('<div class="section-title">Bill Payments</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Pay electricity, water, internet, gas, school, and other bills.</div>',
            unsafe_allow_html=True,
        )

        with st.form("bill_payment_form"):
            col1, col2 = st.columns(2)
            with col1:
                account_no = st.text_input("Account Number")
                bill_type = st.selectbox("Bill Type", ["Electricity", "Water", "Internet", "Gas", "School Fee", "Other"])
                biller_name = st.text_input("Biller Name")
            with col2:
                consumer_number = st.text_input("Consumer / Account Number")
                amount = st.number_input("Bill Amount", min_value=1, step=1)
                note = st.text_input("Reference Note")

            submitted = st.form_submit_button("Pay Bill", type="primary")
            if submitted:
                if not account_no.strip() or not biller_name.strip() or not consumer_number.strip():
                    render_error("Please fill account number, biller name, and consumer number.")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        render_error("Account not found. Please check the account number.")
                    else:
                        result = payment_manager.pay_bill(account_no.strip(), biller_name.strip(), consumer_number.strip(), amount, bill_type)
                        if result:
                            st.success("Bill payment completed successfully.")
                            st.caption(f"Reference: {note.strip() or 'N/A'}")
                            st.caption(f"Updated balance: {money(result.get_balance())}")
                        else:
                            render_error("Payment failed. Please check your balance and details.")

    elif menu == "Recharge":
        st.markdown('<div class="section-title">Recharge</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Recharge a mobile number using your bank account.</div>',
            unsafe_allow_html=True,
        )

        with st.form("recharge_form"):
            col1, col2 = st.columns(2)
            with col1:
                account_no = st.text_input("Account Number")
                mobile_number = st.text_input("Mobile Number")
            with col2:
                operator = st.selectbox("Operator", ["Airtel", "Jio", "VI", "BSNL", "Other"])
                amount = st.number_input("Recharge Amount", min_value=1, step=1)

            submitted = st.form_submit_button("Recharge Now", type="primary")
            if submitted:
                if not account_no.strip() or not mobile_number.strip():
                    render_error("Please enter account number and mobile number.")
                else:
                    account = bank.find_account(account_no.strip())
                    if not account:
                        render_error("Account not found. Please check the account number.")
                    else:
                        result = payment_manager.recharge(account_no.strip(), mobile_number.strip(), operator, amount)
                        if result:
                            st.success("Recharge completed successfully.")
                            st.caption(f"Updated balance: {money(result.get_balance())}")
                        else:
                            render_error("Recharge failed. Please check your balance and details.")
    elif menu == "Issue Credit Card":
        st.markdown('<div class="section-title">Issue Credit Card</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Create a new credit card linked to an existing savings account.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            account_no = st.text_input("Account Number")
            holder_name = st.text_input("Card Holder Name")

        with col2:
            credit_limit = st.number_input("Credit Limit", min_value=1000, step=1000)
            st.caption("New cards are created with Active status.")

        if st.button("Issue Card", type="primary"):
            if not account_no.strip():
                render_error("Please enter an account number.")
            else:
                account = bank.find_account(account_no.strip())
                if not account:
                    render_error("Account not found. Please check the account number.")
                else:
                    final_holder = holder_name.strip() or account.name
                    card = credit_card_manager.create_card(account_no.strip(), final_holder, credit_limit)
                    st.success("Credit card issued successfully.")
                    st.markdown(
                        f"""
                        **Card Details**
                        - Card Number: `{card.card_no}`
                        - Holder Name: {card.holder_name}
                        - Linked Account: `{card.account_no}`
                        - Credit Limit: {money(card.credit_limit)}
                        - Status: {card.status}
                        """,
                        unsafe_allow_html=True,
                    )

    elif menu == "My Credit Cards":
        st.markdown('<div class="section-title">My Credit Cards</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">View all credit cards linked to a savings account.</div>',
            unsafe_allow_html=True,
        )

        account_no = st.text_input("Enter Account Number")

        if st.button("View Cards"):
            if not account_no.strip():
                render_error("Please enter an account number.")
            else:
                credit_card_manager.load_cards()
                cards = credit_card_manager.get_cards_by_account(account_no.strip())

                if cards:
                    rows = []
                    for card in cards:
                        rows.append(
                            {
                                "Card Number": card.card_no,
                                "Holder": card.holder_name,
                                "Status": card.status,
                                "Credit Limit": money(card.credit_limit),
                                "Outstanding": money(card.outstanding_amount),
                                "Available Limit": money(card.available_limit()),
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No credit cards found for this account.")

    elif menu == "Credit Card Purchase":
        st.markdown('<div class="section-title">Credit Card Purchase</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Record a purchase against an active credit card.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            card_no = st.text_input("Card Number")
            merchant = st.text_input("Merchant Name")

        with col2:
            amount = st.number_input("Purchase Amount", min_value=1, step=100)

        if st.button("Record Purchase", type="primary"):
            if not card_no.strip():
                render_error("Please enter a card number.")
            else:
                credit_card_manager.load_cards()
                card = credit_card_manager.make_purchase(card_no.strip(), amount, merchant.strip())
                if card:
                    st.success("Purchase recorded successfully.")
                    render_credit_card_details(card)
                else:
                    render_error("Purchase failed. Check the card number, status, and available limit.")

    elif menu == "Credit Card Payment":
        st.markdown('<div class="section-title">Credit Card Payment</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Make a payment toward your credit card outstanding balance.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            card_no = st.text_input("Card Number")

        with col2:
            amount = st.number_input("Payment Amount", min_value=1, step=100)

        if st.button("Make Payment", type="primary"):
            if not card_no.strip():
                render_error("Please enter a card number.")
            else:
                credit_card_manager.load_cards()
                card = credit_card_manager.make_payment(card_no.strip(), amount)
                if card:
                    st.success("Payment posted successfully.")
                    render_credit_card_details(card)
                else:
                    render_error("Payment failed. Check the card number and payment amount.")

    elif menu == "Credit Card Details":
        st.markdown('<div class="section-title">Credit Card Details</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Inspect a single card profile and its transaction history.</div>',
            unsafe_allow_html=True,
        )

        card_no = st.text_input("Enter Card Number")

        if st.button("View Card"):
            if not card_no.strip():
                render_error("Please enter a card number.")
            else:
                credit_card_manager.load_cards()
                card = credit_card_manager.find_card(card_no.strip())
                if card:
                    render_credit_card_details(card)
                else:
                    render_error("Card not found. Please check the card number.")

    elif menu == "Update Card Status":
        st.markdown('<div class="section-title">Update Card Status</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Change a card status to Active, Suspended, or Closed.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            card_no = st.text_input("Card Number")

        with col2:
            new_status = st.selectbox("New Status", ["Active", "Suspended", "Closed"])

        if st.button("Update Status", type="primary"):
            if not card_no.strip():
                render_error("Please enter a card number.")
            else:
                credit_card_manager.load_cards()
                card = credit_card_manager.update_status(card_no.strip(), new_status)
                if card:
                    st.success(f"Card status updated to {card.status}.")
                    render_credit_card_details(card)
                else:
                    render_error("Card not found. Please check the card number.")
