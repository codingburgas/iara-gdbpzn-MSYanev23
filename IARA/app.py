from flask import Flask, session, redirect, url_for, request, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MSYanev23'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iara.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class FishingTicket(db.Model):
    __tablename__ = 'fishing_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_type = db.Column(db.String(20), nullable=False)    # Седмичен, Месечен, Годишен
    category = db.Column(db.String(20), nullable=False)       # Стандартен, Под 14г, Пенсионер, ТЕЛК
    price = db.Column(db.Float, nullable=False)
    holder_name = db.Column(db.String(100), nullable=False)   # Име на риболовеца
    holder_egn = db.Column(db.String(10), nullable=False)    # ЕГН за проверка на възраст
    telk_number = db.Column(db.String(50), nullable=True)     # Само за категория ТЕЛК
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Inspection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inspector_name = db.Column(db.String(100), nullable=False)
    target_egn = db.Column(db.String(20), nullable=False)
    is_violation = db.Column(db.Boolean, default=False)
    fine_amount = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    date_checked = db.Column(db.DateTime, default=datetime.now)

class FishingVessel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cfr_number = db.Column(db.String(50), unique=True, nullable=False)  # Международен номер
    vessel_name = db.Column(db.String(100), nullable=False)
    call_sign = db.Column(db.String(50), nullable=True)                  # Позивна
    owner_name = db.Column(db.String(150), nullable=False)
    captain_name = db.Column(db.String(150), nullable=False)
    length = db.Column(db.Float, nullable=False)                         # Дължина в метри
    engine_power = db.Column(db.Float, nullable=False)                   # Мощност в kW
    date_registered = db.Column(db.DateTime, default=datetime.now)

class FishingPermit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permit_number = db.Column(db.String(50), unique=True, nullable=False)
    vessel_id = db.Column(db.Integer, db.ForeignKey('fishing_vessel.id'), nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    allowed_gear = db.Column(db.String(200), nullable=False)  # Разрешени риболовни уреди
    is_active = db.Column(db.Boolean, default=True)           # Може да бъде отнето при нарушение
    date_issued = db.Column(db.DateTime, default=datetime.now)

    # Връзка към кораба, за да извличаме лесно неговите данни в шаблона
    vessel = db.relationship('FishingVessel', backref=db.backref('permits', lazy=True))

class FishingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vessel_id = db.Column(db.Integer, db.ForeignKey('fishing_vessel.id'), nullable=False)
    trip_start = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    gear_used = db.Column(db.String(100), nullable=False)
    fish_species = db.Column(db.String(100), nullable=False)
    fish_quantity_kg = db.Column(db.Float, nullable=False)
    date_submitted = db.Column(db.DateTime, default=datetime.now)

    vessel = db.relationship('FishingVessel', backref=db.backref('logs', lazy=True))

class FishLanding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('fishing_log.id'), nullable=False)
    landing_port = db.Column(db.String(100), nullable=False)        
    unloaded_species = db.Column(db.String(100), nullable=False)    
    weight_kg = db.Column(db.Float, nullable=False)                 
    transport_vehicle = db.Column(db.String(50), nullable=True)     
    destination_shop = db.Column(db.String(150), nullable=False)    
    date_landed = db.Column(db.DateTime, default=datetime.now)

    log = db.relationship('FishingLog', backref=db.backref('landings', lazy=True))

class EnforcementAct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    act_number = db.Column(db.String(50), unique=True, nullable=False)
    violator_type = db.Column(db.String(50), nullable=False)        # Кораб, Магазин, Хладилен камион, Любител
    violator_name = db.Column(db.String(150), nullable=False)       # Име на лицето или фирмата/кораба
    violation_details = db.Column(db.Text, nullable=False)          # Описание на нарушението
    fine_amount = db.Column(db.Float, nullable=False)               # Размер на глобата в лева
    status = db.Column(db.String(50), default="Издаден")            # Издаден, Платен, Обжалван
    date_issued = db.Column(db.DateTime, default=datetime.now)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # Инспектор, Капитан, Любител
    full_name = db.Column(db.String(100), nullable=False)

@app.route('/')
def index():
    return render_template("home.html")    
    
@app.route('/tickets')
def tickets_page():
    return render_template("tickets.html")
@app.route('/register')
def register_page():
    # Изтегляме всички записи от таблицата fishing_tickets, подредени по дата на създаване (най-новите най-отгоре)
    all_tickets = FishingTicket.query.order_by(FishingTicket.created_at.desc()).all()
    
    # Изпращаме променливата all_tickets към HTML файла под името 'tickets'
    return render_template("register.html", tickets=all_tickets)

