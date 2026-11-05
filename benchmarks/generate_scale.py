import os,argparse,psycopg
DB=os.getenv('DATABASE_URL','postgresql://skillsync:skillsync@localhost:5432/skillsync')
def main():
 p=argparse.ArgumentParser(); p.add_argument('--users',type=int,default=100000); p.add_argument('--events',type=int,default=500000); a=p.parse_args()
 with psycopg.connect(DB) as c:
  with c.cursor() as cur:
   cur.execute("INSERT INTO users(full_name,email,availability_hours,experience_years) SELECT 'Synthetic '||g,'synthetic_'||g||'@skillsync.local',CASE WHEN random()<0.65 THEN 10 ELSE (5+floor(random()*26))::int END,round((random()*7)::numeric,1) FROM generate_series(1,%s) g",(a.users,))
   cur.execute("INSERT INTO benchmark_events(created_at,event_type,payload) SELECT now()-(random()*interval '365 days'),CASE WHEN random()<0.8 THEN 'profile_search' ELSE 'analytics' END,jsonb_build_object('skill_id',1+(floor(power(random(),2)*30))::int) FROM generate_series(1,%s)",(a.events,))
  c.commit()
 print('Scale data generated.');
if __name__=='__main__': main()
