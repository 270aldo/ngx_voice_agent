# ML Drift Detection System

## Overview

The ML Drift Detection system monitors the performance and behavior of machine learning models in production, detecting when models need retraining due to changing data patterns. This ensures the NGX Voice Sales Agent maintains high accuracy and conversion rates over time.

## Types of Drift Detected

### 1. **Data Drift**
- **What it is**: Changes in the distribution of input features
- **Example**: Customer demographics shift, new types of objections emerge
- **Detection Method**: Kolmogorov-Smirnov test, Population Stability Index (PSI)

### 2. **Concept Drift**
- **What it is**: Changes in the relationship between features and target
- **Example**: What used to indicate high interest no longer converts
- **Detection Method**: Performance degradation + data drift

### 3. **Performance Drift**
- **What it is**: Model accuracy decreases over time
- **Example**: Conversion predictions become less accurate
- **Detection Method**: Sliding window performance monitoring

### 4. **Prediction Drift**
- **What it is**: Changes in model output distributions
- **Example**: Model starts predicting fewer conversions overall
- **Detection Method**: Distribution comparison of predictions

## Key Metrics

### Statistical Tests
- **KS Statistic**: Measures maximum distance between distributions
- **P-value**: Statistical significance of drift
- **PSI Score**: Population Stability Index
  - < 0.1: No significant drift
  - 0.1-0.25: Moderate drift
  - > 0.25: Significant drift
- **Wasserstein Distance**: Earth mover's distance between distributions

### Severity Levels
- **None**: No drift detected
- **Low**: Minor drift, monitor closely
- **Medium**: Noticeable drift, plan retraining
- **High**: Significant drift, schedule retraining soon
- **Critical**: Severe drift, immediate retraining required

## Implementation Details

### Architecture

```python
MLDriftDetector
├── Track Predictions
│   ├── Features
│   ├── Predictions
│   └── Actual Outcomes
├── Detect Drift
│   ├── Statistical Tests
│   ├── Performance Analysis
│   └── Pattern Recognition
├── Generate Reports
│   ├── Severity Assessment
│   ├── Affected Features
│   └── Recommendations
└── Alert & Action
    ├── Send Notifications
    └── Trigger Retraining
```

### Data Flow

1. **Prediction Tracking**
   - Every model prediction is tracked with features
   - Outcomes recorded when available
   - Data stored in sliding windows

2. **Baseline Management**
   - Initial baselines set during model deployment
   - Updated after each retraining
   - Stored in database for persistence

3. **Continuous Monitoring**
   - Hourly drift checks
   - Real-time performance tracking
   - Automatic alert generation

## API Endpoints

### Check Drift Status
```http
GET /api/ml/drift/status/{model_name}
```
Returns current drift status for a specific model.

### Get Drift Summary
```http
GET /api/ml/drift/summary?hours=24
```
Returns summary of all drift detections in specified time window.

### Update Baseline
```http
POST /api/ml/drift/baseline/{model_name}/update
```
Updates baseline distributions after model retraining.

### List Monitored Models
```http
GET /api/ml/drift/models
```
Lists all models being monitored for drift.

### Get Alerts
```http
GET /api/ml/drift/alerts?severity=high&unresolved_only=true
```
Returns drift alerts requiring attention.

## Usage Examples

### 1. Checking Model Drift

```python
# Check drift for conversion predictor
response = await drift_detector.detect_drift("conversion_predictor")

if response.requires_retraining:
    print(f"Model needs retraining: {response.severity}")
    print(f"Affected features: {response.affected_features}")
    print(f"Recommendations: {response.recommendations}")
```

### 2. Tracking Predictions

```python
# Track each prediction for drift analysis
await drift_detector.track_prediction(
    model_name="objection_predictor",
    features={
        "message_count": 5,
        "conversation_phase": "pricing",
        "customer_segment": "enterprise"
    },
    prediction=["price_too_high", "need_approval"],
    actual=["price_too_high"]  # When available
)
```

### 3. Updating Baselines

```python
# After model retraining, update baselines
await drift_detector.update_baseline(
    model_name="conversion_predictor",
    features={
        "message_count": recent_message_counts,
        "interest_level": recent_interest_levels
    },
    predictions=recent_predictions,
    performance_score=0.92
)
```

## Database Schema

### ml_baseline_distributions
Stores baseline feature distributions for each model.

### ml_baseline_performance
Stores baseline performance metrics.

### ml_prediction_tracking
Tracks individual predictions for analysis.

### ml_drift_reports
Stores drift detection reports and alerts.

## Best Practices

### 1. **Regular Monitoring**
- Check drift status daily
- Review weekly summaries
- Act on high/critical alerts immediately

### 2. **Baseline Management**
- Update baselines after each retraining
- Keep baselines representative of expected data
- Document baseline update reasons

### 3. **Feature Selection**
- Track only meaningful features
- Avoid high-cardinality categorical features
- Focus on features that impact predictions

### 4. **Response to Drift**

#### Low/Medium Drift
1. Investigate root cause
2. Check for data quality issues
3. Plan retraining if trend continues

#### High/Critical Drift
1. Immediate investigation
2. Consider reverting to previous model
3. Fast-track retraining process
4. Update monitoring thresholds if needed

## Integration with ML Pipeline

The drift detector is fully integrated with the ML Pipeline Service:

```python
# In MLPipelineService
async def process_conversation_predictions(...):
    # Generate predictions
    predictions = await self._compute_all_predictions(...)
    
    # Track for drift detection
    await self._track_for_drift_detection(
        predictions=predictions,
        context=context,
        messages=messages
    )
    
    # Return predictions
    return predictions
```

## Monitoring Dashboard

Key metrics to monitor:
- Drift detection frequency by model
- Severity distribution over time
- Feature contribution to drift
- Model performance trends
- Time since last retraining

## Troubleshooting

### Common Issues

1. **False Positive Drift**
   - Check sample size (need minimum 30 samples)
   - Verify baseline is representative
   - Consider seasonal patterns

2. **Missing Drift Detection**
   - Ensure predictions are being tracked
   - Check feature extraction logic
   - Verify baseline exists

3. **Performance Issues**
   - Limit window sizes for large-scale deployments
   - Use batch processing for historical analysis
   - Consider sampling for high-volume models

## Future Enhancements

1. **Advanced Detection Methods**
   - ADWIN for adaptive windowing
   - Deep learning-based drift detection
   - Multivariate drift detection

2. **Automated Response**
   - Auto-trigger retraining pipelines
   - Dynamic model switching
   - Online learning integration

3. **Enhanced Analytics**
   - Drift prediction (forecast when drift will occur)
   - Root cause analysis
   - Cross-model drift correlation