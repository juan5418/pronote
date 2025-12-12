"""
Pronote Flask app (single-file)
Compatible Pronote 2024 (nouveau chiffrement)
- Uses pronotepy to connect to the given Pronote instance
- Shows homeworks and timetable in a clean, colorful UI
"""

from flask import Flask, render_template_string, request, redirect, url_for, flash
from datetime import date, timedelta
import traceback

try:
    import pronotepy
    from pronotepy import Client
except Exception:
    pronotepy = None

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret_in_production"

PRONOTE_URL = "https://4170004n.index-education.net/pronote/eleve.html"

# Jinja template embedded directly in the file
TEMPLATE = '''
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pronote — Devoirs & Emploi du temps</title>
  <style>
    :root{
      --bg:#0f1724; --card:#0b1220; --muted:#9aa4b2; --accent:#7dd3fc;
    }
    *{box-sizing:border-box;font-family:Inter, system-ui, -apple-system, 'Segoe UI'}
    body{margin:0;background:linear-gradient(180deg,#071024 0%, #0b1220 100%);color:#e6eef6}
    .wrap{max-width:1100px;margin:36px auto;padding:24px}
    header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
    h1{font-size:22px;margin:0}
    form.login{display:flex;gap:8px;align-items:center}
    input{padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.02);color:inherit}
    button{padding:10px 14px;border-radius:10px;border:none;background:var(--accent);color:#06202a;font-weight:600}

    .grid{display:grid;grid-template-columns:1fr 420px;gap:18px}
    .card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));padding:18px;border-radius:14px;box-shadow:0 6px 20px rgba(2,6,23,0.6)}
    .section-title{font-size:14px;color:var(--muted);margin-bottom:10px}

    .hw-list{display:flex;flex-direction:column;gap:10px}
    .hw{display:flex;gap:12px;align-items:flex-start;padding:12px;border-radius:12px;background:rgba(255,255,255,0.02);}
    .hw .label{min-width:12px;height:44px;border-radius:8px}
    .hw .subject{font-weight:700}

    .timetable{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
    .day h3{margin:0;font-size:13px;color:var(--muted)}
    .lesson{margin-top:8px;padding:8px;border-radius:10px;font-size:13px;background:rgba(255,255,255,0.02)}
    .lesson .sub{font-weight:700}
    .lesson .hour{font-size:12px;color:var(--muted)}

    @media (max-width:900px){.grid{grid-template-columns:1fr} .timetable{grid-template-columns:repeat(2,1fr)}}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Pronote — Devoirs & Emploi du temps</h1>
        <div style="color:var(--muted);font-size:13px">Instance: {{ pronote_url }}</div>
      </div>

      <form class="login" method="post" action="{{ url_for('fetch') }}">
        <input name="username" placeholder="Identifiant Pronote" required>
        <input name="password" placeholder="Mot de passe" type="password" required>
        <button type="submit">Se connecter</button>
      </form>
    </header>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div style="margin-bottom:12px">
          {% for m in messages %}
            <div class="card" style="background:#3b0826;">{{ m }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <div class="grid">
      <div class="card">
        <div class="section-title">Devoirs ({{ homeworks|length }})</div>
        <div class="hw-list">
          {% for hw in homeworks %}
            <div class="hw">
              <div class="label" style="background: {{ hw.color or '#7dd3fc' }}"></div>
              <div>
                <div class="subject">{{ hw.subject }}</div>
                <div style="color:var(--muted);font-size:13px">Pour le {{ hw.date }} • Prof: {{ hw.teacher }}</div>
                <div style="margin-top:6px;">{{ hw.description|safe }}</div>
              </div>
            </div>
          {% else %}
            <div style="color:var(--muted)">Aucun devoir à afficher.</div>
          {% endfor %}
        </div>
      </div>

      <div class="card">
        <div class="section-title">Emploi du temps — Semaine du {{ week_start }}</div>
        <div class="timetable">
          {% for day in week_days %}
            <div>
              <h3>{{ day.label }}</h3>
              {% if day.lessons %}
                {% for l in day.lessons %}
                  <div class="lesson" style="border-left:4px solid {{ l.color or '#7dd3fc' }}">
                    <div class="sub">{{ l.subject }}</div>
                    <div class="hour">{{ l.start }} — {{ l.end }} | {{ l.room }}</div>
                    <div style="font-size:12px;color:var(--muted)">Prof: {{ l.teacher }}</div>
                  </div>
                {% endfor %}
              {% else %}
                <div style="color:var(--muted)">Aucun cours</div>
              {% endif %}
            </div>
          {% endfor %}
        </div>
      </div>
    </div>

  </div>
</body>
</html>
'''


@app.route('/', methods=['GET'])
def index():
    return render_template_string(TEMPLATE,
                                 pronote_url=PRONOTE_URL,
                                 homeworks=[],
                                 week_start=date.today().strftime('%d %b %Y'),
                                 week_days=[])


@app.route('/fetch', methods=['POST'])
def fetch():
    if pronotepy is None:
        flash("pronotepy n'est pas installé.")
        return redirect(url_for("index"))

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        flash("Identifiant et mot de passe requis.")
        return redirect(url_for("index"))

    try:
        # 🔥 IMPORTANT → Connexion Pronote 2024
        client = Client(
            PRONOTE_URL,
            username=username,
            password=password,
            ent=None,
            uuid=None,
            bypass_crypto=False   # obligatoire pour Pronote 2024
        )

        if not client.logged_in:
            flash("Connexion impossible : identifiants ou méthode CAS incorrecte.")
            return redirect(url_for("index"))

        # ------- HOMEWORK -------
        today = date.today()
        raw_hw = client.homework(today, today + timedelta(days=14))

        homeworks = []
        for hw in raw_hw:
            homeworks.append({
                "subject": getattr(hw.subject, "name", "—"),
                "description": (hw.description or "").replace("\n", "<br>"),
                "date": hw.date.strftime("%d %b %Y"),
                "teacher": getattr(hw, "teacher", "—"),
                "color": getattr(hw.subject, "color", None)
            })

        # ------- TIMETABLE -------
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        lessons_raw = client.lessons(start_week, end_week)

        week_days = []
        for i in range(7):
            d = start_week + timedelta(days=i)
            lessons_today = [l for l in lessons_raw if l.start.date() == d]

            lessons = []
            for l in lessons_today:
                lessons.append({
                    "subject": getattr(l.subject, "name", "—"),
                    "start": l.start.strftime("%H:%M"),
                    "end": l.end.strftime("%H:%M"),
                    "teacher": getattr(l, "teacher", "—"),
                    "room": getattr(l, "classroom", "-"),
                    "color": getattr(l.subject, "color", None)
                })

            week_days.append({
                "label": d.strftime("%a %d"),
                "lessons": lessons
            })

        return render_template_string(
            TEMPLATE,
            pronote_url=PRONOTE_URL,
            homeworks=homeworks,
            week_start=start_week.strftime("%d %b %Y"),
            week_days=week_days
        )

    except Exception as e:
        print(traceback.format_exc())
        flash("Erreur : " + str(e))
        return redirect(url_for("index"))


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
