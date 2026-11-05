CREATE TABLE IF NOT EXISTS users (
 user_id BIGSERIAL PRIMARY KEY, full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 availability_hours INTEGER NOT NULL DEFAULT 10 CHECK (availability_hours BETWEEN 0 AND 80),
 experience_years NUMERIC(4,1) NOT NULL DEFAULT 0 CHECK (experience_years >= 0),
 password_hash TEXT,
 profile_visible BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS projects (
 project_id BIGSERIAL PRIMARY KEY, owner_id BIGINT NOT NULL REFERENCES users(user_id), name TEXT NOT NULL,
 project_type TEXT NOT NULL CHECK (project_type IN ('hackathon','lab','startup','research','competition')),
 status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','draft')), created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS skills (
 skill_id BIGSERIAL PRIMARY KEY, canonical_name TEXT NOT NULL UNIQUE, category TEXT NOT NULL, description TEXT);
CREATE TABLE IF NOT EXISTS project_roles (
 role_id BIGSERIAL PRIMARY KEY, project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 title TEXT NOT NULL, role_type TEXT NOT NULL CHECK (role_type IN ('frontend','backend','ml','data','devops','design','security','research','other')),
 slots_total INTEGER NOT NULL CHECK (slots_total > 0), slots_filled INTEGER NOT NULL DEFAULT 0 CHECK (slots_filled >= 0 AND slots_filled <= slots_total),
 status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')), min_experience NUMERIC(4,1) NOT NULL DEFAULT 0 CHECK (min_experience >= 0), created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS user_skills (
 user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, skill_id BIGINT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
 proficiency SMALLINT NOT NULL CHECK (proficiency BETWEEN 1 AND 5), years_used NUMERIC(4,1) NOT NULL DEFAULT 0 CHECK (years_used >= 0), PRIMARY KEY(user_id,skill_id));
CREATE TABLE IF NOT EXISTS role_skills (
 role_id BIGINT NOT NULL REFERENCES project_roles(role_id) ON DELETE CASCADE, skill_id BIGINT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
 importance SMALLINT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5), PRIMARY KEY(role_id,skill_id));
CREATE TABLE IF NOT EXISTS applications (
 application_id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(user_id), role_id BIGINT NOT NULL REFERENCES project_roles(role_id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','rejected','withdrawn')), applied_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id,role_id));
CREATE TABLE IF NOT EXISTS milestones (
 milestone_id BIGSERIAL PRIMARY KEY, project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 title TEXT NOT NULL, due_at TIMESTAMPTZ NOT NULL, completed BOOLEAN NOT NULL DEFAULT FALSE);
CREATE TABLE IF NOT EXISTS profile_vectors (
 user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE, embedding vector(384) NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS benchmark_events (
 event_id BIGSERIAL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), user_id BIGINT, project_id BIGINT,
 event_type TEXT NOT NULL, payload JSONB) PARTITION BY RANGE(created_at);
CREATE TABLE IF NOT EXISTS benchmark_events_2026 PARTITION OF benchmark_events FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE IF NOT EXISTS benchmark_events_2027 PARTITION OF benchmark_events FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');
CREATE INDEX IF NOT EXISTS idx_users_availability ON users(availability_hours);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_roles_project ON project_roles(project_id);
CREATE INDEX IF NOT EXISTS idx_roles_open ON project_roles(role_id) WHERE status='open';
CREATE INDEX IF NOT EXISTS idx_user_skills_skill ON user_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_applications_role_status ON applications(role_id,status);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON benchmark_events(event_type,created_at);
CREATE INDEX IF NOT EXISTS idx_profile_vectors_hnsw ON profile_vectors USING hnsw(embedding vector_cosine_ops) WITH(m=16,ef_construction=64);
CREATE OR REPLACE VIEW project_application_summary AS
 SELECT p.project_id,p.name,COUNT(a.application_id) total_applications,
 COUNT(*) FILTER(WHERE a.status='accepted') accepted,COUNT(*) FILTER(WHERE a.status='pending') pending,
 COUNT(*) FILTER(WHERE a.status='rejected') rejected
 FROM projects p LEFT JOIN project_roles r ON r.project_id=p.project_id LEFT JOIN applications a ON a.role_id=r.role_id GROUP BY p.project_id,p.name;
CREATE MATERIALIZED VIEW IF NOT EXISTS project_monthly_application_stats AS
SELECT
    r.project_id,
    date_trunc('month', a.applied_at) AS month_start,
    COUNT(*) AS applications,
    COUNT(*) FILTER (
        WHERE a.status = 'accepted'
    ) AS accepted
FROM applications a
JOIN project_roles r
    ON r.role_id = a.role_id
GROUP BY
    r.project_id,
    date_trunc('month', a.applied_at)
WITH NO DATA;
CREATE OR REPLACE FUNCTION close_full_role() RETURNS TRIGGER AS $$ BEGIN IF NEW.slots_filled>=NEW.slots_total THEN NEW.status:='closed'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_close_full_role ON project_roles;
CREATE TRIGGER trg_close_full_role BEFORE INSERT OR UPDATE OF slots_filled,slots_total ON project_roles FOR EACH ROW EXECUTE FUNCTION close_full_role();
CREATE OR REPLACE FUNCTION apply_to_role(p_user_id BIGINT,p_role_id BIGINT) RETURNS applications AS $$
DECLARE r project_roles%ROWTYPE; out_app applications%ROWTYPE;
BEGIN
 SELECT * INTO r FROM project_roles WHERE role_id=p_role_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Role % does not exist',p_role_id; END IF;
 IF r.status<>'open' OR r.slots_filled>=r.slots_total THEN RAISE EXCEPTION 'Role % has no open slots',p_role_id; END IF;
 IF EXISTS(SELECT 1 FROM applications WHERE user_id=p_user_id AND role_id=p_role_id AND status IN('pending','accepted')) THEN RAISE EXCEPTION 'User % already has an active application',p_user_id; END IF;
 INSERT INTO applications(user_id,role_id,status) VALUES(p_user_id,p_role_id,'pending') ON CONFLICT(user_id,role_id) DO UPDATE SET status='pending',applied_at=now() RETURNING * INTO out_app;
 UPDATE project_roles SET slots_filled=slots_filled+1 WHERE role_id=p_role_id;
 RETURN out_app;
END; $$ LANGUAGE plpgsql;
