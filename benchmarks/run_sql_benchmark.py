import os,psycopg,pandas as pd
DB=os.getenv('DATABASE_URL','postgresql://skillsync:skillsync@localhost:5432/skillsync')
Q={
'profile_filter':"SELECT u.user_id,u.full_name FROM users u JOIN user_skills us ON us.user_id=u.user_id WHERE u.availability_hours>=10 AND us.skill_id=1 LIMIT 100",
'applications_by_role':"SELECT role_id,status,count(*) FROM applications GROUP BY role_id,status ORDER BY count(*) DESC LIMIT 100",
'events_recent':"SELECT event_type,count(*) FROM benchmark_events WHERE created_at>=now()-interval '30 days' GROUP BY event_type",
'correlated_filter':"SELECT count(*) FROM users WHERE availability_hours>=10 AND experience_years>=3"}
def run(label,q):
 with psycopg.connect(DB) as c:
  with c.cursor() as cur:
   cur.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q); p=cur.fetchone()[0][0]
   return {'query':label,'execution_ms':p['Execution Time'],'planning_ms':p['Planning Time'],'plan_rows':p['Plan'].get('Plan Rows'),'actual_rows':p['Plan'].get('Actual Rows'),'shared_hit_blocks':p['Plan'].get('Shared Hit Blocks'),'shared_read_blocks':p['Plan'].get('Shared Read Blocks')}
def main():
 Path='results'; os.makedirs(Path,exist_ok=True); before=[run(k,q) for k,q in Q.items()]; pd.DataFrame(before).assign(stage='before').to_csv(Path+'/before_tuning.csv',index=False)
 with psycopg.connect(DB) as c:
  with c.cursor() as cur:
   cur.execute('CREATE INDEX IF NOT EXISTS idx_users_avail_exp ON users(availability_hours,experience_years)'); cur.execute('CREATE INDEX IF NOT EXISTS idx_us_skill_user ON user_skills(skill_id,user_id)'); cur.execute('CREATE STATISTICS IF NOT EXISTS stats_user_avail_exp (dependencies,mcv) ON availability_hours,experience_years FROM users'); cur.execute('ANALYZE users'); cur.execute('ANALYZE user_skills')
  c.commit()
 after=[run(k,q) for k,q in Q.items()]; pd.DataFrame(after).assign(stage='after').to_csv(Path+'/after_tuning.csv',index=False); pd.concat([pd.DataFrame(before).assign(stage='before'),pd.DataFrame(after).assign(stage='after')]).to_csv(Path+'/latency_before_after.csv',index=False); print(pd.DataFrame(after))
if __name__=='__main__': main()
