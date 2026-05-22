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
        data = conn.read(ttl=0)
        if data is not None and not data.empty:
            # GLOBAL CLEANING: Remove .0 and whitespace from all SIDs immediately
            data['sid'] = data['sid'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        return data
    except Exception:
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

# Initialize data
df = get_data()

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    msg.set_content(f"Dear {donor_name},\n\nURGENT: A patient needs {blood_group} blood. Please contact the receiver at: {receiver_phone}\n\n- CUET Medical Team")
    msg['Subject'] = f"🚨 CUET Blood Request: {blood_group}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

st.title("🏥 CUET Student Medical Portal")
tab1, tab2, tab3 = st.tabs(["🚨 Patient Search", "🩸 Find Donors", "📝 Register/Update"])

# --- TAB 1: PATIENT SEARCH (STRICT MATCHING) ---
with tab1:
    st.subheader("Search Student Records")
    sid_query = st.text_input("Enter Student ID to Search", key="search_input").strip()
    
    if sid_query:
        if not df.empty:
            # We already cleaned df in get_data(), so a simple match works now
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

# --- TAB 2: FIND DONORS (CUET EMAIL FIX) ---
with tab2:
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_phone = st.text_input("Your Phone Number (for donors to call):")
    
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                clean_sid = row['sid']
                st.write(f"**{row['name']}** (ID: {clean_sid})")
                
                if st.button(f"E-mail {clean_sid}", key=f"mail_{clean_sid}"):
                    if receiver_phone:
                        # EXACT DOMAIN: studnet.cuet.ac.bd
                        target_mail = f"u{clean_sid}@studnet.cuet.ac.bd"
                        with st.spinner(f"Sending to {target_mail}..."):
                            if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                                st.success(f"Notification sent to {target_mail}")
                    else: 
                        st.error("Please enter your contact number first.")
        else:
            st.write("No donors found for this blood group.")

# --- TAB 3: REGISTER/UPDATE (ONE OPTION LOGIC) ---
with tab3:
    st.subheader("Update Your Profile")
    st.markdown("Enter your ID to register. If you already exist, your info will be updated.")
    
    with st.form("reg_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID (e.g., 2311029)").strip()
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", "None")
        f_his = st.text_area("Medical History", "None")
        
        # Improved Donation Toggle
        donation_status = st.radio("Have you donated before?", ["Never Donated", "I have a specific date"])
        f_date = "Never"
        if donation_status == "I have a specific date":
            f_date = str(st.date_input("Last Donation Date"))

        if st.form_submit_button("Submit Data"):
            if f_sid and f_name and f_phone:
                new_entry = pd.DataFrame([{
                    "sid": f_sid, 
                    "name": f_name, 
                    "bg": f_bg, 
                    "phone": f_phone,
                    "allergies": f_all, 
                    "history": f_his, 
                    "last donation": f_date
                }])
                
                try:
                    # 1. Get latest data
                    fresh_df = get_data()
                    # 2. Filter out the old record for this SID (Profile Update)
                    filtered_df = fresh_df[fresh_df['sid'] != f_sid]
                    # 3. Add the new data
                    final_df = pd.concat([filtered_df, new_entry], ignore_index=True)
                    
                    # 4. Update the Google Sheet
                    conn.update(data=final_df)
                    st.success(f"Success! Profile for {f_sid} has been updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")
            else:
                st.error("ID, Name, and Phone are required.")
