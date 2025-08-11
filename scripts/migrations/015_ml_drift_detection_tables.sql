-- Migration: Create ML Drift Detection Tables
-- Description: Tables for tracking ML model drift and baselines
-- Date: 2025-07-29

-- Table for storing baseline distributions
CREATE TABLE IF NOT EXISTS ml_baseline_distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(255) NOT NULL,
    feature_name VARCHAR(255) NOT NULL,
    distribution JSONB NOT NULL, -- Array of values representing the baseline distribution
    statistics JSONB, -- Optional statistics (mean, std, quantiles, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint on model and feature combination
    UNIQUE(model_name, feature_name)
);

-- Table for baseline performance metrics
CREATE TABLE IF NOT EXISTS ml_baseline_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(255) NOT NULL UNIQUE,
    baseline_score FLOAT NOT NULL,
    metric_name VARCHAR(100) DEFAULT 'accuracy',
    sample_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracking predictions (for drift analysis)
CREATE TABLE IF NOT EXISTS ml_prediction_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(255) NOT NULL,
    features JSONB NOT NULL,
    prediction JSONB NOT NULL,
    actual JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for drift detection reports
CREATE TABLE IF NOT EXISTS ml_drift_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(255) NOT NULL,
    detection_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    drift_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    metrics JSONB NOT NULL, -- KS stats, PSI, etc.
    affected_features TEXT[],
    recommendations TEXT[],
    requires_retraining BOOLEAN DEFAULT FALSE,
    confidence FLOAT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_ml_baseline_dist_model ON ml_baseline_distributions(model_name);
CREATE INDEX idx_ml_baseline_perf_model ON ml_baseline_performance(model_name);
CREATE INDEX idx_ml_prediction_tracking_model ON ml_prediction_tracking(model_name);
CREATE INDEX idx_ml_prediction_tracking_created ON ml_prediction_tracking(created_at);
CREATE INDEX idx_ml_drift_reports_model ON ml_drift_reports(model_name);
CREATE INDEX idx_ml_drift_reports_timestamp ON ml_drift_reports(detection_timestamp);
CREATE INDEX idx_ml_drift_reports_severity ON ml_drift_reports(severity);
CREATE INDEX idx_ml_drift_reports_unresolved ON ml_drift_reports(model_name, resolved) WHERE NOT resolved;

-- Enable RLS
ALTER TABLE ml_baseline_distributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_baseline_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_prediction_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_drift_reports ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust based on your auth setup)
-- For now, we'll create permissive policies for authenticated users

-- Baseline distributions policies
CREATE POLICY "Enable read access for all users" ON ml_baseline_distributions
    FOR SELECT USING (true);

CREATE POLICY "Enable write access for authenticated users" ON ml_baseline_distributions
    FOR ALL USING (auth.role() = 'authenticated');

-- Baseline performance policies
CREATE POLICY "Enable read access for all users" ON ml_baseline_performance
    FOR SELECT USING (true);

CREATE POLICY "Enable write access for authenticated users" ON ml_baseline_performance
    FOR ALL USING (auth.role() = 'authenticated');

-- Prediction tracking policies
CREATE POLICY "Enable read access for all users" ON ml_prediction_tracking
    FOR SELECT USING (true);

CREATE POLICY "Enable write access for authenticated users" ON ml_prediction_tracking
    FOR ALL USING (auth.role() = 'authenticated');

-- Drift reports policies
CREATE POLICY "Enable read access for all users" ON ml_drift_reports
    FOR SELECT USING (true);

CREATE POLICY "Enable write access for authenticated users" ON ml_drift_reports
    FOR ALL USING (auth.role() = 'authenticated');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_ml_baseline_distributions_updated_at BEFORE UPDATE
    ON ml_baseline_distributions FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ml_baseline_performance_updated_at BEFORE UPDATE
    ON ml_baseline_performance FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for drift detection summary
CREATE OR REPLACE VIEW ml_drift_summary AS
SELECT 
    model_name,
    COUNT(*) as total_detections,
    COUNT(*) FILTER (WHERE severity = 'critical') as critical_count,
    COUNT(*) FILTER (WHERE severity = 'high') as high_count,
    COUNT(*) FILTER (WHERE severity = 'medium') as medium_count,
    COUNT(*) FILTER (WHERE severity = 'low') as low_count,
    COUNT(*) FILTER (WHERE requires_retraining AND NOT resolved) as pending_retraining,
    MAX(detection_timestamp) as last_detection,
    ARRAY_AGG(DISTINCT drift_type) as drift_types_detected
FROM ml_drift_reports
WHERE detection_timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY model_name
ORDER BY critical_count DESC, high_count DESC;

-- Grant permissions on view
GRANT SELECT ON ml_drift_summary TO authenticated;

COMMENT ON TABLE ml_baseline_distributions IS 'Stores baseline feature distributions for drift detection';
COMMENT ON TABLE ml_baseline_performance IS 'Stores baseline performance metrics for models';
COMMENT ON TABLE ml_prediction_tracking IS 'Tracks individual predictions for drift analysis';
COMMENT ON TABLE ml_drift_reports IS 'Stores drift detection reports and recommendations';
COMMENT ON VIEW ml_drift_summary IS 'Summary view of recent drift detections by model';