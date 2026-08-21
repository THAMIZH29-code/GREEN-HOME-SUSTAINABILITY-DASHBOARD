from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from models import db, ConsumptionLog, APPLIANCE_WATTAGE
from datetime import datetime

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sustainability.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def calculate_slab_cost(units, base_rate):
    """Calculates realistic tier-based electricity tariff cost."""
    if units <= 100:
        return units * (base_rate * 0.7)
    elif units <= 300:
        return (100 * (base_rate * 0.7)) + ((units - 100) * base_rate)
    else:
        return (100 * (base_rate * 0.7)) + (200 * base_rate) + ((units - 300) * (base_rate * 1.3))

def generate_sustainability_recommendations(breakdown, daily_kwh, water_liters, waste_kg):
    recs = []
    
    # Check High Wattage Heating/Cooling Loads
    ac_kwh = sum(v for k, v in breakdown.items() if "Air Conditioner" in k)
    if ac_kwh > 100:
        recs.append({
            "category": "Energy Efficiency",
            "title": "Optimize Thermostat Settings",
            "desc": f"Air conditioning accounts for ~{round(ac_kwh, 1)} kWh/month. Setting the thermostat between 24°C–26°C reduces cooling load by up to 18%."
        })
        
    water_heater_kwh = sum(v for k, v in breakdown.items() if "Water Heater" in k or "Geyser" in k)
    if water_heater_kwh > 50:
        recs.append({
            "category": "Thermal Load",
            "title": "Geyser Duty Cycle Optimization",
            "desc": "Water heaters draw high peak wattage (2000W). Switch off units after 15-20 minutes of heating rather than leaving them continuously powered."
        })

    # Check Lighting/Fan Efficiency
    legacy_load = sum(v for k, v in breakdown.items() if "Standard" in k or "Fluorescent" in k)
    if legacy_load > 0:
        recs.append({
            "category": "Hardware Upgrade",
            "title": "Migrate to BLDC & LED Standards",
            "desc": "Replacing traditional ceiling fans (75W) with BLDC fans (28W) and standard tubes with LEDs cuts lighting/fan power draw by 60%."
        })

    # Water Footprint Evaluation
    if water_liters > 12000:
        recs.append({
            "category": "Water Conservation",
            "title": "Low-Flow Tap Aerators",
            "desc": "Monthly household water demand is above baseline benchmark. Installing sink aerators reduces tap water flow rate without altering usability."
        })

    # Waste Management Evaluation
    if waste_kg > 2.0:
        recs.append({
            "category": "Waste Management",
            "title": "Segregation & Organic Composting",
            "desc": "Daily solid waste generation is above 2.0 kg. Segregating organic wet waste for home composting reduces municipal landfill methane impact."
        })

    if not recs:
        recs.append({
            "category": "Sustainability Status",
            "title": "Optimized Resource Profile",
            "desc": "Your baseline electricity, water, and waste footprints are well within sustainable residential benchmarks."
        })
        
    return recs

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/appliances', methods=['GET'])
def get_appliances():
    return jsonify(APPLIANCE_WATTAGE)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json(force=True) or {}
    
    appliances = data.get('appliances', [])
    rate_per_unit = float(data.get('rate_per_unit', 8.5))
    fixed_charge = float(data.get('fixed_charge', 100.0))
    actual_bill = float(data.get('actual_bill', 0.0))
    person_count = int(data.get('person_count', 4))
    waste_kg = float(data.get('waste_kg', 1.5))
    month_label = data.get('month_label', datetime.now().strftime('%b %Y'))

    daily_kwh = 0.0
    appliance_kwh_breakdown = {}

    for item in appliances:
        app_type = item.get('type', '')
        qty = float(item.get('qty', 0))
        hrs = float(item.get('hrs', 0))
        
        # Support user manual entry for wattage & custom name
        if app_type == "Custom Appliance":
            wattage = float(item.get('custom_wattage', 100))
            display_name = item.get('custom_name', 'Custom Appliance')
            if not display_name.strip():
                display_name = "Custom Appliance"
        else:
            wattage = APPLIANCE_WATTAGE.get(app_type, 0)
            display_name = app_type

        item_daily_kwh = (wattage * qty * hrs) / 1000.0
        daily_kwh += item_daily_kwh
        
        monthly_app_kwh = round(item_daily_kwh * 30, 2)
        appliance_kwh_breakdown[display_name] = appliance_kwh_breakdown.get(display_name, 0) + monthly_app_kwh

    monthly_kwh = daily_kwh * 30
    energy_cost = calculate_slab_cost(monthly_kwh, rate_per_unit)
    estimated_bill = energy_cost + fixed_charge

    # Model Accuracy Percent Calculation
    accuracy_pct = 0.0
    if actual_bill > 0:
        diff = abs(actual_bill - estimated_bill)
        accuracy_pct = max(0.0, 100.0 - ((diff / actual_bill) * 100.0))

    # Water Footprint: 135 LPD benchmark per capita
    monthly_water_liters = person_count * 135 * 30
    
    # Environmental CO2 Footprint Calculation
    monthly_co2 = (monthly_kwh * 0.85) + (monthly_water_liters * 0.001) + (waste_kg * 30 * 1.2)

    # Eco-Score Algorithm (Base 100)
    eco_score = 100
    if daily_kwh > 15:
        eco_score -= min(35, int((daily_kwh - 15) * 2))
    if (person_count * 135) > 500:
        eco_score -= min(25, int(((person_count * 135) - 500) * 0.05))
    if waste_kg > 2.0:
        eco_score -= min(20, int((waste_kg - 2.0) * 10))
    eco_score = max(10, eco_score)

    # Dynamic Recommendation Engine
    suggestions = generate_sustainability_recommendations(appliance_kwh_breakdown, daily_kwh, monthly_water_liters, waste_kg)

    # Persist log entry to database
    log = ConsumptionLog(
        month_name=month_label,
        daily_kwh=round(daily_kwh, 2),
        monthly_kwh=round(monthly_kwh, 2),
        estimated_bill=round(estimated_bill, 2),
        actual_bill=round(actual_bill, 2),
        accuracy_pct=round(accuracy_pct, 1),
        monthly_water_liters=round(monthly_water_liters, 0),
        daily_waste_kg=waste_kg,
        monthly_co2_kg=round(monthly_co2, 2),
        eco_score=eco_score
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "status": "success",
        "monthly_kwh": round(monthly_kwh, 2),
        "estimated_bill": round(estimated_bill, 2),
        "actual_bill": round(actual_bill, 2),
        "accuracy_pct": round(accuracy_pct, 1),
        "monthly_water_liters": round(monthly_water_liters, 0),
        "daily_waste_kg": waste_kg,
        "monthly_co2_kg": round(monthly_co2, 2),
        "eco_score": eco_score,
        "appliance_breakdown": appliance_kwh_breakdown,
        "suggestions": suggestions
    })

