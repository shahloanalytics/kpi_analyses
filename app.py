import copy,json,sqlite3,time,re
from datetime import date,datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import database as db
from metrics import ROLES,METRICS,STATES,calculate,aggregate
from imports import FIELDS,DICTIONARY,read_file,validate_rows,differences,csv_bytes
from reports import excel_report,pdf_report,analysis
from auth import verify

st.set_page_config(page_title='Security KPI — Avtozavod',page_icon='🛡️',layout='wide')
db.init()
try:users=dict(st.secrets.get('users',{}))
except FileNotFoundError:users={}
if users:
    if 'actor' not in st.session_state:
        st.title('Security KPI — Avtozavod')
        with st.form('login'):
            login=st.text_input('Foydalanuvchi kodi');password=st.text_input('Parol',type='password')
            if st.form_submit_button('Kirish'):
                if time.time()<st.session_state.get('retry_after',0):st.error('30 soniyadan keyin qayta urinib ko‘ring.')
                else:
                    u=users.get(login,{})
                    if verify(password,u.get('password_hash','')) and u.get('role') in db.PERMS:
                        st.session_state.actor={'code':login,'role':u['role']};st.rerun()
                    else:st.session_state.retry_after=time.time()+30;st.error('Login yoki parol noto‘g‘ri.')
        st.stop()
    # Re-check current secrets on every rerun; no role is trusted from upload data.
    u=users.get(st.session_state.actor['code'],{})
    if u.get('role') not in db.PERMS:st.session_state.pop('actor',None);st.rerun()
    actor={'code':st.session_state.actor['code'],'role':u['role']}
else:
    if db.settings().get('demo')!='1':st.error('Ishchi baza uchun Secrets → users hisoblarini sozlang. README_UZ.md ni o‘qing.');st.stop()
    role=st.sidebar.selectbox('Demo rol',['entry','reviewer','admin'],format_func=lambda x:{'entry':'Ma’lumot kirituvchi','reviewer':'Tekshiruvchi','admin':'Administrator'}[x])
    actor={'code':'DEMO-'+role,'role':role}

st.markdown('''<style>.stApp{background:#f4f7f8}[data-testid="stSidebar"]{background:#e8eff1}h1,h2,h3{color:#173f50}[data-testid="stMetric"]{background:white;border:1px solid #d8e2e6;border-radius:12px;padding:16px}div.stButton>button[kind="primary"]{background:#1b706a;border:0}</style>''',unsafe_allow_html=True)
settings=db.settings();entities=db.entities();ts=db.templates();all_results=db.results();all_actions=db.actions()
can_write=actor['role'] in ('entry','admin')
with st.sidebar:
    st.title('🛡 Security KPI')
    st.caption('Avtozavod · nazorat va natija')
    page=st.radio('Menyu',['Dashboard','Ma’lumot kiritish','Excel / CSV yuklash','KPI kartalari','Chora-tadbirlar','Hisobotlar','Sozlamalar'])
    st.divider();st.caption(actor['code']+' · '+actor['role'])
    if users and st.button('Chiqish'):st.session_state.pop('actor',None);st.rerun()
    st.caption('Oqim: davr → lavozim → shablon → ma’lumot → tekshiruv → hisobot')
st.caption(settings.get('org','Avtozavod'))
st.title(page)
st.caption('BYD rasmiy mahsuloti emas. Ichki me’yorlar kiritilmaguncha: Tasdiqlash uchun namuna.')
if settings.get('demo')=='1':st.info('DEMO: faqat sun’iy ma’lumotlar. Secrets sozlanmagan bo‘lsa, rollarni sinash uchun demo rol tanlanadi. Haqiqiy ma’lumot kiritmang.')
st.caption('Cloud mahalliy bazani doimiy saqlashni kafolatlamaydi. Sozlamalarda JSON zaxira oling; haqiqiy zavod uchun tasdiqlangan ichki server yoki doimiy baza kerak.')
if st.session_state.get('flash'):st.success(st.session_state.pop('flash'))
def done(msg):st.session_state.flash=msg;st.rerun()
def attempt(fn):
    try:return fn()
    except (ValueError,PermissionError,sqlite3.Error,KeyError,TypeError) as e:st.error(str(e));return None

