from flask import Flask, request, Blueprint, render_template
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Materias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha_examen = db.Column(db.String(100), nullable=False)
    tipo_inscripcion = db.Column(db.String(500), nullable=False)
    inicio_inscripcion = db.Column(db.Integer, nullable=False)
    fin_inscripcion = db.Column(db.Integer, nullable=False)
    hora_inicio_examen = db.Column(db.String(500), nullable=False)
    hora_fin_examen = db.Column(db.String(500), nullable=False)
    aula = db.Column(db.String(500), nullable=False)
    fecha_tope_bajas = db.Column(db.String(500), nullable=False)
    docentes = db.Column(db.String(500), nullable=False)
    propuestas = db.Column(db.String(500), nullable=False)

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/search")
def search():
    q = request.args.get("q")
    print(q)

    if q:
        results = Materias.query.filter(Materias.nombre.icontains(q) | Materias.docentes.icontains(q)) \
        .order_by(Materias.inicio_inscripcion.asc()).order_by(Materias.fecha_examen.desc()).limit(100).all()
    else:
        results = []

    return render_template("search_results.html", results=results)

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scrapeddata.db"

    db.init_app(app)

    app.register_blueprint(main)

    return app