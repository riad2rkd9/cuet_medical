import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.message import EmailMessage

# =========================
# EMAIL SETTINGS
# =========================
# Use Streamlit Secrets in deployment
# .streamlit/secrets.toml

# SENDER_EMAIL = "yourmail@gmail.com"
# SENDER_PASSWORD = "your_app_password"

SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="CUET Medical Portal",
    page_icon="🏥",
    layout="wide"
)

# =========================
# DATABASE CONNECTION
# =========================
conn = st.connection("gsheets", type=GSheetsConnection)

# =========================
# LOAD DATA
# =========================
def get_data():
    try:
        data = conn.read(ttl=0)

        if data is not None and not data.empty:

            # FIX .0 issue
            data['sid'] = (
                data['sid']
                .astype(str)
                .str.replace(r'\.0$', '', regex=True)
                .str.strip()
            )

        return data

    except Exception:
        return pd.DataFrame(
            columns=[
                "sid",
                "name",
                "bg",
                "phone",
                "allergies",
                "history",
                "last donation"
            ]
        )

df = get_data()

# =========================
# EMAIL FUNCTION
# =========================
def send_donor_email(to_email, donor_name, blood_group, receiver_phone):

    msg = EmailMessage()

    msg.set_content(
        f"""
Dear {donor_name},

URGENT: A patient needs {blood_group} blood.

Please contact:
{receiver_phone}

Thank you.
CUET Medical Portal
"""
    )

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

# =========================
# TITLE
# =========================
st.title("🏥 CUET Student Medical Portal")

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs([
    "🚨 Patient Search",
    "🩸 Find Donors",
    "📝 Register/Update"
])

# =========================================================
# TAB 1 : PATIENT SEARCH
# =========================================================
with tab1:

    st.subheader("Search Student Records")

    sid_query = st.text_input(
        "Enter Student ID to Search",
        key="search_input"
    ).strip()

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

# =========================================================
# TAB 2 : FIND DONORS
# =========================================================
with tab2:

    st.subheader("Find Blood Donors")

    target_bg = st.selectbox(
        "Blood Group Needed",
        ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    )

    receiver_phone = st.text_input("Your Phone Number")

    if not df.empty:

        donors = df[df['bg'] == target_bg]

        if donors.empty():

            st.warning("No donors found.")

        else:

            for _, row in donors.iterrows():

                clean_sid = row['sid']

                st.write(f"### {row['name']}")
                st.write(f"ID: {clean_sid}")
                st.write(f"Phone: {row['phone']}")

                if st.button(
                    f"Send Email to {clean_sid}",
                    key=f"mail_{clean_sid}"
                ):

                    if receiver_phone:

                        # CUET student email
                        target_mail = f"u{clean_sid}@student.cuet.ac.bd"

                        success = send_donor_email(
                            target_mail,
                            row['name'],
                            target_bg,
                            receiver_phone
                        )

                        if success:
                            st.success(f"Email sent to {target_mail}")

                    else:
                        st.error("Please enter your phone number.")

                st.divider()

# =========================================================
# TAB 3 : REGISTER / UPDATE
# =========================================================
with tab3:

    st.subheader("Update Your Profile")

    with st.form("reg_form", clear_on_submit=True):

        f_sid = st.text_input("Student ID").strip()

        f_name = st.text_input("Full Name")

        f_bg = st.selectbox(
            "Blood Group",
            ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
        )

        f_phone = st.text_input("Phone Number")

        f_all = st.text_area(
            "Allergies",
            "None"
        )

        f_his = st.text_area(
            "Medical History",
            "None"
        )

        donation_status = st.radio(
            "Last Donation Info:",
            ["Never Donated", "Select Date"]
        )

        f_date = "Never"

        if donation_status == "Select Date":

            f_date = str(
                st.date_input(
                    "When was your last donation?"
                )
            )

        submit = st.form_submit_button("Submit Data")

        if submit:

            if f_sid and f_name:

                new_entry = pd.DataFrame([
                    {
                        "sid": f_sid,
                        "name": f_name,
                        "bg": f_bg,
                        "phone": f_phone,
                        "allergies": f_all,
                        "history": f_his,
                        "last donation": f_date
                    }
                ])

                try:

                    fresh_df = get_data()

                    updated_df = pd.concat(
                        [
                            fresh_df[fresh_df['sid'] != f_sid],
                            new_entry
                        ],
                        ignore_index=True
                    )

                    conn.update(data=updated_df)

                    st.success("Database Updated Successfully!")

                    st.rerun()

                except Exception as e:
                    st.error(f"Update failed: {e}")

            else:
                st.error("Student ID and Name are required.")
