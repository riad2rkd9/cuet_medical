import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage

# --- EMAIL SETTINGS ---
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "ifhb iydp mdvj wrug" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥", layout="wide")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl=0)
        if data is not None and not data.empty:
            data['sid'] = data['sid'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            data['phone'] = data['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            data['phone'] = data['phone'].apply(lambda x: '0' + x if not x.startswith('0') and x != 'nan' else x)
            data = data.fillna("None").replace("nan", "None")
        return data
    except Exception:
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

df = get_data()

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    msg.set_content(f"Dear {donor_name},\n\nURGENT: A patient needs {blood_group} blood. Please contact: {receiver_phone}")
    msg['Subject'] = f"🚨 CUET Blood Request: {blood_group}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
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

# --- TAB 1: PATIENT SEARCH ---
with tab1:
    st.subheader("Search Patient Records")
    sid_query = st.text_input("Enter Student ID", key="search_input").strip()
    if sid_query:
        if not df.empty:
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

# --- TAB 2: FIND DONORS ---
with tab2:
    target_bg = st.selectbox("Blood Group Needed", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    receiver_phone = st.text_input("Your Contact Number:")
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            for _, row in donors.iterrows():
                clean_sid = row['sid']
                st.write(f"**{row['name']}** (ID: {clean_sid})")
                if st.button(f"E-mail {clean_sid}", key=f"mail_{clean_sid}"):
                    if receiver_phone:
                        target_mail = f"u{clean_sid}@student.cuet.ac.bd"
                        if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                            st.success(f"Mail sent to {target_mail}")
                    else: st.error("Phone required!")

# --- TAB 3: REGISTER/UPDATE ---
with tab3:
    st.subheader("Update Your Profile")
    
    # FIX: Move the toggle OUTSIDE the form so it reruns the page when changed
    has_donated = st.radio("Have you donated blood before?", ["No", "Yes"], horizontal=True)
    
    # Variable to hold the final date string
    f_date = "Never"
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_sid = st.text_input("Student ID (e.g., 2311029)").strip()
            f_name = st.text_input("Full Name")
            f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        with col2:
            f_phone = st.text_input("Phone Number")
            f_all = st.text_area("Allergies", "None")
            f_his = st.text_area("Medical History", "None")
        
        # If user picked "Yes" above, show the date input INSIDE the form
        if has_donated == "Yes":
            final_date_val = st.date_input("Select Last Donation Date")
            f_date = str(final_date_val)

        submitted = st.form_submit_button("Submit to Database")
        
        if submitted:
            if f_sid and f_name:
                new_row = pd.DataFrame([{
                    "sid": f_sid, "name": f_name, "bg": f_bg, "phone": f_phone,
                    "allergies": f_all, "history": f_his, "last donation": f_date
                }])
                try:
                    fresh_df = get_data()
                    final_df = pd.concat([fresh_df[fresh_df['sid'] != f_sid], new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Successfully updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please fill ID and Name.")
