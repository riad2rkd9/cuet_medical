import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage

# --- EMAIL SETTINGS ---
# Ensure you have a fresh App Password from Google
SENDER_EMAIL = "ridwanbme23@gmail.com"
SENDER_PASSWORD = "ifhb iydp mdvj wrug" 

st.set_page_config(page_title="CUET Medical Portal", page_icon="🏥", layout="wide")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl=0)
        if data is not None and not data.empty:
            # 1. FIX SID: Force string and remove .0 decimals
            data['sid'] = data['sid'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. FIX PHONE: Remove .0 and ensure leading '0'
            data['phone'] = data['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            data['phone'] = data['phone'].apply(lambda x: '0' + x if not x.startswith('0') and x != 'nan' else x)
            
            # 3. FIX nan: Replace empty spreadsheet cells with "None"
            data = data.fillna("None").replace("nan", "None")
        return data
    except Exception:
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation"])

# Load data
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
                if st.button(f"Notify {clean_sid}", key=f"mail_{clean_sid}"):
                    if receiver_phone:
                        # Exact domain format uID@studnet.cuet.ac.bd
                        target_mail = f"u{clean_sid}@studnet.cuet.ac.bd"
                        if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                            st.success(f"Mail sent to {target_mail}")
                    else: st.error("Phone required!")

# --- TAB 3: REGISTER/UPDATE ---
with tab3:
    st.subheader("Update Your Profile")
    
    # We create the form container
    with st.form("registration_form", clear_on_submit=True):
        f_sid = st.text_input("Student ID (e.g., 2311029)").strip()
        f_name = st.text_input("Full Name")
        f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        f_phone = st.text_input("Phone Number")
        f_all = st.text_area("Allergies", "None")
        f_his = st.text_area("Medical History", "None")
        
        # --- FIXED DATE BAR LOGIC ---
        # Note: In Streamlit forms, the UI only updates after a SUBMIT.
        # To show/hide things instantly, the radio must be OUTSIDE the form, 
        # BUT for your use case, we will use a radio that defaults to 
        # showing the date picker if they select "Yes".
        
        has_donated = st.radio("Have you donated blood before?", ["No", "Yes"])
        
        # If they pick Yes, the date input appears inside the form
        f_date = "Never"
        if has_donated == "Yes":
            f_date = str(st.date_input("Last Donation Date"))

        submitted = st.form_submit_button("Submit to Database")
        
        if submitted:
            if f_sid and f_name:
                new_row = pd.DataFrame([{
                    "sid": f_sid, "name": f_name, "bg": f_bg, "phone": f_phone,
                    "allergies": f_all, "history": f_his, "last donation": f_date
                }])
                try:
                    fresh_df = get_data()
                    # Profile Update: Delete old row for this ID before adding new one
                    final_df = pd.concat([fresh_df[fresh_df['sid'] != f_sid], new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Successfully updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please fill ID and Name.")
