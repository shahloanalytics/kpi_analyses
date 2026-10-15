import sqlite3,json,os,shutil,uuid,hashlib
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone,date
from metrics import default_templates,validate_template
ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get('SECURITY_KPI_DB',ROOT/'data'/'security.db'))
SCHEMA='''CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entities(code TEXT PRIMARY KEY,role TEXT NOT NULL,label TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS results(key TEXT PRIMARY KEY,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL,creator TEXT NOT NULL,reviewer TEXT,approver TEXT,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,actor TEXT,operation TEXT,object_id TEXT,before_data TEXT,after_data TEXT);'''
PERMS={'entry':{'write','report'},'reviewer':{'review'},'admin':{'write','report','review','approve','config','restore'}}
def now():return datetime.now(timezone.utc).isoformat()
def require(actor,action):
    if not isinstance(actor,dict) or not actor.get('code') or action not in PERMS.get(actor.get('role'),set()):raise PermissionError('Ushbu amal uchun ruxsat yo‘q.')
@contextmanager
def connect():
    DB.parent.mkdir(parents=True,exist_ok=True);c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row
    try:
        with c:yield c
    finally:c.close()
def init():
    seed=ROOT/'data'/'sample.db';DB.parent.mkdir(parents=True,exist_ok=True)
    if not DB.exists() and seed.exists():shutil.copyfile(seed,DB)
    with connect() as c:
        c.executescript(SCHEMA)
        for t in default_templates():c.execute('INSERT OR IGNORE INTO templates VALUES (?,?)',(t['id'],json.dumps(t,ensure_ascii=False)))
        c.execute("INSERT OR IGNORE INTO settings VALUES ('org','Avtozavod — namuna')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('demo','1')")
def log(c,actor,op,obj,before=None,after=None):
    c.execute('INSERT INTO audit(at,actor,operation,object_id,before_data,after_data) VALUES (?,?,?,?,?,?)',(now(),actor['code'],op,obj,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False)))
def settings():
    with connect() as c:return {r['k']:r['v'] for r in c.execute('SELECT * FROM settings')}
def set_setting(k,v,actor):
    require(actor,'config')
    with connect() as c:
        before=c.execute('SELECT v FROM settings WHERE k=?',(k,)).fetchone();c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(k,v));log(c,actor,'setting',k,before[0] if before else None,v)
def entities():
    with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM entities ORDER BY code')]
def add_entity(code,role,label,actor):
    import re
    from metrics import ROLES
    require(actor,'config')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',code) or role not in ROLES or not label.strip():raise ValueError('Kod, lavozim yoki nom noto‘g‘ri.')
    with connect() as c:c.execute('INSERT INTO entities VALUES (?,?,?)',(code,role,label[:120]));log(c,actor,'entity',code,None,dict(role=role,label=label))
def templates():
    with connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT payload FROM templates')]
def save_template(t,actor):
    require(actor,'config');validate_template(t);t=dict(t)
    t['id']=t['role']+'-'+uuid.uuid4().hex[:8];t['version']=max(x['version'] for x in templates() if x['role']==t['role'])+1
    t['approved']=False;t['approved_by']='';t['label']='Tasdiqlash uchun namuna'
    with connect() as c:c.execute('INSERT INTO templates VALUES (?,?)',(t['id'],json.dumps(t,ensure_ascii=False)));log(c,actor,'template_create',t['id'],None,t)
    return t['id']
def approve_template(tid,actor):
    require(actor,'config')
    with connect() as c:
        t=json.loads(c.execute('SELECT payload FROM templates WHERE id=?',(tid,)).fetchone()[0]);before=dict(t);validate_template(t)
        t.update(approved=True,approved_by=actor['code'],label='Ichki foydalanuvchi tasdiqlagan namuna')
        c.execute('UPDATE templates SET payload=? WHERE id=?',(json.dumps(t,ensure_ascii=False),tid));log(c,actor,'template_approve',tid,before,t)
def results():
    with connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT payload FROM results')]
