from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy instance
db = SQLAlchemy()

class ConsumptionLog(db.Model):
    __tablename__ = 'consumption_log'

    id = db.Column(db.Integer, primary_key=True)
    month_name = db.Column(db.String(50), nullable=False)
    daily_kwh = db.Column(db.Float, nullable=False, default=0.0)
    monthly_kwh = db.Column(db.Float, nullable=False, default=0.0)
    estimated_bill = db.Column(db.Float, nullable=False, default=0.0)
    actual_bill = db.Column(db.Float, nullable=False, default=0.0)
    accuracy_pct = db.Column(db.Float, nullable=False, default=0.0)
    monthly_water_liters = db.Column(db.Float, nullable=False, default=0.0)
    daily_waste_kg = db.Column(db.Float, nullable=False, default=0.0)
    monthly_co2_kg = db.Column(db.Float, nullable=False, default=0.0)
    eco_score = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        """Convert database record object to dictionary for API JSON responses."""
        return {
            "id": self.id,
            "month_name": self.month_name,
            "daily_kwh": self.daily_kwh,
            "monthly_kwh": self.monthly_kwh,
            "estimated_bill": self.estimated_bill,
            "actual_bill": self.actual_bill,
            "accuracy_pct": self.accuracy_pct,
            "monthly_water_liters": self.monthly_water_liters,
            "daily_waste_kg": self.daily_waste_kg,
            "monthly_co2_kg": self.monthly_co2_kg,
            "eco_score": self.eco_score
        }

    def __repr__(self):
        return f"<ConsumptionLog {self.month_name} - Score: {self.eco_score}>"