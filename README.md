# SIH26033 AgriDirect — production-oriented prototype

## Features
- JWT farmer/customer authentication
- Direct farmer produce marketplace
- Nearby product search using latitude/longitude
- Orders and inventory decrement
- Price intelligence
- Demand forecast API with a replaceable ML baseline
- Delivery distance and ETA
- Admin/farmer dashboard summary
- PostgreSQL/PostGIS-ready Docker deployment
- Swagger/OpenAPI docs

## Run locally without Docker

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Run PostgreSQL + PostGIS

```bash
docker compose up --build
```

Then open `http://127.0.0.1:8000/docs`.

## Demo sequence
1. Register a farmer.
2. Register a customer.
3. Login to receive JWT.
4. Authorize Swagger using `Bearer <token>`.
5. Farmer creates a listing with GPS coordinates.
6. Customer calls `/api/products/nearby`.
7. Customer creates an order.
8. Price records can be added and queried.
9. `/api/demand/forecast/{crop}` gives a baseline demand forecast.
10. Create a delivery request to calculate distance and ETA.

## Turning the prototype into a real product
- Integrate verified agricultural market-price feeds instead of manual/demo price records.
- Add FPO/SHG/farmer KYC workflows.
- Use PostGIS geometry columns and spatial indexes for large-scale location queries.
- Replace the demand baseline with a trained model using historical orders, seasonality, weather, holidays and regional demand.
- Integrate a production maps/routing provider.
- Add payment gateway, refunds, invoices and reconciliation.
- Add notification service (SMS/WhatsApp/push).
- Add audit logs, rate limits, HTTPS, secret management and backups.
- Add role-based admin controls.
