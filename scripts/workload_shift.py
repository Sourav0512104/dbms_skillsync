import os,time,random,statistics,psycopg
DB=os.getenv('DATABASE_URL','postgresql://skillsync:skillsync@localhost:5432/skillsync')
Q1="SELECT u.user_id FROM users u JOIN user_skills us ON us.user_id=u.user_id WHERE us.skill_id=%s AND u.availability_hours>=10 LIMIT 50"
Q2="SELECT event_type,date_trunc('day',created_at),count(*) FROM benchmark_events GROUP BY event_type,date_trunc('day',created_at) ORDER BY 3 DESC LIMIT 50"
def bench(q,args,n=50):
 xs=[]
 with psycopg.connect(DB) as c:
  with c.cursor() as cur:
   for _ in range(n):
    t=time.perf_counter(); cur.execute(q,args); cur.fetchall(); xs.append((time.perf_counter()-t)*1000)
 return {'median_ms':statistics.median(xs),'p95_ms':sorted(xs)[int(.95*len(xs))-1]}
if __name__=='__main__':
 print('W1 profile-heavy:',bench(Q1,(1,),80)); print('W2 analytics-heavy:',bench(Q2,(),80))
