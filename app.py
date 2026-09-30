import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from models import db, ConsumptionLog

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

APPLIANCE_DATA = {
    "Air Conditioner 1.5 Ton (Inverter - 1500W)": 1500,
    "Air Conditioner 1.5 Ton (Non-Inverter - 1800W)": 1800,
    "Water Heater / Geyser (2000W)": 2000,
    "Water Pump / Submersible (750W)": 750,
    "Washing Machine (650W)": 650,
    "Microwave Oven (1200W)": 1200,
    "Refrigerator (Double Door - 250W)": 250,
    "Refrigerator (Single Door - 100W)": 100,
    "Ceiling Fan (Standard - 75W)": 75,
    "Television (43-inch LED - 75W)": 75,
    "Desktop Computer (200W)": 200,
    "Laptop (65W)": 65,
    "Tube Light (20W)": 20,
    "LED Bulb (9W)": 9,
    "Custom Appliance": 0
}

with app.app_context():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    db.create_all()

def calculate_slab_bill(monthly_kwh, rate_per_unit, fixed_charge):
    """Calculates progressive Indian slab tariff billing"""
    if monthly_kwh <= 100:
        energy_charge = monthly_kwh * (rate_per_unit * 0.7)
    elif monthly_kwh <= 300:
        energy_charge = (100 * rate_per_unit * 0.7) + ((monthly_kwh - 100) * rate_per_unit)
    else:
        energy_charge = (100 * rate_per_unit * 0.7) + (200 * rate_per_unit) + ((monthly_kwh - 300) * rate_per_unit * 1.3)
    return round(energy_charge + fixed_charge, 2)

