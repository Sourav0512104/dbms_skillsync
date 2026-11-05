import concurrent.futures,os,psycopg
DB=os.getenv('DATABASE_URL','postgresql://skillsync:skillsync@localhost:5432/skillsync')
def attempt(uid,rid):
 try:
  with psycopg.connect(DB) as conn:
   with conn.cursor() as cur: cur.execute('SELECT * FROM apply_to_role(%s,%s)',(uid,rid)); row=cur.fetchone()
   conn.commit()
  return ('SUCCESS',uid,row)
 except Exception as e:return ('REJECTED',uid,str(e))
if __name__=='__main__':
 rid=int(os.getenv('ROLE_ID','1'))
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: results=list(ex.map(lambda u:attempt(u,rid),range(100,106)))
 for r in results: print(r)
 print('Property: successful applications cannot exceed the role slot count.')
