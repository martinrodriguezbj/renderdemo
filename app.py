import os
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS, cross_origin
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
from functools import wraps

# configuro app y db
app = Flask(__name__)
app.config[
"SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "super-secret"

# postgres://apidssd_user:2QWopUmD6QWSHFR9LIGBfnIY9oRT2O93@dpg-ckne4f2v7m0s7387s800-a.oregon-postgres.render.com/apidssd

# Configuracion de CORS para swagger
cors = CORS(app)


db = SQLAlchemy(app)
ma = Marshmallow(app)

# MATERIAL
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    stock = db.Column(db.Integer)
    producer = db.Column(db.String(50))
    delivery_time = db.Column(db.Integer)
    pedido = db.relationship("Pedido", backref="material", uselist=False)

    def __init__(self, name, stock, producer, delivery_time):
        self.name = name
        self.stock = stock
        self.producer = producer
        self.delivery_time = delivery_time


class MaterialSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "stock", "producer", "delivery_time")


# PEDIDO
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    colection_id = db.Column(db.Integer)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"))
    quantity = db.Column(db.Integer)

    def __init__(self, user_id, colection_id, material_id, quantity):
        self.user_id = user_id
        self.colection_id = colection_id
        self.material_id = material_id
        self.quantity = quantity


class PedidoSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_id", "colection_id", "material_id", "quantity")


# USER
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))

    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


# creo las tablas
with app.app_context():
    db.create_all()


def token_required(f):
    @wraps(f)
    def decorated():
        token = request.headers["Authorization"].split(" ")[1]
        print(token)
        if not token:
            return jsonify({"message": "El token no existe"}), 401
        try:
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return jsonify({"message": "El token ha expirado o es inválido"}), 401
        return f()

    return decorated


# defino las rutas
@cross_origin
@app.route("/login", methods=["PUT"])
def login():
    username = request.json["username"]
    password = request.json["password"]
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:
        token = jwt.encode(
            {
                "user": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=40),
            },
            app.config["SECRET_KEY"],
        )
        return jsonify({"token": token})
    return make_response("Usuario o contraseña incorrectos", 401)


@cross_origin
@app.route("/materiales", methods=["PUT"])
@token_required
def get_materials():
    names = request.json["names"]
    materials = []
    for name in names:
        m = Material.query.filter_by(name=name).all()
        if m:
            for material in m:
                materials.append(material)
    return jsonify(MaterialSchema(many=True).dump(materials))


@cross_origin
@app.route("/reservar_materiales", methods=["PUT"])
@token_required
def reserve_materials():
    reserva = request.json["materials"]
    user_id = request.json["user_id"]
    colection_id = request.json["colection_id"]
    pedidos = []
    for pedido in reserva:
        material = Material.query.get(pedido["id"])
        if material:
            if material.stock >= pedido["quantity"]:
                material.stock = material.stock - pedido["quantity"]
                nuevo_pedido = Pedido(
                    user_id, colection_id, material.id, pedido["quantity"]
                )
                db.session.add(nuevo_pedido)
                pedidos.append(nuevo_pedido)
    if pedidos:
        db.session.commit()
    return jsonify(PedidoSchema(many=True).dump(pedidos))


# corro la app con debug true para que se actualice dinamicamente
if __name__ == ("__main__"):
    app.run(debug=True)
