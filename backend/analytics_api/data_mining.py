import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

def run_kmeans_pca(transactions):
    """Groups merchants using K-Means and reduces dimensions with PCA."""
    if len(transactions) < 5:
        return []

    # 1. Vectorize merchant names (Text -> Numbers)
    merchants = [str(tx.merchant) for tx in transactions]
    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    X = vectorizer.fit_transform(merchants).toarray()

    # 2. K-Means Clustering (group into up to 5 categories)
    n_clusters = min(5, len(merchants))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(X)
    
    # 3. PCA to reduce to 2D for a scatter plot
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)

    # Return data for the frontend Scatter Plot
    scatter_data = []
    for i in range(len(merchants)):
        scatter_data.append({
            "merchant": merchants[i],
            "cluster": int(kmeans.labels_[i]),
            "x": float(X_pca[i, 0]),
            "y": float(X_pca[i, 1]),
            "amount": float(transactions[i].amount)
        })
    return scatter_data

def run_apriori(transactions):
    """Finds associations between categories (e.g., Coffee & Transport)."""
    if not transactions:
        return []

    # Group by date to find things bought on the same day
    daily_categories = {}
    for tx in transactions:
        date_str = str(tx.date)
        if date_str not in daily_categories:
            daily_categories[date_str] = set()
        daily_categories[date_str].add(tx.category)

    dataset = [list(cats) for cats in daily_categories.values()]
    if len(dataset) < 2:
        return []

    te = TransactionEncoder()
    te_ary = te.fit(dataset).transform(dataset)
    df = pd.DataFrame(te_ary, columns=te.columns_)

    # Apriori Algorithm
    frequent_itemsets = apriori(df, min_support=0.1, use_colnames=True)
    if frequent_itemsets.empty:
        return []

    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5)
    rules = rules[rules['lift'] > 1.0].sort_values(by='confidence', ascending=False)

    insights = []
    for _, row in rules.head(5).iterrows():
        antecedent = ", ".join(list(row['antecedents']))
        consequent = ", ".join(list(row['consequents']))
        insights.append({
            "rule": f"If you spend on {antecedent}",
            "result": f"You likely also spend on {consequent}",
            "confidence": round(row['confidence'] * 100, 1)
        })
    return insights