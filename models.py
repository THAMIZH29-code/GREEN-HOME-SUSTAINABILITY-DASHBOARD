from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Expanded appliance database with varying wattage ranges
APPLIANCE_WATTAGE = {
    # Cooling & Ventilation
    "Ceiling Fan (BLDC Energy Efficient - 28W)": 28,
    "Ceiling Fan (Standard - 75W)": 75,
    "Air Conditioner (1 Ton Standard - 1000W)": 1000,
    "Air Conditioner (1.5 Ton Inverter - 1500W)": 1500,
    "Air Conditioner (2 Ton Heavy Duty - 2200W)": 2200,
    "Air Cooler (180W)": 180,
    
    # Refrigeration & Kitchen
    "Refrigerator (Single Door - 100W)": 100,
    "Refrigerator (Double Door - 250W)": 250,
    "Induction Cooktop (1800W)": 1800,
    "Microwave Oven (1200W)": 1200,
    "Electric Kettle (1500W)": 1500,
    "Mixer Grinder (750W)": 750,
    "Toaster (800W)": 800,
    "Dishwasher (1400W)": 1400,

    # Water Heating & Utility
    "Water Heater / Geyser (2000W)": 2000,
    "Washing Machine (Semi-Automatic - 350W)": 350,
    "Washing Machine (Front Load - 2000W)": 2000,
    "Water Purifier / RO (60W)": 60,

    # Entertainment & Electronics
    "LED TV 32\" (50W)": 50,
    "LED TV 55\" (110W)": 110,
    "Set-Top Box (15W)": 15,
    "Gaming Desktop PC (450W)": 450,
    "Laptop Computer (65W)": 65,
    "Wi-Fi Router (10W)": 10,

    # Lighting & Cleaning
    "LED Bulb (9W)": 9,
    "LED Bulb (14W)": 14,
    "Tube Light (LED - 20W)": 20,
    "Tube Light (Fluorescent - 40W)": 40,
    "Clothes Iron (1000W)": 1000,
    "Vacuum Cleaner (1200W)": 1200,
    "Custom Appliance": 0
}

class ConsumptionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month_name = db.Column(db.String(20), nullable=False)
    daily_kwh = db.Column(db.Float, nullable=False)
    monthly_kwh = db.Column(db.Float, nullable=False)
    estimated_bill = db.Column(db.Float, nullable=False)
    actual_bill = db.Column(db.Float, nullable=False)
    accuracy_pct = db.Column(db.Float, nullable=False)
    monthly_water_liters = db.Column(db.Float, nullable=False)
    daily_waste_kg = db.Column(db.Float, nullable=False)
    monthly_co2_kg = db.Column(db.Float, nullable=False)
    eco_score = db.Column(db.Integer, nullable=False)

    def to_dict(self):
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