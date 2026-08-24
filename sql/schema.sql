-- FinLens schema
--
-- Design notes:
--  * Money is NUMERIC(14,2), not FLOAT. Floating point cannot represent
--    decimal fractions exactly (0.1 + 0.2 != 0.3), which is unacceptable
--    for currency. NUMERIC is exact decimal arithmetic.
--  * Ratios are NUMERIC(6,4) -- decimals, matching the engine convention
--    (0.3424, not 34.24).
--  * Assumptions are JSONB rather than one column per field, because
--    SimulationAssumptions will gain fields over time and we always read
--    it as a whole. Results use typed columns, because we filter and
--    aggregate on them.

DROP TABLE IF EXISTS simulation_results CASCADE;
DROP TABLE IF EXISTS simulation_runs CASCADE;
DROP TABLE IF EXISTS scenario_evaluations CASCADE;
DROP TABLE IF EXISTS loan_scenarios CASCADE;
DROP TABLE IF EXISTS financial_profiles CASCADE;


CREATE TABLE financial_profiles (
    id                           BIGSERIAL PRIMARY KEY,
    monthly_income               NUMERIC(14,2) NOT NULL CHECK (monthly_income >= 0),
    monthly_expenses             NUMERIC(14,2) NOT NULL CHECK (monthly_expenses >= 0),
    existing_emi                 NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (existing_emi >= 0),
    savings                      NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (savings >= 0),
    emergency_fund_target_months INTEGER       NOT NULL DEFAULT 6 CHECK (emergency_fund_target_months > 0),
    created_at                   TIMESTAMPTZ   NOT NULL DEFAULT now()
);


CREATE TABLE loan_scenarios (
    id           BIGSERIAL PRIMARY KEY,
    profile_id   BIGINT       NOT NULL REFERENCES financial_profiles(id) ON DELETE CASCADE,
    label        TEXT         NOT NULL,
    principal    NUMERIC(14,2) NOT NULL CHECK (principal > 0),
    annual_rate  NUMERIC(6,3)  NOT NULL CHECK (annual_rate >= 0),
    tenure_years INTEGER       NOT NULL CHECK (tenure_years > 0),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),

    -- A profile shouldn't have two scenarios with the same name;
    -- deltas are reported by label, so duplicates would be ambiguous.
    UNIQUE (profile_id, label)
);


CREATE TABLE scenario_evaluations (
    id                      BIGSERIAL PRIMARY KEY,
    scenario_id             BIGINT        NOT NULL REFERENCES loan_scenarios(id) ON DELETE CASCADE,
    emi                     NUMERIC(14,2) NOT NULL,
    total_interest          NUMERIC(14,2) NOT NULL,
    total_repayment         NUMERIC(14,2) NOT NULL,
    total_emi               NUMERIC(14,2) NOT NULL,
    debt_to_income          NUMERIC(6,4),          -- nullable: undefined at zero income
    monthly_surplus         NUMERIC(14,2) NOT NULL,
    savings_rate            NUMERIC(6,4),
    emergency_fund_months   NUMERIC(8,2),
    expense_coverage_months NUMERIC(8,2),
    stress_score            NUMERIC(5,2)  CHECK (stress_score BETWEEN 0 AND 100),
    stress_band             TEXT          CHECK (stress_band IN ('low','moderate','elevated','high')),
    stress_components       JSONB,                 -- component breakdown, for explainability
    evaluated_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),

    UNIQUE (scenario_id)   -- one cached evaluation per scenario
);


CREATE TABLE simulation_runs (
    id             BIGSERIAL PRIMARY KEY,
    scenario_id    BIGINT      NOT NULL REFERENCES loan_scenarios(id) ON DELETE CASCADE,
    n_trials       INTEGER     NOT NULL CHECK (n_trials > 0),
    horizon_months INTEGER     NOT NULL CHECK (horizon_months > 0),
    seed           BIGINT,                        -- NULL means unseeded / non-reproducible
    assumptions    JSONB       NOT NULL,          -- full SimulationAssumptions snapshot
    total_emi      NUMERIC(14,2) NOT NULL,        -- the EMI actually simulated against
    run_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE TABLE simulation_results (
    id                         BIGSERIAL PRIMARY KEY,
    run_id                     BIGINT        NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    p_negative_cashflow_month  NUMERIC(6,4)  NOT NULL CHECK (p_negative_cashflow_month BETWEEN 0 AND 1),
    p_thin_margin_month        NUMERIC(6,4)  NOT NULL CHECK (p_thin_margin_month BETWEEN 0 AND 1),
    p_savings_depleted         NUMERIC(6,4)  NOT NULL CHECK (p_savings_depleted BETWEEN 0 AND 1),
    median_negative_months     INTEGER       NOT NULL,
    p95_negative_months        INTEGER       NOT NULL,
    mean_negative_months       NUMERIC(6,2)  NOT NULL,
    median_thin_months         INTEGER       NOT NULL,
    median_ending_savings      NUMERIC(14,2) NOT NULL,
    p5_ending_savings          NUMERIC(14,2) NOT NULL,
    p25_ending_savings         NUMERIC(14,2) NOT NULL,
    p5_min_monthly_surplus     NUMERIC(14,2) NOT NULL,
    median_min_monthly_surplus NUMERIC(14,2) NOT NULL,

    UNIQUE (run_id)
);


-- Indexes on foreign keys used for lookups. Postgres does NOT create these
-- automatically for FK columns (it does for PRIMARY KEY and UNIQUE), and
-- every query we care about filters by parent id.
CREATE INDEX idx_loan_scenarios_profile   ON loan_scenarios(profile_id);
CREATE INDEX idx_simulation_runs_scenario ON simulation_runs(scenario_id);