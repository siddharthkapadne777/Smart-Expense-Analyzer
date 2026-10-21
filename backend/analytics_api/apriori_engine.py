import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

def generate_association_rules(transactions):
    """
    Takes a queryset of transactions and finds co-occurring spending habits.
    """
    if not transactions:
        return []

    # 1. Group categories by date (assuming a user might make multiple purchases in a day)
    daily_categories = {}
    for tx in transactions:
        date_str = str(tx.date)
        if date_str not in daily_categories:
            daily_categories[date_str] = set()
        daily_categories[date_str].add(tx.category)

    # 2. Convert to list of lists for mlxtend
    dataset = [list(cats) for cats in daily_categories.values()]
    
    if len(dataset) < 2:
        return [] # Need at least 2 days of data to find associations

    # 3. One-hot encode the transactions
    te = TransactionEncoder()
    te_ary = te.fit(dataset).transform(dataset)
    df = pd.DataFrame(te_ary, columns=te.columns_)

    # 4. Apply Apriori (min_support = 10% of days)
    frequent_itemsets = apriori(df, min_support=0.1, use_colnames=True)
    
    if frequent_itemsets.empty:
        return []

    # 5. Generate rules (min_threshold = 50% confidence)
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5)
    
    # Filter for interesting rules
    rules = rules[rules['lift'] > 1.0].sort_values(by='confidence', ascending=False)

    # 6. Format for the frontend
    insights = []
    for _, row in rules.head(5).iterrows(): # Top 5 rules
        antecedent = ", ".join(list(row['antecedents']))
        consequent = ", ".join(list(row['consequents']))
        confidence = round(row['confidence'] * 100, 1)
        
        insights.append({
            "rule": f"If you spend on {antecedent}",
            "result": f"You likely also spend on {consequent}",
            "confidence": confidence,
            "message": f"On {confidence}% of days when you spent on {antecedent}, you also spent on {consequent}."
        })

    return insights