# Persistent context makes month-to-month entry easier.
a,b,c=st.columns(3)
month=a.text_input('Hisobot oyi (YYYY-MM)',value='2026-09',key='period')
if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):st.error('Hisobot oyini YYYY-MM shaklida kiriting.');st.stop()
role=b.selectbox('Baholash darajasi',list(ROLES),index=3,format_func=ROLES.get,key='eval_role')
choices=[t for t in ts if t['role']==role]
tid=c.selectbox('KPI shabloni',[t['id'] for t in choices],format_func=lambda x:x+(' ✓' if next(t for t in choices if t['id']==x)['approved'] else ' · namuna'))
template=next(t for t in choices if t['id']==tid)
options=[e['code'] for e in entities if e['role']==role]
entity=st.selectbox('Baholanadigan kod',options) if options else None
if not options:st.warning('Bu daraja uchun kod yo‘q. Administrator Sozlamalarda kod qo‘shsin.')
selected=[r for r in all_results if r['month']==month and r['template']==tid and r['entity']==entity]
calc=calculate(selected,template)

if page=='Dashboard':
    if role=='department':
        st.caption('Bo‘limga bevosita kiritilgan jami natija yoki bir-birini takrorlamaydigan smenalar yig‘indisini tanlang.')
        use_agg=st.checkbox('Smenalardan surat/maxrajlarni yig‘ish')
        if use_agg:
            shift_tid=st.selectbox('Manba smena metodikasi',[t['id'] for t in ts if t['role']=='shift'])
            shifts=st.multiselect('Agregatga kiradigan smenalar',[e['code'] for e in entities if e['role']=='shift'],default=[e['code'] for e in entities if e['role']=='shift'])
            st.caption('Manbalar bir-birini takrorlamasligi shart. Smena shablonida bo‘lmagan bo‘lim KPI’lari yetishmayotgan deb belgilanadi.')
            selected=aggregate([r for r in all_results if r['month']==month and r['template']==shift_tid],shifts,template) if shifts else []
            calc=calculate(selected,template)
    cols=st.columns(4)
    cols[0].metric('Yakuniy KPI',f"{calc['total']:.2f}" if calc['final'] else 'Dastlabki hisob')
    cols[1].metric('Kuzatilgan vaznli ball',f"{calc['observed_points']:.2f}")
    cols[2].metric('Ma’lumot to‘liqligi',f"{calc['coverage']:.1f}%")
    overdue=[a for a in all_actions if a['entity']==entity and a['state']=='open' and a['due']<date.today().isoformat()]
    cols[3].metric('Muddati o‘tgan choralar',len(overdue))
    st.caption('Kuzatilgan ball yetishmayotgan ma’lumotlarni nol natija deb baholamaydi; u yakuniy reyting emas.')
    if calc['na_weight']:st.info(f"Qo‘llanilmaydigan vazn: {calc['na_weight']:.1f}%. Qayta taqsimlash: {'tasdiqlangan qoida asosida' if calc['redistributed'] else 'amalga oshirilmagan'}.")
    frame=pd.DataFrame(calc['rows']);left,right=st.columns(2)
    valid=frame[frame.score.notna()]
    if not valid.empty:
        left.plotly_chart(px.bar(valid,x='code',y='score',range_y=[0,100],labels={'code':'KPI','score':'Ball'},title='KPI natijalari',color_discrete_sequence=['#267a70']),use_container_width=True)
        lost=valid.assign(loss=valid.effective_weight-valid.contribution).sort_values('loss',ascending=False)
        right.plotly_chart(px.bar(lost,x='code',y='loss',labels={'code':'KPI','loss':'Yo‘qotilgan vaznli ball'},title='Qaysi mezonda ball yo‘qotildi?',color_discrete_sequence=['#bb8449']),use_container_width=True)
    st.subheader('Reja, amalda va hisob')
    st.dataframe(frame[['code','name','unit','plan','actual','rate','target','score','weight','effective_weight','contribution','state']].rename(columns={'rate':'Bajarilish %','score':'Ball','contribution':'Vaznli hissa'}),hide_index=True,use_container_width=True)
    chart_metric=st.selectbox('Reja / amalda grafigi uchun KPI',[m['code'] for m in template['metrics']])
    cr=next(r for r in calc['rows'] if r['code']==chart_metric)
    if cr['plan'] is not None and cr['actual'] is not None:st.plotly_chart(px.bar(x=['Reja','Amalda'],y=[cr['plan'],cr['actual']],labels={'x':'','y':cr['unit']},title=cr['name']),use_container_width=True)
    st.subheader('Bir xil metodika bo‘yicha taqqoslash')
    comparisons=[]
    for e in options:
        cc=calculate([r for r in all_results if r['entity']==e and r['month']==month and r['template']==tid],template)
        comparisons.append({'Kod':e,'Ball':cc['total'] if cc['final'] else None,'To‘liqlik %':cc['coverage'],'Holat':'Yakuniy hisob' if cc['final'] else 'Dastlabki'})
    st.dataframe(pd.DataFrame(comparisons),hide_index=True,use_container_width=True)
    history=[]
    for mo in sorted({r['month'] for r in all_results if r['entity']==entity and r['template']==tid}):
        cc=calculate([r for r in all_results if r['entity']==entity and r['month']==mo and r['template']==tid],template)
        history.append({'Oy':mo,'Kuzatilgan ball':cc['observed_points'],'To‘liqlik %':cc['coverage']})
    if history:st.plotly_chart(px.line(pd.DataFrame(history),x='Oy',y=['Kuzatilgan ball','To‘liqlik %'],markers=True,title='Dinamika — shu kod va metodika; dastlabki ball yakuniy reyting emas'),use_container_width=True)
    if role=='department' and use_agg and can_write and entity and st.button('Agregat hisobdan qoralama yaratish'):
        snap=dict(org=settings['org'],month=month,entity=entity,template=copy.deepcopy(template),calculation=calc,analysis=analysis(calc),actions=[a for a in all_actions if a['entity']==entity and a['month']==month],inputs=selected,aggregate_sources=shifts,source_template=shift_tid)
        rid=db.create_report(snap,actor);done('Agregat qoralama yaratildi: '+rid+' — Hisobotlar menyusida oching.')
    st.subheader('Tahlil')
    for line in analysis(calc):st.write('• '+line)

