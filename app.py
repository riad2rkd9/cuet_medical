import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# --- EMAIL CONFIGURATION ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥", layout="wide")

# --- DATABASE CONNECTION ---
# Uses the Service Account credentials from your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 ensures we get the most recent updates from the sheet
        return conn.read(ttl=0)
    except Exception:
        # Fallback template matching your sheet headers
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    content = (f"Dear {donor_name},\n\n"
               f"This is an EMERGENCY blood request from CUET Medical Center.\n\n"
               f"A patient urgently needs {blood_group} blood.\n"
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

# Load fresh data
df = get_data()

st.title("🏥 CUET Student Medical Portal")
tab1, tab2, tab3 = st.tabs(["🚨 Emergency Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: EMERGENCY SEARCH ---
# --- TAB 1: EMERGENCY SEARCH ---
with tab1:
    sid_search = st.text_input("Search ID (Ex: 2311029)")
    if sid_search:
        if not df.empty:
            # FIX: Force the sheet column (sid) and the input to both be cleaned Strings
            res = df[df['sid'].astype(str).str.strip() == str(sid_search).strip()]
            
            if not res.empty:
                row = res.iloc[0]
                st.warning(f"**Patient:** {str(row['name']).upper()} | **Blood:** {row['bg']}")
                st.info(f"**Allergies:** {row['allergies']}\n\n**History:** {row['history']}")
                st.write(f"**Contact:** {row['phone']} | **Last Donation:** {row['last donation']}")
            else: 
                st.error("No record found. Check ID or Register in the 📝 tab.")
# --- TAB 2: FIND DONORS ---
with tab2:
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_contact = st.text_input("Your Phone Number (for donors to call):")
    
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                # Logic to check eligibility (4 months interval)
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
                if eligible and c2.button(f"Email {row['sid']}", key=f"btn_{row['sid']}"):
                    if receiver_contact:
                        with st.spinner("Notifying donor..."):
                            if send_donor_email(f"u{row['sid']}@student.cuet.ac.bd", row['name'], target_bg, receiver_contact):
                                st.success("Notification sent to student email!")
                    else: st.error("Enter your contact number first!")

# --- TAB 3: REGISTER/UPDATE ---
with tab3:
    st.subheader("Update your Medical Profile")
    st.markdown("> Enter your Student ID to register. If already registered, your old info will be updated.")
    
    with st.form("reg_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID (Required)")
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", value="None")
        f_his = st.text_area("Medical History", value="None")
        has_donated = st.radio("Donated blood before?", ["No, never", "Yes"])
        f_last_picker = st.date_input("Last donation date")
        
        if st.form_submit_button("Submit to Database"):
            if f_sid and f_name:
                clean_id = str(f_sid).strip()
                new_entry = pd.DataFrame([{
                    "sid": clean_id, 
                    "name": f_name, 
                    "bg": f_bg, 
                    "phone": str(f_phone), 
                    "allergies": f_all, 
                    "history": f_his, 
                    "last donation": str(f_last_picker) if has_donated == "Yes" else "Never"
                }])
                
                try:
                    # Fetch latest sheet data
                    current_df = conn.read(ttl=0)
                    
                    if current_df is not None and not current_df.empty:
                        # Profile Update Logic: Remove old record for this ID if it exists
                        filtered_df = current_df[current_df['sid'].astype(str).str.strip() != clean_id]
                        updated_df = pd.concat([filtered_df, new_entry], ignore_index=True)
                    else:
                        updated_df = new_entry
                    
                    # Push back to Google Sheets
                    conn.update(data=updated_df)
                    st.success(f"Profile for {clean_id} synced to database!")
                    st.rerun()
                except Exception as e:
                    # Triggered if 'token_uri' or 'spreadsheet' URL is missing in Secrets
                    st.error(f"Database Error: {e}")
            else:
                st.error("Please fill in Student ID and Name.")
