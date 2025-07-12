# Requisitos: instale com 'pip install -r requirements.txt'
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_cors import CORS
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
CORS(app) # Permite que o seu frontend comunique com este backend

# Configuração do Banco de Dados
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração do JWT
app.config['JWT_SECRET_KEY'] = 'mude-esta-chave-secreta-em-producao' # Mude esta chave!
jwt = JWTManager(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- MODELOS DO BANCO DE DADOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    plan = db.Column(db.String(20), nullable=False, default='free') # free, basic, pro
    prompts = db.relationship('Prompt', backref='user', lazy=True)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    prompt_type = db.Column(db.String(10), nullable=False) # 'image' ou 'text'
    platform = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    favorited = db.Column(db.Boolean, default=False)

# --- ROTAS DA API ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not email or not name or not password:
        return jsonify({"msg": "Faltam dados"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Este email já está registado"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Utilizador registado com sucesso"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Faltam dados"}), 400

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        access_token = create_access_token(identity={'id': user.id, 'name': user.name, 'plan': user.plan})
        return jsonify(access_token=access_token, name=user.name, plan=user.plan)
    
    return jsonify({"msg": "Email ou palavra-passe incorretos"}), 401

@app.route('/api/prompts', methods=['POST'])
@jwt_required()
def save_prompt():
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']
    
    data = request.get_json()
    prompt_text = data.get('prompt')
    prompt_type = data.get('type')
    platform = data.get('platform')

    if not prompt_text or not prompt_type or not platform:
        return jsonify({"msg": "Faltam dados para salvar o prompt"}), 400

    new_prompt = Prompt(
        user_id=user_id,
        prompt_text=prompt_text,
        prompt_type=prompt_type,
        platform=platform
    )
    db.session.add(new_prompt)
    db.session.commit()

    return jsonify({"msg": "Prompt salvo com sucesso"}), 201

@app.route('/api/prompts', methods=['GET'])
@jwt_required()
def get_prompts():
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']
    
    user_prompts = Prompt.query.filter_by(user_id=user_id).order_by(Prompt.created_at.desc()).all()
    
    history = [
        {
            "id": p.id,
            "prompt": p.prompt_text,
            "type": p.prompt_type,
            "platform": p.platform,
            "date": p.created_at.isoformat(),
            "favorited": p.favorited
        } for p in user_prompts
    ]

    return jsonify(history), 200

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria as tabelas do banco de dados se não existirem
    app.run(debug=True, port=5001)
