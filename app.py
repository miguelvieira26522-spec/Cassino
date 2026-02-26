from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'cassino_super_secreto_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    saldo = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    if 'usuario_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and usuario.check_password(password):
            session['usuario_id'] = usuario.id
            session['username'] = usuario.username
            session['saldo'] = usuario.saldo
            return redirect(url_for('index'))
        flash('❌ Usuário ou senha incorretos!', 'erro')
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirmar = request.form['confirmar']
        if password != confirmar:
            flash('❌ As senhas não coincidem!', 'erro')
            return render_template('cadastro.html')
        if Usuario.query.filter_by(username=username).first():
            flash('❌ Usuário já existe!', 'erro')
            return render_template('cadastro.html')
        novo_usuario = Usuario(username=username)
        novo_usuario.set_password(password)
        novo_usuario.saldo = 5000
        db.session.add(novo_usuario)
        db.session.commit()
        transacao = Transacao(usuario_id=novo_usuario.id, tipo='bonus', valor=5000, descricao='Bônus de boas-vindas')
        db.session.add(transacao)
        db.session.commit()
        flash('✅ Cadastro realizado! Você ganhou R$ 5000 de bônus!', 'sucesso')
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/cassino')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    session['saldo'] = usuario.saldo
    return render_template('index.html', username=session['username'], saldo=session['saldo'])

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    transacoes = Transacao.query.filter_by(usuario_id=session['usuario_id']).order_by(Transacao.created_at.desc()).limit(50).all()
    return render_template('perfil.html', usuario=usuario, transacoes=transacoes)

@app.route('/depositar', methods=['POST'])
def depositar():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    try:
        valor = float(request.form['valor'])
        if valor <= 0 or valor < 10:
            flash('❌ Valor mínimo de R$ 10!', 'erro')
            return redirect(url_for('perfil'))
        usuario = Usuario.query.get(session['usuario_id'])
        usuario.saldo += valor
        transacao = Transacao(usuario_id=usuario.id, tipo='deposito', valor=valor, descricao=f'Depósito via {request.form.get("metodo", "cartão")}')
        db.session.add(transacao)
        db.session.commit()
        session['saldo'] = usuario.saldo
        flash(f'✅ Depósito de R$ {valor:.0f} realizado!', 'sucesso')
    except:
        flash('❌ Valor inválido!', 'erro')
    return redirect(url_for('perfil'))

@app.route('/sacar', methods=['POST'])
def sacar():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    try:
        valor = float(request.form['valor'])
        if valor <= 0 or valor < 10:
            flash('❌ Valor mínimo de R$ 10!', 'erro')
            return redirect(url_for('perfil'))
        usuario = Usuario.query.get(session['usuario_id'])
        if valor > usuario.saldo:
            flash('❌ Saldo insuficiente!', 'erro')
            return redirect(url_for('perfil'))
        usuario.saldo -= valor
        transacao = Transacao(usuario_id=usuario.id, tipo='saque', valor=-valor, descricao='Saque solicitado')
        db.session.add(transacao)
        db.session.commit()
        session['saldo'] = usuario.saldo
        flash(f'✅ Saque de R$ {valor:.0f} solicitado!', 'sucesso')
    except:
        flash('❌ Valor inválido!', 'erro')
    return redirect(url_for('perfil'))

