import os,tempfile,unittest,sys
from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import database as db

class AppSmoke(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=db.DB;db.DB=Path(self.tmp.name)/'app.db'
  self.app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
 def tearDown(self):db.DB=self.old;self.tmp.cleanup()
 def test_pages(self):
  self.assertFalse(self.app.exception)
  for role in ['entry','reviewer','admin']:
   next(x for x in self.app.selectbox if x.label=='Demo rol').set_value(role).run()
   for menu in ['Dashboard','Ma’lumot kiritish','Excel / CSV yuklash','KPI kartalari','Chora-tadbirlar','Hisobotlar','Sozlamalar']:
    self.app.radio[0].set_value(menu).run();self.assertFalse(self.app.exception,(role,menu,str(self.app.exception)))
 def test_secrets_login(self):
  from auth import hash_password
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
  app.secrets['users']={'OP01':{'role':'entry','password_hash':hash_password('Example-long-pass')}}
  app.run();self.assertFalse(app.exception)
  app.text_input[0].set_value('OP01');app.text_input[1].set_value('Example-long-pass')
  app.button[0].click().run();self.assertFalse(app.exception)
  self.assertEqual(app.session_state['actor']['code'],'OP01')
  app.radio[0].set_value('Sozlamalar').run();self.assertFalse(app.exception)
  self.assertTrue(any('faqat administrator' in str(x.value) for x in app.info))
 def test_manual_report(self):
  self.app.radio[0].set_value('Ma’lumot kiritish').run()
  next(x for x in self.app.text_input if x.label=='Rejalashtirilgan post-soatlar').set_value('720')
  next(x for x in self.app.text_input if x.label=='Amalda ta’minlangan post-soatlar').set_value('715')
  self.app.checkbox[0].check()
  next(b for b in self.app.button if b.label=='Saqlash').click().run()
  self.assertFalse(self.app.exception);self.assertTrue(any(r['actual']==715 for r in db.results()))
  self.app.radio[0].set_value('Hisobotlar').run()
  next(b for b in self.app.button if b.label=='Joriy hisobdan qoralama yaratish').click().run()
  self.assertFalse(self.app.exception);self.assertEqual(len(db.reports()),1)
  self.assertEqual(len(self.app.get('download_button')),2)

if __name__=='__main__':unittest.main(verbosity=2)