@app.route('/buy-ticket', methods=['POST'])
def buy_ticket():
    name = request.form.get('holder_name')
    egn = request.form.get('holder_egn')
    t_type = request.form.get('ticket_type')
    category = request.form.get('category')
    telk = request.form.get('telk_number')

    # Изчисляване на цената
    base_prices = {"Седмичен": 4.0, "Месечен": 8.0, "Годишен": 25.0}
    price = base_prices.get(t_type, 0.0)

    if category in ["Под 14г", "ТЕЛК"]:
        price = 0.0
    elif category == "Пенсионер":
        price = price * 0.5

    # Изчисляване на валидността с чист datetime.now()
    start_date = datetime.now()
    if t_type == "Седмичен":
        end_date = start_date + timedelta(days=7)
    elif t_type == "Месечен":
        end_date = start_date + timedelta(days=30)
    else:
        end_date = start_date + timedelta(days=365)

    # Подсигуряваме се, че ако telk е празен стринг, в базата се записва None
    if not telk or category != "ТЕЛК":
        telk = None

    try:
        new_ticket = FishingTicket(
            ticket_type=t_type,
            category=category,
            price=price,
            holder_name=name,
            holder_egn=egn,
            telk_number=telk,
            valid_from=start_date,
            valid_to=end_date
        )

        db.session.add(new_ticket)
        db.session.commit()
        
        flash(f"Билетът на {name} беше издаден успешно! Цена: {price:.2f} лв.")
    except Exception as e:
        db.session.rollback()
        # Това ще отпечата точната грешка в терминала, ако записът се провали
        print("ГРЕШКА ПРИ ЗАПИС В БАЗАТА:", str(e))
        flash("Възникна грешка при запис в базата данни.")
        return redirect(url_for('tickets_page'))

    return redirect(url_for('tickets_page'))


@app.route('/inspections', methods=['GET', 'POST'])
def inspections_page():
    if request.method == 'POST':
        inspector = request.form.get('inspector_name')
        egn = request.form.get('target_egn')
        violation = True if request.form.get('is_violation') == 'on' else False
        fine = request.form.get('fine_amount')
        desc = request.form.get('description')

        fine_value = 0.0
        if fine:
            fine_value = float(fine)

        new_inspection = Inspection(
            inspector_name=inspector,
            target_egn=egn,
            is_violation=violation,
            fine_amount=fine_value,
            description=desc,
            date_checked=datetime.now()
        )
        
        try:
            db.session.add(new_inspection)
            db.session.commit()
            flash("Инспекцията е записана успешно!")
        except Exception as e:
            db.session.rollback()
            print("ГРЕШКА:", str(e))
            flash("Възникна грешка при записа.")
            
        return redirect(url_for('inspections_page'))

    all_inspections = Inspection.query.order_by(Inspection.date_checked.desc()).all()
    return render_template('inspections.html', inspections=all_inspections)

@app.route('/vessels', methods=['GET', 'POST'])
def vessels_page():
    if request.method == 'POST':
        cfr = request.form.get('cfr_number')
        name = request.form.get('vessel_name')
        sign = request.form.get('call_sign')
        owner = request.form.get('owner_name')
        captain = request.form.get('captain_name')
        length_val = float(request.form.get('length', 0))
        power_val = float(request.form.get('engine_power', 0))

        new_vessel = FishingVessel(
            cfr_number=cfr,
            vessel_name=name,
            call_sign=sign,
            owner_name=owner,
            captain_name=captain,
            length=length_val,
            engine_power=power_val,
            date_registered=datetime.now()
        )

        try:
            db.session.add(new_vessel)
            db.session.commit()
            flash(f"Корабът '{name}' беше регистриран успешно!")
        except Exception as e:
            db.session.rollback()
            print("ГРЕШКА ПРИ ЗАПИС НА КОРАБ:", str(e))
            flash("Възникна грешка. Възможно е този международен номер вече да съществува.")
            
        return redirect(url_for('vessels_page'))

    all_vessels = FishingVessel.query.order_by(FishingVessel.date_registered.desc()).all()
    return render_template('vessels.html', vessels=all_vessels)
    
@app.route('/permits', methods=['GET', 'POST'])
def permits_page():
    if request.method == 'POST':
        p_number = request.form.get('permit_number')
        v_id = request.form.get('vessel_id')
        gear = request.form.get('allowed_gear')
        until_str = request.form.get('valid_until')
        
        # Превръщаме текстовата дата от формата в обект за дата
        valid_date = datetime.strptime(until_str, '%Y-%m-%d').date()

        new_permit = FishingPermit(
            permit_number=p_number,
            vessel_id=v_id,
            allowed_gear=gear,
            valid_until=valid_date,
            is_active=True
        )

        try:
            db.session.add(new_permit)
            db.session.commit()
            flash("Разрешителното е издадено успешно!")
        except Exception as e:
            db.session.rollback()
            print("ГРЕШКА ПРИ ЗАПИС НА РАЗРЕШИТЕЛНО:", str(e))
            flash("Възникна грешка. Проверете дали този номер на разрешително вече не съществува.")
            
        return redirect(url_for('permits_page'))

    all_permits = FishingPermit.query.order_by(FishingPermit.date_issued.desc()).all()
    all_vessels = FishingVessel.query.all()  # Необходимо за попълване на падащото меню
    return render_template('permits.html', permits=all_permits, vessels=all_vessels)

