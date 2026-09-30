from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ConsumptionLog(db.Model):
    __tablename__ = 'consumption_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    month_name = db.Column(db.String(50), nullable=False)
    daily_kwh = db.Column(db.Float, nullable=False)
    monthly_kwh = db.Column(db.Float, nullable=False)
    estimated_bill = db.Column(db.Float, nullable=False)
    actual_bill = db.Column(db.Float, default=0.0)
    accuracy_pct = db.Column(db.Float, default=100.0)
    monthly_water_liters = db.Column(db.Float, default=0.0)
    daily_waste_kg = db.Column(db.Float, default=0.0)
    monthly_co2_kg = db.Column(db.Float, default=0.0)
    eco_score = db.Column(db.Integer, default=100)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime('%d %b %Y, %H:%M'),
            "month_name": self.month_name,
            "daily_kwh": round(self.daily_kwh, 2),
            "monthly_kwh": round(self.monthly_kwh, 2),
            "estimated_bill": round(self.estimated_bill, 2),
            "actual_bill": round(self.actual_bill, 2),
            "accuracy_pct": round(self.accuracy_pct, 1),
            "monthly_water_liters": round(self.monthly_water_liters, 0),
            "daily_waste_kg": round(self.daily_waste_kg, 1),
            "monthly_co2_kg": round(self.monthly_co2_kg, 2),
            "eco_score": self.eco_score
        }