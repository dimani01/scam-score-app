# Scam Score Fraud Detection Web App

This is a simple Streamlit web application that allows users to upload a CSV file containing borrower data and computes a fraud risk score called **Scam\_Score** to flag potential first-party fraud cases.

---

## 🚀 Features

- Upload `.csv` files with flexible delimiter options (`comma`, `semicolon`, `tab`, `pipe`).
- Cleans and parses numeric and categorical fields automatically.
- Computes a comprehensive fraud risk score based on behavioral and financial features.
- Flags users likely to commit first-party fraud (`is_fraud` flag).
- Download the resulting dataset with predictions.

---

## 📦 Requirements

Make sure you have Python 3.8 or later installed.
Install required packages with:

```bash
pip install streamlit pandas numpy
```

---

## 💡 How to Run

1. Save the main code as `app.py` (already provided).
2. Open terminal and navigate to the folder where `app.py` is saved.
3. Run the app:

```bash
streamlit run app.py
```

4. The app will open in your browser at `http://localhost:8501`.

---

## 📄 Input Format

Your CSV file should contain at least the following fields:

```
was_canceled, NEGATIVESTATUS, overdueinstalmentcount_po_subektu,
SUM_SIG_PEAKS_OVERDUECOUNT_LAST_2Y, NUM_CONTRACTS,
MONTH_OVERDUE_C0 ... MONTH_OVERDUE_C12, NUM_CONTRACT_PDL,
overdueamount, instalmentamount, CLASSIFICATION, DTI3M,
NUM_PHONENUMBERS, NUM_ADDRESSES
```

---

## 📈 Output

The output file will include two new columns:

- `Scam_Score`: numeric score
- `is_fraud`: True if `Scam_Score > 0.7`

---

## 🧠 Based On

This app was built using domain-specific formulas for fraud detection as provided in internal documents. All weights and indicators are customizable in `app.py`.

---

## 🛡 Disclaimer

This tool is for research and prototype purposes. Always test and validate scoring models on real-world data before production use.

---

## ✨ Author

Built with ❤️ using Streamlit and Pandas.

Улыбайся получилось)
