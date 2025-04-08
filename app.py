import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Scam Detection App", layout="wide")
st.title("📊 Scam Score Fraud Detection")
st.write("Upload your CSV file and we'll calculate Scam Score, risk categories, and decisions.")

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
            except ValueError:
                return np.nan
        return val

    numeric_cols = [col for col in df.columns if df[col].dtype == 'object']
    for col in numeric_cols:
        df[col] = df[col].apply(clean_numeric)

    # Fix gender if coded as numbers
    if "gender" in df.columns:
        df["gender"] = df["gender"].replace({515: "male", 516: "female"})
        df["gender"] = df["gender"].astype(str).str.lower().str.strip()

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
        + 0.15 * (df["DTI3M"] if "DTI3M" in df.columns else pd.Series(0, index=df.index)).apply(lambda x: 1 if x > 0.6 else 0)
        + 0.1 * df.get("NUM_PHONENUMBERS", 0).apply(lambda x: 1 if x > 3 else 0)
        + 0.1 * df.get("NUM_ADDRESSES", 0).apply(lambda x: 1 if x > 2 else 0)
    )

    # Flag fraud cases
    df["is_fraud"] = df["Scam_Score"] > 0.7

    # Calculate DTI
    df["DTI"] = (df["instalmentamount"] * 3) / (df["AS3M"] * 3)
    df["DTI_Risk"] = df["DTI"].apply(lambda x: "низкий" if x <= 0.4 else ("средний" if x <= 0.6 else "высокий"))

    # Decision based on DTI risk
    df["Credit_Decision"] = df["DTI"].apply(lambda x: "ОДОБРЕНО" if x <= 0.4 else ("ПРОВЕРИТЬ" if x <= 0.6 else "ОТКАЗ"))

    # Sort by risk score and show full summary
    df_sorted = df.sort_values(by="Scam_Score", ascending=False)

    st.success("Scam Score, DTI risk and decisions calculated!")

    st.subheader("📊 Клиенты (фильтрация по риску, решению, полу)")

    # Фильтрация по уровню риска
    risk_filter = st.selectbox(
        "🔍 Выберите уровень риска:",
        options=["все", "низкий", "средний", "высокий"]
    )

    # Фильтрация по решению
    decision_filter = st.selectbox(
        "✅ Выберите решение:",
        options=["все", "ОДОБРЕНО", "ПРОВЕРИТЬ", "ОТКАЗ"]
    )

    # Фильтрация по полу
    gender_filter = st.selectbox(
        "🧍 Фильтр по полу:",
        options=["все"] + sorted(df_sorted["gender"].dropna().unique().tolist()) if "gender" in df.columns else ["все"]
    )

    df_filtered = df_sorted.copy()

    if risk_filter != "все":
        df_filtered = df_filtered[df_filtered["DTI_Risk"] == risk_filter]

    if decision_filter != "все":
        df_filtered = df_filtered[df_filtered["Credit_Decision"] == decision_filter]

    if gender_filter != "все" and "gender" in df.columns:
        df_filtered = df_filtered[df_filtered["gender"] == gender_filter]

    # Сводка по фильтру
    st.markdown(f"**👥 Найдено клиентов:** {len(df_filtered)}")
    st.markdown(f"- 🧮 Уровень риска: `{risk_filter}`")
    st.markdown(f"- 📋 Решение: `{decision_filter}`")
    st.markdown(f"- 🚻 Пол: `{gender_filter}`")

    # Дополнительно: распределение по полу
    if "gender" in df_filtered.columns:
        gender_counts = df_filtered["gender"].value_counts().reset_index()
        gender_counts.columns = ["Пол", "Количество"]
        fig_gender = px.pie(gender_counts, names="Пол", values="Количество", title="Распределение по полу")
        st.plotly_chart(fig_gender, use_container_width=True)

    # Визуализация: распределение по решению
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.histogram(df_filtered, x="Credit_Decision", title="Распределение по решению", color="Credit_Decision")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.histogram(df_filtered, x="DTI_Risk", title="Распределение по уровню риска", color="DTI_Risk")
        st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(df_filtered[["Scam_Score", "is_fraud", "DTI", "DTI_Risk", "Credit_Decision"] + df.columns[:10].tolist()])

    # Download link
    csv_out = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV with Results", data=csv_out, file_name="scam_scored_output.csv", mime="text/csv")

