import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage
import安全 as sa  # Using standard base64 for image encoding
import base64
from io import BytesIO
from PIL import Image

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
            data['phone'] = data['phone'].apply(lambda x: '0' + x if not x.startswith('0' ) and x != 'nan' else x)
            data = data.fillna("None").replace("nan", "None")
        return data
    except Exception:
        # Added 'photo', 'weight', 'height', 'systolic', 'diastolic' columns to the schema
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation", "photo", "weight", "height", "systolic", "diastolic"])

df = get_data()

# Helper function to convert uploaded image file to a base64 string
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        # Resize slightly to avoid making the Google Sheet cell too massive
        img.thumbnail((300, 300))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode()
    return "None"

def send_donor_email(to_email, donor_name, blood_group, receiver_phone):
    msg = EmailMessage()
    email_body = (
        f"Dear {donor_name},\n\n"
        f"This is an EMERGENCY blood request from CUET Medical Center.\n\n"
        f"A patient urgently needs {blood_group} blood. Please contact the receiver at: {receiver_phone}\n\n"
        f"- CUET Medical Team"
    )
    msg.set_content(email_body)
    msg['Subject'] = f"🚨 URGENT: {blood_group} Blood Needed"
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
# Added a 4th tab for Health Index tools
tab1, tab2, tab3, tab4 = st.tabs(["🚨 Patient Search", "🩸 Find Donors", "📝 Register/Update", "📊 Health Index Calculator"])

# --- TAB 1: PATIENT SEARCH (WITH PHOTO & LIVE HEALTH METRICS) ---
with tab1:
    st.subheader("Search Patient Records")
    sid_query = st.text_input("Enter Student ID to Search", key="search_input").strip()
    if sid_query:
        if not df.empty:
            result = df[df['sid'] == sid_query]
            if not result.empty:
                row = result.iloc[0]
                st.success(f"### Profile Found: {row['name']}")
                
                # Split layout into 3 columns to neatly show photo and details
                c_photo, c1, c2 = st.columns([1, 2, 2])
                
                with c_photo:
                    # Check and display photo from Base64 string
                    if 'photo' in row and row['photo'] != "None" and row['photo'] != "":
                        try:
                            img_data = base64.b64decode(row['photo'])
                            st.image(BytesIO(img_data), caption="Student Photo", use_container_width=True)
                        except:
                            st.warning("No photo available")
                    else:
                        st.info("No profile photo uploaded.")
                
                with c1:
                    st.metric("Blood Group", row['bg'])
                    st.write(f"**Phone:** {row['phone']}")
                    if 'weight' in row and row['weight'] != "None":
                        st.write(f"**Weight:** {row['weight']} kg | **Height:** {row['height']} cm")
                
                with c2:
                    st.error(f"**Allergies:** {row['allergies']}")
                    st.error(f"**Medical History:** {row['history']}")
                    if 'systolic' in row and row['systolic'] != "None":
                        st.write(f"**Last Recorded BP:** {row['systolic']}/{row['diastolic']} mmHg")
                
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
                        target_mail = f"u{clean_sid}@student.cuet.ac.bd"
                        if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                            st.success(f"Emergency Alert sent to {target_mail}")
                    else: st.error("Phone required!")

# --- TAB 3: REGISTER/UPDATE (WITH PHOTO UPLOAD & HEALTH STATS) ---
with tab3:
    st.subheader("Update Your Profile")
    
    has_donated = st.radio("Have you donated blood before?", ["No", "Yes"], horizontal=True)
    
    f_date = "Never"
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_sid = st.text_input("Student ID (e.g., 2311029)").strip()
            f_name = st.text_input("Full Name")
            f_bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
            f_phone = st.text_input("Phone Number")
        with col2:
            f_all = st.text_area("Allergies", "None")
            f_his = st.text_area("Medical History", "None")
            
            # Sub-columns inside form for physical attributes
            sc1, sc2 = st.columns(2)
            with sc1:
                f_weight = st.number_input("Weight (kg)", min_value=10.0, max_value=200.0, value=60.0)
                f_sys = st.number_input("Systolic BP (mmHg)", min_value=50, max_value=250, value=120)
            with sc2:
                f_height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=165.0)
                f_dia = st.number_input("Diastolic BP (mmHg)", min_value=30, max_value=150, value=80)
        
        # New Feature: Profile Photo Uploader
        uploaded_photo = st.file_uploader("Upload Profile Picture (JPG/PNG)", type=["jpg", "jpeg", "png"])
        
        if has_donated == "Yes":
            final_date_val = st.date_input("Select Last Donation Date")
            f_date = str(final_date_val)

        submitted = st.form_submit_button("Submit to Database")
        if submitted:
            if f_sid and f_name:
                # Process the photo into text string strings
                photo_encoded = image_to_base64(uploaded_photo)
                
                new_row = pd.DataFrame([{
                    "sid": f_sid, "name": f_name, "bg": f_bg, "phone": f_phone,
                    "allergies": f_all, "history": f_his, "last donation": f_date,
                    "photo": photo_encoded, "weight": str(f_weight), "height": str(f_height),
                    "systolic": str(f_sys), "diastolic": str(f_dia)
                }])
                try:
                    fresh_df = get_data()
                    final_df = pd.concat([fresh_df[fresh_df['sid'] != f_sid], new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Successfully updated registration matrix!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving data: {e}")
            else:
                st.error("Please fill ID and Name.")

# --- TAB 4: AUTOMATED HEALTH INDEX CALCULATOR ---
with tab4:
    st.subheader("📊 Instant Clinical Index Evaluator")
    st.write("Calculate Body Mass Index (BMI) and Blood Pressure categories instantly using automated medical validation boundaries.")
    
    calc_col1, calc_col2 = st.columns(2)
    
    with calc_col1:
        st.markdown("### 🏋️ BMI Calculator")
        c_w = st.number_input("Current Weight (kg)", min_value=10.0, value=70.0, key="bmi_w")
        c_h = st.number_input("Current Height (cm)", min_value=50.0, value=170.0, key="bmi_h")
        
        if st.button("Evaluate BMI"):
            height_meters = c_h / 100.0
            bmi = c_w / (height_meters ** 2)
            st.metric("Your Calculated BMI", f"{bmi:.2f}")
            
            if bmi < 18.5:
                st.warning("Category: Underweight")
            elif 18.5 <= bmi < 24.9:
                st.success("Category: Normal Weight (Healthy Donor)")
            elif 25.0 <= bmi < 29.9:
                st.warning("Category: Overweight")
            else:
                st.error("Category: Obese")
                
    with calc_col2:
        st.markdown("### 🫀 Blood Pressure Analyzer")
        sys_val = st.number_input("Systolic Value (Top Number)", min_value=50, value=120, key="bp_sys")
        dia_val = st.number_input("Diastolic Value (Bottom Number)", min_value=30, value=80, key="bp_dia")
        
        if st.button("Evaluate Cardiorespiratory Status"):
            st.write(f"Reading: **{sys_val}/{dia_val} mmHg**")
            if sys_val < 120 and dia_val < 80:
                st.success("Diagnosis: Normal Blood Pressure")
            elif 120 <= sys_val < 130 and dia_val < 80:
                st.warning("Diagnosis: Elevated")
            elif 130 <= sys_val < 140 or 80 <= dia_val < 90:
                st.error("Diagnosis: Stage 1 Hypertension")
            else:
                st.error("Diagnosis: Stage 2 Hypertension / Crisis Check Needed")
