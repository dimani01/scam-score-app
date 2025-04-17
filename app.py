import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import math

st.set_page_config(page_title="Scam Detection App", layout="wide")
st.title("📊 Scam Score Fraud Detection")
st.write("Загрузите CSV-файл — мы рассчитаем Scam Score, уровень риска, вероятность мошенничества и предложим решение.")

# --- Загрузка файла ---
uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])
sep_option = st.selectbox("Разделитель в CSV", options=[",", ";", "\t", "|"], index=0)

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=sep_option)
    df.columns = df.columns.str.strip()

    # --- Очистка числовых значений ---
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

    # --- Преобразование пола ---
    if "gender" in df.columns:
        df["gender"] = df["gender"].replace({515: "male", 516: "female"})
        df["gender"] = df["gender"].astype(str).str.lower().str.strip()

    # --- Расчёт Scam Score ---
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

    df["is_fraud"] = df["Scam_Score"] > 0.7

    # --- DTI и его риск ---
    df["DTI"] = (df["instalmentamount"] * 3) / (df["AS3M"] * 3)
    df["DTI"] = pd.to_numeric(df["DTI"], errors='coerce').clip(upper=10)

    def classify_dti_risk(x):
        if pd.isna(x): return "неизвестно"
        if x <= 0.4: return "низкий"
        elif x <= 0.6: return "средний"
        else: return "высокий"

    df["DTI_Risk"] = df["DTI"].apply(classify_dti_risk)

    # --- Выбор формулы Fraud Score ---
    fraud_formula = st.selectbox("📌 Выберите формулу Fraud Score:", [
        "Fraud_Risk_Score",
        "Behavioral_Fraud_Score",
        "Contract_Activity_Fraud_Score"
    ])

    if fraud_formula == "Fraud_Risk_Score":
        df["Fraud_Score"] = (
            0.8 * df["NEGATIVESTATUS"].apply(lambda x: 1 if x == 'Y' else 0)
            + 0.7 * np.log1p(df.get("NUM_CONTRACTS_STARTED_L3M", 0))
            + 0.6 * df.get("NUM_PHONENUMBERS", 0).apply(lambda x: 1 if x > 3 else 0)
            + 0.4 * df.get("overdueamount", 0).apply(lambda x: 1 if x > 0 else 0)
            + 0.2 * df.get("NUM_ADDRESSES", 0).apply(lambda x: 1 if x > 2 else 0)
        )

    elif fraud_formula == "Behavioral_Fraud_Score":
        df["Fraud_Score"] = (
            0.8 * df.get("NUM_PHONENUMBERS", 0).apply(lambda x: 1 if x > 3 else 0)
            + 0.7 * df.get("NUM_ADDRESSES", 0).apply(lambda x: 1 if x > 2 else 0)
            + 0.6 * df.get("was_canceled", 0).apply(lambda x: 1 if x == 1 else 0)
            + 0.4 * np.log1p(df.get("NUM_CONTRACTS_STARTED_L3M", 0))
            + 0.2 * df["NEGATIVESTATUS"].apply(lambda x: 1 if x == 'Y' else 0)
        )

    elif fraud_formula == "Contract_Activity_Fraud_Score":
        df["Fraud_Score"] = (
            0.8 * np.log1p(df.get("NUM_CONTRACTS_STARTED_L3M", 0))
            + 0.7 * df["NEGATIVESTATUS"].apply(lambda x: 1 if x == 'Y' else 0)
            + 0.6 * np.log1p(df.get("NUM_CONTRACT_PDL", 0))
            + 0.4 * df.get("NUM_PHONENUMBERS", 0).apply(lambda x: 1 if x > 3 else 0)
            + 0.2 * np.log1p(df.get("NUM_CONTRACTS_OTHER", 0))
        )

    df["Fraud_Probability"] = df["Fraud_Score"].apply(lambda x: 1 / (1 + math.exp(-x)))

    # --- Credit Decision ---
    def make_decision(row):
        if row["Scam_Score"] > 0.8 or row["Fraud_Probability"] > 0.8:
            return "ОТКАЗ"
        elif row["Scam_Score"] > 0.6 or row["Fraud_Probability"] > 0.6:
            return "ПРОВЕРИТЬ"
        else:
            return "ОДОБРЕНО"

    df["Credit_Decision"] = df.apply(make_decision, axis=1)
    df_sorted = df.sort_values(by="Scam_Score", ascending=False)

    st.success("✅ Расчёты завершены!")

    # --- Фильтрация ---
    st.subheader("📊 Клиенты (фильтрация)")
    risk_filter = st.selectbox("🔍 Уровень риска:", ["все", "низкий", "средний", "высокий"])
    decision_filter = st.selectbox("✅ Решение:", ["все", "ОДОБРЕНО", "ПРОВЕРИТЬ", "ОТКАЗ"])

    gender_filter_options = ["все"]
    if "gender" in df.columns:
        gender_filter_options += sorted(df["gender"].dropna().unique().tolist())
    gender_filter = st.selectbox("🧍 Пол:", gender_filter_options)

    df_filtered = df_sorted.copy()
    if risk_filter != "все": df_filtered = df_filtered[df_filtered["DTI_Risk"] == risk_filter]
    if decision_filter != "все": df_filtered = df_filtered[df_filtered["Credit_Decision"] == decision_filter]
    if gender_filter != "все" and "gender" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["gender"] == gender_filter]

    st.markdown(f"**👥 Клиентов найдено:** {len(df_filtered)}")
    st.markdown(f"- 🧮 Риск: `{risk_filter}`\n- 📋 Решение: `{decision_filter}`\n- 🚻 Пол: `{gender_filter}`")

    # --- Визуализации ---
    if "gender" in df_filtered.columns:
        gender_counts = df_filtered["gender"].value_counts().reset_index()
        gender_counts.columns = ["Пол", "Количество"]
        fig_gender = px.pie(gender_counts, names="Пол", values="Количество", title="Распределение по полу")
        st.plotly_chart(fig_gender, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.histogram(df_filtered, x="Credit_Decision", title="По решению", color="Credit_Decision",
                            color_discrete_map={"ОДОБРЕНО": "green", "ПРОВЕРИТЬ": "orange", "ОТКАЗ": "red"})
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.histogram(df_filtered, x="DTI_Risk", title="По риску", color="DTI_Risk")
        st.plotly_chart(fig2, use_container_width=True)

    # --- Таблица и выгрузка ---
    show_cols = ["Scam_Score", "is_fraud", "DTI", "DTI_Risk", "Credit_Decision", "Fraud_Score", "Fraud_Probability"]
    show_cols += [col for col in df.columns if col not in show_cols][:10]  # Первые 10 доп. колонок
    st.dataframe(df_filtered[show_cols])

    st.download_button("📥 Скачать результаты", df_filtered.to_csv(index=False).encode('utf-8'),
                       file_name="scam_scored_output.csv", mime="text/csv")

    prob_output = df_filtered[["ID", "Fraud_Probability"]] if "ID" in df.columns else df_filtered[["Fraud_Probability"]]
    st.download_button("📥 Скачать только Fraud Probability", prob_output.to_csv(index=False).encode("utf-8"),
                       file_name="fraud_prob_output.csv", mime="text/csv")