def key(r):return '|'.join(str(r[x]) for x in ['month','entity','template','metric'])
def digest(records):return hashlib.sha256(json.dumps(records,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def import_rows(records,actor,expected_hash):
    require(actor,'write')
    from imports import validate_rows
    clean,errors=validate_rows(records)
    if errors:raise ValueError('Import tekshiruvdan o‘tmadi: '+str(errors[:2]))
    with connect() as c:
        current=[json.loads(r[0]) for r in c.execute('SELECT payload FROM results')]
        if digest(current)!=expected_hash:raise ValueError('Ma’lumotlar o‘zgargan. Import ko‘rinishini yangilang.')
        n=0
        for r in clean:
            k=key(r);old=c.execute('SELECT payload FROM results WHERE key=?',(k,)).fetchone();before=json.loads(old[0]) if old else None
            # Uploaded identity is provenance only; trusted actor is captured here.
            r['saved_by']=actor['code']
            if before==r:continue
            c.execute('INSERT OR REPLACE INTO results VALUES (?,?)',(k,json.dumps(r,ensure_ascii=False)));log(c,actor,'result_upsert',k,before,r);n+=1
        return n

def actions():
    with connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT payload FROM actions')]
def save_action(r,actor):
    require(actor,'write');date.fromisoformat(r['due'])
    if not r['task'].strip() or not r['owner'].strip():raise ValueError('Vazifa va mas’ulni kiriting.')
    if r['state'] not in ('open','closed'):raise ValueError('Holat noto‘g‘ri.')
    r=dict(r);r['id']=r.get('id') or uuid.uuid4().hex
    with connect() as c:
        old=c.execute('SELECT payload FROM actions WHERE id=?',(r['id'],)).fetchone();c.execute('INSERT OR REPLACE INTO actions VALUES (?,?)',(r['id'],json.dumps(r,ensure_ascii=False)));log(c,actor,'action',r['id'],json.loads(old[0]) if old else None,r)

def create_report(snapshot,actor):
    require(actor,'report');rid=uuid.uuid4().hex[:12]
    with connect() as c:c.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?)',(rid,json.dumps(snapshot,ensure_ascii=False),'Qoralama',actor['code'],None,None,now()));log(c,actor,'report_create',rid,None,snapshot)
    return rid

def reports():
    with connect() as c:return [{**dict(r),'payload':json.loads(r['payload'])} for r in c.execute('SELECT * FROM reports ORDER BY created DESC')]
def transition(rid,actor):
    with connect() as c:
        row=c.execute('SELECT * FROM reports WHERE id=?',(rid,)).fetchone()
        if not row:raise ValueError('Hisobot topilmadi.')
        row=dict(row);snap=json.loads(row['payload'])
        if row['state']=='Qoralama':
            require(actor,'review')
            if row['creator']==actor['code']:raise ValueError('Muallif o‘z hisobotini tekshira olmaydi.')
            c.execute("UPDATE reports SET state='Tekshirildi',reviewer=? WHERE id=?",(actor['code'],rid))
        elif row['state']=='Tekshirildi':
            require(actor,'approve')
            if actor['code'] in (row['creator'],row['reviewer']):raise ValueError('Tasdiqlovchi muallif va tekshiruvchidan boshqa bo‘lsin.')
            if not snap['calculation']['final']:raise ValueError('Dastlabki hisob tasdiqlanmaydi. Ma’lumot/metodikani to‘ldirib yangi hisobot yarating.')
            c.execute("UPDATE reports SET state='Tasdiqlandi',approver=? WHERE id=?",(actor['code'],rid))
        else:raise ValueError('Tasdiqlangan hisobot o‘zgarmaydi.')
        log(c,actor,'report_transition',rid,row['state'],'Tekshirildi' if row['state']=='Qoralama' else 'Tasdiqlandi')

def audit():
    with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 1000')]
def backup():
    with connect() as c:
        c.execute('BEGIN');return json.dumps({'version':1,'tables':{t:[dict(r) for r in c.execute('SELECT * FROM '+t)] for t in ('settings','entities','templates','results','actions','reports','audit')}},ensure_ascii=False,indent=2)
def restore(payload,actor):
    require(actor,'restore')
    # Data-only recovery: historical report snapshots and audit trail are never overwritten.
    if payload.get('version')!=1:raise ValueError('Zaxira versiyasi mos emas.')
    tables=payload.get('tables',{}); required={'settings','entities','templates','results','actions','reports','audit'}
    if set(tables)!=required:raise ValueError('Zaxira jadvallari mos emas.')
    for t in required:
        if not isinstance(tables[t],list) or len(tables[t])>100000:raise ValueError('Zaxira hajmi noto‘g‘ri.')
    for r in tables['templates']:validate_template(json.loads(r['payload']))
    with connect() as c:
        for t in ('entities','templates','results','actions'):
            fields=[x[1] for x in c.execute('PRAGMA table_info('+t+')')]
            c.execute('DELETE FROM '+t)
            for r in tables[t]:
                if set(r)!=set(fields):raise ValueError('Zaxira ustunlari noto‘g‘ri.')
                c.execute(f"INSERT INTO {t} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",[r[k] for k in fields])
        # Structural verification uses this same transaction.
        ts={r['id']:json.loads(r['payload']) for r in c.execute('SELECT * FROM templates')};es={r['code']:r['role'] for r in c.execute('SELECT * FROM entities')}
        from imports import validate_rows
        clean,errors=validate_rows([json.loads(r[0]) for r in c.execute('SELECT payload FROM results')],ts,es)
        if errors:raise ValueError('Zaxira natijalarida xatolik: '+str(errors[:2]))
        for r in c.execute('SELECT payload FROM actions'):
            a=json.loads(r[0]);date.fromisoformat(a['due'])
            if a['state'] not in ('open','closed'):raise ValueError('Chora holati noto‘g‘ri.')
        for r in tables['settings']:
            if r['k'] in ('org','demo'):c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(r['k'],str(r['v'])))
        # Merge immutable history only when absent; reject collisions with different content.
        for t in ('reports',):
            fields=[x[1] for x in c.execute('PRAGMA table_info('+t+')')]
            for r in tables[t]:
                old=c.execute('SELECT * FROM reports WHERE id=?',(r['id'],)).fetchone()
                if old and dict(old)!=r:raise ValueError('Hisobot tarixi bilan ziddiyat. Tiklash bekor qilindi.')
                if not old:
                    # Recovered reports are drafts requiring a new review cycle.
                    r={**r,'state':'Qoralama','reviewer':None,'approver':None}
                    c.execute(f"INSERT INTO {t} VALUES ({','.join('?' for _ in fields)})",[r[k] for k in fields])
        log(c,actor,'restore','database',None,{'records':len(clean),'source_audit':tables['audit']})
