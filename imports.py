import csv,io,math,re
from datetime import datetime
import pandas as pd
from metrics import METRICS
FIELDS=['month','entity','template','metric','plan','actual','state','evidence','note','entered_by','checked_by']
DICTIONARY=[
('month','Hisobot oyi','YYYY-MM','2026-09','Ha','Hisobot kalendari'),
('entity','Xodim/smena kodi','matn','SM-01','Ha','Sozlamalarda ro‘yxatdan o‘tgan kod'),
('template','Metodika versiyasi','matn','shift-v1','Ha','KPI shablonlari ro‘yxati'),
('metric','Ko‘rsatkich kodi','matn','PATROL','Ha','KPI kartalari'),
('plan','Bajarilishi kerak ish / tekshirilgan jami','KPI birligi','60','ok holatda','Tegishli reja yoki jurnal'),
('actual','Tasdiqlangan bajarilgan ish','KPI birligi','57','ok holatda','Dalil bilan tasdiqlangan jurnal'),
('state','Ma’lumot holati','ok / missing / na','ok','Ha','ok — haqiqiy qiymat; missing — yetishmaydi; na — qo‘llanilmaydi'),
('evidence','Hujjat raqami yoki anonim dalil','matn','DALIL-001','ok va na holatda','Ichki hujjat reyestri; maxfiy tafsilot kiritilmaydi'),
('note','Izoh va istisno sababi','matn','Davrda hodisa bo‘lmagan','na holatda','Mas’ul xodim izohi'),
('entered_by','Manbadagi ma’lumot kirituvchi','kod','OP-01','Ha','Manba uchun; tizim haqiqiy foydalanuvchini alohida qayd etadi'),
('checked_by','Manbadagi tekshiruvchi','kod','RV-01','Yo‘q','Import matni tasdiqlangan hisobot maqomini bermaydi')]

def blank(v):return v is None or (isinstance(v,float) and math.isnan(v)) or str(v).strip()==''
def text(v):return '' if blank(v) else str(v).strip()
def number(v):
    if blank(v):return None
    try:n=float(str(v).replace(' ','').replace(',','.'))
    except (ValueError,TypeError):raise ValueError('Son formatida emas.')
    if not math.isfinite(n) or n<0:raise ValueError('Manfiy yoki cheksiz son qabul qilinmaydi.')
    return n

def validate_rows(records,templates=None,entities=None):
    import database as db
    ts=templates if templates is not None else {t['id']:t for t in db.templates()}
    es=entities if entities is not None else {e['code']:e['role'] for e in db.entities()}
    out=[];errors=[];seen=set()
    for index,source in enumerate(records,2):
        try:
            if not isinstance(source,dict):raise ValueError('Satr tuzilishi noto‘g‘ri.')
            if any(k not in source for k in FIELDS):raise ValueError('Majburiy ustunlar yo‘q: '+', '.join(k for k in FIELDS if k not in source))
            r={k:text(source[k]) for k in FIELDS};r['plan']=number(source['plan']);r['actual']=number(source['actual'])
            if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',r['month']):raise ValueError('Oy YYYY-MM shaklida bo‘lsin.')
            datetime.strptime(r['month'],'%Y-%m')
            if r['entity'] not in es:raise ValueError('Xodim/smena kodi ro‘yxatdan o‘tmagan: '+r['entity'])
            if r['template'] not in ts:raise ValueError('Shablon topilmadi: '+r['template'])
            t=ts[r['template']]
            if es[r['entity']]!=t['role']:raise ValueError('Xodim lavozimi shablonga mos emas.')
            if r['metric'] not in {m['code'] for m in t['metrics']}:raise ValueError('KPI shablonga kirmaydi.')
            if r['state'] not in ('ok','missing','na'):raise ValueError('Holat ok, missing yoki na bo‘lsin.')
            if not r['entered_by']:raise ValueError('Ma’lumot kirituvchi kodi kerak.')
            if any(len(str(v))>2000 for v in r.values() if v is not None):raise ValueError('Maydon 2000 belgidan uzun.')
            if r['state']=='ok':
                if r['plan'] is None or r['actual'] is None:raise ValueError('Bo‘sh sonni nolga almashtirmang: missing holatini tanlang.')
                if r['actual']>r['plan']:raise ValueError('Amalda rejadan katta — tekshirish va to‘g‘rilash kerak.')
                if r['plan']==0:raise ValueError('Maxraj nol: asosli na yoki missing holatini tanlang; 100 ball berilmaydi.')
                if not r['evidence']:raise ValueError('Dalil kodi kerak.')
            if r['state']=='na':
                if not r['note'] or not r['evidence']:raise ValueError('Qo‘llanilmaydi holati uchun sabab va dalil kiriting.')
                if any(v not in (None,0) for v in (r['plan'],r['actual'])):raise ValueError('na holatida amaldagi ish soni bo‘lmasin.')
            if r['state']=='missing' and r['plan'] is not None and r['actual'] is not None:raise ValueError('Ikkala son mavjud: ok yoki asosli na holatini belgilang.')
            if METRICS[r['metric']]['unit']!='post-soat' and any(v is not None and not v.is_integer() for v in (r['plan'],r['actual'])):raise ValueError('Ushbu KPI uchun butun son kiriting.')
            k=db.key(r)
            if k in seen:raise ValueError('Faylda takroriy oy/xodim/shablon/KPI yozuvi.')
            seen.add(k);out.append(r)
        except (ValueError,TypeError,KeyError) as e:errors.append({'satr':index,'xatolik':str(e)})
    return out,errors

def read_file(content,filename):
    if len(content)>10_000_000:raise ValueError('Fayl 10 MB dan katta.')
    if filename.lower().endswith('.csv'):df=pd.read_csv(io.BytesIO(content),dtype=object,keep_default_na=False,encoding='utf-8-sig')
    else:
        import zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if sum(i.file_size for i in z.infolist())>50_000_000:raise ValueError('Excel ochilgandagi hajmi juda katta.')
        df=pd.read_excel(io.BytesIO(content),sheet_name='Oylik_natijalar',dtype=object,keep_default_na=False)
    if len(df)>20000:raise ValueError('20 000 qatordan ko‘p.')
    if df.columns.duplicated().any():raise ValueError('Takroriy ustun nomi.')
    return df

def differences(clean,current):
    import database as db
    old={db.key(r):r for r in current};out=[]
    for r in clean:
        before=old.get(db.key(r))
        changed=[k for k in FIELDS if before and before.get(k)!=r.get(k)]
        out.append({'kalit':db.key(r),'amal':'Yangi' if before is None else 'Yangilash' if changed else 'O‘zgarishsiz','farq':'; '.join(f'{k}: {before.get(k)} → {r.get(k)}' for k in changed)})
    return out

def safe_value(v):
    if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')):return "'"+v
    return v

def csv_bytes(records,fields=None):
    fields=fields or (list(records[0]) if records else FIELDS)
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields,extrasaction='ignore');w.writeheader()
    for r in records:w.writerow({k:safe_value(r.get(k,'')) for k in fields})
    return ('\ufeff'+s.getvalue()).encode('utf-8')
