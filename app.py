import streamlit as st
import sqlite3
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# --- UPDATED EMAIL CREDENTIALS ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 

# --- DATABASE SETUP ---
DB_FILE = 'cuet_medical.db'

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_connection() as conn:
        # If you ever change columns, it's safer to DROP and CREATE for a student project
        # Or just ensure the table exists with the exact 7 columns we need
        conn.execute('DROP TABLE IF EXISTS students') # Force refresh to fix your error
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
               f"If you are able to donate, please contact the receiver immediately at: {receiver_phone}\n\n"
               f"Your help could save a life.\n\n- CUET Medical Team")
    
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

# --- TAB 1: EMERGENCY LOOKUP ---
with tab1:
    st.subheader("Patient ID Lookup")
    sid_search = st.text_input("Enter Student ID (Ex: 2311029)")
    if sid_search:
        with get_connection() as conn:
            res = conn.execute("SELECT * FROM students WHERE sid = ?", (sid_search,)).fetchone()
        if res:
            st.warning(f"**Patient:** {res[1].upper()} | **Blood:** {res[2]}")
            st.info(f"**Allergies:** {res[4]}\n\n**History:** {res[5]}")
            st.write(f"**Contact:** {res[3]}")
            st.write(f"**Last Donation:** {res[6]}")
        else:
            st.error("No record found.")

# --- TAB 2: DONOR LIST ---
with tab2:
    st.subheader("Blood Match Finder")
    target_bg = st.selectbox("Select Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_contact = st.text_input("Enter your phone number (to include in email):")
    
    st.divider()
    
    with get_connection() as conn:
        donors = conn.execute("SELECT sid, name, last_donation FROM students WHERE bg = ?", (target_bg,)).fetchall()
    
    if donors:
        for d_id, d_name, d_date in donors:
            is_eligible = True
            if d_date != "Never" and d_date is not None:
                try:
                    last_dt = datetime.strptime(d_date, "%Y-%m-%d")
                    if datetime.now() - last_dt < timedelta(days=120):
                        is_eligible = False
                except: pass
            
            col1, col2 = st.columns([3, 1])
            status_text = "✅ Available" if is_eligible else "⏳ Recently Donated"
            col1.write(f"**{d_name}** ({status_text})")
            
            if is_eligible:
                if col2.button(f"Email {d_id}", key=f"btn_{d_id}"):
                    if not receiver_contact:
                        st.error("Please enter your contact number first!")
                    else:
                        with st.spinner("Sending email..."):
                            if send_donor_email(f"u{d_id}@student.cuet.ac.bd", d_name, target_bg, receiver_contact):
                                st.success(f"Email sent to {d_name}!")
    else:
        st.info("No donors registered for this blood group.")

# --- TAB 3: REGISTRATION & UPDATES ---
with tab3:
    st.subheader("Student Data Entry")
    with st.form("reg_form", clear_on_submit=True):
        st.write("Example IDs: 2311029, 1911029")
        f_sid = st.text_input("Student ID (At least 7 digits)")
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Your Phone Number")
        f_all = st.text_area("Allergies", value="None")
        f_his = st.text_area("Medical History", value="None")
        
        has_donated = st.radio("Have you ever donated blood?", ["No, never", "Yes"])
        f_last_picker = st.date_input("If yes, select last donation date:")
        
        if st.form_submit_button("Submit / Update Record"):
            if len(f_sid) < 7:
                st.error("❌ ID must be at least 7 digits.")
            elif not f_name or not f_phone:
                st.error("❌ Please fill in the name and phone.")
            else:
                final_date = str(f_last_picker) if has_donated == "Yes" else "Never"
                with get_connection() as conn:
                    # This now matches the 7 columns in init_db
                    conn.execute("INSERT OR REPLACE INTO students VALUES (?,?,?,?,?,?,?)", 
                                (f_sid, f_name, f_bg, f_phone, f_all, f_his, final_date))
                st.success(f"Record for {f_name} saved!")
