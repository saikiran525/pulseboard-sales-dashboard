# Pulseboard

Pulseboard is a lightweight sales intelligence dashboard built with Flask, Pandas, and vanilla JavaScript. It turns a CSV or Excel sales export into an interactive view of revenue, products, categories, growth, and near-term sales trends.

## Features

- Revenue, units, order count, average order value, and growth metrics
- Monthly revenue trend and three-month forecast
- Product and category performance breakdowns
- Upload support for CSV and Excel workbooks
- Automatic mapping for common sales-column names
- Local, transparent recommendations based on the uploaded data

## Run locally

On Windows, double-click `run_dashboard.bat`. The launcher creates `.venv`, installs the dependencies, starts Flask, and opens the dashboard.

For a manual setup:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000 in a browser. The dashboard starts with built-in sample data, so no upload is required for a first run.

## Deployment

The included `render.yaml` can be used to deploy the app to Render. Connect the GitHub repository to a new Render Blueprint; Render installs the dependencies and starts the app with Gunicorn.

## Data format

The importer identifies a date column, a product or item column, and either a revenue, sales, amount, or price column. `quantity` and `category` are optional. If quantity is missing, each row counts as one transaction; if category is missing, rows are grouped as `Uncategorized`.

Supported aliases include `order_date`, `transaction_date`, `invoice_date`, `item`, `product_name`, `description`, `qty`, `units`, `quantity_ordered`, `unit_price`, `sales`, `total_sales`, `amount`, and `total_revenue`.

The forecast uses a local trend model over the most recent six months. Recommendations are local heuristics calculated from the selected dataset; uploaded files are not sent to an external service.