elif page=='Ma’lumot kiritish':
    if not can_write:st.info('Ushbu rol ma’lumotlarni faqat ko‘radi.');st.stop()
    if not entity:st.stop()
    code=st.selectbox('KPI',[m['code'] for m in template['metrics']],format_func=lambda k:k+' — '+METRICS[k]['name'])
    m=METRICS[code];old=next((r for r in selected if r['metric']==code),{})
    st.info(f"Manba: {m['source']}. Birlik: {m['unit']}. Reja misoli: {m['example']}. Formula: amalda / reja × 100.")
    with st.form('manual_'+str(entity)+tid+code+month):
        state=st.selectbox('Holat',['ok','missing','na'],index=['ok','missing','na'].index(old.get('state','ok')),format_func=STATES.get)
        l,r=st.columns(2)
        plan=l.text_input(m['plan_label'],value='' if old.get('plan') is None else str(old['plan']),help='Bo‘sh maydon nol emas. missing yoki na holatida bo‘sh qoldiring.')
        actual=r.text_input(m['actual_label'],value='' if old.get('actual') is None else str(old['actual']))
        evidence=st.text_input('Dalil kodi / hujjat raqami',old.get('evidence',''),help='ok va na uchun majburiy; maxfiy tafsilot kerak emas.')
        note=st.text_area('Izoh / istisno sababi',old.get('note',''))
        confirmed=st.checkbox('Mavjud yozuv bo‘lsa yangilanishini tasdiqlayman',value=not bool(old))
        if st.form_submit_button('Saqlash',type='primary'):
            row=dict(month=month,entity=entity,template=tid,metric=code,plan=plan,actual=actual,state=state,evidence=evidence,note=note,entered_by=actor['code'],checked_by='')
            if not confirmed:st.error('Yangilashni tasdiqlang.')
            else:
                n=attempt(lambda:db.import_rows([row],actor,db.digest(all_results)))
                if n is not None:done('Ma’lumot saqlandi.')

