from datetime import datetime, timedelta
import os, math

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sih26033.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(
    title="SIH26033 AgriDirect API",
    version="2.0.0",
    description="Farmer-to-consumer marketplace with price intelligence, demand forecasting and logistics."
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")
    location = Column(String)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crop = Column(String, index=True, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    price_per_kg = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    harvest_date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    delivery_location = Column(String, nullable=False)
    delivery_latitude = Column(Float)
    delivery_longitude = Column(Float)
    status = Column(String, default="PLACED")
    created_at = Column(DateTime, default=datetime.utcnow)

class PriceRecord(Base):
    __tablename__ = "price_records"
    id = Column(Integer, primary_key=True)
    crop = Column(String, index=True, nullable=False)
    market = Column(String, nullable=False)
    price_per_kg = Column(Float, nullable=False)
    source = Column(String, default="demo")
    recorded_at = Column(DateTime, default=datetime.utcnow)

class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)
    delivery_latitude = Column(Float, nullable=False)
    delivery_longitude = Column(Float, nullable=False)
    distance_km = Column(Float)
    estimated_minutes = Column(Integer)
    status = Column(String, default="REQUESTED")
    created_at = Column(DateTime, default=datetime.utcnow)

class DemandObservation(Base):
    __tablename__ = "demand_observations"
    id = Column(Integer, primary_key=True)
    crop = Column(String, index=True, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    observed_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="orders")

Base.metadata.create_all(engine)

def db_session():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def token(user_id):
    return jwt.encode(
        {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY, algorithm=ALGORITHM
    )

def current_user(token_value=Depends(oauth2), db: Session=Depends(db_session)):
    try:
        uid = int(jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])["sub"])
    except (JWTError, TypeError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, uid)
    if not user: raise HTTPException(401, "User not found")
    return user

class Register(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)
    role: str
    location: str | None = None

class ProductIn(BaseModel):
    crop: str
    quantity_kg: float = Field(gt=0)
    price_per_kg: float = Field(gt=0)
    location: str
    latitude: float | None = None
    longitude: float | None = None
    harvest_date: str | None = None

class OrderIn(BaseModel):
    product_id: int
    quantity_kg: float = Field(gt=0)
    delivery_location: str
    delivery_latitude: float | None = None
    delivery_longitude: float | None = None

class PriceIn(BaseModel):
    crop: str
    market: str
    price_per_kg: float = Field(gt=0)
    source: str = "manual"

class DeliveryIn(BaseModel):
    order_id: int
    pickup_latitude: float
    pickup_longitude: float
    delivery_latitude: float
    delivery_longitude: float

@app.get("/")
def root():
    return {"name":"AgriDirect","problem_statement":"SIH26033","version":"2.0.0"}

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/api/auth/register", status_code=201)
def register(x:Register, db:Session=Depends(db_session)):
    if x.role not in ("farmer","customer"):
        raise HTTPException(400,"role must be farmer or customer")
    if db.query(User).filter_by(email=x.email).first():
        raise HTTPException(409,"Email already registered")
    u=User(name=x.name,email=x.email,password_hash=pwd.hash(x.password),role=x.role,location=x.location)
    db.add(u); db.commit(); db.refresh(u)
    return {"id":u.id,"name":u.name,"email":u.email,"role":u.role}

@app.post("/api/auth/login")
def login(form:OAuth2PasswordRequestForm=Depends(), db:Session=Depends(db_session)):
    u=db.query(User).filter_by(email=form.username).first()
    if not u or not pwd.verify(form.password,u.password_hash):
        raise HTTPException(401,"Incorrect email or password")
    return {"access_token":token(u.id),"token_type":"bearer"}

@app.get("/api/me")
def me(u=Depends(current_user)):
    return {"id":u.id,"name":u.name,"email":u.email,"role":u.role,"location":u.location}

