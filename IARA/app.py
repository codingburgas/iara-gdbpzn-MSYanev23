from flask import Flask, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)