@app.route('/')
def index():
    return render_template('index.html')

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
        person_count = max(1, int(data.get('person_count', 4)))
        waste_kg = float(data.get('waste_kg', 1.5))
        month_label = data.get('month_label', datetime.now().strftime('%b %Y'))

        total_daily_kwh = 0.0
        breakdown = {}
        appliance_details = []

        for app_item in appliances:
            app_type = app_item.get('type')
            qty = float(app_item.get('qty', 1))
            hrs = float(app_item.get('hrs', 0))

            wattage = APPLIANCE_DATA.get(app_type, 0)
            label_name = app_type.split(' (')[0] if '(' in app_type else app_type

            daily_kwh_item = (wattage * qty * hrs) / 1000.0
            total_daily_kwh += daily_kwh_item
            
            monthly_item_kwh = round(daily_kwh_item * 30, 2)
            breakdown[label_name] = breakdown.get(label_name, 0) + monthly_item_kwh

            if hrs > 0 and wattage > 0:
                appliance_details.append({
                    "name": label_name,
                    "wattage": wattage,
                    "qty": qty,
                    "hrs": hrs,
                    "monthly_kwh": monthly_item_kwh
                })

        monthly_kwh = round(total_daily_kwh * 30, 2)
        estimated_bill = calculate_slab_bill(monthly_kwh, rate_per_unit, fixed_charge)

        # Accuracy Score
        if actual_bill > 0:
            error = abs(actual_bill - estimated_bill)
            accuracy_pct = max(0.0, round(100.0 - ((error / actual_bill) * 100.0), 1))
        else:
            accuracy_pct = 100.0

        # Environmental Standards
        monthly_water_liters = person_count * 135 * 30  # BIS Standard 135 LPD
        monthly_co2_kg = round(monthly_kwh * 0.82, 2)   # Indian CEA Factor: 0.82 kg CO2/kWh

        # Multi-factor Sustainability Score
        per_person_kwh = monthly_kwh / person_count
        e_score = 100 if per_person_kwh <= 60 else (80 if per_person_kwh <= 120 else (60 if per_person_kwh <= 180 else 40))
        w_score = 90
        per_person_waste = waste_kg / person_count
        waste_score = 100 if per_person_waste <= 0.4 else (75 if per_person_waste <= 0.8 else 50)
        b_score = accuracy_pct

        overall_eco_score = int((e_score * 0.40) + (w_score * 0.25) + (waste_score * 0.20) + (b_score * 0.15))
        overall_eco_score = max(10, min(100, overall_eco_score))

        # Smart Data-Driven Recommendations
        suggestions = []
        appliance_details.sort(key=lambda x: x['monthly_kwh'], reverse=True)

        # Top High Power Recommendations
        for app in appliance_details[:2]:
            pct_share = round((app['monthly_kwh'] / max(1, monthly_kwh)) * 100, 1)
            suggested_reduce_hrs = 2 if app['hrs'] >= 4 else 1
            new_hrs = max(0, app['hrs'] - suggested_reduce_hrs)
            
            saved_kwh_month = round(((app['wattage'] * app['qty'] * suggested_reduce_hrs) / 1000.0) * 30, 1)
            new_monthly_kwh = max(0, monthly_kwh - saved_kwh_month)
            new_bill = calculate_slab_bill(new_monthly_kwh, rate_per_unit, fixed_charge)
            bill_savings = round(estimated_bill - new_bill, 2)

            suggestions.append({
                "badge": "High Savings Opportunity",
                "badge_color": "bg-emerald-100 text-emerald-800 border-emerald-300",
                "title": f"Optimize {app['name']} Hours",
                "desc": f"Your **{app['name']}** consumes **{pct_share}%** of total home electricity ({app['monthly_kwh']} kWh/mo). Reducing usage from **{app['hrs']} hrs/day to {new_hrs} hrs/day** saves **~{saved_kwh_month} kWh/month**.",
                "monthly_savings": f"Save ₹{bill_savings} / month"
            })

        if monthly_kwh > 300:
            suggestions.append({
                "badge": "Slab Tariff Alert",
                "badge_color": "bg-amber-100 text-amber-800 border-amber-300",
                "title": "Surcharge Tier Reached (>300 kWh)",
                "desc": f"Your monthly load of **{monthly_kwh} kWh** puts you into the **130% premium tariff bracket**. Reducing consumption below 300 kWh drops your rate base.",
                "monthly_savings": "Avoid Tariff Surcharge"
            })

        # Save to SQLite Database Log
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
            eco_score=overall_eco_score
        )
        db.session.add(log_entry)
        db.session.commit()

        # Extract TOP 3 Highest Consumers for What-If Simulator
        top_3_appliances = appliance_details[:3]

        return jsonify({
            "estimated_bill": estimated_bill,
            "monthly_kwh": monthly_kwh,
            "accuracy_pct": accuracy_pct,
            "monthly_water_liters": monthly_water_liters,
            "monthly_co2_kg": monthly_co2_kg,
            "eco_score": overall_eco_score,
            "score_breakdown": {
                "energy": e_score,
                "water": w_score,
                "waste": waste_score,
                "accuracy": round(b_score, 1)
            },
            "appliance_breakdown": breakdown,
            "top_3_appliances": top_3_appliances,
            "suggestions": suggestions
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
def simulate():
    try:
        data = request.get_json(silent=True) or {}
        appliances = data.get('appliances', [])
        rate_per_unit = float(data.get('rate_per_unit', 8.5))
        fixed_charge = float(data.get('fixed_charge', 100))

        orig_daily_kwh = 0.0
        sim_daily_kwh = 0.0

        for app in appliances:
            wattage = float(app.get('wattage', 0))
            qty = float(app.get('qty', 1))
            orig_hrs = float(app.get('orig_hrs', 0))
            sim_hrs = float(app.get('sim_hrs', 0))

            orig_daily_kwh += (wattage * qty * orig_hrs) / 1000.0
            sim_daily_kwh += (wattage * qty * sim_hrs) / 1000.0

        orig_monthly_kwh = round(orig_daily_kwh * 30, 2)
        sim_monthly_kwh = round(sim_daily_kwh * 30, 2)

        orig_bill = calculate_slab_bill(orig_monthly_kwh, rate_per_unit, fixed_charge)
        sim_bill = calculate_slab_bill(sim_monthly_kwh, rate_per_unit, fixed_charge)

        kwh_saved = round(orig_monthly_kwh - sim_monthly_kwh, 2)
        cost_saved = round(orig_bill - sim_bill, 2)
        co2_reduced = round(kwh_saved * 0.82, 2)

        return jsonify({
            "kwh_saved": kwh_saved,
            "cost_saved": cost_saved,
            "co2_reduced": co2_reduced
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    logs = ConsumptionLog.query.order_by(ConsumptionLog.id.asc()).all()
    return jsonify([log.to_dict() for log in logs])

@app.route('/api/history/delete/<int:log_id>', methods=['DELETE'])
def delete_history(log_id):
    try:
        log = ConsumptionLog.query.get(log_id)
        if log:
            db.session.delete(log)
            db.session.commit()
            return jsonify({"success": True}), 200
        return jsonify({"error": "Log not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)