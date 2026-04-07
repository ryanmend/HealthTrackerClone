import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
import hashlib
import re
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











# Database Connection
dbPath = os.path.join(os.getcwd(), "project.db")

@st.cache_resource
def get_connection():
    connection = sqlite3.connect(dbPath, check_same_thread=False)
    cursor = connection.cursor()

    ## User table
    cursor.execute(
        """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
"""
    )


    #Profile
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles(
        username TEXT PRIMARY KEY,
        height REAL,
        age INTEGER,
        sex TEXT
        )
        """)

    #Goal Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        username TEXT PRIMARY KEY,
        goal_weight REAL
    )                              
    """)




    # Create Records Table
    cursor.execute(
        """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    weight REAL,
    date DATE
)
"""
    )

    connection.commit()
    return connection, cursor

connection, cursor = get_connection()


##Hashing Function
def hashPassword(password: str) -> str:
    """Returns the SHA-256 hash of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()














## Authentication Functions
def createUser(username: str, password: str):
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashPassword(password)),
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

def setProfile(username, height, age, sex):
    cursor.execute(
        "INSERT OR REPLACE INTO profiles (username, height, age, sex) VALUES (?, ?, ?, ?)",
        (username, height, age, sex),
    )
    connection.commit()

def getProfile(username):
    cursor.execute(
        "SELECT height, age, sex FROM profiles WHERE username = ?",
        (username,),
    )

    result = cursor.fetchone()
    return result if result else (None, None, None)













# System Validation Functions

# Username Validation
def validateUsername(username: str):
    """Return (True, '') or (False, errorMessage)."""
    if not username or not username.strip():
        return False, "Username cannot be empty."
    if len(username) < 3:
        return False, "Username must be atleast 3 characters long."
    if not re.match("^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers and underscores."
    return True, ""


# Password Validation
def validatePassword(password: str):
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 6:
        return False, "Password must be atleast 6 characters long."
    return True, ""


# Weight Validation
def validateWeight(weight: float):
    if weight <= 0:
        return False, "Weight must be a positive number."
    if weight > 1000:
        return False, "Weight must be less than 1000."
    return True, ""


# Data Functions
def addData(username: str, weight: float, dateStr: str):
    cursor.execute(
        "INSERT INTO records (username, weight, date) VALUES (?, ?, ?)",
        (username, weight, dateStr),
    )
    connection.commit()

#Fetch UserData
def getUserData(username: str):
    cursor.execute(
        "SELECT id, weight, date FROM records WHERE username = ? ORDER BY date ASC",
        (username,),
    )
    return cursor.fetchall()

#Delete User Data
def deleteData(recordId: int, username: str):
    cursor.execute(
        "DELETE FROM records WHERE id = ? AND username = ?",
        (recordId, username),
    )
    connection.commit()

#Update User Data
def updateData(recordId: int, newWeight: float, username: str):
    cursor.execute(
        "UPDATE records SET weight = ? WHERE id = ? AND username = ?",
        (newWeight, recordId, username),
    )
    connection.commit()
















#Render Profile
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

    #Load Profile
    height, age, sex = getProfile(username)

    storedHeight = int(height) if height else 0
    defaultFeet = storedHeight // 12
    defaultInches = storedHeight % 12

    st.subheader("Personal Information")

    col1, col2 = st.columns(2)

    with col1:
        feet = st.number_input(
            "Height (Ft)",
            min_value = 0,
            max_value = 8,
            step = 1,
            value = defaultFeet,
    )
        inches = st.number_input(
            "Inches",
            min_value =0,
            max_value =11,
            step =1,
            value = defaultInches,
    )
        
    with col2:
        ageInput = st.number_input(
            "Age",
            min_value = 0,
            value= age if age else 0,
        )

        sexInput = st.selectbox(
            "Sex",
            ["Male", "Female"],
            index=0 if sex != "Female" else 1,
        )

    if st.button ("Save Profile"):
        totalInches = feet * 12 + inches
        setProfile(username, totalInches, ageInput, sexInput)
        st.success("Profile Updated!")
        st.rerun()
    
    st.divider()

    #Password Change
    st.subheader("Change Password")

    currentPw = st.text_input("Current Password", type= "password")
    newPw = st.text_input("New Password", type="password")
    confirmPw = st.text_input("Confirm New Password", type = "password")

    if st.button("Update Password"):
        user = loginUser(username, currentPw)

        if not user:
            st.error("Current Password is incorrect")
        elif newPw != confirmPw:
            st.error("Passwords do not match")
        else:
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hashPassword(newPw), username),
            )
            connection.commit()
            st.success("Password Updated Successfully")



    st.info("Profile settings are managed in the Dashboard under 'Health Profile' section.")




#Render Dashboard
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











    # Add Weight Entry
    with st.expander("Add new Weight Entry", expanded=not has_data):
        weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1, format="%.1f")
        selectedDate = st.date_input("Date", value=date.today())

        if st.button("Add Entry", type="primary"):
            okW, msgW = validateWeight(weight)
            if not okW:
                st.error(msgW)
            else:
                addData(
                    username,
                    weight,
                    selectedDate.strftime("%Y-%m-%d"),
                )
                st.success(f"Added {weight} lbs on {selectedDate.strftime('%Y-%m-%d')}.")
                st.rerun()


   






#Goal
    st.subheader("Weight Goal")

    currentGoal = getGoal(username)

    goalInput = st.number_input(
        "Set your Goal Weight(lbs)",
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









#Goal Progress Bar
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

        st.write(f"Current Weight: **{latestWeight: .1f} lbs**")
        st.write(f"Goal Weight: **{currentGoal: .1f} lbs**")

        remaining = abs(latestWeight - currentGoal)

        if currentGoal < latestWeight:
            st.caption("Goal: Weight Loss")
            st.write(f"Remaining to Loose: **{remaining: .1f} lbs**")
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


#Filter Records

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
        filter_start = st.date_input(
            "From Date", key="filter_start", disabled=not has_data
        )

    with col_f2:
        filter_end = st.date_input(
            "To Date", key="filter_end", disabled=not has_data
        )

    with col_f3:
        filter_min_w = st.number_input(
            "Min Weight",
            step=0.1,
            format="%.1f",
            key="filter_min_w",
            disabled=not has_data,
        )

    with col_f4:
        filter_max_w = st.number_input(
            "Max Weight",
            step=0.1,
            format="%.1f",
            key="filter_max_w",
            disabled=not has_data,
        )


    if has_data:
        if filter_start > filter_end:
            st.warning("'From Date' is after 'To Date'. Showing all Dates.")
            filter_start = min_date_data
            filter_end = max_date_data

        if filter_min_w > filter_max_w:
            st.warning("'Min Weight' is greater than 'Max Weight'. Showing all Weights.")
            filter_min_w = min_w_data
            filter_max_w = max_w_data

        df_filtered = df[
            (df["Date"].dt.date >= filter_start)
            & (df["Date"].dt.date <= filter_end)
            & (df["Weight"] >= filter_min_w)
            & (df["Weight"] <= filter_max_w)
        ]
        st.caption(
            f"Showing **{len(df_filtered)}** of **{len(df)}** records based on filters."
        )
    else:
        df_filtered = df.copy()  # empty DataFrame






    # Weight Trend Chart
    st.subheader("Weight Trend")
    if has_data and not df_filtered.empty:
        df_grouped = (
            df_filtered.groupby("Date", as_index=False)["Weight"]
            .mean()
            .sort_values("Date")
        )
        fig = px.line(
            df_grouped,
            x="Date",
            y="Weight",
            markers=True,
            title="Weight Over Time (Filtered)",
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
            annotations=[
                {
                    "text": "No data yet — add your first entry above!",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 16, "color": "gray"},
                }
            ]
        )
        st.plotly_chart(empty_fig, use_container_width=True)










    # Metrics Summary
    st.subheader("Summary Metrics")
    c1, c2, c3, c4 = st.columns(4)
    if has_data and not df_filtered.empty:
        c1.metric(
            "Latest Weight",
            f"{df_filtered.sort_values('Date')['Weight'].iloc[-1]:.1f} lbs",
        )
        c2.metric("Average Weight", f"{df_filtered['Weight'].mean():.1f} lbs")
        c3.metric("Lowest Weight", f"{df_filtered['Weight'].min():.1f} lbs")
        c4.metric("Highest Weight", f"{df_filtered['Weight'].max():.1f} lbs")
    else:
        c1.metric("Latest Weight", "-")
        c2.metric("Average Weight", "-")
        c3.metric("Lowest Weight", "-")
        c4.metric("Highest Weight", "-")








    st.subheader("BMI")

    height, age, sex = getProfile(username)

    if has_data and height:
        latestWeight = df.sort_values("Date") ["Weight"].iloc[-1]

        weightKg = latestWeight * 0.453592
        heightM = height * 0.0254

        bmi = weightKg / (heightM ** 2)

        st.metric("Your BMI", f"{bmi: .1f}")

        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal Weight"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        st.write(f"Category: **{category} **")
    else:
        st.info("Add your profile and weight to see BMI")

    



    


    # Edit and Delete Records
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
                "New Weight(lbs)", min_value=0.0, step=0.1, format="%.1f", key="edit_w"
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

    # Raw Data Table
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
            st.info("No Data Yet - Add your first weight entry to see the trend and metrics!")









# Sidebar Navigation
with st.sidebar:
    st.markdown("Weight Tracker")
    st.divider()

    if "user" in st.session_state:
        st.markdown(f"Logged in as: **{st.session_state['user']}**")
        st.divider()

    menu = st.selectbox(
        "Navigation",
        ["Login", "Sign Up", "Dashboard", "Profile"],
        index=["Login", "Sign Up", "Dashboard", "Profile"].index(st.session_state["page"]),
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










# Login Page
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

    if st.button("Go to Sign Up"):
        st.session_state["page"] = "Sign Up"
        st.rerun()












# Signup Page
elif menu == "Sign Up":
    st.title("Signup")
    newUsername = st.text_input("Create Username")
    newPassword = st.text_input("Create Password", type="password")
    confirmPassword = st.text_input("Confirm Password", type="password")

    st.subheader("Optional Profile Info")
    col1, col2, col3 = st.columns(3)
    with col1: 
        feet = st.number_input("Height(ft)", min_value = 0, max_value = 8, step = 1)

    with col2:
        inches = st.number_input("Inches", min_value = 0, max_value = 11, step = 1)

    with col3:
        ageInput = st.number_input("Age", min_value = 0)
        
        sexInput = st.selectbox("Sex", ["Prefer not to say", "Male", "Female"])


    if st.button("Create Account", type="primary"):
        okU, msgU = validateUsername(newUsername)
        okP, msgP = validatePassword(newPassword)

        if not okU:
            st.error(msgU)
        elif not okP:
            st.error(msgP)
        elif newPassword != confirmPassword:
            st.error("Passwords do not match!")
        else:
            success = createUser(newUsername, newPassword)
            if success:
                totalInches = feet * 12 + inches
                if (
                    totalInches > 0
                    or ageInput > 0
                    or sexInput != "Prefer not to say"
                ):
                    setProfile(
                        newUsername,
                        totalInches if totalInches > 0 else None,
                        ageInput if ageInput > 0 else None,
                        sexInput if sexInput != "Prefer not to say" else None,
                    )
                st.success("Account Created Successfully")
                st.session_state["page"] = "Login"
                st.info("Please Login with your new account")
                st.rerun()
            else:
                st.error("Username already exists!")
    
    
    

    if st.button("Back to Login"):
        st.session_state["page"] = "Login"
        st.rerun()









# Dashboard Page
elif menu == "Dashboard":
    if "user" not in st.session_state:
        st.warning("Please Login to access the Dashboard")
        st.session_state["page"] = "Login"
        st.rerun()

    render_dashboard(st.session_state["user"])

elif menu == "Profile":
    if "user" not in st.session_state:
        st.warning("Please Login to Access Profile")
        st.session_state["page"] = "Login"
        st.rerun()

    render_profile(st.session_state["user"])

