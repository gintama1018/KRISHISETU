-- ================================================================
-- KrishiSetu — Supabase PostgreSQL Database Schema
-- 6 Core Tables: Farmer Profiles, Health Observations (FHIR),
--                DPDP Compliance, Push, Insurance, Audit Log
-- ================================================================

-- 1. Farmers table
CREATE TABLE IF NOT EXISTS farmers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  phone_hash TEXT NOT NULL,
  crop TEXT,
  state TEXT,
  district TEXT,
  village_code TEXT,
  area_acres FLOAT,
  language TEXT DEFAULT 'en',
  consent_given BOOLEAN DEFAULT true,
  consent_timestamp TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Push Subscriptions table
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT,
  village_code TEXT,
  endpoint TEXT NOT NULL UNIQUE,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Insurance Events table (SHA-256 Tamper-Evident Evidence Log)
CREATE TABLE IF NOT EXISTS insurance_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT,
  event_type TEXT,
  crop TEXT,
  risk_score FLOAT,
  advisory_text TEXT,
  evidence_hash TEXT,   -- SHA-256 hash for tamper-evidence (not immutability)
  pest_detected TEXT,
  spray_product TEXT,
  lat FLOAT,
  lon FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Consent Records table (India DPDP Act 2023 Compliance)
CREATE TABLE IF NOT EXISTS consent_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT UNIQUE NOT NULL,
  phone_hash TEXT NOT NULL,
  consent_given BOOLEAN DEFAULT true,
  consent_method TEXT DEFAULT 'app',
  consent_timestamp TIMESTAMPTZ DEFAULT now(),
  ip_address TEXT,
  data_uses TEXT,
  erasure_requested BOOLEAN DEFAULT false,
  erasure_timestamp TIMESTAMPTZ,
  scheduled_deletion TIMESTAMPTZ,  -- 30-day erasure window (manual execution required)
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Audit Log table (DPDP Audit Trail — stored in Supabase, NOT SQLite)
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT,
  action TEXT NOT NULL,
  phone_hash TEXT,
  consent_given BOOLEAN,
  ip_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Health Observations table (ASHA Worker Records — FHIR R4 Compatible)
CREATE TABLE IF NOT EXISTS health_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT NOT NULL,
  asha_id TEXT NOT NULL,
  village_code TEXT,
  symptoms TEXT[],              -- Array of symptom strings
  temp_c FLOAT,
  humidity_pct FLOAT,
  pesticide_hours_week FLOAT DEFAULT 0,
  has_ppe BOOLEAN DEFAULT false,
  heat_risk_score INT,
  pesticide_risk_score INT,
  composite_risk_score INT,
  risk_level TEXT,              -- LOW / MODERATE / HIGH / CRITICAL
  fhir_bundle_id TEXT,          -- UUID of the generated FHIR R4 Bundle
  notes TEXT,
  recorded_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast village-level health queries
CREATE INDEX IF NOT EXISTS idx_health_obs_village ON health_observations(village_code);
CREATE INDEX IF NOT EXISTS idx_health_obs_farmer  ON health_observations(farmer_id);
CREATE INDEX IF NOT EXISTS idx_farmers_village    ON farmers(village_code);
