"""Versioned sample methodology. No proprietary BYD standards."""
import math
ROLES={'department':'Bo‘lim umumiy','head':'Bo‘lim boshlig‘i','deputy':'Boshliq o‘rinbosari','shift':'Smena boshlig‘i'}
SPECS=[
('POST','Postlarni ta’minlash','post-soat','Postlar tabeli','Rejalashtirilgan post-soatlar','Amalda ta’minlangan post-soatlar',720),
('PATROL','Patrul rejasining bajarilishi','ta','Patrul jurnali','Rejalashtirilgan tekshiruvlar','Dalil bilan tasdiqlangan tekshiruvlar',60),
('ACCESS','Kirish-chiqish nazorati sifati','ta','Tanlama audit','Tekshirilgan operatsiyalar','Tartibga mos operatsiyalar',200),
('CARGO','Transport va yuk nazorati','ta','Yuk hujjatlari auditi','Rejalashtirilgan hujjat tekshiruvlari','To‘liq va to‘g‘ri tekshiruvlar',50),
('RESPONSE','Hodisaga o‘z vaqtida javob','ta','Hodisalar jamlanmasi','Javob berish talab etilgan hodisalar','Ichki muddatda javob berilgan hodisalar',5),
('REPORT','Hisobot intizomi','ta','Hisobotlar reyestri','Topshirilishi kerak hisobotlar','O‘z vaqtida va to‘liq hisobotlar',60),
('ACTION','Tuzatish choralarini bajarish','ta','Ijro nazorati jurnali','Muddati kelgan choralar','O‘z vaqtida yopilgan choralar',10),
('TRAIN','O‘qitish va yo‘riqnoma','nafar','O‘qitish reyestri','O‘qitilishi kerak xodimlar','O‘qitishni yakunlagan xodimlar',20),
('AUDIT','Audit va boshqaruv vazifalari','ta','Tasdiqlangan audit rejasi','Audit talablari','Bajarilgan talablar',20),
('EQUIP','Nosozlik haqida xabar berish','ta','Texnik xabarlar reyestri','Aniqlangan nosozliklar','O‘z vaqtida yuborilgan xabarlar',4)]
METRICS={s[0]:dict(code=s[0],name=s[1],unit=s[2],source=s[3],plan_label=s[4],actual_label=s[5],example=s[6]) for s in SPECS}
WEIGHTS={'department':[15,10,10,10,10,10,10,10,10,5],'head':[5,5,5,5,10,10,20,10,25,5],'deputy':[10,15,10,10,10,5,10,15,10,5],'shift':[15,15,15,10,10,15,5,5,5,5]}

def default_templates():
    return [dict(id=role+'-v1',role=role,version=1,approved=False,approved_by='',redistribute=False,label='Tasdiqlash uchun namuna',metrics=[dict(**METRICS[k],weight=w,target=100.0,required=True) for k,w in zip(METRICS,ws) if w]) for role,ws in WEIGHTS.items()]

def validate_template(t):
    if t['role'] not in ROLES or not t['metrics']: raise ValueError('Shablon lavozimi noto‘g‘ri.')
    codes=[m['code'] for m in t['metrics']]
    if len(codes)!=len(set(codes)) or set(codes)-set(METRICS): raise ValueError('KPI kodlari takrorlangan yoki noma’lum.')
    if abs(sum(float(m['weight']) for m in t['metrics'])-100)>1e-8: raise ValueError('Vaznlar yig‘indisi 100% bo‘lishi kerak.')
    for m in t['metrics']:
        if not all(math.isfinite(float(m[k])) for k in ('weight','target')) or not 0<float(m['weight'])<=100 or not 0<float(m['target'])<=100: raise ValueError('Vazn va maqsad 0 dan katta, 100 gacha bo‘lsin.')

def calculate(records,template):
    validate_template(template)
    by={r['metric']:r for r in records};result=[]
    for m in template['metrics']:
        r=by.get(m['code']);state='missing';rate=score=None;plan=actual=None
        if r:
            state=r['state'];plan=r['plan'];actual=r['actual']
            if state=='ok':
                if plan is None or actual is None: state='missing'
                elif plan<0 or actual<0 or actual>plan: state='review'
                elif plan==0: state='zero_denominator'
                else: rate=actual/plan*100;score=min(100,rate/m['target']*100)
        result.append(dict(code=m['code'],name=m['name'],unit=m['unit'],target=m['target'],weight=m['weight'],effective_weight=m['weight'],plan=plan,actual=actual,rate=rate,score=score,contribution=None,state=state,note=r.get('note','') if r else '',required=m.get('required',True)))
    na_weight=sum(x['weight'] for x in result if x['state']=='na')
    allow=template['approved'] and template['redistribute']
    for x in result:
        if x['state']=='na': x['effective_weight']=0
        elif na_weight and allow and na_weight<100: x['effective_weight']=x['weight']*100/(100-na_weight)
        if x['score'] is not None: x['contribution']=x['score']*x['effective_weight']/100
    unresolved=any(x['state'] not in ('ok','na') for x in result)
    complete=not unresolved and na_weight<100 and (not na_weight or allow)
    observed=sum(x['contribution'] or 0 for x in result)
    return dict(rows=result,observed_points=observed,total=observed if complete else None,complete=complete,final=complete and template['approved'],coverage=sum(x['state'] in ('ok','na') for x in result)/len(result)*100,na_weight=na_weight,redistributed=bool(na_weight and allow),method='ratio-target-v1')

def aggregate(records,entities,template):
    """Each distinct shift is one non-overlapping source; sum numerators/denominators."""
    out=[]
    for m in template['metrics']:
        parts=[next((r for r in records if r['entity']==e and r['metric']==m['code']),None) for e in entities]
        if any(r is None or r['state']=='missing' for r in parts): state='missing';p=a=None
        elif any(r['state']=='ok' and (r['plan'] is None or r['actual'] is None or r['plan']==0 or r['actual']>r['plan']) for r in parts): state='missing';p=a=None
        elif all(r['state']=='na' for r in parts): state='na';p=a=None
        else:
            state='ok';p=sum(r['plan'] for r in parts if r['state']=='ok');a=sum(r['actual'] for r in parts if r['state']=='ok')
        out.append(dict(metric=m['code'],state=state,plan=p,actual=a,note='Agregat: '+', '.join(entities)))
    return out

STATES={'ok':'Amaldagi natija','missing':'Ma’lumot yetishmaydi','na':'Qo‘llanilmaydi','review':'Tekshiruv talab qilinadi','zero_denominator':'Maxraj nol — tasniflash kerak'}