elif page=='Excel / CSV yuklash':
    st.subheader('1. Namunani oling')
    paths=list((db.ROOT/'templates').glob('*'))
    for path in paths:
        if path.suffix in ('.xlsx','.csv'):st.download_button(path.name,path.read_bytes(),path.name,key=path.name)
    st.caption('Excel’dan faqat Oylik_natijalar sahifasi import qilinadi. Xodimlar va metodika Sozlamalarda, chora-tadbirlar o‘z menyusida boshqariladi. Qo‘shimcha sahifalar yig‘ish yo‘riqnomasi bo‘lib, ikki marta hisoblanmaydi.')
    if not can_write:st.stop()
    file=st.file_uploader('2. Excel yoki CSV yuklang',type=['xlsx','csv'])
    if file:
        raw=attempt(lambda:read_file(file.getvalue(),file.name))
        if raw is not None:
            with st.expander('3. Ustunlarni moslashtirish',expanded=not set(FIELDS).issubset(raw.columns)):
                mapping={}
                for field in FIELDS:
                    cols=['—']+list(raw.columns);choice=st.selectbox(field,cols,index=cols.index(field) if field in cols else 0,key='map_'+field)
                    if choice!='—':mapping[field]=choice
            if len(mapping)!=len(FIELDS):st.warning('Barcha ustunlarni moslashtiring. Ixtiyoriy qiymatlar bo‘sh bo‘lishi mumkin, lekin ustun mavjud bo‘lsin.')
            elif len(set(mapping.values()))!=len(mapping):st.error('Bitta ustunni ikki maydonga moslashtirib bo‘lmaydi.')
            else:
                mapped=[{k:r[v] for k,v in mapping.items()} for r in raw.to_dict('records')]
                clean,errors=validate_rows(mapped)
                if errors:
                    st.error(f'{len(errors)} ta xato. Barcha xatolar tuzatilmaguncha import qilinmaydi.');st.dataframe(pd.DataFrame(errors),hide_index=True)
                    st.download_button('Xatolar CSV',csv_bytes(errors),'Import_xatolari.csv','text/csv')
                else:
                    st.subheader('4. Tekshiring va tasdiqlang');st.dataframe(pd.DataFrame(clean),hide_index=True,use_container_width=True)
                    diff=differences(clean,all_results);st.dataframe(pd.DataFrame(diff),hide_index=True,use_container_width=True)
                    st.caption('Yangi: '+str(sum(x['amal']=='Yangi' for x in diff))+' · Yangilanadi: '+str(sum(x['amal']=='Yangilash' for x in diff)))
                    confirm=st.checkbox('Yuqoridagi ma’lumotlar va o‘zgarishlarni tasdiqlayman')
                    if st.button('Bazaga yozish',disabled=not confirm,type='primary'):
                        n=attempt(lambda:db.import_rows(clean,actor,db.digest(all_results)))
                        if n is not None:done(f'{n} ta yozuv saqlandi. Bir kalit bo‘yicha takror hisoblanmaydi.')

elif page=='KPI kartalari':
    st.info(template['label']+' · versiya '+str(template['version']))
    for m in template['metrics']:
        with st.expander(m['code']+' — '+m['name']):
            st.write('Maqsad: '+m['name']+' bajarilishini o‘lchash.');st.write('Manba: '+m['source'])
            st.write(f"Mas’ul: {ROLES[role]}. Vazn: {m['weight']}%. Maqsadli daraja: {m['target']}%.")
            st.write('Formula: amalda / reja × 100; KPI balli = min(100, bajarilish / maqsad × 100).')
            st.write('Namuna chegaralar: 90–100 yaxshi; 70–90 dan past kuzatuvda; 70 dan past e’tibor kerak. Ichki tasdiq talab etiladi.')
            st.write('Ta’sir doirasi: o‘z vakolatidagi nazorat, bajarish va hujjatlashtirish. Bo‘lim natijasi shaxsga avtomatik berilmaydi.')
            st.write('Istisno: ish/hodisa bo‘lmagan davrda asosli na; hujjat yetishmasa missing. Nosozlik ta’mirlash emas, o‘z vaqtida xabar berish orqali baholanadi.')
    st.dataframe(pd.DataFrame(DICTIONARY,columns=['Maydon','Mazmun','Birlik','Misol','Majburiy','Manba']),hide_index=True,use_container_width=True)

