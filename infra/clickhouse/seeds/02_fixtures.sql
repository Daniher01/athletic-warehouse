-- Athletic Warehouse - Development & Testing Seed Fixtures
-- Isolated from production schemas. Loaded only in local/dev/test environments.

USE athletic_warehouse;

-- 1. Club Semilla
INSERT INTO dim_club (club_id, name, country) VALUES
('11111111-1111-1111-1111-111111111111', 'Athletic Club', 'Spain');

-- 2. Categorías Semilla
INSERT INTO dim_category (category_id, club_id, name, sort_order) VALUES
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111111', 'Primer Equipo', 1),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111111', 'Bilbao Athletic', 2);

-- 3. Jugadores Semilla (4 verified, 1 unverified)
INSERT INTO dim_player (player_id, club_id, category_id, first_name, last_name, nationality, birth_date, position, status) VALUES
('33333333-3333-3333-3333-333333333301', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222201', 'Iñaki', 'Williams', 'Ghana', '1994-06-15', 'Forward', 'verified'),
('33333333-3333-3333-3333-333333333302', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222201', 'Nico', 'Williams', 'Spain', '2002-07-12', 'Forward', 'verified'),
('33333333-3333-3333-3333-333333333303', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222201', 'Oihan', 'Sancet', 'Spain', '2000-04-25', 'Midfielder', 'verified'),
('33333333-3333-3333-3333-333333333304', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222201', 'Unai', 'Simón', 'Spain', '1997-06-11', 'Goalkeeper', 'verified'),
('33333333-3333-3333-3333-333333333305', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222202', 'Mikel', 'Jauregizar', 'Spain', '2003-11-13', 'Midfielder', 'unverified');
