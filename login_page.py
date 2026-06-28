import streamlit as st
from auth import Auth


def show_login_page():
    """Display a centered login page"""
    
    # Add custom CSS for centering
    st.markdown("""
        <style>
        .center-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .login-box {
            width: 100%;
            max-width: 400px;
            padding: 40px;
            border-radius: 10px;
            background: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .login-title {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 30px;
            color: #0b2545;
        }
        .login-input {
            margin-bottom: 15px;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Center the entire login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">🏦 Banking Login</div>', unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form"):
            username = st.text_input(
                "👤 Username",
                placeholder="Enter your username",
                key="login_username"
            )
            
            password = st.text_input(
                "🔐 Password",
                type="password",
                placeholder="Enter your password",
                key="login_password"
            )
            
            col1_btn, col2_btn, col3_btn = st.columns(3)
            
            with col2_btn:
                submit = st.form_submit_button(
                    "🔓 Login",
                    use_container_width=True
                )
            
            if submit:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                else:
                    user = Auth.get_user(username)
                    if user and user.get("password") == password:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
        
        # Sign up option
        st.markdown("---")
        if st.button("📝 Create New Account", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()


def show_signup_page():
    """Display a centered signup page"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">📋 Create Account</div>', unsafe_allow_html=True)
        
        with st.form("signup_form"):
            full_name = st.text_input(
                "👤 Full Name",
                placeholder="Enter your full name",
                key="signup_name"
            )
            
            username = st.text_input(
                "📧 Username",
                placeholder="Choose a username",
                key="signup_username"
            )
            
            password = st.text_input(
                "🔐 Password",
                type="password",
                placeholder="Create a password",
                key="signup_password"
            )
            
            confirm_password = st.text_input(
                "🔐 Confirm Password",
                type="password",
                placeholder="Confirm your password",
                key="signup_confirm"
            )
            
            col1_btn, col2_btn, col3_btn = st.columns(3)
            
            with col2_btn:
                submit = st.form_submit_button(
                    "✅ Sign Up",
                    use_container_width=True
                )
            
            if submit:
                if not full_name or not username or not password or not confirm_password:
                    st.error("❌ Please fill all fields")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif Auth.get_user(username):
                    st.error("❌ Username already exists")
                else:
                    # Register new user
                    users = Auth._load_users()
                    users.append({
                        "username": username,
                        "password": password,
                        "full_name": full_name
                    })
                    Auth._save_users(users)
                    st.success("✅ Account created successfully! Please login.")
                    st.session_state.page = "login"
                    st.rerun()
        
        st.markdown("---")
        if st.button("🔙 Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