elif page=='Chora-tadbirlar':
    visible=[a for a in all_actions if a['entity']==entity and a['month']==month]
    st.dataframe(pd.DataFrame(visible),hide_index=True,use_container_width=True)
    if can_write and entity:
        ids=['Yangi']+[a['id'] for a in visible];aid=st.selectbox('Vazifa',ids)
        old=next((a for a in visible if a['id']==aid),{})
        with st.form('action_'+aid):
            task=st.text_area('Vazifa',old.get('task',''));owner=st.text_input('Mas’ul kodi',old.get('owner',entity));due=st.date_input('Muddat',value=date.fromisoformat(old['due']) if old else date.today())
            state=st.selectbox('Holat',['open','closed'],index=1 if old.get('state')=='closed' else 0)
            if st.form_submit_button('Vazifani saqlash'):
                try:db.save_action(dict(id=old.get('id'),month=month,entity=entity,task=task,owner=owner,due=due.isoformat(),state=state),actor);done('Vazifa saqlandi.')
                except (ValueError,PermissionError) as e:st.error(str(e))

elif page=='Hisobotlar':
    st.caption('Hisobot yaratilganda raqamlar, metodika, tahlil va vazifalar alohida nusxaga olinadi. Keyingi tahrirlar ushbu nusxani o‘zgartirmaydi.')
    if can_write and entity and st.button('Joriy hisobdan qoralama yaratish',type='primary'):
        snap=dict(org=settings['org'],month=month,entity=entity,template=copy.deepcopy(template),calculation=calc,analysis=analysis(calc),actions=[a for a in all_actions if a['entity']==entity and a['month']==month],inputs=selected)
        rid=attempt(lambda:db.create_report(snap,actor))
        if rid:done('Qoralama yaratildi: '+rid)
    reps=db.reports();reps=[r for r in reps if r['payload']['entity']==entity and r['payload']['month']==month]
    if reps:
        rid=st.selectbox('Saqlangan hisobot',[r['id'] for r in reps],format_func=lambda x:x+' · '+next(r['state'] for r in reps if r['id']==x))
        report=next(r for r in reps if r['id']==rid);snap=report['payload']
        st.write(f"Holat: **{report['state']}** · Muallif: {report['creator']} · Tekshiruvchi: {report['reviewer'] or '—'} · Tasdiqlovchi: {report['approver'] or '—'}")
        st.dataframe(pd.DataFrame(snap['calculation']['rows']),hide_index=True,use_container_width=True)
        a,b=st.columns(2)
        a.download_button('Excel hisobot',excel_report(report),f'Security_KPI_{rid}.xlsx')
        b.download_button('PDF hisobot',pdf_report(report),f'Security_KPI_{rid}.pdf','application/pdf')
        if report['state']!='Tasdiqlandi' and actor['role'] in ('reviewer','admin'):
            confirm=st.checkbox('Hisobot nusxasini tekshirdim; keyingi holatga o‘tkazishni tasdiqlayman')
            if st.button('Tekshirildi deb belgilash' if report['state']=='Qoralama' else 'Tasdiqlash',disabled=not confirm):
                try:db.transition(rid,actor);done('Hisobot holati yangilandi.')
                except (ValueError,PermissionError) as e:st.error(str(e))
    else:st.info('Bu kod va davr uchun saqlangan hisobot yo‘q.')

