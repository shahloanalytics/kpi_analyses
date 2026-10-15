"""Regenerate synthetic seed only; never overwrites the runtime database."""
import csv,json,os
from pathlib import Path
import database as db
from metrics import METRICS,default_templates
from imports import FIELDS,DICTIONARY

def make():
    seed=db.ROOT/'data'/'sample.db'
    if seed.exists():raise SystemExit('sample.db mavjud; avval nusxa oling va uni qo‘lda olib tashlang.')
    db.DB=seed;db.init();admin={'code':'DEMO-admin','role':'admin'};entry={'code':'DEMO-entry','role':'entry'}
    for code,role,label in [('SM-01','shift','Smena A'),('SM-02','shift','Smena B'),('SM-03','shift','Smena C'),('HEAD-01','head','Boshliq kodi'),('DEP-01','deputy','O‘rinbosar kodi'),('DEPT','department','Bo‘lim umumiy')]:db.add_entity(code,role,label,admin)
    records=[]
    for month in ['2026-09','2026-10']:
        for i,entity in enumerate(['SM-01','SM-02','SM-03']):
            for j,(code,m) in enumerate(METRICS.items()):
                p=float(m['example']);a=p if (i+j)%3 else max(0,p-(2 if p>=10 else 1))
                r=dict(month=month,entity=entity,template='shift-v1',metric=code,plan=p,actual=a,state='ok',evidence=f'DALIL-{month}-{i+1}-{code}',note='Sun’iy namuna',entered_by='OP-DEMO',checked_by='')
                if month=='2026-10' and entity=='SM-02' and code=='REPORT':r.update(actual=None,state='missing',note='Hisobot soni hali topshirilmagan')
                if month=='2026-10' and entity=='SM-03' and code=='RESPONSE':r.update(plan=0,actual=0,state='na',note='Davrda javob talab qiladigan hodisa bo‘lmagan')
                records.append(r)
    db.import_rows(records,entry,db.digest([]))
    db.save_action(dict(month='2026-09',entity='SM-01',task='Patrul dalillarini tekshirish va bajarilmagan ish sababini aniqlash',owner='SM-01',due='2026-10-05',state='open'),entry)
    db.set_setting('demo','1',admin)
    p=db.ROOT/'templates'/'Security_KPI_Namuna.csv'
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(records)
    templates=default_templates()
    sheets={
      'Yoriqnoma':[['SECURITY KPI — TASDIQLASH UCHUN NAMUNA',''],['Manba','Barcha sonlar sun’iy. BYD rasmiy me’yorlari emas.'],['Import','Faqat Oylik_natijalar sahifasi import qilinadi.'],['Kodlar','Xodim va shablonlarni avval Sozlamalarda ro‘yxatdan o‘tkazing.'],['Holat','ok = haqiqiy son; missing = yetishmaydi; na = asosli qo‘llanilmaydi.'],['Nol','Reja 0 bo‘lsa na yoki missing: avtomatik 100 ball yo‘q.'],['Takror','Bir oy/kod/shablon/KPI bitta yozuv. Qayta yuklash sonlarni ko‘paytirmaydi.'],['Maxfiylik','Faqat anonim dalil kodi; patrul yo‘nalishi va zaif nuqtalar kerak emas.'],['Qo‘shimcha sahifalar','Hodisa va choralar yig‘ish uchun; KPI natijalarini Oylik_natijalar jadvaliga jamlang.'],['Ish tartibi','Reja va amalda qiymatlarni faqat tasdiqlangan manbadan kiriting.']],
      'Xodimlar_va_smenalar':[['code','role','label']]+[[e[k] for k in ('code','role','label')] for e in db.entities()],
      'KPI_sozlamalari':[['template','role','metric','name','weight','target','unit','source','holat']]+[[t['id'],t['role'],m['code'],m['name'],m['weight'],m['target'],m['unit'],m['source'],'Tasdiqlash uchun namuna'] for t in templates for m in t['metrics']],
      'Oylik_natijalar':[FIELDS]+[[r[k] for k in FIELDS] for r in records],
      'Hodisalar_jamlanmasi':[['month','entity','javob_talab_hodisalar','muddatida_javob','dalil','izoh']]+[[r['month'],r['entity'],r['plan'],r['actual'],r['evidence'],r['note']] for r in records if r['metric']=='RESPONSE'],
      'Tuzatish_choralari':[['month','entity','task','owner','due','state']]+[[a[k] for k in ('month','entity','task','owner','due','state')] for a in db.actions()],
      'Malumotlar_lugati':[['Maydon','Mazmun','Birlik','Misol','Majburiy','Manba']]+[list(r) for r in DICTIONARY]
    }
    (db.ROOT/'data'/'template_content.json').write_text(json.dumps(sheets,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Seed: {len(records)} yozuv, 3 smena, 2 oy.')
if __name__=='__main__':make()
