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
        # ttl=0 ensures we don't see "No record found" due to caching
        return conn.read(ttl=0)
    except Exception:
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

df = get_data()

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    content = (f"Dear {donor_name},\n\nEmergency blood request from CUET Medical.\n"
               f"Patient needs {blood_group}. Contact receiver: {receiver_phone}")
    msg.set_content(content)
    msg['Subject'] = f"🚨 URGENT: {blood_group} Needed"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except: return False

st.title("🏥 CUET Student Medical Portal")
tab1, tab2, tab3 = st.tabs(["🚨 Emergency Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: FIXED EMERGENCY SEARCH ---
with tab1:
    st.subheader("Search Patient Records")
    sid_search = st.text_input("Enter Student ID to Search", placeholder="e.g. 2311020")
    if sid_search:
        if not df.empty:
            # FIX: Force string comparison to solve "No record found"
            res = df[df['sid'].astype(str).str.strip() == str(sid_search).strip()]
            if not res.empty:
                row = res.iloc[0]
                st.success(f"Record Found for {row['name']}")
                col1, col2 = st.columns(2)
                with col1:
                    st.warning(f"**Blood Group:** {row['bg']}")
                    st.info(f"**Phone:** {row['phone']}")
                with col2:
                    st.error(f"**Allergies:** {row['allergies']}")
                    st.error(f"**Medical History:** {row['history']}")
                st.write(f"**Last Donation:** {row['last donation']}")
            else: 
                st.error("No record found. Please verify the ID.")

# --- TAB 2: FIND DONORS ---
with tab2:
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_contact = st.text_input("Your Phone Number:")
    
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                eligible = True
                d_date = str(row['last donation'])
                if d_date != "Never":
                    try:
                        if datetime.now() - datetime.strptime(d_date, "%Y-%m-%d") < timedelta(days=120):
                            eligible = False
                    except: pass
                
                c1, c2 = st.columns([3, 1])
                status = "✅ Available" if eligible else "⏳ Recently Donated"
                c1.write(f"**{row['name']}** ({status})")
                if eligible and c2.button(f"Notify {row['sid']}", key=f"btn_{row['sid']}"):
                    if receiver_contact:
                        if send_donor_email(f"u{row['sid']}@student.cuet.ac.bd", row['name'], target_bg, receiver_contact):
                            st.success("Mail Sent!")
                    else: st.error("Phone required!")

# --- TAB 3: REGISTER/UPDATE (FIXED VISIBILITY) ---
with tab3:
    st.subheader("Student Registration & Profile Update")
    st.info("Entering an existing ID will update your current information.")
    
    with st.form("main_reg_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID (e.g. 2311020)")
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", value="None")
        f_his = st.text_area("Medical History", value="None")
        
        # FIX: Date visibility logic
        has_donated = st.radio("Have you donated blood before?", ["No", "Yes"])
        
        # Only show date picker if "Yes" is selected
        f_last_donation = "Never"
        if has_donated == "Yes":
            f_last_donation = str(st.date_input("Select Last Donation Date"))
        
        if st.form_submit_button("Save to Database"):
            if f_sid and f_name and f_phone:
                clean_sid = str(f_sid).strip()
                new_row = pd.DataFrame([{
                    "sid": clean_sid, "name": f_name, "bg": f_bg, 
                    "phone": str(f_phone), "allergies": f_all, 
                    "history": f_his, "last donation": f_last_donation
                }])
                
                try:
                    # Update/Insert logic to keep ID unique
                    current_df = conn.read(ttl=0)
                    if current_df is not None and not current_df.empty:
                        updated_df = pd.concat([
                            current_df[current_df['sid'].astype(str).str.strip() != clean_sid], 
                            new_row
                        ], ignore_index=True)
                    else:
                        updated_df = new_row
                    
                    conn.update(data=updated_df)
                    st.success("Registration Successful!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Critical Error: {e}")
            else:
                st.error("Please fill required fields (ID, Name, Phone).")
