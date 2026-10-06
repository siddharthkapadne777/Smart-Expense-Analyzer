import io
import os
import re
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

import chardet
from dotenv import load_dotenv

from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    print("\n" + "!" * 60)
    print("⚠ WARNING: OPENROUTER_API_KEY is missing. AI categorization will fall back to General Expense.")
    print("!" * 60 + "\n")


# Single-word merchants that must NOT be misclassified as "Peer Transfer".
# These are payment gateways / wallets / known brand tokens.
MERCHANT_BLOCKLIST = {
    'PAYTM', 'PHONEPE', 'GOOGLEPAY', 'AMAZONPAY', 'BHIM', 'MOBIKWIK',
    'FREECHARGE', 'CRED', 'SLICE', 'JUPITER', 'NAVI', 'RAZORPAY',
    'PAYU', 'CASHFREE', 'INSTAMOJO', 'UPI', 'NEFT', 'IMPS', 'RTGS',
    'NETFLIX', 'SPOTIFY', 'SWIGGY', 'ZOMATO', 'BLINKIT', 'ZEPTO',
    'AMAZON', 'FLIPKART', 'MYNTRA', 'UBER', 'OLA', 'RAPIDO',
}

# Suffixes that indicate a business, not a person.
MERCHANT_SUFFIXES = {
    'ENTERPRISES', 'AGENCY', 'TRADERS', 'MEDICAL', 'STORE', 'MART',
    'CENTER', 'CENTRE', 'SERVICES', 'CLINIC', 'HOTEL', 'CAFE', 'TEA',
    'STATIONERY', 'XEROX', 'SNACKS', 'BHELPURI', 'BAKERY', 'DAIRY',
    'COLLEGE', 'SCHOOL', 'INSTITUTE', 'ACADEMY', 'SHOP', 'BAZAR',
    'BAZAAR', 'PHARMA', 'HOSPITAL', 'LAB', 'LABS', 'RESTAURANT',
    'TECH', 'SOLUTIONS', 'SYSTEMS', 'INFOTECH', 'PARK', 'PLAZA',
}

AI_BATCH_SIZE = 25
AI_MAX_RETRIES = 3
AI_TIMEOUT = 45


