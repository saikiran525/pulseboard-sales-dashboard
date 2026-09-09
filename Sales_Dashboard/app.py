import os
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
COLUMN_ALIASES = {
    "orderdate": "date",
    "order_date": "date",
    "transaction_date": "date",
    "transactiondate": "date",
    "date_of_purchase": "date",
    "invoicedate": "date",
    "invoice_date": "date",
    "item_name": "product",
    "item": "product",
    "product_name": "product",
    "productname": "product",
    "description": "product",
    "sku": "product",
    "stock_code": "product",
    "preferred_category_1": "product",
    "subcategory": "category",
    "segment_category": "category",
    "units": "quantity",
    "qty": "quantity",
    "quantity_ordered": "quantity",
    "quantityordered": "quantity",
    "total_purchases": "quantity",
    "unit_price": "price",
    "unitprice": "price",
    "selling_price": "price",
    "sales": "revenue",
    "total_sales": "revenue",
    "total_revenue": "revenue",
    "total_amount": "revenue",
    "amount": "revenue",
    "total_spent_usd": "revenue",
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
    frame.columns = [str(column).strip().lower().replace(" ", "_").replace("-", "_") for column in frame.columns]
    frame = frame.rename(columns={key: value for key, value in COLUMN_ALIASES.items() if key in frame.columns})
    if "dataset_year" in frame.columns and "date" not in frame.columns:
        frame["date"] = pd.to_datetime(frame["dataset_year"].astype(str) + "-01-01", errors="coerce")

    if "date" not in frame.columns:
        for column in frame.columns:
            parsed_dates = pd.to_datetime(frame[column], errors="coerce")
            if parsed_dates.notna().mean() >= 0.7:
                frame = frame.rename(columns={column: "date"})
                break
    if "product" not in frame.columns:
        for candidate in ("name", "product_id", "item_id"):
            if candidate in frame.columns:
                frame = frame.rename(columns={candidate: "product"})
                break
    if "date" not in frame.columns or "product" not in frame.columns:
        missing = [column for column in ("date", "product") if column not in frame.columns]
        raise ValueError("Could not identify these columns: " + ", ".join(missing) + ". Rename them or provide a dataset with a date and product/name column.")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if "quantity" not in frame.columns:
        frame["quantity"] = 1
    else:
        frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    if "revenue" in frame.columns:
        frame["revenue"] = pd.to_numeric(frame["revenue"], errors="coerce")
    else:
        if "price" not in frame.columns:
            numeric_columns = frame.select_dtypes(include="number").columns.tolist()
            if len(numeric_columns) == 1 and numeric_columns[0] != "quantity":
                frame = frame.rename(columns={numeric_columns[0]: "revenue"})
            else:
                raise ValueError("Could not identify revenue or price. Add a sales, revenue, amount, or price column so sales can be calculated.")
        if "revenue" not in frame.columns:
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


def forecast_revenue(monthly, periods=3):
    """Forecast monthly revenue with a local trend model and a confidence score."""
    history = monthly["revenue"].astype(float).to_numpy()
    if len(history) == 0:
        return [], 0, "Insufficient history"

    window = min(len(history), 6)
    recent = history[-window:]
    if len(recent) == 1:
        slope = 0
        intercept = recent[0]
        baseline = recent[-1]
    else:
        x_values = np.arange(len(recent), dtype=float)
        slope, intercept = np.polyfit(x_values, recent, 1)
        baseline = intercept + slope * (len(recent) - 1)

    fitted = intercept + slope * np.arange(len(recent))
    error = float(np.mean(np.abs(recent - fitted)))
    scale = max(float(np.mean(recent)), 1)
    confidence = int(np.clip(100 - (error / scale * 100), 35, 96))
    last_month = pd.Period(monthly.iloc[-1]["month"], freq="M")
    predictions = []
    for offset in range(1, periods + 1):
        predicted = max(0, baseline + slope * offset)
        predictions.append({"month": str(last_month + offset), "revenue": money(predicted)})
    direction = "rising" if slope > scale * 0.02 else "falling" if slope < -scale * 0.02 else "steady"
    return predictions, confidence, direction


def load_upload(upload):
    extension = Path(upload.filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Upload a CSV or Excel workbook (.xlsx) file.")
    if extension == ".xlsx":
        workbook = pd.ExcelFile(upload)
        for sheet in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet)
            if not frame.dropna(how="all").empty:
                return frame, f"{upload.filename} / {sheet}"
        raise ValueError("The Excel workbook does not contain a non-empty sheet.")
    return pd.read_csv(upload), upload.filename


def analyze(frame):
    frame = prepare_data(frame)
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    monthly = frame.groupby("month", as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum"))
    monthly["growth"] = monthly["revenue"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0) * 100
    products = frame.groupby(["product", "category"], as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum"), orders=("product", "size"))
    products = products.sort_values("revenue", ascending=False)
    categories = frame.groupby("category", as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum")).sort_values("revenue", ascending=False)
    forecast, confidence, forecast_direction = forecast_revenue(monthly)

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
    if forecast:
        next_month = forecast[0]
        if forecast_direction == "rising":
            suggestions.append({"type": "forecast", "title": "Prepare for the next lift", "body": f"The local model projects {money(next_month['revenue'])} in {next_month['month']}. Protect stock for {top_product['product']} and plan capacity before demand arrives."})
        elif forecast_direction == "falling":
            suggestions.append({"type": "warning", "title": "Act before the slowdown", "body": f"The local model points to {money(next_month['revenue'])} in {next_month['month']}. Test a targeted offer and check inventory on your strongest products now."})
        else:
            suggestions.append({"type": "forecast", "title": "Plan around a steady baseline", "body": f"The local model projects {money(next_month['revenue'])} in {next_month['month']}. Use this baseline to evaluate campaign and pricing experiments."})

    return {
        "summary": {"revenue": money(total_revenue), "units": int(frame["quantity"].sum()), "orders": int(len(frame)), "avg_order": money(avg_order), "growth": round(latest_growth, 1), "best_month": best_month["month"], "top_product": top_product["product"]},
        "monthly": [{"month": row.month, "revenue": money(row.revenue), "units": int(row.units), "growth": round(float(row.growth), 1)} for row in monthly.itertuples()],
        "forecast": forecast,
        "forecast_meta": {"confidence": confidence, "direction": forecast_direction, "method": "Recent 6-month trend model"},
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
            frame, source = load_upload(request.files["file"])
        else:
            frame = demo_data()
            source = "Built-in sample dataset"
        result = analyze(frame)
        result["source"] = source
        return jsonify(result)
    except (ValueError, pd.errors.ParserError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
