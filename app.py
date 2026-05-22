import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage

# --- EMAIL SETTINGS ---
# Note: If you still see 'BadCredentials', you must generate a NEW App Password in Gmail.
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "raluwzarunwirgjms" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥", layout="wide")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Load fresh data
        data = conn.read(ttl=0)
        if data is not None and not data.empty:
            # FIX: Global cleaner for the ".0" float bug
            data['sid'] = data['sid'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        return data
    except Exception:
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

# Initialize cleaned data
df = get_data()

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    msg.set_content(f"Dear {donor_name},\n\nURGENT: A patient needs {blood_group} blood. Please contact the receiver at: {receiver_phone}")
    msg['Subject'] = f"🚨 CUET Blood Request: {blood_group}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        # Using Port 587 with STARTTLS for better reliability
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

st.title("🏥 CUET Student Medical Portal")
tab1, tab2, tab3 = st.tabs(["🚨 Patient Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: PATIENT SEARCH (FIXED SEARCH BUG) ---
with tab1:
    st.subheader("Search Patient Records")
    sid_query = st.text_input("Enter Student ID to Search", key="search_input").strip()
    
    if sid_query:
        if not df.empty:
            # Match against the cleaned SID string
            result = df[df['sid'] == sid_query]
            
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

# --- TAB 2: FIND DONORS (FIXED DOMAIN & EMAIL) ---
with tab2:
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_phone = st.text_input("Your Phone Number (for call):")
    
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                clean_sid = row['sid']
                st.write(f"**{row['name']}** (ID: {clean_sid})")
                
                if st.button(f"Notify {clean_sid}", key=f"mail_{clean_sid}"):
                    if receiver_phone:
                        # EXACT DOMAIN: studnet.cuet.ac.bd
                        target_mail = f"u{clean_sid}@studnet.cuet.ac.bd"
                        if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                            st.success(f"Notification sent to {target_mail}")
                    else: 
                        st.error("Please enter your contact number.")
        else:
            st.write("No donors currently found for this group.")

# --- TAB 3: REGISTER/UPDATE (SAME ID UPDATES PROFILE) ---
with tab3:
    st.subheader("Update Your Profile")
    with st.form("reg_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID").strip()
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", "None")
        f_his = st.text_area("Medical History", "None")
        
        # Fixed Donation Selection
        donation_status = st.radio("Donation Info:", ["Never Donated", "Select Date"])
        f_date = "Never"
        if donation_status == "Select Date":
            f_date = str(st.date_input("When was your last donation?"))

        if st.form_submit_button("Submit Data"):
            if f_sid and f_name:
                user_id = str(f_sid).strip()
                new_data = pd.DataFrame([{
                    "sid": user_id, "name": f_name, "bg": f_bg, "phone": f_phone,
                    "allergies": f_all, "history": f_his, "last donation": f_date
                }])
                
                try:
                    # Logic: Remove the old ID row and append the new one
                    fresh_df = get_data()
                    updated_df = pd.concat([fresh_df[fresh_df['sid'] != user_id], new_data], ignore_index=True)
                    
                    conn.update(data=updated_df)
                    st.success(f"Profile for {user_id} updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")
