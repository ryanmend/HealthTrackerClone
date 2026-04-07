import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
import hashlib
import re
import random
import string
from datetime import date

st.set_page_config(page_title="Weight Tracker", layout="wide")

st.markdown(
    """
<style>
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    header {visibility: hidden;}

    [data-testid="stMetric"] {
        background: #f7f9fc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 18px;
    }

    [data-testid = "stMetric"] * {
        color: #2d3748 !important;}

    div[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        background-color: #e53e3e;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.45rem 1rem;
        font-weight: 600;
    }

    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #c53030;
    }
</style>
""",
    unsafe_allow_html=True,
)

if "page" not in st.session_state:
    st.session_state["page"] = "Login"


# ─────────────────────────── Database Connection ───────────────────────────
dbPath = os.path.join(os.getcwd(), "project.db")

@st.cache_resource
def get_connection():
    connection = sqlite3.connect(dbPath, check_same_thread=False)
    cursor = connection.cursor()

    # User table  (email added)
    cursor.execute(
        """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    email    TEXT
)
"""
    )

    # Migrate: add email column if it does not exist yet
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
        connection.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Profile table (email included)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles(
        username TEXT PRIMARY KEY,
        height   REAL,
        age      INTEGER,
        sex      TEXT,
        email    TEXT
        )
        """)

    # Migrate: add email column to profiles if missing
    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN email TEXT")
        connection.commit()
    except sqlite3.OperationalError:
        pass

    # Goal table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        username    TEXT PRIMARY KEY,
        goal_weight REAL
    )
    """)

    # Records table
    cursor.execute(
        """
CREATE TABLE IF NOT EXISTS records (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    weight   REAL,
    date     DATE
)
"""
    )

    connection.commit()
    return connection, cursor

connection, cursor = get_connection()


