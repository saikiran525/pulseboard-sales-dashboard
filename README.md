# Pulseboard

A simple sales intelligence dashboard powered by Flask and Pandas. Upload a CSV and get revenue trends, category mix, product performance, growth metrics, and practical AI-style recommendations.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000.

## CSV format

Required columns: `date`, `product`, `quantity`, and either `price` or `revenue`. Optional: `category`.

The app also accepts aliases like `order_date`, `transaction_date`, `item`, `qty`, `units`, `unit_price`, and `sales`.

Recommendations are transparent, local heuristics based on the uploaded data. No file leaves your machine.
