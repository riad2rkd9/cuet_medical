import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime

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
        return pd.DataFrame(columns=["sid", "name", "bg", "phone", "allergies", "history", "last donation", "photo", "weight", "height", "systolic", "diastolic"])

df = get_data()

# --- OPTIMIZED PASSPORT SIZE PHOTO CROPPER & CELL COMPRESSOR ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        width, height = img.size
        
        # Target passport aspect ratio (approx 3.5:4.5)
        target_ratio = 3.5 / 4.5
        current_ratio = width / height
        
        # Center Crop logic
        if current_ratio > target_ratio:
            new_width = int(target_ratio * height)
            left = (width - new_width) / 2
            top = 0
            right = left + new_width
            bottom = height
        else:
            new_height = int(width / target_ratio)
            left = 0
            top = (height - new_height) / 2
            right = width
            bottom = top + new_height
            
        img_cropped = img.crop((left, top, right, bottom))
        
        # Scale to compact resolution to save spreadsheet memory limits
        img_passport = img_cropped.resize((220, 283), Image.Resampling.LANCZOS)
        
        # Quality compression at 60% stays well beneath Google's 50,000 character limit
        buffer = BytesIO()
        img_passport.save(buffer, format="JPEG", quality=60) 
        
        base64_string = base64.b64encode(buffer.getvalue()).decode()
        
        # Fallback safeguard
        if len(base64_string) > 49000:
            img_passport = img_passport.resize((150, 193), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img_passport.save(buffer, format="JPEG", quality=50)
            base64_string = base64.b64encode(buffer.getvalue()).decode()
            
        return base64_string
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
tab1, tab2, tab3, tab4 = st.tabs(["🚨 Patient Search", "🩸 Find Donors", "📝 Register/Update", "📊 Health Index Calculator"])

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
                
                c_photo, c1, c2 = st.columns([1.2, 2, 2])
                
                with c_photo:
                    if 'photo' in row and row['photo'] != "None" and row['photo'] != "":
                        try:
                            img_data = base64.b64decode(row['photo'])
                            st.image(BytesIO(img_data), caption="Photo", width=180)
                        except:
                            st.warning("Photo unavailable")
                    else:
                        st.info("No profile photo uploaded.")
                
                with c1:
                    st.metric("Blood Group", row['bg'])
                    st.write(f"**Phone:** {row['phone']}")
                    if 'weight' in row and row['weight'] != "None":
                        try:
                            total_cm = float(row['height'])
                            total_inches = total_cm / 2.54
                            ft = int(total_inches // 12)
                            inch = int(round(total_inches % 12))
                            st.write(f"**Weight:** {row['weight']} kg")
                            st.write(f"**Height:** {ft} ft {inch} in ({total_cm:.1f} cm)")
                        except:
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
    receiver_phone = st.text_input("Your Contact Number:", key="donor_contact")
    
    if not df.empty:
        donors = df[df['bg'] == target_bg]
        if not donors.empty:
            st.write("### Available Donors Matching Criteria:")
            
            for _, row in donors.iterrows():
                clean_sid = row['sid']
                donation_status = row['last donation']
                
                is_eligible = True
                deferral_reason = ""
                days_left = 0
                
                # 1. Check Timeline Eligibility (90-day rest rule)
                if donation_status != "Never" and donation_status != "None":
                    try:
                        donation_date = datetime.strptime(donation_status, "%Y-%m-%d").date()
                        today = datetime.now().date()
                        days_since_donation = (today - donation_date).days
                        
                        if days_since_donation < 90:
                            is_eligible = False
                            days_left = 90 - days_since_donation
                            deferral_reason = f"⏳ Recently Donated-{days_left} Days Left to donate"
                    except Exception:
                        pass 

                # 2. Check Clinical BP Safety Limits (Systolic: 90-180 | Diastolic: 50-100)
                if is_eligible and 'systolic' in row and row['systolic'] != "None":
                    try:
                        sys_check = int(float(row['systolic']))
                        dia_check = int(float(row['diastolic']))
                        
                        if sys_check < 90 or sys_check > 180 or dia_check < 50 or dia_check > 100:
                            is_eligible = False
                            deferral_reason = f"❌ Unsafe BP ({sys_check}/{dia_check})"
                    except Exception:
                        pass

                # Render List Items Dynamically
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    if is_eligible:
                        st.write(f"🟢 {row['name']} (ID: {clean_sid}) — Available to Donate")
                    else:
                        st.write(f"🔴 {row['name']} (ID: {clean_sid}) — {deferral_reason}")
                
                with col_action:
                    if is_eligible:
                        if st.button(f"E-mail {clean_sid}", key=f"mail_{clean_sid}"):
                            if receiver_phone:
                                # Email address configured per request
                                target_mail = f"u{clean_sid}@student.cuet.ac.bd"
                                if send_donor_email(target_mail, row['name'], target_bg, receiver_phone):
                                    st.success(f"E-Mail sent to {target_mail}")
                            else:
                                st.error("Phone required!")
                    else:
                        st.button(f"Not available", key=f"blocked_{clean_sid}", disabled=True, help=deferral_reason)
                st.markdown("---")
        else:
            st.info("No donors found with this blood group.")

# --- TAB 3: REGISTER/UPDATE ---
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
            f_all = st.text_area("Allergies", "---")
            f_his = st.text_area("Medical History", "---")
            
            sc1, sc2 = st.columns(2)
            with sc1:
                f_weight = st.number_input("Weight (kg)", min_value=10.0, max_value=200.0, value=60.0)
            with sc2:
                h_col1, h_col2 = st.columns(2)
                with h_col1:
                    f_feet = st.selectbox("Height (Feet)", list(range(3, 9)), index=2)
                with h_col2:
                    f_inches = st.selectbox("Inches", list(range(0, 12)), index=5)
                
                f_sys = st.number_input("Systolic BP (mmHg)", min_value=50, max_value=250, value=120, key="reg_sys")
                f_dia = st.number_input("Diastolic BP (mmHg)", min_value=30, max_value=150, value=80)
        
        uploaded_photo = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"])
        
        if has_donated == "Yes":
            final_date_val = st.date_input("Select Last Donation Date")
            f_date = str(final_date_val)

        submitted = st.form_submit_button("Submit to Database")
        if submitted:
            if f_sid and f_name:
                photo_encoded = image_to_base64(uploaded_photo)
                total_inches_calc = (f_feet * 12) + f_inches
                calculated_cm = total_inches_calc * 2.54
                
                new_row = pd.DataFrame([{
                    "sid": f_sid, "name": f_name, "bg": f_bg, "phone": f_phone,
                    "allergies": f_all, "history": f_his, "last donation": f_date,
                    "photo": photo_encoded, "weight": str(f_weight), "height": f"{calculated_cm:.2f}",
                    "systolic": str(f_sys), "diastolic": str(f_dia)
                }])
                try:
                    fresh_df = get_data()
                    for col in ["sid", "name", "bg", "phone", "allergies", "history", "last donation", "photo", "weight", "height", "systolic", "diastolic"]:
                        if col not in fresh_df.columns:
                            fresh_df[col] = None
                    
                    final_df = pd.concat([fresh_df[fresh_df['sid'] != f_sid], new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Profile update successful!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Database write error: {e}")
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
        
        bmi_h_col1, bmi_h_col2 = st.columns(2)
        with bmi_h_col1:
            c_feet = st.selectbox("Height (Feet)", list(range(3, 9)), index=2, key="calc_ft")
        with bmi_h_col2:
            c_inches = st.selectbox("Inches", list(range(0, 12)), index=7, key="calc_in")
        
        if st.button("Evaluate BMI"):
            total_inches = (c_feet * 12) + c_inches
            height_meters = (total_inches * 2.54) / 100.0
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