@app.route('/logbook', methods=['GET', 'POST'])
def logbook_page():
    if request.method == 'POST':
        v_id = request.form.get('vessel_id')
        start_str = request.form.get('trip_start')
        loc = request.form.get('location')
        duration = float(request.form.get('duration_hours', 0))
        gear = request.form.get('gear_used')
        species = request.form.get('fish_species')
        quantity = float(request.form.get('fish_quantity_kg', 0))

        start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')

        new_log = FishingLog(
            vessel_id=v_id,
            trip_start=start_dt,
            location=loc,
            duration_hours=duration,
            gear_used=gear,
            fish_species=species,
            fish_quantity_kg=quantity
        )

        try:
            db.session.add(new_log)
            db.session.commit()
            flash("Записът в електронния дневник е регистриран успешно!")
        except Exception as e:
            db.session.rollback()
            print("ГРЕШКА ПРИ ЗАПИС В ДНЕВНИК:", str(e))
            flash("Възникна грешка при въвеждането на данните.")
            
        return redirect(url_for('logbook_page'))

    all_logs = FishingLog.query.order_by(FishingLog.date_submitted.desc()).all()
    all_vessels = FishingVessel.query.all()
    return render_template('logbook.html', logs=all_logs, vessels=all_vessels)


@app.route('/landings', methods=['GET', 'POST'])
def landings_page():
    if request.method == 'POST':
        l_id = request.form.get('log_id')
        port = request.form.get('landing_port')
        species = request.form.get('unloaded_species')
        weight = float(request.form.get('weight_kg', 0))
        vehicle = request.form.get('transport_vehicle')
        shop = request.form.get('destination_shop')

        new_landing = FishLanding(
            log_id=l_id,
            landing_port=port,
            unloaded_species=species,
            weight_kg=weight,
            transport_vehicle=vehicle,
            destination_shop=shop
        )

        try:
            db.session.add(new_landing)
            db.session.commit()
            flash("Данните за разтоварване и дистрибуция бяха записани успешно!")
        except Exception as e:
            db.session.rollback()
            print("ГРЕШКА ПРИ РАЗТОВАРВАНЕ:", str(e))
            flash("Възникна грешка при запис на данните.")
            
        return redirect(url_for('landings_page'))

    all_landings = FishLanding.query.order_by(FishLanding.date_landed.desc()).all()
    all_logs = FishingLog.query.all()
    return render_template('landings.html', landings=all_landings, logs=all_logs)

@app.route('/acts', methods=['GET', 'POST'])
def acts_page():
    if request.method == 'POST':
        act_num = request.form.get('act_number')
        v_type = request.form.get('violator_type')
        v_name = request.form.get('violator_name')
        details = request.form.get('violation_details')
        fine = float(request.form.get('fine_amount', 0))

        new_act = EnforcementAct(
            act_number=act_num,
            violator_type=v_type,
            violator_name=v_name,
            violation_details=details,
            fine_amount=fine,
            status="Издаден"
        )

        try:
            db.session.add(new_act)
            db.session.commit()
            flash("Актът за установеното нарушение е съставен успешно!")
        except Exception as e:
            db.session.rollback()
            print("ГРЕШКА ПРИ СЪСТАВЯНЕ НА АКТ:", str(e))
            flash("Неуспешно записване. Проверете дали този номер на акт вече не съществува.")
            
        return redirect(url_for('acts_page'))

    all_acts = EnforcementAct.query.order_by(EnforcementAct.date_issued.desc()).all()
    return render_template('acts.html', acts=all_acts)  

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['full_name'] = user.full_name
            flash(f"Добре дошли, {user.full_name}!")
            return redirect(url_for('vessels_page'))
            
        flash("Невалидно потребителско име или парола.")
    return render_template('login.html')

@app.route('/logout')
def logout_action():
    session.clear()
    flash("Успешно излязохте от системата.")
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="inspector1").first():
            inspector_user = User(
                username="inspector1",
                password_hash=generate_password_hash("iara2026"),
                role="Инспектор",
                full_name="инсп. Димитър Георгиев"
            )
            captain_user = User(
                username="captain1",
                password_hash=generate_password_hash("ship2026"),
                role="Капитан",
                full_name="кап. Иван Петров"
            )
            db.session.add(inspector_user)
            db.session.add(captain_user)
            db.session.commit()
    app.run(debug=True)