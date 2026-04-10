from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import Markup
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' ou 'user'
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    predictions = db.relationship('Prediction', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def total_points(self):
        return sum(p.points_earned or 0 for p in self.predictions if p.points_earned is not None)

    @property
    def earliest_prediction(self):
        preds = [p.created_at for p in self.predictions]
        return min(preds) if preds else None


class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(100), nullable=False)
    away_team = db.Column(db.String(100), nullable=False)
    match_datetime = db.Column(db.DateTime, nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    venue = db.Column(db.String(100), default='')
    home_score = db.Column(db.Integer)
    away_score = db.Column(db.Integer)
    status = db.Column(db.String(20), default='upcoming')  # upcoming / finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    predictions = db.relationship('Prediction', backref='match', lazy=True)

    @property
    def is_locked(self):
        """Trava 5 minutos antes do início."""
        now = datetime.utcnow()
        diff = (self.match_datetime - now).total_seconds()
        return diff <= 300

    @property
    def display_score(self):
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score} x {self.away_score}"
        return "- x -"

    @property
    def flag_home(self):
        return _flag_html(self.home_team)

    @property
    def flag_away(self):
        return _flag_html(self.away_team)

    @property
    def iso_home(self):
        return _country_iso(self.home_team)

    @property
    def iso_away(self):
        return _country_iso(self.away_team)


