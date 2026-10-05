import io
import os
import pandas as pd
import numpy as np
import re
import json
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

# Load environment variables from .env file
load_dotenv()

# Securely configure the Gemini API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("\n" + "!"*60)
    print("⚠ WARNING: GEMINI_API_KEY is missing from environment variables or .env file.")
    print("!"*60 + "\n")

class SmartExpenseEngine:
    _category_cache = {}

    @staticmethod
    def fast_rule_categorize(merchant_name):
        name = str(merchant_name).strip().upper()

        def match(keywords):
            pattern = r'\b(?:' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            return bool(re.search(pattern, name))

        if match(['NETFLIX', 'SPOTIFY', 'PVR', 'INOX', 'HOTSTAR', 'STEAM', 'PRIME', 'SONYLIV']):
            return 'Entertainment & Media'
        if match(['SWIGGY', 'ZOMATO', 'RESTO', 'CAFE', 'MCDONALDS', 'KFC', 'BURGER', 'DOMINOS']):
            return 'Food & Dining'
        if match(['BLINKIT', 'ZEPTO', 'INSTAMART', 'BIGBASKET', 'DMART']):
            return 'Groceries & Essentials'
        if match(['AMAZON', 'FLIPKART', 'MYNTRA']):
            return 'Shopping'
        if match(['PETROL', 'UBER', 'OLA', 'IRCTC', 'METRO', 'RAPIDO']):
            return 'Travel & Fuel'

        words = name.split()
        if len(words) >= 2 and all(w.isalpha() for w in words):
            merchant_suffixes = {'ENTERPRISES', 'AGENCY', 'TRADERS', 'MEDICAL', 'STORE', 'MART', 'CENTER', 'CENTRE', 'SERVICES', 'CLINIC', 'HOTEL', 'CAFE', 'TEA', 'STATIONERY', 'XEROX', 'SNACKS', 'BHELPURI', 'BAKERY', 'DAIRY', 'COLLEGE', 'SCHOOL', 'INSTITUTE', 'ACADEMY'}
            if not any(w in merchant_suffixes for w in words):
                return 'Peer Transfer'

        return None

    @staticmethod
    def process_upi_csv(file):
        if hasattr(file, 'seek'):
            file.seek(0)
            
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')

        lines = content.splitlines()
        if not lines:
            raise ValueError("Uploaded file is empty.")

        header_idx = next((idx for idx, line in enumerate(lines[:25]) if 'date' in line.lower() and 'amount' in line.lower()), 0)

        processed_lines = [lines[header_idx].strip()]
        for line in lines[header_idx + 1:]:
            if line.strip():
                fixed_line = re.sub(r'([A-Za-z]{3}\s+\d{1,2}),\s*(\d{4})', r'\1 \2', line)
                processed_lines.append(fixed_line)

        csv_text = "\n".join(processed_lines)
        df = pd.read_csv(io.StringIO(csv_text))

        if df.empty:
            raise ValueError("CSV table is empty after parsing.")

        df.columns = [str(c).strip() for c in df.columns]

        date_col = next((c for c in df.columns if 'date' in c.lower()), df.columns[0])
        desc_col = next((c for c in df.columns if any(x in c.lower() for x in ['details', 'desc', 'particulars', 'payee'])), df.columns[min(2, len(df.columns)-1)])
        type_col = next((c for c in df.columns if 'type' in c.lower()), None)
        amt_col = next((c for c in df.columns if c.lower().strip() == 'amount'), df.columns[-1])

        if type_col and type_col in df.columns:
            df = df[df[type_col].astype(str).str.upper().str.contains('DEBIT')].reset_index(drop=True)

        df['Date'] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
        df['Date'] = df['Date'].fillna(datetime.now().strftime('%Y-%m-%d'))
        df['Amount'] = pd.to_numeric(df[amt_col].astype(str).str.replace(r'[^0-9.]', '', regex=True), errors='coerce').fillna(0.0).abs()

        def clean_merchant(text):
            t = str(text).strip()
            t = re.sub(r'(?i)^(paid to|paid|payment to)\s+', '', t)
            cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', t).strip().upper()
            return cleaned[:40] if cleaned else 'UPI USER'

        df['Merchant'] = df[desc_col].apply(clean_merchant)
        df = df[df['Amount'] > 0].reset_index(drop=True)

        if df.empty:
            raise ValueError("No valid debit transactions found in CSV.")

        # ==========================================
        # Dynamic AI Categorization Engine
        # ==========================================
        unique_merchants = df['Merchant'].unique()
        merchants_for_ai = []

        for m in unique_merchants:
            if m in SmartExpenseEngine._category_cache and SmartExpenseEngine._category_cache[m] != "General Expense":
                continue
            
            rule_cat = SmartExpenseEngine.fast_rule_categorize(m)
            if rule_cat:
                SmartExpenseEngine._category_cache[m] = rule_cat
            else:
                merchants_for_ai.append(m)

        if merchants_for_ai and GEMINI_API_KEY:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                You are a financial AI analyzing Indian UPI transaction merchant names.
                Generate a concise, specific, human-readable expense category (1 to 3 words max, Title Case) for each merchant.

                EXEMPLAR CATEGORIES TO USE WHEN RELEVANT:
                - Tea/Snacks/Dhabas -> "Street Food & Snacks"
                - Universities/IITs/Colleges/Xerox/Fees -> "Education & Fees"
                - Medical/Pharmacies/Labs -> "Healthcare & Medicine"
                - Grocery/Kirana/Dairy -> "Groceries & Essentials"
                - Recharge/Electricity/Water -> "Bills & Utilities"

                Respond strictly as a raw JSON object where keys are the EXACT merchant names provided, and values are the generated dynamic category strings. Do not include any markdown formatting like ```json.

                Merchants to categorize:
                {json.dumps(merchants_for_ai)}
                """
                
                response = model.generate_content(prompt)
                
                raw_text = response.text.strip()
                raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.IGNORECASE)
                raw_text = re.sub(r'\s*```$', '', raw_text)
                
                ai_results = json.loads(raw_text)
                
                for m, category in ai_results.items():
                    clean_cat = str(category).strip().title() if category else "General Expense"
                    SmartExpenseEngine._category_cache[m] = clean_cat
                    
            except Exception as e:
                print("\n" + "!"*60)
                print("🚨 GEMINI API FAILED")
                print(f"Error Reason: {e}")
                print("!"*60 + "\n")
                
                for m in merchants_for_ai:
                    SmartExpenseEngine._category_cache[m] = "General Expense"
        else:
            for m in merchants_for_ai:
                SmartExpenseEngine._category_cache[m] = "General Expense"

        df['Category'] = df['Merchant'].map(SmartExpenseEngine._category_cache).fillna("General Expense")

        # Isolation Forest Anomaly Detection
        n_samples = len(df)
        try:
            if n_samples >= 4:
                contamination = min(0.1, max(0.01, 1 / n_samples))
                iso = IsolationForest(contamination=contamination, random_state=42)
                df['is_anomaly'] = iso.fit_predict(df[['Amount']]) == -1
            else:
                df['is_anomaly'] = False
        except Exception:
            df['is_anomaly'] = False

        # Forecast Calculation
        try:
            daily = df.groupby('Date')['Amount'].sum().reset_index()
            daily['Day_Num'] = np.arange(len(daily))
            if len(daily) > 1:
                lr_model = LinearRegression().fit(daily[['Day_Num']], daily['Amount'])
                future_df = pd.DataFrame({'Day_Num': np.arange(len(daily), len(daily) + 7)})
                forecast = [float(x) for x in np.maximum(0, lr_model.predict(future_df)).round(2)]
            else:
                forecast = [float(df['Amount'].mean())] * 7
        except Exception:
            forecast = [0.0] * 7

        df['Amount'] = df['Amount'].astype(float)
        df['is_anomaly'] = df['is_anomaly'].astype(bool)

        return df, forecast