@app.route('/api/slots', methods=['POST'])
def api_slots():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    aposta = int(data.get('aposta', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    simbolos = ['🍒', '🍋', '🍇', '⭐', '💎', '🔔', '7️⃣', '🍀']
    s1, s2, s3 = random.choice(simbolos), random.choice(simbolos), random.choice(simbolos)
    if s1 == s2 == s3:
        premio = aposta * 10
        resultado = 'jackpot'
        msg = f'🎉 JACKPOT! R$ {premio}!'
    elif s1 == s2 or s2 == s3 or s1 == s3:
        premio = aposta * 2
        resultado = 'ganhou'
        msg = f'✨ Boa! R$ {premio}!'
    else:
        premio = 0
        resultado = 'perdeu'
        msg = '😢 Não foi dessa vez...'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Slots: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'slots': [s1, s2, s3], 'resultado': resultado, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

@app.route('/api/dados', methods=['POST'])
def api_dados():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    chute = int(data.get('chute', 0))
    aposta = int(data.get('aposta', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if chute < 2 or chute > 12:
        return jsonify({'erro': 'Chute deve ser entre 2 e 12!'})
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    soma = d1 + d2
    if soma == chute:
        premio = aposta * 6
        resultado = 'ganhou'
        msg = f'🎉 ACERTOU! R$ {premio}!'
    else:
        premio = 0
        resultado = 'perdeu'
        msg = f'😢 Errou! Era {soma}...'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Dados: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'dados': [d1, d2], 'soma': soma, 'resultado': resultado, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

@app.route('/api/moeda', methods=['POST'])
def api_moeda():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    escolha = data.get('escolha', 'C')
    aposta = int(data.get('aposta', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    resultado = random.choice(['C', 'O'])
    emoji = '👤' if resultado == 'C' else '🌙'
    texto = 'CARA' if resultado == 'C' else 'COROA'
    if resultado == escolha:
        premio = aposta * 2
        resultado_jogo = 'ganhou'
        msg = f'🎉 ACERTOU ({texto})! R$ {premio}!'
    else:
        premio = 0
        resultado_jogo = 'perdeu'
        msg = f'😢 Errou! Deu {texto}...'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Moeda: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'emoji': emoji, 'texto': texto, 'resultado': resultado_jogo, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

@app.route('/api/roleta', methods=['POST'])
def api_roleta():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    escolha = data.get('escolha', 'vermelho')
    aposta = int(data.get('aposta', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    numeros = list(range(0, 37))
    cores = {0: 'verde'}
    for i in range(1, 10): cores[i] = 'vermelho'
    for i in range(10, 19): cores[i] = 'preto'
    for i in range(19, 28): cores[i] = 'vermelho'
    for i in range(28, 37): cores[i] = 'preto'
    resultado_numero = random.choice(numeros)
    resultado_cor = cores.get(resultado_numero, 'verde')
    if escolha == resultado_cor:
        premio = aposta * 2
        resultado_jogo = 'ganhou'
        msg = f'🎉 ACERTOU! R$ {premio}!'
    else:
        premio = 0
        resultado_jogo = 'perdeu'
        msg = f'😢 Errou! Saiu {resultado_numero} ({resultado_cor})...'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Roleta: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'numero': resultado_numero, 'cor': resultado_cor, 'resultado': resultado_jogo, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

@app.route('/api/tigrinho', methods=['POST'])
def api_tigrinho():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    aposta = int(data.get('aposta', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    simbolos = ['🐯', '🐰', '🦊', '🐼', '🦁', '🐸', '💎', '⭐', '7️⃣']
    linhas = [random.choice(simbolos) for _ in range(5)]
    multiplicadores = {'🐯': 10, '💎': 8, '7️⃣': 5, '⭐': 3, '🦁': 2, '🐰': 2, '🦊': 2, '🐼': 2, '🐸': 2}
    premio = 0
    for s in set(linhas):
        if linhas.count(s) >= 2:
            premio += aposta * multiplicadores.get(s, 1) * (linhas.count(s) - 1)
    if premio > 0:
        resultado = 'ganhou'
        msg = f'🐯 TIGRINHO! R$ {premio}!'
    else:
        premio = 0
        resultado = 'perdeu'
        msg = '😢 Não foi dessa vez no Tigrinho...'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Tigrinho: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'linhas': linhas, 'resultado': resultado, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

@app.route('/api/coelhinho', methods=['POST'])
def api_coelhinho():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    aposta = int(data.get('aposta', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    cartelas = []
    for _ in range(3):
        cartela = sorted(random.sample(range(1, 26), 5))
        cartelas.append(cartela)
    numeros_sorteados = random.sample(range(1, 26), 15)
    premio = 0
    linhas_completas = 0
    for cartela in cartelas:
        if all(n in numeros_sorteados for n in cartela):
            linhas_completas += 1
    if linhas_completas == 1:
        premio = aposta * 2
    elif linhas_completas == 2:
        premio = aposta * 5
    elif linhas_completas == 3:
        premio = apuesta * 10
    if premio > 0:
        resultado = 'ganhou'
        msg = f'🐰 COELHINHO! R$ {premio}!'
    else:
        premio = 0
        resultado = 'perdeu'
        msg = '😢 Não foi dessa vez no Coelhinho...'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Coelhinho: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'cartelas': cartelas, 'sorteados': numeros_sorteados, 'resultado': resultado, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

@app.route('/api/mina', methods=['POST'])
def api_mina():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    posicao = int(data.get('posicao', 0))
    aposta = int(data.get('aposta', 0))
    fase = int(data.get('fase', 0))
    usuario = Usuario.query.get(session['usuario_id'])
    if fase == 0:
        if aposta <= 0 or aposta > usuario.saldo:
            return jsonify({'erro': 'Aposta inválida!'})
        usuario.saldo -= aposta
    minas = random.sample(range(15), 3)
    if posicao in minas:
        premio = 0
        resultado = 'perdeu'
        msg = '💣 BOMBA! Você perdeu!'
    else:
        multiplicadores = [1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.3, 2.7, 3.2, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        premio = int(aposta * multiplicadores[min(fase, len(multiplicadores)-1)])
        resultado = 'ganhou'
        msg = f'🎯 SAFE! Multiplicador x{multiplicadores[min(fase, len(multiplicadores)-1)]}!'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Mina: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'minas': minas, 'resultado': resultado, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio, 'fase': fase})

@app.route('/api/aviator', methods=['POST'])
def api_aviator():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'})
    data = request.json
    aposta = int(data.get('aposta', 0))
    multiplicador = float(data.get('multiplicador', 1.0))
    usuario = Usuario.query.get(session['usuario_id'])
    if aposta <= 0 or aposta > usuario.saldo:
        return jsonify({'erro': 'Aposta inválida!'})
    usuario.saldo -= aposta
    crash_point = random.choice([1.0, 1.1, 1.2, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0, 20.0, 50.0])
    if multiplicador <= crash_point:
        premio = int(aposta * multiplicador)
        resultado = 'ganhou'
        msg = f'✈️ Aviator! R$ {premio}!'
    else:
        premio = 0
        resultado = 'perdeu'
        msg = f'💥 Voou! Crash em {crash_point}x'
    usuario.saldo += premio
    transacao = Transacao(usuario_id=usuario.id, tipo='jogo', valor=-aposta + premio, descricao=f'Aviator: {msg}')
    db.session.add(transacao)
    db.session.commit()
    session['saldo'] = usuario.saldo
    return jsonify({'crash_point': crash_point, 'resultado': resultado, 'mensagem': msg, 'saldo': usuario.saldo, 'premio': premio})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)