class Prediction(db.Model):
    __tablename__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    home_score_pred = db.Column(db.Integer, nullable=False)
    away_score_pred = db.Column(db.Integer, nullable=False)
    points_earned = db.Column(db.Integer)  # None até o jogo terminar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'match_id'),)

    @property
    def points_label(self):
        if self.points_earned is None:
            return 'Pendente'
        labels = {10: 'Placar Exato', 7: 'Resultado + Gols', 5: 'Resultado Seco', 2: 'Gols de um Time', 0: 'Erro Total'}
        return labels.get(self.points_earned, str(self.points_earned))

    @property
    def points_color(self):
        if self.points_earned is None:
            return 'secondary'
        colors = {10: 'success', 7: 'info', 5: 'primary', 2: 'warning', 0: 'danger'}
        return colors.get(self.points_earned, 'secondary')


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Mapa: nome do país (lowercase) → código ISO 3166-1 alpha-2 (para flag-icons)
_ISO: dict[str, str] = {
    # América do Sul
    'brasil': 'br', 'brazil': 'br',
    'argentina': 'ar',
    'uruguai': 'uy', 'uruguay': 'uy',
    'colombia': 'co', 'colômbia': 'co',
    'chile': 'cl',
    'peru': 'pe',
    'venezuela': 've',
    'ecuador': 'ec', 'equador': 'ec',
    'paraguai': 'py', 'paraguay': 'py',
    'bolivia': 'bo', 'bolívia': 'bo',
    # América do Norte / Central / Caribe
    'estados unidos': 'us', 'usa': 'us', 'united states': 'us',
    'canada': 'ca', 'canadá': 'ca',
    'mexico': 'mx', 'méxico': 'mx',
    'costa rica': 'cr',
    'panama': 'pa', 'panamá': 'pa',
    'honduras': 'hn',
    'jamaica': 'jm',
    'el salvador': 'sv',
    'guatemala': 'gt',
    'haiti': 'ht',
    'trinidad e tobago': 'tt', 'trinidad and tobago': 'tt',
    'curacao': 'cw',
    # Europa
    'alemanha': 'de', 'germany': 'de',
    'franca': 'fr', 'france': 'fr', 'frança': 'fr',
    'espanha': 'es', 'spain': 'es',
    'portugal': 'pt',
    'inglaterra': 'gb-eng', 'england': 'gb-eng',
    'escócia': 'gb-sct', 'escocia': 'gb-sct', 'scotland': 'gb-sct',
    'gales': 'gb-wls', 'wales': 'gb-wls',
    'irlanda do norte': 'gb-nir', 'northern ireland': 'gb-nir',
    'holanda': 'nl', 'netherlands': 'nl', 'países baixos': 'nl',
    'belgica': 'be', 'bélgica': 'be', 'belgium': 'be',
    'croacia': 'hr', 'croácia': 'hr', 'croatia': 'hr',
    'suica': 'ch', 'suíça': 'ch', 'switzerland': 'ch',
    'polonia': 'pl', 'polônia': 'pl', 'poland': 'pl',
    'dinamarca': 'dk', 'denmark': 'dk',
    'suecia': 'se', 'suécia': 'se', 'sweden': 'se',
    'austria': 'at', 'áustria': 'at',
    'turquia': 'tr', 'turkey': 'tr',
    'ucrania': 'ua', 'ucrânia': 'ua', 'ukraine': 'ua',
    'hungria': 'hu', 'hungary': 'hu',
    'eslovaquia': 'sk', 'eslováquia': 'sk', 'slovakia': 'sk',
    'eslovenia': 'si', 'eslovênia': 'si', 'slovenia': 'si',
    'romania': 'ro', 'romênia': 'ro',
    'albania': 'al', 'albânia': 'al', 'albania': 'al',
    'georgia': 'ge', 'geórgia': 'ge',
    'noruega': 'no', 'norway': 'no',
    'finlandia': 'fi', 'finlândia': 'fi', 'finland': 'fi',
    'irlanda': 'ie', 'ireland': 'ie',
    'israel': 'il',
    'serbia': 'rs', 'sérbia': 'rs',
    'bosnia': 'ba', 'bósnia': 'ba', 'bosnia and herzegovina': 'ba',
    'russia': 'ru', 'rússia': 'ru',
    'república tcheca': 'cz', 'czech republic': 'cz', 'tchéquia': 'cz',
    'grécia': 'gr', 'greece': 'gr',
    'itália': 'it', 'italy': 'it',
    'moldova': 'md', 'moldávia': 'md',
    'azerbaijão': 'az', 'azerbaijan': 'az',
    'armênia': 'am', 'armenia': 'am',
    'montenegro': 'me',
    'norte da macedônia': 'mk', 'north macedonia': 'mk',
    'kosovo': 'xk',
    'cazaquistão': 'kz', 'cazaquistao': 'kz', 'kazakhstan': 'kz',
    # África
    'marrocos': 'ma', 'morocco': 'ma',
    'nigeria': 'ng', 'nigéria': 'ng',
    'senegal': 'sn',
    'ghana': 'gh', 'gana': 'gh',
    'camaroes': 'cm', 'camarões': 'cm', 'cameroon': 'cm',
    'tunisia': 'tn', 'tunísia': 'tn',
    'egito': 'eg', 'egypt': 'eg',
    'africa do sul': 'za', 'south africa': 'za', 'áfrica do sul': 'za',
    'costa do marfim': 'ci', "côte d'ivoire": 'ci', 'ivory coast': 'ci',
    'mali': 'ml',
    'guiné': 'gn', 'guinea': 'gn',
    'angola': 'ao',
    'tanzânia': 'tz',
    'zâmbia': 'zm',
    'moçambique': 'mz',
    'etiópia': 'et',
    'argélia': 'dz', 'algeria': 'dz',
    'libia': 'ly', 'líbia': 'ly',
    # Ásia / Oceania
    'japao': 'jp', 'japão': 'jp', 'japan': 'jp',
    'coreia do sul': 'kr', 'south korea': 'kr',
    'irã': 'ir', 'iran': 'ir',
    'arábia saudita': 'sa', 'arabia saudita': 'sa', 'saudi arabia': 'sa',
    'qatar': 'qa',
    'australia': 'au', 'austrália': 'au',
    'nova zelandia': 'nz', 'nova zelândia': 'nz', 'new zealand': 'nz',
    'china': 'cn',
    'índia': 'in', 'india': 'in',
    'iraque': 'iq', 'iraq': 'iq',
    'emirados árabes': 'ae', 'united arab emirates': 'ae',
    'omã': 'om', 'oman': 'om',
    'bahrein': 'bh', 'bahrain': 'bh',
    'kuwait': 'kw',
    'jordânia': 'jo', 'jordan': 'jo',
    'uzbequistão': 'uz', 'uzbekistan': 'uz',
    'tajiquistão': 'tj', 'tajikistan': 'tj',
    'tailândia': 'th', 'thailand': 'th',
    'vietnã': 'vn', 'vietnam': 'vn',
    'indonésia': 'id', 'indonesia': 'id',
    'filipinas': 'ph', 'philippines': 'ph',
    # ── Clubes europeus (Champions League) ───────────────────────────────────
    # Espanha
    'real madrid': 'es', 'barcelona': 'es', 'atletico madrid': 'es',
    'atletico de madrid': 'es', 'sevilla': 'es', 'valencia': 'es',
    'villarreal': 'es', 'real sociedad': 'es', 'betis': 'es',
    # Inglaterra
    'arsenal': 'gb-eng', 'chelsea': 'gb-eng',
    'liverpool': 'gb-eng', 'manchester city': 'gb-eng',
    'manchester united': 'gb-eng', 'tottenham': 'gb-eng',
    'newcastle': 'gb-eng', 'aston villa': 'gb-eng',
    'brighton': 'gb-eng', 'west ham': 'gb-eng',
    # Alemanha
    'bayern munich': 'de', 'bayern munique': 'de', 'fc bayern': 'de',
    'borussia dortmund': 'de', 'bvb': 'de',
    'rb leipzig': 'de', 'bayer leverkusen': 'de',
    'borussia monchengladbach': 'de', 'eintracht frankfurt': 'de',
    # França
    'psg': 'fr', 'paris saint-germain': 'fr', 'paris sg': 'fr',
    'marseille': 'fr', 'lyon': 'fr', 'olympique lyonnais': 'fr',
    'monaco': 'fr', 'lille': 'fr', 'nice': 'fr',
    # Itália
    'inter milan': 'it', 'internazionale': 'it', 'inter': 'it',
    'ac milan': 'it', 'milan': 'it',
    'juventus': 'it', 'napoli': 'it', 'as roma': 'it', 'roma': 'it',
    'lazio': 'it', 'atalanta': 'it', 'fiorentina': 'it',
    # Portugal
    'porto': 'pt', 'fc porto': 'pt',
    'benfica': 'pt', 'sl benfica': 'pt',
    'sporting cp': 'pt', 'sporting': 'pt',
    # Holanda
    'ajax': 'nl', 'psv': 'nl', 'psv eindhoven': 'nl',
    'feyenoord': 'nl', 'az alkmaar': 'nl',
    # Escócia
    'celtic': 'gb-sct', 'rangers': 'gb-sct',
    # Outros
    'benfica': 'pt',
    'shakhtar donetsk': 'ua', 'dynamo kyiv': 'ua',
    'anderlecht': 'be', 'club brugge': 'be',
    'galatasaray': 'tr', 'fenerbahce': 'tr', 'besiktas': 'tr',
    'red bull salzburg': 'at', 'rapid vienna': 'at',
    'young boys': 'ch', 'basle': 'ch',
    'cska moscow': 'ru', 'zenit': 'ru',
    'steaua bucuresti': 'ro',
    'dinamo zagreb': 'hr',
    'slavia prague': 'cz', 'sparta prague': 'cz',
}


