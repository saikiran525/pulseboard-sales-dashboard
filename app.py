from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

REQUIRED_COLUMNS = {"date", "product", "quantity"}
COLUMN_ALIASES = {
    "order_date": "date",
    "transaction_date": "date",
    "item": "product",
    "product_name": "product",
    "units": "quantity",
    "qty": "quantity",
    "unit_price": "price",
    "sales": "revenue",
    "amount": "revenue",
}


def demo_data():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    products = ["Canvas Backpack", "Ceramic Bottle", "Desk Lamp", "Travel Journal", "Wireless Stand"]
    categories = ["Bags", "Home", "Home", "Stationery", "Tech"]
    rows = []
    for date in dates:
        for product, category in zip(products, categories):
            quantity = max(1, int(rng.poisson(4) + (date.month in [11, 12]) * 3))
            price = {"Canvas Backpack": 62, "Ceramic Bottle": 28, "Desk Lamp": 74, "Travel Journal": 18, "Wireless Stand": 46}[product]
            rows.append({"date": date, "product": product, "category": category, "quantity": quantity, "price": price})
    return pd.DataFrame(rows)


def prepare_data(frame):
    frame = frame.copy()
    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    frame = frame.rename(columns={key: value for key, value in COLUMN_ALIASES.items() if key in frame.columns})
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    if "revenue" in frame.columns:
        frame["revenue"] = pd.to_numeric(frame["revenue"], errors="coerce")
    else:
        if "price" not in frame.columns:
            raise ValueError("Add a price or revenue column so sales can be calculated.")
        frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
        frame["revenue"] = frame["quantity"] * frame["price"]
    frame = frame.dropna(subset=["date", "product", "quantity", "revenue"])
    frame = frame[frame["quantity"] > 0]
    if frame.empty:
        raise ValueError("No valid sales rows were found in this file.")
    frame["product"] = frame["product"].astype(str)
    frame["category"] = frame.get("category", pd.Series("Uncategorized", index=frame.index)).fillna("Uncategorized").astype(str)
    return frame


def money(value):
    return round(float(value), 2)


def analyze(frame):
    frame = prepare_data(frame)
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    monthly = frame.groupby("month", as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum"))
    monthly["growth"] = monthly["revenue"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0) * 100
    products = frame.groupby(["product", "category"], as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum"), orders=("product", "size"))
    products = products.sort_values("revenue", ascending=False)
    categories = frame.groupby("category", as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum")).sort_values("revenue", ascending=False)

    total_revenue = frame["revenue"].sum()
    best_month = monthly.loc[monthly["revenue"].idxmax()]
    top_product = products.iloc[0]
    avg_order = total_revenue / frame["product"].count()
    latest_growth = float(monthly.iloc[-1]["growth"]) if len(monthly) > 1 else 0
    suggestions = []
    if latest_growth < 0:
        suggestions.append({"type": "warning", "title": "Re-ignite recent momentum", "body": f"Revenue softened {abs(latest_growth):.1f}% in the latest month. Test a focused offer around {top_product['product']} and review acquisition channels."})
    else:
        suggestions.append({"type": "positive", "title": "Protect your growth curve", "body": f"The latest month is up {latest_growth:.1f}%. Keep inventory ready for {top_product['product']}, your leading revenue driver."})
    suggestions.append({"type": "opportunity", "title": "Lean into your best seller", "body": f"{top_product['product']} contributes {top_product['revenue'] / total_revenue * 100:.1f}% of revenue. Bundle it with a lower-volume item to lift basket size."})
    if len(products) > 1:
        weakest = products.iloc[-1]
        suggestions.append({"type": "insight", "title": "Give the long tail a job", "body": f"{weakest['product']} is the lowest revenue product. Try a small experiment: reposition it, bundle it, or reduce replenishment until demand improves."})
    suggestions.append({"type": "tip", "title": "Watch the next decision", "body": f"Average order value is ${avg_order:,.0f}. Use this as your baseline when judging promotions and cross-sell tests."})

    return {
        "summary": {"revenue": money(total_revenue), "units": int(frame["quantity"].sum()), "orders": int(len(frame)), "avg_order": money(avg_order), "growth": round(latest_growth, 1), "best_month": best_month["month"], "top_product": top_product["product"]},
        "monthly": [{"month": row.month, "revenue": money(row.revenue), "units": int(row.units), "growth": round(float(row.growth), 1)} for row in monthly.itertuples()],
        "products": [{"product": row.product, "category": row.category, "revenue": money(row.revenue), "units": int(row.units), "orders": int(row.orders), "share": round(row.revenue / total_revenue * 100, 1)} for row in products.head(8).itertuples()],
        "categories": [{"category": row.category, "revenue": money(row.revenue), "units": int(row.units)} for row in categories.itertuples()],
        "suggestions": suggestions,
        "rows": len(frame),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def api_analyze():
    try:
        if "file" in request.files and request.files["file"].filename:
            frame = pd.read_csv(request.files["file"])
            source = request.files["file"].filename
        else:
            frame = demo_data()
            source = "Built-in sample dataset"
        result = analyze(frame)
        result["source"] = source
        return jsonify(result)
    except (ValueError, pd.errors.ParserError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
