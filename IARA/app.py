from flask import Flask, render_template, request, redirect, url_for, flash
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


if __name__ == '__main__':
    app.run(debug=True)