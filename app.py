import streamlit as st
import pandas as pd
import numpy as np
from math import log1p

st.set_page_config(page_title="Scam Detection App", layout="wide")
st.title("📊 Scam Score Fraud Detection")
st.write("Upload your CSV file and we'll calculate Scam Score and flag potential fraud cases.")

# File uploader and separator selection
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
sep_option = st.selectbox("Choose CSV separator", options=[",", ";", "\t", "|"], index=0)

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=sep_option)
    df.columns = df.columns.str.strip()  # Clean column names

    # Clean numeric values
    def clean_numeric(val):
        if isinstance(val, str):
            val = val.replace(" ", "").replace(",", ".").replace("-", "")
            try:
                return float(val)
            except:
                return np.nan
        return val

    numeric_cols = [col for col in df.columns if df[col].dtype == 'object']
    for col in numeric_cols:
        df[col] = df[col].apply(clean_numeric)

    # Compute Scam Score
    df["Scam_Score"] = (
        0.7 * df.get("was_canceled", 0).fillna(0)
        + 0.6 * df["NEGATIVESTATUS"].apply(lambda x: 1 if x == 'Y' else 0)
        + 0.5 * np.log1p(df.get("overdueinstalmentcount_po_subektu", 0))
        + 0.4 * (df.get("SUM_SIG_PEAKS_OVERDUECOUNT_LAST_2Y", 0) / (df.get("NUM_CONTRACTS", 0) + 1))
        + 0.3 * df[[col for col in df.columns if "MONTH_OVERDUE_C" in col]].max(axis=1) / 30
        + 0.25 * np.log1p(df.get("NUM_CONTRACT_PDL", 0))
        + 0.2 * (df.get("overdueamount", 0) / (df.get("instalmentamount", 0) + 1))
        + 0.2 * df["CLASSIFICATION"].apply(lambda x: 1 if x in ['E', 'F'] else 0)
        + 0.15 * df.get("DTI3M", 0).apply(lambda x: 1 if x > 0.6 else 0)
        + 0.1 * df.get("NUM_PHONENUMBERS", 0).apply(lambda x: 1 if x > 3 else 0)
        + 0.1 * df.get("NUM_ADDRESSES", 0).apply(lambda x: 1 if x > 2 else 0)
    )

    # Flag fraud cases
    df["is_fraud"] = df["Scam_Score"] > 0.7

    st.success("Scam Score calculated and fraud flagged!")

    st.subheader("Sample Results")
    st.dataframe(df[["Scam_Score", "is_fraud"] + df.columns[:10].tolist()])

    # Download link
    csv_out = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV with Results", data=csv_out, file_name="scam_scored_output.csv", mime="text/csv")
