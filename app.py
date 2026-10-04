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

# Residential electricity tariffs for FY 2026-27 (effective 1 April 2026).
# The dashboard uses energy + wheeling + fixed charge, then applies 16% electricity duty.
TARIFFS = {
    "MSEDCL": {
        "utility": "MSEDCL (Mahavitaran)",
        "category": "LT-I(B) Residential",
        "effective_from": "1 April 2026",
        "fixed_schedule": [{"limit": float("inf"), "charge": 130.0}],
        "wheeling_charge": 1.20,
        "duty_pct": 16.0,
        "slabs": [
            {"limit": 100.0, "rate": 4.32, "label": "1–100 kWh"},
            {"limit": 200.0, "rate": 9.40, "label": "101–300 kWh"},
            {"limit": 200.0, "rate": 12.51, "label": "301–500 kWh"},
            {"limit": float("inf"), "rate": 13.97, "label": "Above 500 kWh"}
        ]
    },
    "BEST": {
        "utility": "BEST Undertaking",
        "category": "LT-I(B) Residential",
        "effective_from": "1 April 2026",
        "fixed_schedule": [
            {"limit": 100.0, "charge": 90.0},
            {"limit": 200.0, "charge": 135.0},
            {"limit": 200.0, "charge": 135.0},
            {"limit": float("inf"), "charge": 160.0}
        ],
        "wheeling_charge": 1.82,
        "duty_pct": 16.0,
        "slabs": [
            {"limit": 100.0, "rate": 2.02, "label": "1–100 kWh"},
            {"limit": 200.0, "rate": 5.35, "label": "101–300 kWh"},
            {"limit": 200.0, "rate": 10.04, "label": "301–500 kWh"},
            {"limit": float("inf"), "rate": 11.25, "label": "Above 500 kWh"}
        ]
    },
    "ADANI": {
        "utility": "Adani Electricity Mumbai Limited",
        "category": "LT-I(B) Residential",
        "effective_from": "1 April 2026",
        "fixed_schedule": [
            {"limit": 100.0, "charge": 90.0},
            {"limit": 200.0, "charge": 135.0},
            {"limit": 200.0, "charge": 135.0},
            {"limit": float("inf"), "charge": 160.0}
        ],
        "wheeling_charge": 2.28,
        "duty_pct": 16.0,
        "slabs": [
            {"limit": 100.0, "rate": 2.65, "label": "1–100 kWh"},
            {"limit": 200.0, "rate": 5.85, "label": "101–300 kWh"},
            {"limit": 200.0, "rate": 7.10, "label": "301–500 kWh"},
            {"limit": float("inf"), "rate": 8.35, "label": "Above 500 kWh"}
        ]
    },
    "TATA": {
        "utility": "Tata Power Mumbai",
        "category": "LT-I(B) Residential",
        "effective_from": "1 April 2026",
        "fixed_schedule": [
            {"limit": 100.0, "charge": 90.0},
            {"limit": 200.0, "charge": 135.0},
            {"limit": 200.0, "charge": 135.0},
            {"limit": float("inf"), "charge": 160.0}
        ],
        "wheeling_charge": 2.40,
        "duty_pct": 16.0,
        "slabs": [
            {"limit": 100.0, "rate": 1.90, "label": "1–100 kWh"},
            {"limit": 200.0, "rate": 4.70, "label": "101–300 kWh"},
            {"limit": 200.0, "rate": 9.24, "label": "301–500 kWh"},
            {"limit": float("inf"), "rate": 10.24, "label": "Above 500 kWh"}
        ]
    }
}

with app.app_context():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    db.create_all()

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def safe_int(value, default=1):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