@app.route('/api/history', methods=['GET'])
def history():
    logs = ConsumptionLog.query.order_by(ConsumptionLog.id.asc()).all()
    return jsonify([l.to_dict() for l in logs])

def seed_sample_data():
    if ConsumptionLog.query.count() == 0:
        samples = [
            ConsumptionLog(month_name="May 2026", daily_kwh=18.5, monthly_kwh=555, estimated_bill=4817, actual_bill=4950, accuracy_pct=97.3, monthly_water_liters=16200, daily_waste_kg=1.8, monthly_co2_kg=512.5, eco_score=82),
            ConsumptionLog(month_name="Jun 2026", daily_kwh=16.2, monthly_kwh=486, estimated_bill=4231, actual_bill=4300, accuracy_pct=98.4, monthly_water_liters=16200, daily_waste_kg=1.5, monthly_co2_kg=455.1, eco_score=88),
            ConsumptionLog(month_name="Jul 2026", daily_kwh=14.0, monthly_kwh=420, estimated_bill=3620, actual_bill=3500, accuracy_pct=96.6, monthly_water_liters=16200, daily_waste_kg=1.4, monthly_co2_kg=398.2, eco_score=91)
        ]
        db.session.bulk_save_objects(samples)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_sample_data()
    app.run(host='0.0.0.0', port=5000, debug=True)