# Mapa: nome do clube → ID ESPN (CDN: https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png)
_ESPN: dict[str, str] = {
    # Espanha
    'real madrid': '86', 'barcelona': '83', 'atletico madrid': '1068',
    'atletico de madrid': '1068', 'sevilla': '243', 'valencia': '94',
    'villarreal': '102', 'real sociedad': '89', 'betis': '244',
    # Inglaterra
    'arsenal': '359', 'chelsea': '363', 'liverpool': '364',
    'manchester city': '382', 'manchester united': '360',
    'tottenham': '367', 'newcastle': '361', 'aston villa': '362',
    'brighton': '331', 'west ham': '371',
    # Alemanha
    'bayern munich': '132', 'bayern munique': '132', 'fc bayern': '132',
    'borussia dortmund': '124', 'bvb': '124',
    'rb leipzig': '157', 'bayer leverkusen': '168',
    'eintracht frankfurt': '128',
    # França
    'psg': '160', 'paris saint-germain': '160', 'paris sg': '160',
    'marseille': '116', 'lyon': '115', 'olympique lyonnais': '115',
    'monaco': '118', 'lille': '117', 'nice': '119',
    # Itália
    'inter milan': '110', 'internazionale': '110', 'inter': '110',
    'ac milan': '103', 'milan': '103',
    'juventus': '111', 'napoli': '113', 'as roma': '104', 'roma': '104',
    'lazio': '112', 'atalanta': '108', 'fiorentina': '109',
    # Portugal
    'porto': '197', 'fc porto': '197',
    'benfica': '193', 'sl benfica': '193',
    'sporting cp': '245', 'sporting': '245',
    # Holanda
    'ajax': '169', 'psv': '371', 'psv eindhoven': '371',
    'feyenoord': '420',
    # Escócia
    'celtic': '264', 'rangers': '399',
    # Outros
    'club brugge': '436', 'anderlecht': '434',
    'galatasaray': '386', 'fenerbahce': '387',
    'red bull salzburg': '678', 'young boys': '601',
    'dinamo zagreb': '447', 'shakhtar donetsk': '381',
}


def _country_iso(name: str) -> str | None:
    """Retorna o código ISO 3166-1 alpha-2 do país ou None se não encontrado."""
    return _ISO.get(name.lower().strip())


def _flag_html(name: str) -> Markup:
    """Retorna escudo do clube (ESPN CDN) ou bandeira do país (flag-icons)."""
    key = name.lower().strip()

    # 1. Escudo de clube
    espn_id = _ESPN.get(key)
    if espn_id:
        url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{espn_id}.png"
        return Markup(
            f'<img src="{url}" alt="{name}" title="{name}" '
            f'style="width:32px;height:32px;object-fit:contain;vertical-align:middle;" '
            f'onerror="this.replaceWith(document.createTextNode(\'{name}\'))">'
        )

    # 2. Bandeira de seleção
    iso = _country_iso(name)
    if iso:
        return Markup(
            f'<span class="fi fi-{iso}" title="{name}" '
            f'style="font-size:1.4em;border-radius:3px;'
            f'box-shadow:0 1px 3px rgba(0,0,0,.3);"></span>'
        )

    # 3. Placeholder (times ainda indefinidos nas fases eliminatórias)
    return Markup(
        f'<span class="bi bi-shield-fill" title="{name}" '
        f'style="color:#adb5bd;font-size:1.1em;vertical-align:middle;"></span>'
    )