class SmartExpenseEngine:

    # ============================================================
    # 1. Rule-based categorizer (deterministic, runs first)
    # ============================================================
    @staticmethod
    def fast_rule_categorize(merchant_name):
        name = str(merchant_name).strip().upper()

        def match(keywords):
            pattern = r'\b(?:' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            return bool(re.search(pattern, name))

        if match(['NETFLIX', 'SPOTIFY', 'PVR', 'INOX', 'HOTSTAR', 'STEAM',
                  'PRIME', 'SONYLIV', 'YOUTUBE']):
            return 'Entertainment & Media'
        if match(['SWIGGY', 'ZOMATO', 'RESTO', 'CAFE', 'MCDONALDS', 'KFC',
                  'BURGER', 'DOMINOS', 'PIZZA']):
            return 'Food & Dining'
        if match(['BLINKIT', 'ZEPTO', 'INSTAMART', 'BIGBASKET', 'DMART',
                  'GROFERS', 'JIOMART']):
            return 'Groceries & Essentials'
        if match(['AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'MEESHO', 'NYKAA']):
            return 'Shopping'
        if match(['PETROL', 'UBER', 'OLA', 'IRCTC', 'METRO', 'RAPIDO',
                  'INDIANOIL', 'HPCL', 'BPCL', 'FUEL']):
            return 'Travel & Fuel'
        if match(['RECHARGE', 'ELECTRICITY', 'BROADBAND', 'AIRTEL', 'JIO',
                  'VODAFONE', 'BESCOM', 'MSEB']):
            return 'Bills & Utilities'

        # Known gateways / single-word brands must NEVER fall through to
        # Peer Transfer — send them to the LLM instead.
        if any(tok in MERCHANT_BLOCKLIST for tok in name.split()):
            return None
        if name in MERCHANT_BLOCKLIST:
            return None

        # Peer-transfer heuristic: all words are alphabetic AND none are
        # business suffixes AND merchant is not a known gateway.
        words = name.split()
        if 1 <= len(words) <= 3 and all(w.isalpha() for w in words):
            if not any(w in MERCHANT_SUFFIXES for w in words):
                return 'Peer Transfer'

        return None

    # ============================================================
    # 2. CSV parsing (encoding-safe, bank-format tolerant)
    # ============================================================
    @staticmethod
    def _decode_file_bytes(raw_bytes):
        """Try UTF-8 first; fall back to chardet-detected encoding."""
        try:
            return raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            detected = chardet.detect(raw_bytes) or {}
            enc = detected.get('encoding') or 'latin-1'
            return raw_bytes.decode(enc, errors='replace')

    @staticmethod
    def process_upi_csv(file):
        if hasattr(file, 'seek'):
            file.seek(0)

        content = file.read()
        if isinstance(content, bytes):
            content = SmartExpenseEngine._decode_file_bytes(content)

        lines = content.splitlines()
        if not lines:
            raise ValueError("Uploaded file is empty.")

        header_idx = next(
            (idx for idx, line in enumerate(lines[:25])
             if 'date' in line.lower() and 'amount' in line.lower()),
            0,
        )

        processed_lines = [lines[header_idx].strip()]
        for line in lines[header_idx + 1:]:
            if line.strip():
                fixed_line = re.sub(
                    r'([A-Za-z]{3}\s+\d{1,2}),\s*(\d{4})', r'\1 \2', line
                )
                processed_lines.append(fixed_line)

        csv_text = "\n".join(processed_lines)
        df = pd.read_csv(io.StringIO(csv_text))

        if df.empty:
            raise ValueError("CSV table is empty after parsing.")

        df.columns = [str(c).strip() for c in df.columns]

        date_col = next((c for c in df.columns if 'date' in c.lower()), df.columns[0])
        desc_col = next(
            (c for c in df.columns if any(
                x in c.lower() for x in ['details', 'desc', 'particulars', 'payee', 'narration']
            )),
            df.columns[min(2, len(df.columns) - 1)],
        )
        type_col = next((c for c in df.columns if 'type' in c.lower()), None)
        amt_col = next(
            (c for c in df.columns if c.lower().strip() == 'amount'),
            df.columns[-1],
        )
        ref_col = next(
            (c for c in df.columns if any(
                x in c.lower() for x in ['ref', 'utr', 'cheque', 'transaction id', 'txn']
            )),
            None,
        )

        if type_col and type_col in df.columns:
            df = df[df[type_col].astype(str).str.upper().str.contains('DEBIT')].reset_index(drop=True)

        df['Date'] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
        df['Date'] = df['Date'].fillna(datetime.now().strftime('%Y-%m-%d'))
        df['Amount'] = pd.to_numeric(
            df[amt_col].astype(str).str.replace(r'[^0-9.]', '', regex=True),
            errors='coerce',
        ).fillna(0.0).abs()

        def clean_merchant(text):
            t = str(text).strip()
            t = re.sub(r'(?i)^(paid to|paid|payment to)\s+', '', t)
            cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', t).strip().upper()
            return cleaned[:40] if cleaned else 'UPI USER'

        df['Merchant'] = df[desc_col].apply(clean_merchant)
        if ref_col and ref_col in df.columns:
            df['TransactionId'] = df[ref_col].astype(str).str.strip()
        else:
            df['TransactionId'] = ''

        df = df[df['Amount'] > 0].reset_index(drop=True)

        if df.empty:
            raise ValueError("No valid debit transactions found in CSV.")

        # ============================================================
        # 3. Categorization: rules → DB cache → batched LLM
        # ============================================================
        from .models import MerchantCategory  # local import to avoid circular refs

        unique_merchants = df['Merchant'].unique().tolist()
        resolved = {}

        # 3a. Rule engine + DB cache
        merchants_for_ai = []
        db_cache = {
            m.merchant: m.category
            for m in MerchantCategory.objects.filter(merchant__in=unique_merchants)
        }
        for m in unique_merchants:
            rule_cat = SmartExpenseEngine.fast_rule_categorize(m)
            if rule_cat:
                resolved[m] = rule_cat
            elif m in db_cache:
                resolved[m] = db_cache[m]
            else:
                merchants_for_ai.append(m)

        # 3b. LLM fallback in batches
        if merchants_for_ai and OPENROUTER_API_KEY:
            ai_results = SmartExpenseEngine._categorize_with_ai_batched(merchants_for_ai)
            for m, cat in ai_results.items():
                resolved[m] = cat
                MerchantCategory.objects.update_or_create(
                    merchant=m,
                    defaults={'category': cat, 'source': 'ai'},
                )

        # 3c. Any leftovers → General Expense
        for m in merchants_for_ai:
            resolved.setdefault(m, "General Expense")

        df['Category'] = df['Merchant'].map(resolved).fillna("General Expense")

        # ============================================================
        # 4. Anomaly detection (log-transformed, multi-feature)
        # ============================================================
        df['is_anomaly'] = SmartExpenseEngine._detect_anomalies(df)

        # ============================================================
        # 5. Per-row forecast is NOT computed here (dashboard owns it).
        # ============================================================
        df['Amount'] = df['Amount'].astype(float)
        df['is_anomaly'] = df['is_anomaly'].astype(bool)

        return df

    # ============================================================
    # 6. Batched OpenRouter call with retries
    # ============================================================
    @staticmethod
    def _categorize_with_ai_batched(merchants):
        """Chunk merchants into batches, call OpenRouter, aggregate results."""
        results = {}
        for i in range(0, len(merchants), AI_BATCH_SIZE):
            batch = merchants[i:i + AI_BATCH_SIZE]
            batch_result = SmartExpenseEngine._call_openrouter_batch(batch)
            results.update(batch_result)
        return results

    @staticmethod
    def _call_openrouter_batch(merchants):
        prompt = (
            "You are a financial AI analyzing Indian UPI transaction merchant names.\n"
            "Generate a concise, specific, human-readable expense category "
            "(1 to 3 words max, Title Case) for each merchant.\n\n"
            "EXEMPLAR CATEGORIES:\n"
            "- Tea/Snacks/Dhabas -> \"Street Food & Snacks\"\n"
            "- Universities/IITs/Colleges/Xerox/Fees -> \"Education & Fees\"\n"
            "- Medical/Pharmacies/Labs -> \"Healthcare & Medicine\"\n"
            "- Grocery/Kirana/Dairy -> \"Groceries & Essentials\"\n"
            "- Recharge/Electricity/Water -> \"Bills & Utilities\"\n\n"
            "Respond ONLY with a valid, raw JSON object where keys are the EXACT "
            "merchant names provided, and values are category strings. "
            "Do not include markdown, code fences, or any conversational text.\n\n"
            f"Merchants to categorize:\n{json.dumps(merchants)}"
        )

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost:5173"),
            "X-Title": "Smart Expense Analyzer",
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict data-processing AI. Respond ONLY with a "
                        "valid JSON object mapping merchant names to categories."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        last_error = None
        for attempt in range(1, AI_MAX_RETRIES + 1):
            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                    timeout=AI_TIMEOUT,
                )
                response.raise_for_status()
                raw_text = response.json()['choices'][0]['message']['content'].strip()

                # Strip markdown fences if the model ignored instructions
                raw_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_text, flags=re.MULTILINE)

                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if not json_match:
                    raise ValueError("AI response did not contain a valid JSON object.")

                ai_results = json.loads(json_match.group(0))

                # Normalize + filter
                cleaned = {}
                for m in merchants:
                    cat = ai_results.get(m)
                    cleaned[m] = str(cat).strip().title() if cat else "General Expense"
                return cleaned

            except Exception as e:
                last_error = e
                print(f"⚠ OpenRouter batch attempt {attempt}/{AI_MAX_RETRIES} failed: {e}")
                if attempt < AI_MAX_RETRIES:
                    time.sleep(2 ** attempt)

        print(f"🚨 OpenRouter batch permanently failed: {last_error}")
        return {m: "General Expense" for m in merchants}

    # ============================================================
    # 7. Anomaly detection (log-transformed amount + merchant-relative)
    # ============================================================
    @staticmethod
    def _detect_anomalies(df):
        n = len(df)
        if n < 4:
            return pd.Series([False] * n, index=df.index)

        try:
            work = df.copy()
            work['log_amount'] = np.log1p(work['Amount'])

            # merchant-relative feature: how does this spend compare to
            # the median spend for the same merchant?
            merchant_median = work.groupby('Merchant')['Amount'].transform('median')
            work['ratio_to_merchant_median'] = work['Amount'] / merchant_median.replace(0, np.nan)
            work['ratio_to_merchant_median'] = work['ratio_to_merchant_median'].fillna(1.0)

            features = work[['log_amount', 'ratio_to_merchant_median']].values

            contamination = float(np.clip(1.0 / n, 0.02, 0.10))
            iso = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100,
            )
            preds = iso.fit_predict(features)
            return pd.Series(preds == -1, index=df.index)
        except Exception as e:
            print(f"⚠ Anomaly detection failed: {e}")
            return pd.Series([False] * n, index=df.index)