import os
from flask import Flask, render_template, request, jsonify
from models import db, ConsumptionLog

app = Flask(__name__)

# Absolute database path setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Default appliance wattages dictionary
APPLIANCE_DATA = {
    "Ceiling Fan (Standard - 75W)": 75,
    "Refrigerator (Single Door - 100W)": 100,
    "Refrigerator (Double Door - 250W)": 250,
    "Air Conditioner 1.5 Ton (Inverter - 1500W)": 1500,
    "Air Conditioner 1.5 Ton (Non-Inverter - 1800W)": 1800,
    "LED Bulb (9W)": 9,
    "Tube Light (20W)": 20,
    "Television (43-inch LED - 75W)": 75,
    "Washing Machine (650W)": 650,
    "Water Heater / Geyser (2000W)": 2000,
    "Microwave Oven (1200W)": 1200,
    "Water Pump / Submersible (750W)": 750,
    "Laptop (65W)": 65,
    "Desktop Computer (200W)": 200,
    "Custom Appliance": 0
}

# Auto-create missing database tables
with app.app_context():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# MISSING ENDPOINT FIXED HERE
@app.route('/api/appliances', methods=['GET'])
def get_appliances():
    return jsonify(APPLIANCE_DATA)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json(silent=True) or {}

        appliances = data.get('appliances', [])
        rate_per_unit = float(data.get('rate_per_unit', 8.5))
        fixed_charge = float(data.get('fixed_charge', 100))
        actual_bill = float(data.get('actual_bill', 2150))
        person_count = int(data.get('person_count', 4))
        waste_kg = float(data.get('waste_kg', 1.5))
        month_label = data.get('month_label', 'Aug 2026')

        # 1. Calculate Appliance Energy Breakdown
        total_daily_kwh = 0.0
        breakdown = {}

        for app_item in appliances:
            app_type = app_item.get('type')
            qty = float(app_item.get('qty', 1))
            hrs = float(app_item.get('hrs', 0))

            if app_type == "Custom Appliance":
                wattage = float(app_item.get('custom_wattage', 0))
                label_name = app_item.get('custom_name', 'Custom Item') or 'Custom Item'
            else:
                wattage = APPLIANCE_DATA.get(app_type, 0)
                label_name = app_type.split(' (')[0] if '(' in app_type else app_type

            daily_kwh_item = (wattage * qty * hrs) / 1000.0
            total_daily_kwh += daily_kwh_item
            
            monthly_item_kwh = round(daily_kwh_item * 30, 2)
            breakdown[label_name] = breakdown.get(label_name, 0) + monthly_item_kwh

        monthly_kwh = round(total_daily_kwh * 30, 2)

        # 2. Slab Tariff Electricity Bill Calculation
        if monthly_kwh <= 100:
            energy_charge = monthly_kwh * (rate_per_unit * 0.7)
        elif monthly_kwh <= 300:
            energy_charge = (100 * rate_per_unit * 0.7) + ((monthly_kwh - 100) * rate_per_unit)
        else:
            energy_charge = (100 * rate_per_unit * 0.7) + (200 * rate_per_unit) + ((monthly_kwh - 300) * rate_per_unit * 1.3)

        estimated_bill = round(energy_charge + fixed_charge, 2)

        # 3. Model Accuracy Percentage
        if actual_bill > 0:
            error = abs(actual_bill - estimated_bill)
            accuracy_pct = max(0.0, round(100.0 - ((error / actual_bill) * 100.0), 1))
        else:
            accuracy_pct = 100.0

        # 4. Environmental Footprint Calculations
        monthly_water_liters = person_count * 135 * 30  # BIS Standard: 135 LPD
        monthly_co2_kg = round(monthly_kwh * 0.82, 2)  # Emission factor: 0.82 kg/kWh

        # 5. Eco Score Formula (100 Base)
        score = 100
        if monthly_kwh > (person_count * 75): score -= 15
        if monthly_kwh > (person_count * 120): score -= 20
        if waste_kg > (person_count * 0.5): score -= 10
        eco_score = max(10, score)

        # 6. Generate Dynamic Recommendations
        suggestions = [
            {
                "category": "Energy Saving",
                "title": "Optimize High-Power Appliances",
                "desc": f"Your current usage totals {monthly_kwh} kWh/month. Shifting heavy loads away from peak hours can lower surcharges."
            },
            {
                "category": "Water Management",
                "title": "Water Consumption Tracking",
                "desc": f"Estimated water consumption is {monthly_water_liters:,} Liters/month for {person_count} members."
            }
        ]

        # 7. Save Log to Database
        log_entry = ConsumptionLog(
            month_name=month_label,
            daily_kwh=round(total_daily_kwh, 2),
            monthly_kwh=monthly_kwh,
            estimated_bill=estimated_bill,
            actual_bill=actual_bill,
            accuracy_pct=accuracy_pct,
            monthly_water_liters=monthly_water_liters,
            daily_waste_kg=waste_kg,
            monthly_co2_kg=monthly_co2_kg,
            eco_score=eco_score
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({
            "estimated_bill": estimated_bill,
            "monthly_kwh": monthly_kwh,
            "accuracy_pct": accuracy_pct,
            "monthly_water_liters": monthly_water_liters,
            "monthly_co2_kg": monthly_co2_kg,
            "eco_score": eco_score,
            "appliance_breakdown": breakdown,
            "suggestions": suggestions
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    logs = ConsumptionLog.query.order_by(ConsumptionLog.id.desc()).all()
    return jsonify([log.to_dict() for log in logs])

if __name__ == '__main__':
    app.run(debug=True)