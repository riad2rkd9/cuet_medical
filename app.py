import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# --- EMAIL SETTINGS ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥", layout="wide")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 is vital so search doesn't show "No record found" for new users
        return conn.read(ttl=0)
    except Exception:
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

df = get_data()

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    msg.set_content(f"URGENT: {donor_name}, a patient needs {blood_group} blood. Contact: {receiver_phone}")
    msg['Subject'] = f"🚨 CUET Blood Request: {blood_group}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        # Changed to SMTP (Port 587) with STARTTLS for better compatibility
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls() 
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Mail Error: {e}")
        return False

st.title("🏥 CUET Student Medical Portal")
tab1, tab2, tab3 = st.tabs(["🚨 Patient Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: PATIENT SEARCH (FIXED) ---
with tab1:
    st.subheader("Search Patient Records")
    sid_search = st.text_input("Enter Student ID to Search", key="search_box")
    if sid_search:
        if not df.empty:
            # FIX: Forces everything to String so 2311020 matches "2311020"
            df['sid_str'] = df['sid'].astype(str).str.strip()
            res = df[df['sid_str'] == str(sid_search).strip()]
            
            if not res.empty:
                row = res.iloc[0]
                st.success(f"Record Found: {row['name']}")
                st.info(f"**Blood:** {row['bg']} | **Phone:** {row['phone']}")
                st.warning(f"**History:** {row['history']} | **Allergies:** {row['allergies']}")
            else:
                st.error("No record found. Check ID or Register in the 📝 tab.")

# --- TAB 2: FIND DONORS ---
with tab2:
    # (Donor display logic remains same, it was already working for you)
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_contact = st.text_input("Your Phone:")
    donors = df[df['bg'] == target_bg] if not df.empty else pd.DataFrame()
    
    for _, row in donors.iterrows():
        st.write(f"**{row['name']}**")
        if st.button(f"Notify {row['sid']}", key=f"mail_{row['sid']}"):
            if receiver_contact:
                # Assuming student email follows uSID@student.cuet.ac.bd
                target_mail = f"u{str(row['sid']).strip()}@student.cuet.ac.bd"
                if send_donor_email(target_mail, row['name'], target_bg, receiver_contact):
                    st.success("Mail Sent!")
            else: st.error("Enter your phone number first!")

# --- TAB 3: REGISTER/UPDATE ---
with tab3:
    with st.form("reg_form"):
        f_sid = st.text_input("Student ID")
        f_name = st.text_input("Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone")
        f_all = st.text_area("Allergies", "None")
        f_his = st.text_area("History", "None")
        has_donated = st.radio("Donated before?", ["No", "Yes"])
        
        # This only renders the date input if they say "Yes"
        f_date = "Never"
        if has_donated == "Yes":
            f_date = str(st.date_input("Last Donation Date"))

        if st.form_submit_button("Submit"):
            if f_sid and f_name:
                new_row = pd.DataFrame([{"sid": f_sid, "name": f_name, "bg": f_bg, "phone": f_phone, 
                                         "allergies": f_all, "history": f_his, "last donation": f_date}])
                # Filter old ID, concat new, and update
                updated_df = pd.concat([df[df['sid'].astype(str) != str(f_sid)], new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Done!")
                st.rerun()
