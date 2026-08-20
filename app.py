import os
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
import secrets as _secrets_module
app.secret_key = os.environ.get("SECRET_KEY", _secrets_module.token_hex(32))

PHONE_MODELS = {
    "Redmi": ["Redmi Note 8", "Redmi Note 9", "Redmi Note 9 Pro", "Redmi Note 9 Pro Max", "Redmi Note 10", "Redmi Note 10 Pro", "Redmi Note 11", "Redmi Note 12", "Redmi 9", "Redmi 9A", "Redmi 10", "Redmi 10C", "Poco X3", "Poco F3", "Poco M3"],
    "Samsung": ["Galaxy S8", "Galaxy S9", "Galaxy S10", "Galaxy S20", "Galaxy S21", "Galaxy S22", "Galaxy S23", "Galaxy A03", "Galaxy A10", "Galaxy A12", "Galaxy A20", "Galaxy A21s", "Galaxy A30", "Galaxy A50", "Galaxy A51", "Galaxy A52", "Galaxy A70"],
    "Tecno": ["Spark 6", "Spark 7", "Spark 8", "Camon 16", "Camon 17", "Camon 18", "Pova 3", "Pova Neo"],
    "Infinix": ["Hot 9", "Hot 10", "Hot 11", "Hot 12", "Note 8", "Note 10", "Note 11", "Zero 8"],
    "Itel": ["A48", "A56", "A58", "Vision 1", "Vision 3"],
    "Vivo": ["Y11", "Y12", "Y17", "Y20", "Y21", "Y33s", "V21"],
    "Oppo": ["A3s", "A5s", "A12", "A15", "A54", "A74", "Reno 5"],
    "Realme": ["5", "5i", "6", "7", "C11", "C15", "C21", "C25"],
    "iPhone": ["6", "6s", "7", "8", "X", "11", "12", "13", "SE"],
    "Outro": ["Outro dispositivo"],
}
def _build_all_devices():
    result = []
    for brand, models in PHONE_MODELS.items():
        for model in models:
            if brand == "Outro" or model.startswith(brand):
                result.append(model)
            else:
                result.append(brand + " " + model)
    return result

ALL_DEVICES = _build_all_devices()
STYLES = ["Rush", "Preciso na Cabeca", "Controle Total"]
LEVELS = ["Baixa", "Media", "Alta"]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def clamp(value, low=0, high=200):
    return max(low, min(high, value))


