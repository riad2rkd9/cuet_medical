import streamlit as st
import sqlite3
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# --- CREDENTIALS ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 
DB_FILE = 'cuet_medical.db'

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_connection() as conn:
        # Tables stay forever unless you manually delete the .db file
        conn.execute('''CREATE TABLE IF NOT EXISTS students (
                        sid TEXT PRIMARY KEY, 
                        name TEXT, 
                        bg TEXT, 
                        phone TEXT, 
                        allergies TEXT, 
                        history TEXT, 
                        last_donation TEXT)''')

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    content = (f"Dear {donor_name},\n\n"
               f"This is an EMERGENCY blood request from CUET Medical Center.\n\n"
               f"A patient urgently needs {blood_group} blood. "
               f"Please contact the receiver at: {receiver_phone}\n\n- CUET Medical Team")
    msg.set_content(content)
    msg['Subject'] = f"🚨 URGENT: {blood_group} Blood Needed"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except: return False

st.set_page_config(page_title="CUET Medical", page_icon="🏥")
init_db()

st.title("🏥 CUET Student Medical Portal")

tab1, tab2, tab3 = st.tabs(["🚨 Emergency Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: SEARCH ---
with tab1:
    sid_search = st.text_input("Search ID (Ex: 2311029)")
    if sid_search:
        with get_connection() as conn:
            res = conn.execute("SELECT * FROM students WHERE sid = ?", (sid_search,)).fetchone()
        if res:
            st.warning(f"**Patient:** {res[1].upper()} | **Blood:** {res[2]}")
            st.info(f"**Allergies:** {res[4]}\n\n**History:** {res[5]}")
            st.write(f"**Contact:** {res[3]} | **Last Donation:** {res[6]}")
        else: st.error("No record found.")

# --- TAB 2: DONORS ---
with tab2:
    target_bg = st.selectbox("Select Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_contact = st.text_input("Enter your phone number:")
    with get_connection() as conn:
        donors = conn.execute("SELECT sid, name, last_donation FROM students WHERE bg = ?", (target_bg,)).fetchall()
    
    for d_id, d_name, d_date in donors:
        eligible = True
        if d_date != "Never":
            try:
                if datetime.now() - datetime.strptime(d_date, "%Y-%m-%d") < timedelta(days=120):
                    eligible = False
            except: pass
        
        c1, c2 = st.columns([3, 1])
        c1.write(f"**{d_name}** ({'✅ Available' if eligible else '⏳ Recently Donated'})")
        if eligible and c2.button(f"Email {d_id}"):
            if receiver_contact:
                if send_donor_email(f"u{d_id}@student.cuet.ac.bd", d_name, target_bg, receiver_contact):
                    st.success("Mail Sent!")
            else: st.error("Enter your phone number first!")

# --- TAB 3: REGISTER ---
with tab3:
    with st.form("reg_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID (min 7 digits)")
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group ", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", value="None")
        f_his = st.text_area("Medical History", value="None")
        has_donated = st.radio("Donated before?", ["No, never", "Yes"])
        f_last_picker = st.date_input("Last donation date")
        
        if st.form_submit_button("Submit"):
            if len(f_sid) >= 7 and f_name and f_phone:
                final_date = str(f_last_picker) if has_donated == "Yes" else "Never"
                with get_connection() as conn:
                    conn.execute("INSERT OR REPLACE INTO students VALUES (?,?,?,?,?,?,?)", 
                                (f_sid, f_name, f_bg, f_phone, f_all, f_his, final_date))
                st.success("Record Saved!")
            else: st.error("Please fill all fields (ID must be 7+ digits).")
