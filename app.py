import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# --- EMAIL CREDENTIALS ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥")

# --- GOOGLE SHEETS CONNECTION ---
# Uses the secrets you saved in the Streamlit Dashboard
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 ensures we always get the newest data from the sheet
        return conn.read(ttl=0)
    except:
        return pd.DataFrame()

# Fetch data silently at start
df = get_data()

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
    except: 
        return False

st.title("🏥 CUET Student Medical Portal")

tab1, tab2, tab3 = st.tabs(["🚨 Emergency Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: SEARCH ---
with tab1:
    sid_search = st.text_input("Search ID (Ex: 2311029)")
    if sid_search:
        if not df.empty:
            res = df[df['sid'].astype(str) == str(sid_search)]
            if not res.empty:
                row = res.iloc[0]
                st.warning(f"**Patient:** {str(row['name']).upper()} | **Blood:** {row['bg']}")
                st.info(f"**Allergies:** {row['allergies']}\n\n**History:** {row['history']}")
                st.write(f"**Contact:** {row['phone']} | **Last Donation:** {row['last_donation']}")
            else: 
                st.error("No record found.")
        else:
            st.info("Database is currently empty.")

# --- TAB 2: DONORS ---
with tab2:
    target_bg = st.selectbox("Select Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_contact = st.text_input("Enter your phone number for donors to call:")
    
    if not df.empty:
        # Match donors by blood group
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                eligible = True
                d_date = str(row['last_donation'])
                # Basic 120-day eligibility check
                if d_date != "Never":
                    try:
                        if datetime.now() - datetime.strptime(d_date, "%Y-%m-%d") < timedelta(days=120):
                            eligible = False
                    except: 
                        pass
                
                c1, c2 = st.columns([3, 1])
                status = "✅ Available" if eligible else "⏳ Recently Donated"
                c1.write(f"**{row['name']}** ({status})")
                if eligible and c2.button(f"Email {row['sid']}", key=f"btn_{row['sid']}"):
                    if receiver_contact:
                        with st.spinner("Sending email..."):
                            if send_donor_email(f"u{row['sid']}@student.cuet.ac.bd", row['name'], target_bg, receiver_contact):
                                st.success("Mail Sent!")
                    else: 
                        st.error("Enter phone number first!")
        else:
            st.write("No donors found for this blood group.")

# --- TAB 3: REGISTER ---
with tab3:
    with st.form("reg_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID")
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", value="None")
        f_his = st.text_area("Medical History", value="None")
        has_donated = st.radio("Donated blood before?", ["No, never", "Yes"])
        f_last_picker = st.date_input("Last donation date")
        
        if st.form_submit_button("Submit"):
            if f_sid and f_name and f_phone:
                final_date = str(f_last_picker) if has_donated == "Yes" else "Never"
                
                # New entry must match lowercase headers in Sheet
                new_row = pd.DataFrame([{
                    "sid": str(f_sid), 
                    "name": f_name, 
                    "bg": f_bg, 
                    "phone": str(f_phone), 
                    "allergies": f_all, 
                    "history": f_his, 
                    "last_donation": final_date
                }])
                
                # Update existing or append new
                if not df.empty:
                    updated_df = pd.concat([df[df['sid'].astype(str) != str(f_sid)], new_row], ignore_index=True)
                else:
                    updated_df = new_row
                
                try:
                    conn.update(data=updated_df)
                    st.toast("✅ Success! Record updated.") 
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
            else:
                st.error("Please fill in ID, Name, and Phone Number.")