else:
    if actor['role']!='admin':st.info('Sozlamalar faqat administrator uchun.');st.stop()
    with st.form('org'):
        name=st.text_input('Tashkilot nomi',settings['org'])
        if st.form_submit_button('Nomni saqlash'):
            if name.strip():db.set_setting('org',name.strip(),actor);done('Saqlandi.')
    st.subheader('Xodim va smena kodlari');st.dataframe(pd.DataFrame(entities),hide_index=True)
    with st.form('entity'):
        code=st.text_input('Yangi kod',help='A–Z, raqam, tire va pastki chiziq; masalan SM-04');erole=st.selectbox('Lavozim',list(ROLES),format_func=ROLES.get);label=st.text_input('Ko‘rinadigan nom')
        if st.form_submit_button('Kod qo‘shish'):
            try:db.add_entity(code,erole,label,actor);done('Kod qo‘shildi.')
            except (ValueError,sqlite3.Error) as e:st.error(str(e))
    st.subheader('Metodikani sozlash')
    st.caption('Vazn/maqsad tahriri yangi versiya yaratadi. Importdagi template ustunida yangi ID ni ko‘rsating. Eski versiyalar va hisobotlar saqlanadi.')
    editable=pd.DataFrame([{'code':m['code'],'name':m['name'],'weight':m['weight'],'target':m['target']} for m in template['metrics']])
    edit=st.data_editor(editable,disabled=['code','name'],hide_index=True,key='weights_'+tid)
    redistribution=st.checkbox('Asosli na chiqarilganda vaznlarni qolgan KPI’lar o‘rtasida mutanosib taqsimlash',value=template['redistribute'])
    if st.button('Yangi metodika versiyasini saqlash'):
        try:
            new=copy.deepcopy(template);new['redistribute']=redistribution
            for m,row in zip(new['metrics'],edit.to_dict('records')):m.update(weight=float(row['weight']),target=float(row['target']))
            nid=db.save_template(new,actor);done('Yangi shablon: '+nid)
        except (ValueError,TypeError) as e:st.error(str(e))
    if not template['approved']:
        approve=st.checkbox('Tanlangan metodika va istisno qoidasini ichki foydalanish uchun tasdiqlayman')
        if st.button('Metodikani tasdiqlash',disabled=not approve):db.approve_template(tid,actor);done('Metodika tasdiqlandi.')
    st.subheader('Zaxira va tiklash')
    st.download_button('To‘liq JSON zaxira',db.backup(),'Security_KPI_backup.json','application/json')
    st.caption('Tiklash operatsion ma’lumotlarni almashtiradi. Mavjud hisobot va audit tarixi o‘chmaydi. Faqat zaxirada bor hisobotlar yangi tekshiruv uchun qoralama sifatida qo‘shiladi.')
    upload=st.file_uploader('JSON zaxira',type=['json']);confirm=st.checkbox('Operatsion bazani almashtirishni tasdiqlayman')
    if st.button('Tiklash',disabled=not(upload and confirm)):
        try:
            if upload.size>20_000_000:raise ValueError('20 MB dan katta fayl.')
            db.restore(json.loads(upload.getvalue()),actor);done('Zaxira tiklandi.')
        except (ValueError,TypeError,KeyError,sqlite3.Error) as e:st.error(str(e))
    st.subheader('Ishchi rejim')
    st.caption('Secrets’da kamida uchta alohida kod (entry, reviewer, admin) sozlang. Haqiqiy ma’lumotdan oldin demo natijalarini tozalang. Kodlar va metodika qoladi.')
    confirmed=st.checkbox('Barcha demo natijalar, vazifalar va qoralamalarni tozalashni tasdiqlayman')
    if st.button('Demo ma’lumotlarni tozalash va ishchi rejimga o‘tish',disabled=not(confirmed and users and settings.get('demo')=='1')):
        with db.connect() as conn:
            conn.execute('DELETE FROM results');conn.execute('DELETE FROM actions');conn.execute("DELETE FROM reports WHERE state!='Tasdiqlandi'");db.log(conn,actor,'demo_reset','database');conn.execute("UPDATE settings SET v='0' WHERE k='demo'")
        done('Ishchi rejim yoqildi.')
    st.subheader('O‘zgarishlar jurnali');st.dataframe(pd.DataFrame(db.audit()),hide_index=True,use_container_width=True)
