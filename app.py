import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage

# --- EMAIL SETTINGS ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥", layout="wide")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 is mandatory to see new registrations immediately
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
        # Using Port 587 (TLS) for better reliability on Streamlit Cloud
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Mail failed: {e}")
        return False

st.title("🏥 CUET Student Medical Portal")
tab1, tab2, tab3 = st.tabs(["🚨 Emergency Medical Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: PATIENT SEARCH (FIXED) ---
with tab1:
    st.subheader("Search Student Records")
    sid_query = st.text_input("Enter Student ID", key="search_input")
    
    if sid_query:
        if not df.empty:
            # FIX: Force everything to string and remove decimals (.0) often added by Excel/Pandas
            df_search = df.copy()
            df_search['sid'] = df_search['sid'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            result = df_search[df_search['sid'] == str(sid_query).strip()]
            
            if not result.empty:
                row = result.iloc[0]
                st.success(f"### Profile Found: {row['name']}")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Blood Group", row['bg'])
                    st.write(f"**Phone:** {row['phone']}")
                with c2:
                    st.error(f"**Allergies:** {row['allergies']}")
                    st.error(f"**Medical History:** {row['history']}")
                st.info(f"**Last Donation:** {row['last donation']}")
            else:
                st.error(f"No record found for ID: {sid_query}")

# --- TAB 2: DONORS ---
with tab2:
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_phone = st.text_input("Your Phone Number:")
    
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                st.write(f"**{row['name']}** (Last Donation: {row['last donation']})")
                if st.button(f"E-mail {row['sid']}", key=f"mail_{row['sid']}"):
                    if receiver_phone:
                        target_mail = f"u{str(row['sid']).split('.')[0]}@student.cuet.ac.bd"
                        if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                            st.success("Notification Email Sent!")
                    else: st.error("Please enter your contact number first.")

# --- TAB 3: REGISTER/UPDATE (FIXED DONATION OPTION) ---
with tab3:
    st.subheader("Update Your Profile")
    with st.form("reg_form"):
        f_sid = st.text_input("Student ID")
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", "None")
        f_his = st.text_area("Medical History", "None")
        
        # ONE OPTION: None or Date
        donation_status = st.radio("Last Donation Info:", ["Never Donated", "Select Date"])
        f_date = "Never"
        if donation_status == "Select Date":
            f_date = str(st.date_input("When was your last donation?"))

        if st.form_submit_button("Submit Data"):
            if f_sid and f_name:
                clean_sid = str(f_sid).strip()
                new_data = pd.DataFrame([{
                    "sid": clean_sid, "name": f_name, "bg": f_bg, "phone": f_phone,
                    "allergies": f_all, "history": f_his, "last donation": f_date
                }])
                
                try:
                    # Update Logic: Filter out old record and add new
                    updated_df = pd.concat([df[df['sid'].astype(str).str.replace(r'\.0$', '', regex=True) != clean_sid], new_data], ignore_index=True)
                    conn.update(data=updated_df)
                    st.success("Database Updated Successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")