# ─────────────────────────── Hashing ───────────────────────────────────────
def hashPassword(password: str) -> str:
    """Returns the SHA-256 hash of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()


def generateRandomPassword(length: int = 10) -> str:
    """Generate a random password of given length."""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choices(chars, k=length))


# ─────────────────────────── Auth / User Functions ─────────────────────────
def createUser(username: str, password: str, email: str):
    try:
        cursor.execute(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            (username, hashPassword(password), email.lower().strip()),
        )
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def loginUser(username: str, password: str):
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, hashPassword(password)),
    )
    return cursor.fetchone()


def getUserEmail(username: str):
    cursor.execute("SELECT email FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    return result[0] if result else None


def updateUserEmail(username: str, email: str):
    cursor.execute(
        "UPDATE users SET email = ? WHERE username = ?",
        (email.lower().strip(), username),
    )
    connection.commit()


# ─────────────────────── Forgot Password / Username ────────────────────────
def forgotPassword(username: str):
    """
    If the username exists, generate a new random password, store its hash,
    and return (email, new_plain_password).  Returns (None, None) if not found.
    """
    cursor.execute("SELECT email FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        return None, None
    email = row[0]
    new_pw = generateRandomPassword()
    cursor.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (hashPassword(new_pw), username),
    )
    connection.commit()
    return email, new_pw


def forgotUsername(email: str):
    """
    Look up a username by email address.
    Returns the username string, or None if not found.
    """
    cursor.execute(
        "SELECT username FROM users WHERE email = ?",
        (email.lower().strip(),),
    )
    row = cursor.fetchone()
    return row[0] if row else None


# ─────────────────────────── Goal Functions ────────────────────────────────
def setGoal(username: str, goal: float):
    cursor.execute(
        "INSERT OR REPLACE INTO goals (username, goal_weight) VALUES(?, ?)",
        (username, goal),
    )
    connection.commit()

def getGoal(username: str):
    cursor.execute(
        "SELECT goal_weight FROM goals WHERE username = ?",
        (username,),
    )
    result = cursor.fetchone()
    return result[0] if result else None


# ─────────────────────────── Profile Functions ─────────────────────────────
def setProfile(username, height, age, sex, email=None):
    cursor.execute(
        "INSERT OR REPLACE INTO profiles (username, height, age, sex, email) VALUES (?, ?, ?, ?, ?)",
        (username, height, age, sex, email.lower().strip() if email else None),
    )
    connection.commit()

def getProfile(username):
    cursor.execute(
        "SELECT height, age, sex, email FROM profiles WHERE username = ?",
        (username,),
    )
    result = cursor.fetchone()
    return result if result else (None, None, None, None)


# ─────────────────────────── Validation Functions ──────────────────────────
def validateUsername(username: str):
    if not username or not username.strip():
        return False, "Username cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if not re.match("^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers and underscores."
    return True, ""


def validatePassword(password: str):
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, ""


def validateEmail(email: str):
    if not email or not email.strip():
        return False, "Email cannot be empty."
    pattern = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email.strip()):
        return False, "Please enter a valid email address."
    return True, ""


def validateWeight(weight: float):
    if weight <= 0:
        return False, "Weight must be a positive number."
    if weight > 1000:
        return False, "Weight must be less than 1000."
    return True, ""


# ─────────────────────────── Data Functions ────────────────────────────────
def addData(username: str, weight: float, dateStr: str):
    cursor.execute(
        "INSERT INTO records (username, weight, date) VALUES (?, ?, ?)",
        (username, weight, dateStr),
    )
    connection.commit()

def getUserData(username: str):
    cursor.execute(
        "SELECT id, weight, date FROM records WHERE username = ? ORDER BY date ASC",
        (username,),
    )
    return cursor.fetchall()

def deleteData(recordId: int, username: str):
    cursor.execute(
        "DELETE FROM records WHERE id = ? AND username = ?",
        (recordId, username),
    )
    connection.commit()

def updateData(recordId: int, newWeight: float, username: str):
    cursor.execute(
        "UPDATE records SET weight = ? WHERE id = ? AND username = ?",
        (newWeight, recordId, username),
    )
    connection.commit()


# ═══════════════════════════ PAGE: PROFILE ═══════════════════════════════
def render_profile(username: str):
    col_title, col_back, col_logout = st.columns([5, 1, 1])

    with col_title:
        st.title("Profile Settings")

    with col_back:
        if st.button("Back"):
            st.session_state["page"] = "Dashboard"
            st.rerun()

    with col_logout:
        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.session_state["page"] = "Login"
            st.rerun()
        st.divider()

    # Load Profile
    height, age, sex, profile_email = getProfile(username)
    account_email = getUserEmail(username)

    storedHeight = int(height) if height else 0
    defaultFeet = storedHeight // 12
    defaultInches = storedHeight % 12

    # ── Personal Information ──────────────────────────────────────────────
    st.subheader("Personal Information")

    col1, col2 = st.columns(2)

    with col1:
        feet = st.number_input(
            "Height (Ft)", min_value=0, max_value=8, step=1, value=defaultFeet,
        )
        inches = st.number_input(
            "Inches", min_value=0, max_value=11, step=1, value=defaultInches,
        )

    with col2:
        ageInput = st.number_input(
            "Age", min_value=0, value=age if age else 0,
        )
        sexInput = st.selectbox(
            "Sex", ["Male", "Female"],
            index=0 if sex != "Female" else 1,
        )

    # Email field (pre-filled from users table)
    emailInput = st.text_input(
        "Email Address",
        value=account_email or "",
        placeholder="you@example.com",
    )

    if st.button("Save Profile"):
        okE, msgE = validateEmail(emailInput)
        if not okE:
            st.error(msgE)
        else:
            totalInches = feet * 12 + inches
            setProfile(username, totalInches, ageInput, sexInput, emailInput)
            updateUserEmail(username, emailInput)
            st.success("Profile Updated!")
            st.rerun()

    st.divider()

    # ── Change Password ───────────────────────────────────────────────────
    st.subheader("Change Password")

    currentPw = st.text_input("Current Password", type="password")
    newPw = st.text_input("New Password", type="password")
    confirmPw = st.text_input("Confirm New Password", type="password")

    if st.button("Update Password"):
        user = loginUser(username, currentPw)
        if not user:
            st.error("Current Password is incorrect")
        elif newPw != confirmPw:
            st.error("Passwords do not match")
        else:
            okP, msgP = validatePassword(newPw)
            if not okP:
                st.error(msgP)
            else:
                cursor.execute(
                    "UPDATE users SET password = ? WHERE username = ?",
                    (hashPassword(newPw), username),
                )
                connection.commit()
                st.success("Password Updated Successfully")


# ═══════════════════════════ PAGE: DASHBOARD ══════════════════════════════
def render_dashboard(username: str):
    col_title, col_profile, col_logout = st.columns([5, 1, 1])

    with col_title:
        st.title("Dashboard")
        st.write(f"Welcome Back, **{username}**!")

    with col_profile:
        if st.button("Profile"):
            st.session_state["page"] = "Profile"
            st.rerun()

    with col_logout:
        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.session_state["page"] = "Login"
            st.rerun()

    rows = getUserData(username)

    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Weight", "Date"])
        df["Date"] = pd.to_datetime(df["Date"])
    else:
        df = pd.DataFrame(columns=["ID", "Weight", "Date"])

    has_data = not df.empty

    # ── Add Weight Entry ──────────────────────────────────────────────────
    with st.expander("Add new Weight Entry", expanded=not has_data):
        weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1, format="%.1f")
        selectedDate = st.date_input("Date", value=date.today())

        if st.button("Add Entry", type="primary"):
            okW, msgW = validateWeight(weight)
            if not okW:
                st.error(msgW)
            else:
                addData(username, weight, selectedDate.strftime("%Y-%m-%d"))
                st.success(f"Added {weight} lbs on {selectedDate.strftime('%Y-%m-%d')}.")
                st.rerun()

    # ── Weight Goal ───────────────────────────────────────────────────────
    st.subheader("Weight Goal")

    currentGoal = getGoal(username)

    goalInput = st.number_input(
        "Set your Goal Weight (lbs)",
        min_value=0.0,
        step=0.1,
        value=currentGoal if currentGoal is not None else 0.0,
    )

    if st.button("Save Goal"):
        ok, msg = validateWeight(goalInput)
        if not ok:
            st.error(msg)
        else:
            setGoal(username, goalInput)
            st.success("Goal Saved!")
            st.rerun()

    # ── Goal Progress Bar ─────────────────────────────────────────────────
    if has_data and currentGoal is not None:
        latestWeight = df.sort_values("Date")["Weight"].iloc[-1]
        startWeight = df.sort_values("Date")["Weight"].iloc[0]

        if startWeight != currentGoal:
            if currentGoal < startWeight:
                progress = (startWeight - latestWeight) / (startWeight - currentGoal)
            else:
                progress = (latestWeight - startWeight) / (currentGoal - startWeight)
            progress = max(0.0, min(1.0, progress))
        else:
            progress = 0.0

        st.write(f"Current Weight: **{latestWeight:.1f} lbs**")
        st.write(f"Goal Weight: **{currentGoal:.1f} lbs**")

        remaining = abs(latestWeight - currentGoal)

        if currentGoal < latestWeight:
            st.caption("Goal: Weight Loss")
            st.write(f"Remaining to Lose: **{remaining:.1f} lbs**")
        else:
            st.caption("Goal: Weight Gain")
            st.write(f"Remaining to Gain: **{remaining:.1f} lbs**")

        st.progress(progress)

        if progress >= 1:
            st.success("Goal Reached!")
        elif progress >= 0.75:
            st.info("Almost There!")
    else:
        st.info("Record weights and set a goal to see progress.")

    # ── Filter Records ────────────────────────────────────────────────────
    st.subheader("Filter Records")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    today = date.today()
    min_date_data = df["Date"].min().date() if has_data else today
    max_date_data = df["Date"].max().date() if has_data else today
    min_w_data = float(df["Weight"].min()) if has_data else 0.0
    max_w_data = float(df["Weight"].max()) if has_data else 300.0

    if "filter_start" not in st.session_state:
        st.session_state["filter_start"] = min_date_data
    if "filter_end" not in st.session_state:
        st.session_state["filter_end"] = max_date_data
    if "filter_min_w" not in st.session_state:
        st.session_state["filter_min_w"] = min_w_data
    if "filter_max_w" not in st.session_state:
        st.session_state["filter_max_w"] = max_w_data

    with col_f1:
        filter_start = st.date_input("From Date", key="filter_start", disabled=not has_data)
    with col_f2:
        filter_end = st.date_input("To Date", key="filter_end", disabled=not has_data)
    with col_f3:
        filter_min_w = st.number_input(
            "Min Weight", step=0.1, format="%.1f", key="filter_min_w", disabled=not has_data,
        )
    with col_f4:
        filter_max_w = st.number_input(
            "Max Weight", step=0.1, format="%.1f", key="filter_max_w", disabled=not has_data,
        )

    if has_data:
        if filter_start > filter_end:
            st.warning("'From Date' is after 'To Date'. Showing all dates.")
            filter_start = min_date_data
            filter_end = max_date_data
        if filter_min_w > filter_max_w:
            st.warning("'Min Weight' is greater than 'Max Weight'. Showing all weights.")
            filter_min_w = min_w_data
            filter_max_w = max_w_data

        df_filtered = df[
            (df["Date"].dt.date >= filter_start)
            & (df["Date"].dt.date <= filter_end)
            & (df["Weight"] >= filter_min_w)
            & (df["Weight"] <= filter_max_w)
        ]
        st.caption(f"Showing **{len(df_filtered)}** of **{len(df)}** records based on filters.")
    else:
        df_filtered = df.copy()

    # ── Weight Trend Chart ────────────────────────────────────────────────
    st.subheader("Weight Trend")
    if has_data and not df_filtered.empty:
        df_grouped = (
            df_filtered.groupby("Date", as_index=False)["Weight"]
            .mean()
            .sort_values("Date")
        )
        fig = px.line(
            df_grouped, x="Date", y="Weight",
            markers=True, title="Weight Over Time (Filtered)",
        )
        fig.update_yaxes(
            range=[
                max(0, df_filtered["Weight"].min() - 10),
                df_filtered["Weight"].max() + 10,
            ]
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_fig = px.line(title="Weight Over Time")
        empty_fig.update_layout(
            annotations=[{
                "text": "No data yet — add your first entry above!",
                "xref": "paper", "yref": "paper",
                "x": 0.5, "y": 0.5, "showarrow": False,
                "font": {"size": 16, "color": "gray"},
            }]
        )
        st.plotly_chart(empty_fig, use_container_width=True)

    # ── Summary Metrics ───────────────────────────────────────────────────
    st.subheader("Summary Metrics")
    c1, c2, c3, c4 = st.columns(4)
    if has_data and not df_filtered.empty:
        c1.metric("Latest Weight", f"{df_filtered.sort_values('Date')['Weight'].iloc[-1]:.1f} lbs")
        c2.metric("Average Weight", f"{df_filtered['Weight'].mean():.1f} lbs")
        c3.metric("Lowest Weight", f"{df_filtered['Weight'].min():.1f} lbs")
        c4.metric("Highest Weight", f"{df_filtered['Weight'].max():.1f} lbs")
    else:
        c1.metric("Latest Weight", "-")
        c2.metric("Average Weight", "-")
        c3.metric("Lowest Weight", "-")
        c4.metric("Highest Weight", "-")

    # ── BMI ───────────────────────────────────────────────────────────────
    st.subheader("BMI")
    height, age, sex, _ = getProfile(username)

    if has_data and height:
        latestWeight = df.sort_values("Date")["Weight"].iloc[-1]
        weightKg = latestWeight * 0.453592
        heightM = height * 0.0254
        bmi = weightKg / (heightM ** 2)

        st.metric("Your BMI", f"{bmi:.1f}")

        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal Weight"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        st.write(f"Category: **{category}**")
    else:
        st.info("Add your profile and weight to see BMI.")

    # ── Edit / Delete Records ─────────────────────────────────────────────
    st.subheader("Edit or Delete a Record")
    if has_data and not df_filtered.empty:
        options = [
            (row["ID"], f"{row['Weight']:.1f} lbs | {row['Date'].strftime('%Y-%m-%d')}")
            for _, row in df_filtered.iterrows()
        ]
        selected = st.selectbox(
            "Select a record to edit or delete", options, format_func=lambda x: x[1]
        )
        selectedID = selected[0]

        col_e1, col_e2 = st.columns([2, 1])

        with col_e1:
            newWeight = st.number_input(
                "New Weight (lbs)", min_value=0.0, step=0.1, format="%.1f", key="edit_w"
            )
            if st.button("Update Entry"):
                okW, msgW = validateWeight(newWeight)
                if not okW:
                    st.error(msgW)
                else:
                    updateData(selectedID, newWeight, username)
                    st.success("Record Updated Successfully")
                    st.rerun()

        with col_e2:
            st.write("")
            st.write("")
            if st.button("Delete Entry", type="secondary"):
                deleteData(selectedID, username)
                st.success("Entry Deleted")
                st.rerun()
    else:
        st.info("No entries to edit or delete yet.")

    # ── Raw Data Table ────────────────────────────────────────────────────
    with st.expander("View Raw Data Table"):
        if has_data and not df_filtered.empty:
            display_df = df_filtered[["Date", "Weight"]].copy()
            display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
            display_df = (
                display_df.sort_values("Date", ascending=False)
                .reset_index(drop=True)
            )
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No Data Yet — Add your first weight entry to see the trend and metrics!")


# ═══════════════════════════ SIDEBAR ══════════════════════════════════════
ALL_PAGES = ["Login", "Sign Up", "Forgot Password", "Forgot Username", "Dashboard", "Profile"]

with st.sidebar:
    st.markdown("Weight Tracker")
    st.divider()

    if "user" in st.session_state:
        st.markdown(f"Logged in as: **{st.session_state['user']}**")
        st.divider()

    menu = st.selectbox(
        "Navigation",
        ALL_PAGES,
        index=ALL_PAGES.index(st.session_state["page"]),
    )
    if menu != st.session_state["page"]:
        st.session_state["page"] = menu
        st.rerun()

    if "user" in st.session_state:
        st.divider()
        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.session_state["page"] = "Login"
            st.rerun()


# ═══════════════════════════ PAGE: LOGIN ══════════════════════════════════
if menu == "Login":
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        okU, msgU = validateUsername(username)
        okP, msgP = validatePassword(password)

        if not okU:
            st.error(msgU)
        elif not okP:
            st.error(msgP)
        else:
            user = loginUser(username, password)
            if user:
                st.session_state["user"] = username
                st.session_state["page"] = "Dashboard"
                st.success("Successfully Logged In")
                st.rerun()
            else:
                st.error("Invalid Username or Password")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Go to Sign Up"):
            st.session_state["page"] = "Sign Up"
            st.rerun()
    with col_b:
        if st.button("Forgot Password?"):
            st.session_state["page"] = "Forgot Password"
            st.rerun()
    with col_c:
        if st.button("Forgot Username?"):
            st.session_state["page"] = "Forgot Username"
            st.rerun()


# ═══════════════════════════ PAGE: SIGN UP ════════════════════════════════
elif menu == "Sign Up":
    st.title("Sign Up")

    newUsername = st.text_input("Create Username")
    newEmail    = st.text_input("Email Address", placeholder="you@example.com")
    newPassword = st.text_input("Create Password", type="password")
    confirmPassword = st.text_input("Confirm Password", type="password")

    st.subheader("Optional Profile Info")
    col1, col2, col3 = st.columns(3)
    with col1:
        feet = st.number_input("Height (ft)", min_value=0, max_value=8, step=1)
    with col2:
        inches = st.number_input("Inches", min_value=0, max_value=11, step=1)
    with col3:
        ageInput = st.number_input("Age", min_value=0)
        sexInput = st.selectbox("Sex", ["Prefer not to say", "Male", "Female"])

    if st.button("Create Account", type="primary"):
        okU, msgU = validateUsername(newUsername)
        okE, msgE = validateEmail(newEmail)
        okP, msgP = validatePassword(newPassword)

        if not okU:
            st.error(msgU)
        elif not okE:
            st.error(msgE)
        elif not okP:
            st.error(msgP)
        elif newPassword != confirmPassword:
            st.error("Passwords do not match!")
        else:
            success = createUser(newUsername, newPassword, newEmail)
            if success:
                totalInches = feet * 12 + inches
                if totalInches > 0 or ageInput > 0 or sexInput != "Prefer not to say":
                    setProfile(
                        newUsername,
                        totalInches if totalInches > 0 else None,
                        ageInput if ageInput > 0 else None,
                        sexInput if sexInput != "Prefer not to say" else None,
                        newEmail,
                    )
                st.success("Account Created Successfully!")
                st.session_state["page"] = "Login"
                st.info("Please log in with your new account.")
                st.rerun()
            else:
                st.error("Username or email already exists.")

    if st.button("Back to Login"):
        st.session_state["page"] = "Login"
        st.rerun()


# ═══════════════════════════ PAGE: FORGOT PASSWORD ════════════════════════
elif menu == "Forgot Password":
    st.title("Forgot Password")
    st.info(
        "Enter your username below. A new temporary password will be generated for you. "
        "Use it to log in, then change it in your Profile settings."
    )

    fp_username = st.text_input("Username")

    if st.button("Reset Password", type="primary"):
        if not fp_username.strip():
            st.error("Please enter your username.")
        else:
            email, new_pw = forgotPassword(fp_username.strip())
            if email is None:
                st.error("Username not found.")
            else:
                # In a production app you would email `new_pw` to `email`.
                # Here we display it directly so the demo is self-contained.
                st.success("A new temporary password has been generated.")
                st.warning(
                    f"Your temporary password is: **`{new_pw}`**\n\n"
                    f"_(In production this would be sent to: {email})_\n\n"
                    "Please log in and update your password immediately."
                )

    if st.button("Back to Login"):
        st.session_state["page"] = "Login"
        st.rerun()


# ═══════════════════════════ PAGE: FORGOT USERNAME ════════════════════════
elif menu == "Forgot Username":
    st.title("Forgot Username")
    st.info("Enter the email address associated with your account to retrieve your username.")

    fu_email = st.text_input("Email Address", placeholder="you@example.com")

    if st.button("Find Username", type="primary"):
        okE, msgE = validateEmail(fu_email)
        if not okE:
            st.error(msgE)
        else:
            found_username = forgotUsername(fu_email)
            if found_username is None:
                st.error("No account found with that email address.")
            else:
                # In production, email this to the user instead of displaying it.
                st.success("Account found!")
                st.info(
                    f"Your username is: **`{found_username}`**\n\n"
                    f"_(In production this would be sent to: {fu_email})_"
                )

    if st.button("Back to Login"):
        st.session_state["page"] = "Login"
        st.rerun()


# ═══════════════════════════ PAGE: DASHBOARD ══════════════════════════════
elif menu == "Dashboard":
    if "user" not in st.session_state:
        st.warning("Please log in to access the Dashboard.")
        st.session_state["page"] = "Login"
        st.rerun()
    render_dashboard(st.session_state["user"])


# ═══════════════════════════ PAGE: PROFILE ════════════════════════════════
elif menu == "Profile":
    if "user" not in st.session_state:
        st.warning("Please log in to access your Profile.")
        st.session_state["page"] = "Login"
        st.rerun()
    render_profile(st.session_state["user"])
