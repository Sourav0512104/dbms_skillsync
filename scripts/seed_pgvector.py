from app.db import pg_conn,profiles
def main():
 docs=list(profiles.find({}, {'user_id':1,'embedding':1}))
 with pg_conn() as conn:
  with conn.cursor() as cur:
   for d in docs:
    if d.get('embedding'): cur.execute('INSERT INTO profile_vectors(user_id,embedding) VALUES(%s,%s) ON CONFLICT(user_id) DO UPDATE SET embedding=EXCLUDED.embedding,updated_at=now()',(d['user_id'],d['embedding']))
  conn.commit()
 print('Mirrored Mongo embeddings into pgvector.')
if __name__=='__main__': main()
