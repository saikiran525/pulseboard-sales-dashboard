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

## Publish once for anytime access

This app includes `render.yaml` for deployment on Render. Push this folder to a GitHub repository, create a new Render Blueprint, and select that repository. Render installs the dependencies and runs the app with Gunicorn, so your computer does not need to stay on. Render will provide a public URL that anyone can open.

The forecast is a local, transparent model based on the most recent six months of revenue. It returns a three-month projection and a confidence score; it is not a guarantee of future sales.

## CSV and Excel format

Required columns: `date`, `product`, `quantity`, and either `price` or `revenue`. Optional: `category`.

The app also accepts aliases like `order_date`, `transaction_date`, `item`, `qty`, `units`, `unit_price`, and `sales`.

Recommendations are transparent, local heuristics based on the uploaded data. No file leaves your machine.