def calculate_bill(monthly_kwh, provider="MSEDCL"):
    """Calculate progressive residential bill using the selected provider's tariff."""
    provider = provider if provider in TARIFFS else "MSEDCL"
    tariff = TARIFFS[provider]
    monthly_kwh = max(0.0, safe_float(monthly_kwh))

    remaining = monthly_kwh
    energy_charge = 0.0
    slab_details = []

    for slab in tariff["slabs"]:
        if remaining <= 0:
            break
        units = min(remaining, slab["limit"])
        charge = units * slab["rate"]
        energy_charge += charge
        slab_details.append({
            "label": slab["label"],
            "units": round(units, 2),
            "rate": slab["rate"],
            "charge": round(charge, 2)
        })
        remaining -= units

    wheeling = monthly_kwh * tariff["wheeling_charge"]
    # Fixed charge is provider- and consumption-slab dependent.
    fixed = tariff["fixed_schedule"][-1]["charge"]
    fixed_remaining = monthly_kwh
    for fixed_slab in tariff["fixed_schedule"]:
        if fixed_remaining <= fixed_slab["limit"]:
            fixed = fixed_slab["charge"]
            break
        fixed_remaining -= fixed_slab["limit"]

    subtotal = energy_charge + wheeling + fixed
    duty = subtotal * (tariff["duty_pct"] / 100.0)
    total = subtotal + duty

    return {
        "provider": provider,
        "utility": tariff["utility"],
        "category": tariff["category"],
        "effective_from": tariff["effective_from"],
        "energy_charge": round(energy_charge, 2),
        "wheeling_charge": round(wheeling, 2),
        "fixed_charge": round(fixed, 2),
        "electricity_duty_pct": tariff["duty_pct"],
        "electricity_duty": round(duty, 2),
        "subtotal": round(subtotal, 2),
        "total": round(total, 2),
        "slab_details": slab_details,
        "note": "Estimate = progressive energy charge + wheeling charge + fixed charge + 16% electricity duty. FAC/PPCA and other bill-specific items are not included unless separately entered."
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/appliances', methods=['GET'])
def get_appliances():
    return jsonify(APPLIANCE_DATA)

@app.route('/api/tariffs', methods=['GET'])
def get_tariffs():
    # Return JSON-safe tariff data (Infinity is not valid JSON for browser JSON.parse).
    result = {}
    for key, tariff in TARIFFS.items():
        result[key] = {
            "utility": tariff["utility"],
            "category": tariff["category"],
            "effective_from": tariff["effective_from"],
            "fixed_schedule": [{"charge": s["charge"]} for s in tariff["fixed_schedule"]],
            "wheeling_charge": tariff["wheeling_charge"],
            "duty_pct": tariff["duty_pct"],
            "slabs": [
                {"label": s["label"], "rate": s["rate"]} for s in tariff["slabs"]
            ]
        }
    return jsonify(result)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json(silent=True) or {}

        appliances = data.get('appliances', [])
        actual_bill = safe_float(data.get('actual_bill', 2150), 2150.0)
        provider = data.get('provider', 'MSEDCL') if data.get('provider', 'MSEDCL') in TARIFFS else 'MSEDCL'
        person_count = max(1, safe_int(data.get('person_count', 4), 4))
        waste_kg = max(0.0, safe_float(data.get('waste_kg', 1.5), 1.5))
        benchmark_water_lpd = 135.0
        month_label = data.get('month_label', datetime.now().strftime('%b %Y'))

        total_daily_kwh = 0.0
        breakdown = {}
        appliance_details = []

        for app_item in appliances:
            app_type = app_item.get('type')
            qty = max(0.0, safe_float(app_item.get('qty', 1), 1.0))
            hrs = max(0.0, safe_float(app_item.get('hrs', 0), 0.0))

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

        tariff_breakdown = calculate_bill(monthly_kwh, provider)
        estimated_bill = tariff_breakdown["total"]

        # Model Accuracy compares the estimated electricity bill with the actual bill.
        if actual_bill > 0:
            error = abs(actual_bill - estimated_bill)
            accuracy_pct = max(0.0, round(100.0 - ((error / actual_bill) * 100.0), 1))
        else:
            accuracy_pct = 100.0

        # Optional water input. If blank/invalid, use the 135 L/person/day reference.
        raw_water = data.get('daily_water_liters', None)
        if raw_water is None or str(raw_water).strip() == '':
            daily_water_liters = person_count * 135.0
        else:
            entered_water = safe_float(raw_water, -1.0)
            daily_water_liters = entered_water if entered_water >= 0 else person_count * 135.0

        monthly_water_liters = round(daily_water_liters * 30, 2)
        per_person_water_lpd = daily_water_liters / person_count

        # Project-defined water-efficiency rubric based on per-person daily use.
        # 135 L/person/day is the reference point; household size itself is not penalized.
        if per_person_water_lpd <= 90:
            w_score = 100
        elif per_person_water_lpd <= 110:
            w_score = 95
        elif per_person_water_lpd <= 135:
            w_score = 90
        elif per_person_water_lpd <= 150:
            w_score = 80
        elif per_person_water_lpd <= 180:
            w_score = 70
        elif per_person_water_lpd <= 200:
            w_score = 60
        else:
            w_score = 40

        monthly_co2_kg = round(monthly_kwh * 0.82, 2)

        # Multi-factor project-defined sustainability score.
        per_person_kwh = monthly_kwh / person_count
        e_score = 100 if per_person_kwh <= 60 else (80 if per_person_kwh <= 120 else (60 if per_person_kwh <= 180 else 40))

        per_person_waste = waste_kg / person_count
        waste_score = 100 if per_person_waste <= 0.4 else (75 if per_person_waste <= 0.8 else 50)
        b_score = accuracy_pct

        overall_eco_score = int((e_score * 0.40) + (w_score * 0.25) + (waste_score * 0.20) + (b_score * 0.15))
        overall_eco_score = max(10, min(100, overall_eco_score))

        # Smart rule-based recommendations.
        suggestions = []
        appliance_details.sort(key=lambda x: x['monthly_kwh'], reverse=True)

        for app_item in appliance_details[:2]:
            pct_share = round((app_item['monthly_kwh'] / max(1, monthly_kwh)) * 100, 1)
            suggested_reduce_hrs = 2 if app_item['hrs'] >= 4 else 1
            new_hrs = max(0, app_item['hrs'] - suggested_reduce_hrs)

            saved_kwh_month = round(((app_item['wattage'] * app_item['qty'] * suggested_reduce_hrs) / 1000.0) * 30, 1)
            new_monthly_kwh = max(0, monthly_kwh - saved_kwh_month)
            new_bill = calculate_bill(new_monthly_kwh, provider)["total"]
            bill_savings = round(estimated_bill - new_bill, 2)

            suggestions.append({
                "badge": "High Savings Opportunity",
                "badge_color": "bg-emerald-100 text-emerald-800 border-emerald-300",
                "title": f"Optimize {app_item['name']} Hours",
                "desc": f"Your **{app_item['name']}** consumes **{pct_share}%** of total home electricity ({app_item['monthly_kwh']} kWh/mo). Reducing usage from **{app_item['hrs']} hrs/day to {new_hrs} hrs/day** saves **~{saved_kwh_month} kWh/month**.",
                "monthly_savings": f"Save ₹{bill_savings} / month"
            })

        if monthly_kwh > 500:
            suggestions.append({
                "badge": "Highest Tariff Slab",
                "badge_color": "bg-rose-100 text-rose-800 border-rose-300",
                "title": "Above 500 kWh Slab Reached",
                "desc": f"Your monthly load is **{monthly_kwh} kWh**. The units above 500 kWh use the the provider's highest residential energy slab plus the applicable wheeling charge.",
                "monthly_savings": "Reduce peak consumption"
            })
        elif monthly_kwh > 300:
            suggestions.append({
                "badge": "Higher Tariff Slab",
                "badge_color": "bg-amber-100 text-amber-800 border-amber-300",
                "title": "301–500 kWh Slab Reached",
                "desc": f"Your monthly load is **{monthly_kwh} kWh**. Units from 301–500 use the the provider's 301–500 kWh energy slab plus the applicable wheeling charge.",
                "monthly_savings": "Reduce consumption"
            })

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

        top_3_appliances = appliance_details[:3]

        return jsonify({
            "estimated_bill": estimated_bill,
            "provider": provider,
            "utility": TARIFFS[provider]["utility"],
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
            "water_details": {
                "daily_liters": round(daily_water_liters, 2),
                "monthly_liters": monthly_water_liters,
                "per_person_lpd": round(per_person_water_lpd, 2),
                "score": w_score
            },
            "tariff_breakdown": tariff_breakdown,
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
        provider = data.get('provider', 'MSEDCL') if data.get('provider', 'MSEDCL') in TARIFFS else 'MSEDCL'

        orig_daily_kwh = 0.0
        sim_daily_kwh = 0.0

        for app_item in appliances:
            wattage = safe_float(app_item.get('wattage', 0))
            qty = safe_float(app_item.get('qty', 1), 1.0)
            orig_hrs = safe_float(app_item.get('orig_hrs', 0))
            sim_hrs = safe_float(app_item.get('sim_hrs', 0))

            orig_daily_kwh += (wattage * qty * orig_hrs) / 1000.0
            sim_daily_kwh += (wattage * qty * sim_hrs) / 1000.0

        orig_monthly_kwh = round(orig_daily_kwh * 30, 2)
        sim_monthly_kwh = round(sim_daily_kwh * 30, 2)

        orig_bill = calculate_bill(orig_monthly_kwh, provider)["total"]
        sim_bill = calculate_bill(sim_monthly_kwh, provider)["total"]

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
