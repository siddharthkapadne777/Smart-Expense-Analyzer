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
    print("⚠ WARNING: OPENROUTER_API_KEY missing. AI categorization disabled.")
    print("!" * 60 + "\n")


MERCHANT_BLOCKLIST = {
    'PAYTM', 'PHONEPE', 'GOOGLEPAY', 'AMAZONPAY', 'BHIM', 'MOBIKWIK',
    'FREECHARGE', 'CRED', 'SLICE', 'JUPITER', 'NAVI', 'RAZORPAY',
    'PAYU', 'CASHFREE', 'INSTAMOJO', 'UPI', 'NEFT', 'IMPS', 'RTGS',
    'NETFLIX', 'SPOTIFY', 'SWIGGY', 'ZOMATO', 'BLINKIT', 'ZEPTO',
    'AMAZON', 'FLIPKART', 'MYNTRA', 'UBER', 'OLA', 'RAPIDO',
}

MERCHANT_SUFFIXES = {
    'ENTERPRISES', 'AGENCY', 'TRADERS', 'TRADING', 'MEDICAL', 'MEDICALS',
    'STORE', 'STORES', 'MART', 'MALL', 'CENTER', 'CENTRE', 'SERVICES',
    'CLINIC', 'HOTEL', 'CAFE', 'RESTAURANT', 'TEA', 'STALL', 'SHOP',
    'STATIONERY', 'XEROX', 'SNACKS', 'BHELPURI', 'BAKERY', 'DAIRY',
    'COLLEGE', 'SCHOOL', 'INSTITUTE', 'ACADEMY', 'UNIVERSITY',
    'PHARMACY', 'PHARMACIES', 'CHEMIST', 'DRUGSTORE', 'HOSPITAL',
    'LAB', 'LABS', 'DIAGNOSTICS', 'PATHOLOGY',
    'BAZAR', 'BAZAAR', 'EMPORIUM', 'SUPPLIERS',
    'TECH', 'SOLUTIONS', 'SYSTEMS', 'INFOTECH', 'PARK', 'PLAZA',
    'MEALS', 'FOODS', 'FOOD', 'KITCHEN', 'CATERERS', 'DHABA', 'DHABHA',
    'SWEETS', 'NAMKEEN', 'JUICE', 'COFFEE', 'PIZZA', 'BIRYANI',
}

AI_BATCH_SIZE = 25
AI_MAX_RETRIES = 3
AI_TIMEOUT = 45