@app.post("/api/products", status_code=201)
def create_product(x:ProductIn,u=Depends(current_user),db:Session=Depends(db_session)):
    if u.role!="farmer": raise HTTPException(403,"Only farmers can list produce")
    p=Product(farmer_id=u.id,**x.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return p

@app.get("/api/products")
def products(crop:str|None=None, location:str|None=None, max_price:float|None=None, db:Session=Depends(db_session)):
    q=db.query(Product).filter(Product.quantity_kg>0)
    if crop: q=q.filter(Product.crop.ilike(f"%{crop}%"))
    if location: q=q.filter(Product.location.ilike(f"%{location}%"))
    if max_price is not None: q=q.filter(Product.price_per_kg<=max_price)
    return q.order_by(Product.created_at.desc()).all()

@app.get("/api/products/nearby")
def nearby_products(lat:float,lon:float,radius_km:float=20,crop:str|None=None,db:Session=Depends(db_session)):
    # Haversine distance calculated in Python for portability; use PostGIS ST_DWithin in production.
    q=db.query(Product).filter(Product.quantity_kg>0, Product.latitude.isnot(None), Product.longitude.isnot(None))
    if crop: q=q.filter(Product.crop.ilike(f"%{crop}%"))
    result=[]
    for p in q.all():
        d=haversine(lat,lon,p.latitude,p.longitude)
        if d<=radius_km:
            result.append({"id":p.id,"crop":p.crop,"quantity_kg":p.quantity_kg,"price_per_kg":p.price_per_kg,
                           "location":p.location,"distance_km":round(d,2)})
    return sorted(result,key=lambda x:x["distance_km"])

@app.post("/api/orders", status_code=201)
def order(x:OrderIn,u=Depends(current_user),db:Session=Depends(db_session)):
    if u.role!="customer": raise HTTPException(403,"Only customers can place orders")
    p=db.get(Product,x.product_id)
    if not p: raise HTTPException(404,"Product not found")
    if x.quantity_kg>p.quantity_kg: raise HTTPException(400,"Insufficient quantity")
    p.quantity_kg-=x.quantity_kg
    o=Order(customer_id=u.id,product_id=p.id,quantity_kg=x.quantity_kg,
            total_amount=round(x.quantity_kg*p.price_per_kg,2),
            delivery_location=x.delivery_location,delivery_latitude=x.delivery_latitude,
            delivery_longitude=x.delivery_longitude)
    db.add(o); db.add(DemandObservation(crop=p.crop,quantity_kg=x.quantity_kg)); db.commit(); db.refresh(o)
    return o

@app.get("/api/orders/{order_id}")
def get_order(order_id:int,u=Depends(current_user),db:Session=Depends(db_session)):
    o=db.get(Order,order_id)
    if not o: raise HTTPException(404,"Order not found")
    p=db.get(Product,o.product_id)
    if u.id not in (o.customer_id,p.farmer_id): raise HTTPException(403,"Not authorized")
    return o

@app.post("/api/prices",status_code=201)
def add_price(x:PriceIn,u=Depends(current_user),db:Session=Depends(db_session)):
    if u.role not in ("farmer","admin"): raise HTTPException(403,"Not authorized")
    r=PriceRecord(**x.model_dump()); db.add(r); db.commit(); db.refresh(r); return r

@app.get("/api/prices")
def prices(crop:str|None=None,market:str|None=None,db:Session=Depends(db_session)):
    q=db.query(PriceRecord)
    if crop:q=q.filter(PriceRecord.crop.ilike(f"%{crop}%"))
    if market:q=q.filter(PriceRecord.market.ilike(f"%{market}%"))
    return q.order_by(PriceRecord.recorded_at.desc()).all()

@app.get("/api/price-intelligence/{crop}")
def price_intelligence(crop:str,db:Session=Depends(db_session)):
    rows=db.query(PriceRecord).filter(PriceRecord.crop.ilike(crop)).all()
    if not rows:return {"crop":crop,"records":0,"message":"No price records yet"}
    vals=[r.price_per_kg for r in rows]
    return {"crop":crop,"records":len(vals),"average_price_per_kg":round(sum(vals)/len(vals),2),
            "min_price_per_kg":min(vals),"max_price_per_kg":max(vals),
            "markets":sorted(set(r.market for r in rows))}

@app.get("/api/demand/forecast/{crop}")
def forecast(crop:str,horizon_days:int=7,db:Session=Depends(db_session)):
    obs=db.query(DemandObservation).filter(DemandObservation.crop.ilike(crop)).all()
    if not obs:
        return {"crop":crop,"forecast_demand_kg":100.0*horizon_days/7,
                "model":"baseline","confidence":0.25,"message":"Add historical observations for ML forecasting"}
    total=sum(o.quantity_kg for o in obs)
    days=max(1,(datetime.utcnow()-min(o.observed_at for o in obs)).days+1)
    daily=total/days
    # Baseline forecast; replace with XGBoost/LightGBM/LSTM model after collecting history.
    return {"crop":crop,"forecast_demand_kg":round(daily*horizon_days,2),
            "daily_average_kg":round(daily,2),"horizon_days":horizon_days,
            "model":"rolling-demand-baseline","confidence":0.55}

@app.post("/api/delivery/request",status_code=201)
def delivery(x:DeliveryIn,u=Depends(current_user),db:Session=Depends(db_session)):
    o=db.get(Order,x.order_id)
    if not o: raise HTTPException(404,"Order not found")
    p=db.get(Product,o.product_id)
    if u.id not in (o.customer_id,p.farmer_id): raise HTTPException(403,"Not authorized")
    dkm=haversine(x.pickup_latitude,x.pickup_longitude,x.delivery_latitude,x.delivery_longitude)
    d=Delivery(**x.model_dump(),distance_km=round(dkm,2),estimated_minutes=max(10,math.ceil(dkm/30*60)))
    db.add(d); db.commit(); db.refresh(d)
    return d

@app.get("/api/dashboard/summary")
def dashboard(u=Depends(current_user),db:Session=Depends(db_session)):
    if u.role not in ("admin","farmer"): raise HTTPException(403,"Not authorized")
    return {"active_listings":db.query(Product).filter(Product.quantity_kg>0).count(),
            "orders":db.query(Order).count(),"price_records":db.query(PriceRecord).count(),
            "delivery_requests":db.query(Delivery).count()}

def haversine(lat1,lon1,lat2,lon2):
    r=6371.0
    a=math.sin(math.radians(lat2-lat1)/2)**2+math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(math.radians(lon2-lon1)/2)**2
    return 2*r*math.asin(math.sqrt(a))