def init_db():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("PRAGMA table_info(users)")
    cols = [c[1] for c in cur.fetchall()]
    if "is_active" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    if "created_at" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT NOT NULL,
            style TEXT NOT NULL,
            level TEXT NOT NULL,
            general INTEGER, red_dot INTEGER, scope_2x INTEGER,
            scope_4x INTEGER, sniper INTEGER, free_look INTEGER,
            UNIQUE(device, style, level)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT, style TEXT, level TEXT,
            ip TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("PRAGMA table_info(stats)")
    cols = [c[1] for c in cur.fetchall()]
    if "ip" not in cols:
        cur.execute("ALTER TABLE stats ADD COLUMN ip TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT UNIQUE NOT NULL,
            reason TEXT,
            blocked_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            max_dpi INTEGER DEFAULT 800
        )
    """)

    cur.execute("PRAGMA table_info(devices)")
    cols = [c[1] for c in cur.fetchall()]
    if "max_dpi" not in cols:
        cur.execute("ALTER TABLE devices ADD COLUMN max_dpi INTEGER DEFAULT 800")

    cur.execute("SELECT COUNT(*) AS c FROM devices")
    if cur.fetchone()[0] == 0:
        for name in _build_all_devices():
            cur.execute("INSERT OR IGNORE INTO devices (name) VALUES (?)", (name,))

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    defaults = {
        "whatsapp": "849257170",
        "email": "martonmauro0@gmail.com",
        "site_title": "Gerador de Sensibilidade Free Fire",
        "hero_title": "Gerador de Sensibilidade Free Fire",
        "hero_subtitle": "Escolhe o teu telemovel e estilo de jogo para gerar a sensibilidade ideal.",
        "generate_btn_text": "Gerar Sensibilidade",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            attempted_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            details TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        initial_password = os.environ.get("ADMIN_INITIAL_PASSWORD", "mudaEstaSenha123")
        cur.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
            ("admin", generate_password_hash(initial_password)),
        )


    base_values = {
        "Baixa":  {"general": 80, "red_dot": 70, "scope_2x": 60, "scope_4x": 50, "sniper": 40, "free_look": 90},
        "Media":  {"general": 130, "red_dot": 120, "scope_2x": 110, "scope_4x": 90, "sniper": 70, "free_look": 140},
        "Alta":   {"general": 190, "red_dot": 180, "scope_2x": 160, "scope_4x": 130, "sniper": 110, "free_look": 200},
    }
    style_adjust = {"Rush": 5, "Preciso na Cabeca": -5, "Controle Total": 0}

    for device in ALL_DEVICES:
        for style in STYLES:
            for level in LEVELS:
                cur.execute(
                    "SELECT id FROM configs WHERE device=? AND style=? AND level=?",
                    (device, style, level),
                )
                if cur.fetchone():
                    continue
                v = base_values[level]
                adj = style_adjust[style]
                cur.execute(
                    "INSERT INTO configs (device, style, level, general, red_dot, scope_2x, scope_4x, sniper, free_look) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        device, style, level,
                        clamp(v["general"] + adj), clamp(v["red_dot"] + adj),
                        clamp(v["scope_2x"] + adj), clamp(v["scope_4x"] + adj),
                        clamp(v["sniper"] + adj), clamp(v["free_look"] + adj),
                    ),
                )

    db.commit()
    db.close()


@app.after_request
def add_no_cache_headers(response):
    if request.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id") or not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


def get_all_devices(db):
    rows = db.execute("SELECT name FROM devices ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def get_devices_grouped(db):
    names = get_all_devices(db)
    groups = {}
    for name in names:
        brand = name.split(" ")[0] if " " in name else name
        groups.setdefault(brand, []).append(name)
    return dict(sorted(groups.items()))


def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


@app.context_processor
def inject_settings():
    try:
        return {"settings": get_settings()}
    except Exception:
        return {"settings": {}}


@app.route("/")
def index():
    db = get_db()
    total_uses = db.execute("SELECT COUNT(*) AS c FROM stats").fetchone()["c"]
    devices = get_all_devices(db)
    devices_grouped = get_devices_grouped(db)
    return render_template("index.html", devices=devices, devices_grouped=devices_grouped, styles=STYLES, levels=LEVELS, total_uses=total_uses)


BASE_VALUES = {
    "Baixa":  {"general": 80, "red_dot": 70, "scope_2x": 60, "scope_4x": 50, "sniper": 40, "free_look": 90},
    "Media":  {"general": 130, "red_dot": 120, "scope_2x": 110, "scope_4x": 90, "sniper": 70, "free_look": 140},
    "Alta":   {"general": 190, "red_dot": 180, "scope_2x": 160, "scope_4x": 130, "sniper": 110, "free_look": 200},
}
STYLE_ADJUST = {"Rush": 5, "Preciso na Cabeca": -5, "Controle Total": 0}


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


@app.route("/device-info")
def device_info():
    device = request.args.get("device", "")
    db = get_db()
    row = db.execute("SELECT max_dpi FROM devices WHERE name=?", (device,)).fetchone()
    max_dpi = row["max_dpi"] if row and row["max_dpi"] else 800
    return jsonify({"max_dpi": max_dpi})


@app.route("/comparar")
def comparar():
    db = get_db()
    devices = get_all_devices(db)
    return render_template("comparar.html", devices=devices, styles=STYLES, levels=LEVELS)


@app.route("/registar", methods=["GET", "POST"])
def registar():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3:
            flash("Utilizador precisa ter pelo menos 3 caracteres.")
            return render_template("registar.html")
        if len(password) < 6:
            flash("Senha precisa ter pelo menos 6 caracteres.")
            return render_template("registar.html")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            flash("Esse utilizador ja existe.")
            return render_template("registar.html")

        db.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)",
            (username, generate_password_hash(password)),
        )
        db.commit()
        flash("Conta criada com sucesso! Podes entrar agora.")
        return redirect(url_for("user_login"))

    return render_template("registar.html")


@app.route("/entrar", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user and not user["is_active"]:
            flash("Esta conta foi desativada. Contacta o suporte.")
            return render_template("user_login.html")

        if user and check_password_hash(user["password_hash"], password):
            session["user_uid"] = user["id"]
            session["user_name"] = user["username"]
            flash("Bem-vindo, " + user["username"] + "!")
            return redirect(url_for("index"))

        flash("Utilizador ou senha incorretos.")

    return render_template("user_login.html")


@app.route("/sair-conta")
def user_logout():
    session.pop("user_uid", None)
    session.pop("user_name", None)
    return redirect(url_for("index"))


@app.route("/gerar", methods=["POST"])
def gerar():
    ip = request.remote_addr or "unknown"
    db = get_db()
    blocked = db.execute("SELECT id FROM blocked_ips WHERE ip=?", (ip,)).fetchone()
    if blocked:
        return jsonify({"error": "Acesso bloqueado."}), 403

    data = request.get_json(force=True)
    device = data.get("device")
    style = data.get("style")
    level = data.get("level")

    valid_devices = get_all_devices(db)

    if device not in valid_devices or style not in STYLES or level not in LEVELS:
        return jsonify({"error": "Parametros invalidos"}), 400

    cfg = db.execute(
        "SELECT * FROM configs WHERE device=? AND style=? AND level=?",
        (device, style, level),
    ).fetchone()

    if not cfg:
        v = BASE_VALUES[level]
        adj = STYLE_ADJUST[style]
        db.execute(
            "INSERT INTO configs (device, style, level, general, red_dot, scope_2x, scope_4x, sniper, free_look) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                device, style, level,
                clamp(v["general"] + adj), clamp(v["red_dot"] + adj),
                clamp(v["scope_2x"] + adj), clamp(v["scope_4x"] + adj),
                clamp(v["sniper"] + adj), clamp(v["free_look"] + adj),
            ),
        )
        db.commit()
        cfg = db.execute(
            "SELECT * FROM configs WHERE device=? AND style=? AND level=?",
            (device, style, level),
        ).fetchone()

    def jitter(v):
        return clamp(v + random.randint(-2, 2))

    result = {
        "general": jitter(cfg["general"]),
        "red_dot": jitter(cfg["red_dot"]),
        "scope_2x": jitter(cfg["scope_2x"]),
        "scope_4x": jitter(cfg["scope_4x"]),
        "sniper": jitter(cfg["sniper"]),
        "free_look": jitter(cfg["free_look"]),
    }

    db.execute("INSERT INTO stats (device, style, level, ip) VALUES (?, ?, ?, ?)", (device, style, level, ip))
    db.commit()

    total_uses = db.execute("SELECT COUNT(*) AS c FROM stats").fetchone()["c"]
    return jsonify({"result": result, "total_uses": total_uses})


MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_MINUTES = 15


def send_notification_email(subject, body):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    notify_to = os.environ.get("NOTIFY_EMAIL", gmail_user)

    if not gmail_user or not gmail_password:
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = notify_to

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [notify_to], msg.as_string())
        return True
    except Exception:
        return False


def log_action(username, action, details=""):
    db = get_db()
    db.execute("INSERT INTO audit_log (username, action, details) VALUES (?, ?, ?)", (username, action, details))
    db.commit()


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    db = get_db()
    ip = request.remote_addr or "unknown"

    if request.method == "POST":
        recent = db.execute(
            "SELECT COUNT(*) AS c FROM login_attempts WHERE ip=? AND attempted_at >= datetime('now', ?)",
            (ip, "-" + str(LOGIN_WINDOW_MINUTES) + " minutes"),
        ).fetchone()["c"]

        if recent >= MAX_LOGIN_ATTEMPTS:
            flash("Muitas tentativas. Aguarda " + str(LOGIN_WINDOW_MINUTES) + " minutos antes de tentar de novo.")
            return render_template("login.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.execute("SELECT * FROM users WHERE username=? AND is_admin=1", (username,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            db.execute("DELETE FROM login_attempts WHERE ip=?", (ip,))
            db.commit()
            session["user_id"] = user["id"]
            session["is_admin"] = True
            session["username"] = user["username"]
            log_action(user["username"], "login", "IP: " + ip)
            return redirect(url_for("admin_dashboard"))

        db.execute("INSERT INTO login_attempts (ip) VALUES (?)", (ip,))
        db.commit()
        tentativas_restantes = MAX_LOGIN_ATTEMPTS - recent - 1
        flash("Utilizador ou senha incorretos. Tentativas restantes: " + str(max(0, tentativas_restantes)))
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    total_uses = db.execute("SELECT COUNT(*) AS c FROM stats").fetchone()["c"]
    by_device = db.execute("SELECT device, COUNT(*) AS c FROM stats GROUP BY device ORDER BY c DESC").fetchall()
    by_style = db.execute("SELECT style, COUNT(*) AS c FROM stats GROUP BY style ORDER BY c DESC").fetchall()
    by_level = db.execute("SELECT level, COUNT(*) AS c FROM stats GROUP BY level ORDER BY c DESC").fetchall()
    recent = db.execute("SELECT * FROM stats ORDER BY id DESC LIMIT 15").fetchall()
    by_day = db.execute(
        """SELECT date(created_at) AS day, COUNT(*) AS c
           FROM stats
           WHERE created_at >= datetime('now', '-14 days')
           GROUP BY day ORDER BY day ASC"""
    ).fetchall()
    return render_template("admin_dashboard.html", total_uses=total_uses, by_device=by_device, by_style=by_style, by_level=by_level, recent=recent, by_day=by_day)


@app.route("/admin/configs")
@login_required
def admin_configs():
    db = get_db()
    configs = db.execute("SELECT * FROM configs ORDER BY device, style, level").fetchall()
    return render_template("admin_configs.html", configs=configs)


@app.route("/admin/devices", methods=["GET", "POST"])
@login_required
def admin_devices():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        max_dpi = request.form.get("max_dpi", "800").strip()
        max_dpi = int(max_dpi) if max_dpi.isdigit() else 800
        if name:
            db.execute("INSERT OR IGNORE INTO devices (name, max_dpi) VALUES (?, ?)", (name, max_dpi))
            db.commit()
            log_action(session.get("username"), "adicionar_telemovel", name)
            flash("Telemovel adicionado: " + name)
        return redirect(url_for("admin_devices"))

    devices = db.execute("SELECT * FROM devices ORDER BY name").fetchall()
    return render_template("admin_devices.html", devices=devices)


@app.route("/admin/devices/<int:device_id>/update-dpi", methods=["POST"])
@login_required
def admin_update_device_dpi(device_id):
    max_dpi = request.form.get("max_dpi", "800").strip()
    max_dpi = int(max_dpi) if max_dpi.isdigit() else 800
    db = get_db()
    db.execute("UPDATE devices SET max_dpi=? WHERE id=?", (max_dpi, device_id))
    db.commit()
    log_action(session.get("username"), "atualizar_dpi", "id=" + str(device_id))
    flash("DPI maximo atualizado.")
    return redirect(url_for("admin_devices"))


@app.route("/admin/devices/<int:device_id>/delete", methods=["POST"])
@login_required
def admin_delete_device(device_id):
    db = get_db()
    db.execute("DELETE FROM devices WHERE id=?", (device_id,))
    db.commit()
    log_action(session.get("username"), "remover_telemovel", "id=" + str(device_id))
    flash("Telemovel removido.")
    return redirect(url_for("admin_devices"))


@app.route("/admin/audit")
@login_required
def admin_audit():
    db = get_db()
    logs = db.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
    return render_template("admin_audit.html", logs=logs)


@app.route("/admin/visitors")
@login_required
def admin_visitors():
    db = get_db()
    visitors = db.execute(
        """SELECT ip, COUNT(*) AS total, MAX(created_at) AS last_seen
           FROM stats WHERE ip IS NOT NULL
           GROUP BY ip ORDER BY total DESC"""
    ).fetchall()
    blocked = db.execute("SELECT ip FROM blocked_ips").fetchall()
    blocked_ips = set(r["ip"] for r in blocked)
    return render_template("admin_visitors.html", visitors=visitors, blocked_ips=blocked_ips)


@app.route("/admin/visitors/block", methods=["POST"])
@login_required
def admin_block_ip():
    ip = request.form.get("ip", "").strip()
    reason = request.form.get("reason", "").strip()
    if ip:
        db = get_db()
        db.execute("INSERT OR IGNORE INTO blocked_ips (ip, reason) VALUES (?, ?)", (ip, reason))
        db.commit()
        log_action(session.get("username"), "bloquear_ip", ip)
        flash("IP bloqueado: " + ip)
    return redirect(url_for("admin_visitors"))


@app.route("/admin/visitors/unblock", methods=["POST"])
@login_required
def admin_unblock_ip():
    ip = request.form.get("ip", "").strip()
    if ip:
        db = get_db()
        db.execute("DELETE FROM blocked_ips WHERE ip=?", (ip,))
        db.commit()
        log_action(session.get("username"), "desbloquear_ip", ip)
        flash("IP desbloqueado: " + ip)
    return redirect(url_for("admin_visitors"))


@app.route("/admin/users")
@login_required
def admin_users():
    db = get_db()
    users = db.execute(
        "SELECT * FROM users WHERE is_admin=0 ORDER BY created_at DESC"
    ).fetchall()
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def admin_toggle_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        db.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, user_id))
        db.commit()
        action = "ativar_conta" if new_status else "desativar_conta"
        log_action(session.get("username"), action, user["username"])
        flash("Conta " + ("ativada" if new_status else "desativada") + ": " + user["username"])
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        log_action(session.get("username"), "eliminar_conta", user["username"])
        flash("Conta eliminada: " + user["username"])
    return redirect(url_for("admin_users"))


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    db = get_db()
    if request.method == "POST":
        for key in ["whatsapp", "email", "site_title", "hero_title", "hero_subtitle", "generate_btn_text"]:
            value = request.form.get(key, "").strip()
            if value:
                db.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
        db.commit()
        log_action(session.get("username"), "editar_settings", "")
        flash("Configuracoes atualizadas.")
        return redirect(url_for("admin_settings"))

    current = get_settings()
    return render_template("admin_settings.html", current=current)


@app.route("/admin/export/configs.csv")
@login_required
def admin_export_configs():
    import csv
    import io
    db = get_db()
    rows = db.execute("SELECT * FROM configs ORDER BY device, style, level").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["device", "style", "level", "general", "red_dot", "scope_2x", "scope_4x", "sniper", "free_look"])
    for r in rows:
        writer.writerow([r["device"], r["style"], r["level"], r["general"], r["red_dot"], r["scope_2x"], r["scope_4x"], r["sniper"], r["free_look"]])
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=presets.csv"},
    )


@app.route("/admin/backup")
@login_required
def admin_backup():
    from flask import send_file
    return send_file(DB_PATH, as_attachment=True, download_name="database_backup.db")


@app.route("/admin/configs/<int:config_id>", methods=["POST"])
@login_required
def admin_update_config(config_id):
    fields = ["general", "red_dot", "scope_2x", "scope_4x", "sniper", "free_look"]
    values = [clamp(int(request.form.get(f, 0))) for f in fields]
    db = get_db()
    db.execute(
        "UPDATE configs SET general=?, red_dot=?, scope_2x=?, scope_4x=?, sniper=?, free_look=? WHERE id=?",
        (*values, config_id),
    )
    db.commit()
    log_action(session.get("username"), "editar_preset", "config_id=" + str(config_id))
    flash("Configuracao atualizada.")
    return redirect(url_for("admin_configs"))


@app.route("/admin/change-password", methods=["POST"])
@login_required
def admin_change_password():
    new_password = request.form.get("new_password", "")
    if len(new_password) < 6:
        flash("A senha precisa ter pelo menos 6 caracteres.")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_password), session["user_id"]))
    db.commit()
    log_action(session.get("username"), "trocar_senha", "")
    flash("Senha atualizada com sucesso.")
    return redirect(url_for("admin_dashboard"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
