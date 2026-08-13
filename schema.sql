-- ================================================================
-- KrishiSetu — Supabase PostgreSQL Database Schema
-- 5 Core Tables for Farmer Profiles, DPDP Compliance, Push & Insurance
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

-- 3. Insurance Events table (Tamper-Evident Evidence Log)
CREATE TABLE IF NOT EXISTS insurance_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT,
  event_type TEXT,
  crop TEXT,
  risk_score FLOAT,
  advisory_text TEXT,
  evidence_hash TEXT,
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
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Audit Log table (DPDP Audit Trail)
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id TEXT,
  action TEXT NOT NULL,
  phone_hash TEXT,
  consent_given BOOLEAN,
  ip_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