class SmartExpenseEngine:

    # ============================================================
    # Rule-based categorizer — now returns (category, confidence)
    #   confidence='high'   → trust it, skip AI
    #   confidence='low'    → send to AI for a second opinion
    #   returns (None, None) → no rule matched, definitely send to AI
    # ============================================================
    @staticmethod
    def fast_rule_categorize(merchant_name):
        name = str(merchant_name).strip().upper()

        def match(keywords):
            pattern = r'\b(?:' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            return bool(re.search(pattern, name))

        # -------- HIGH CONFIDENCE (keyword hits) --------
        if match(['PHARMACY', 'PHARMACIES', 'MEDICAL', 'MEDICALS', 'CLINIC',
                  'HOSPITAL', 'DIAGNOSTIC', 'DIAGNOSTICS', 'PATHOLOGY',
                  'CHEMIST', 'DRUGSTORE', 'APOLLO', 'MEDPLUS', 'NETMEDS',
                  'PHARMEASY', '1MG', 'TATA1MG']):
            return 'Healthcare & Medicine', 'high'

        if match(['NETFLIX', 'SPOTIFY', 'PVR', 'INOX', 'HOTSTAR', 'STEAM',
                  'PRIME', 'SONYLIV', 'YOUTUBE']):
            return 'Entertainment & Media', 'high'

        if match(['SWIGGY', 'ZOMATO', 'RESTO', 'RESTAURANT', 'CAFE', 'MEALS',
                  'FOODS', 'KITCHEN', 'CATERERS', 'DHABA', 'MCDONALDS',
                  'KFC', 'BURGER', 'DOMINOS', 'PIZZA', 'BIRYANI', 'SWEETS']):
            return 'Food & Dining', 'high'

        if match(['BLINKIT', 'ZEPTO', 'INSTAMART', 'BIGBASKET', 'DMART',
                  'GROFERS', 'JIOMART', 'KIRANA']):
            return 'Groceries & Essentials', 'high'

        if match(['AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'MEESHO', 'NYKAA']):
            return 'Shopping', 'high'

        if match(['PETROL', 'UBER', 'OLA', 'IRCTC', 'METRO', 'RAPIDO',
                  'INDIANOIL', 'HPCL', 'BPCL', 'FUEL', 'PUMP']):
            return 'Travel & Fuel', 'high'

        if match(['RECHARGE', 'ELECTRICITY', 'BROADBAND', 'AIRTEL', 'JIO',
                  'VODAFONE', 'BESCOM', 'MSEB', 'WATER']):
            return 'Bills & Utilities', 'high'

        if match(['COLLEGE', 'SCHOOL', 'INSTITUTE', 'ACADEMY', 'UNIVERSITY',
                  'IIT', 'NIT', 'XEROX', 'STATIONERY', 'TUITION', 'FEES']):
            return 'Education & Fees', 'high'

        # -------- KNOWN GATEWAYS — never peer transfer, but ambiguous --------
        if any(tok in MERCHANT_BLOCKLIST for tok in name.split()):
            return None, None
        if name in MERCHANT_BLOCKLIST:
            return None, None

        # -------- LOW CONFIDENCE: business suffix present --------
        words = name.split()
        if any(w in MERCHANT_SUFFIXES for w in words):
            # It's a business, but we don't know which type → AI's job
            return None, None

        # -------- LOW CONFIDENCE: peer-transfer guess --------
        # 2–3 alphabetic words, no business suffix → *probably* a person.
        # But PUNE MEALS also fits this pattern, so we mark it LOW confidence
        # and let the AI override it.
        if 2 <= len(words) <= 3 and all(w.isalpha() for w in words):
            return 'Peer Transfer', 'low'

        return None, None

    # ============================================================
    # CSV parsing
    # ============================================================
    @staticmethod
    def _decode_file_bytes(raw_bytes):
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
        # Categorization cascade:
        #   1. User override (DB cache, source='user')    ← highest priority
        #   2. High-confidence rule
        #   3. AI cache (source='ai')
        #   4. Low-confidence rule (Peer Transfer)
        #   5. Batch AI call
        # ============================================================
        from .models import MerchantCategory

        unique_merchants = df['Merchant'].unique().tolist()

        db_cache = {
            m.merchant: (m.category, m.source)
            for m in MerchantCategory.objects.filter(merchant__in=unique_merchants)
        }

        resolved = {}       # merchant -> category
        ai_queue = []       # merchants to send to LLM

        for m in unique_merchants:
            # 1. User override always wins
            if m in db_cache and db_cache[m][1] == 'user':
                resolved[m] = db_cache[m][0]
                continue

            # 2. High-confidence rule
            rule_cat, confidence = SmartExpenseEngine.fast_rule_categorize(m)
            if rule_cat and confidence == 'high':
                resolved[m] = rule_cat
                MerchantCategory.objects.update_or_create(
                    merchant=m,
                    defaults={'category': rule_cat, 'source': 'rule'},
                )
                continue

            # 3. AI cache
            if m in db_cache and db_cache[m][1] == 'ai':
                resolved[m] = db_cache[m][0]
                continue

            # 4/5. Low-confidence → queue for AI, but keep as fallback
            if rule_cat and confidence == 'low':
                resolved[m] = rule_cat   # provisional
            ai_queue.append(m)

        # Batch AI call for everything in the queue
        if ai_queue and OPENROUTER_API_KEY:
            ai_results = SmartExpenseEngine._categorize_with_ai_batched(ai_queue)
            for m, cat in ai_results.items():
                if cat and cat != 'General Expense':
                    resolved[m] = cat   # AI overrides the low-confidence guess
                    MerchantCategory.objects.update_or_create(
                        merchant=m,
                        defaults={'category': cat, 'source': 'ai'},
                    )

        # Final fallback
        for m in unique_merchants:
            resolved.setdefault(m, 'General Expense')

        df['Category'] = df['Merchant'].map(resolved).fillna('General Expense')

        # Anomaly detection
        df['is_anomaly'] = SmartExpenseEngine._detect_anomalies(df)

        df['Amount'] = df['Amount'].astype(float)
        df['is_anomaly'] = df['is_anomaly'].astype(bool)

        return df

    # ============================================================
    # OpenRouter batching
    # ============================================================
    @staticmethod
    def _categorize_with_ai_batched(merchants):
        results = {}
        for i in range(0, len(merchants), AI_BATCH_SIZE):
            batch = merchants[i:i + AI_BATCH_SIZE]
            results.update(SmartExpenseEngine._call_openrouter_batch(batch))
        return results

    @staticmethod
    def _call_openrouter_batch(merchants):
        prompt = (
            "You are a financial AI analyzing Indian UPI transaction merchant names.\n"
            "For each merchant, output a concise, specific, human-readable expense category "
            "(1 to 3 words max, Title Case).\n\n"
            "CRITICAL CLASSIFICATION RULES:\n"
            "- Business names → categorize as that business type.\n"
            "  Examples: 'PUNE MEALS' → 'Food & Dining'\n"
            "            'CARE CORNER PHARMACY' → 'Healthcare & Medicine'\n"
            "            'SHARMA KIRANA' → 'Groceries & Essentials'\n"
            "            'MEESHO' → 'Shopping'\n"
            "- Only use 'Peer Transfer' when the name is clearly a PERSON'S NAME:\n"
            "  - Indian first name alone: 'SATISH', 'RAHUL', 'PRIYA'\n"
            "  - Indian first + last: 'RAHUL SHARMA', 'KASALE MANOHAR VISHN'\n"
            "- NEVER classify a business name as 'Peer Transfer'.\n"
            "  Even ambiguous business names like 'PUNE MEALS' are Food, not Peer Transfer.\n\n"
            "EXEMPLAR CATEGORIES:\n"
            "- Tea/Snacks/Dhabas → 'Street Food & Snacks'\n"
            "- Universities/IITs/Colleges/Xerox/Fees → 'Education & Fees'\n"
            "- Medical/Pharmacies/Labs/Clinic → 'Healthcare & Medicine'\n"
            "- Grocery/Kirana/Dairy → 'Groceries & Essentials'\n"
            "- Recharge/Electricity/Water → 'Bills & Utilities'\n"
            "- Restaurant/Cafe/Meals/Food → 'Food & Dining'\n\n"
            "Respond ONLY with a valid, raw JSON object where keys are the EXACT "
            "merchant names provided, and values are category strings. "
            "No markdown, no code fences, no conversational text.\n\n"
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
                raw_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_text, flags=re.MULTILINE)

                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if not json_match:
                    raise ValueError("AI response did not contain valid JSON.")

                ai_results = json.loads(json_match.group(0))
                cleaned = {}
                for m in merchants:
                    cat = ai_results.get(m)
                    cleaned[m] = str(cat).strip().title() if cat else 'General Expense'
                return cleaned

            except Exception as e:
                last_error = e
                print(f"⚠ OpenRouter attempt {attempt}/{AI_MAX_RETRIES} failed: {e}")
                if attempt < AI_MAX_RETRIES:
                    time.sleep(2 ** attempt)

        print(f"🚨 OpenRouter permanently failed: {last_error}")
        return {m: 'General Expense' for m in merchants}

    # ============================================================
    # Anomaly detection
    # ============================================================
    @staticmethod
    def _detect_anomalies(df):
        n = len(df)
        if n < 4:
            return pd.Series([False] * n, index=df.index)

        try:
            work = df.copy()
            work['log_amount'] = np.log1p(work['Amount'])
            merchant_median = work.groupby('Merchant')['Amount'].transform('median')
            work['ratio_to_merchant_median'] = (
                work['Amount'] / merchant_median.replace(0, np.nan)
            ).fillna(1.0)

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