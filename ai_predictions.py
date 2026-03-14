import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from datetime import timedelta

def predict_future_values(data, date_column, value_column, days_to_predict=30):
    """
    Generate predictions for future values using a simple linear regression model.
    
    Args:
        data (pd.DataFrame): Historical financial data
        date_column (str): Name of the date column
        value_column (str): Name of the value column to predict
        days_to_predict (int, optional): Number of days to predict. Defaults to 30.
    
    Returns:
        tuple: (prediction_result, plotly_figure)
    """
    # Ensure data is sorted by date
    data = data.sort_values(by=date_column)
    
    # Extract the date and value columns
    dates = data[date_column]
    values = data[value_column]
    
    # Check if we have enough data points
    if len(values) < 10:
        raise ValueError("Not enough data points for reliable prediction. Need at least 10 data points.")
    
    # Convert dates to numeric feature (days since first date)
    first_date = dates.min()
    X = np.array([(date - first_date).days for date in dates]).reshape(-1, 1)
    y = values.values
    
    # Create and train the model
    model = LinearRegression()
    model.fit(X, y)
    
    # Generate prediction dates
    last_date = dates.max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(days_to_predict)]
    
    # Convert future dates to numeric feature
    X_future = np.array([(date - first_date).days for date in future_dates]).reshape(-1, 1)
    
    # Make predictions
    y_future = model.predict(X_future)
    
    # Create a combined dataset for plotting
    historical_df = pd.DataFrame({
        'date': dates,
        'value': values,
        'type': 'Historical'
    })
    
    prediction_df = pd.DataFrame({
        'date': future_dates,
        'value': y_future,
        'type': 'Predicted'
    })
    
    combined_df = pd.concat([historical_df, prediction_df])
    
    import matplotlib.pyplot as plt
    import io
    
    # Create plot using Matplotlib
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Add historical data
    ax.plot(historical_df['date'], historical_df['value'], marker='o', linestyle='-', markersize=4, color='blue', label='Historical Data')
    
    # Add prediction data
    ax.plot(prediction_df['date'], prediction_df['value'], linestyle='--', color='red', label='Predicted Values')
    
    # Add confidence interval (simple approximation)
    y_historical_pred = model.predict(X)
    prediction_error = np.std(y - y_historical_pred)
    
    ax.fill_between(
        prediction_df['date'],
        prediction_df['value'] - 2 * prediction_error,
        prediction_df['value'] + 2 * prediction_error,
        color='red', alpha=0.2, label='95% Confidence Interval'
    )
    
    ax.set_title(f'AI Prediction for {value_column} (Next {days_to_predict} Days)')
    ax.set_xlabel('Date')
    ax.set_ylabel(value_column)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Generate prediction summary
    average_prediction = np.mean(y_future)
    last_value = values.iloc[-1]
    change = average_prediction - last_value
    
    if last_value != 0:
        percent_change = (change / last_value) * 100
    else:
        percent_change = 0
    
    if percent_change > 5:
        trend_description = f"Strong upward trend predicted with projected {percent_change:.2f}% increase"
    elif percent_change > 0:
        trend_description = f"Slight upward trend predicted with projected {percent_change:.2f}% increase"
    elif percent_change < -5:
        trend_description = f"Strong downward trend predicted with projected {abs(percent_change):.2f}% decrease"
    elif percent_change < 0:
        trend_description = f"Slight downward trend predicted with projected {abs(percent_change):.2f}% decrease"
    else:
        trend_description = "Stable trend predicted with minimal change"
    
    # Prepare result dictionary
    prediction_result = {
        'average_prediction': average_prediction,
        'percent_change': percent_change,
        'trend_description': trend_description,
        'confidence_interval': prediction_error * 2
    }
    
    return prediction_result, fig

def predict_financial_health(data, numeric_columns):
    """
    Generate a basic financial health score prediction based on trends.
    
    Args:
        data (pd.DataFrame): Historical financial data
        numeric_columns (list): List of numeric column names
    
    Returns:
        dict: Financial health prediction results
    """
    # Check if we have enough data
    if len(data) < 10:
        return {
            'health_score': None,
            'description': 'Not enough data for financial health prediction'
        }
    
    # Identify key financial columns
    revenue_cols = [col for col in numeric_columns if 'revenue' in col.lower() or 'income' in col.lower() or 'sales' in col.lower()]
    expense_cols = [col for col in numeric_columns if 'expense' in col.lower() or 'cost' in col.lower() or 'spend' in col.lower()]
    
    # Initialize features
    features = []
    feature_importances = []
    
    # If we have revenue data, check its trend
    if revenue_cols:
        revenue_col = revenue_cols[0]
        revenue_values = data[revenue_col].values
        
        # Calculate revenue trend (slope of linear regression)
        x = np.arange(len(revenue_values)).reshape(-1, 1)
        model = LinearRegression().fit(x, revenue_values)
        revenue_trend = model.coef_[0]
        
        # Normalize trend
        revenue_mean = np.mean(revenue_values)
        if revenue_mean != 0:
            normalized_revenue_trend = revenue_trend / revenue_mean
        else:
            normalized_revenue_trend = 0
        
        features.append(normalized_revenue_trend)
        feature_importances.append(0.4)  # Revenue trend is important
    
    # If we have expense data, check its trend
    if expense_cols:
        expense_col = expense_cols[0]
        expense_values = data[expense_col].values
        
        # Calculate expense trend
        x = np.arange(len(expense_values)).reshape(-1, 1)
        model = LinearRegression().fit(x, expense_values)
        expense_trend = model.coef_[0]
        
        # Normalize trend
        expense_mean = np.mean(expense_values)
        if expense_mean != 0:
            normalized_expense_trend = expense_trend / expense_mean
        else:
            normalized_expense_trend = 0
        
        features.append(-normalized_expense_trend)  # Negative because decreasing expenses is good
        feature_importances.append(0.3)  # Expense trend is important but less than revenue
    
    # If we have both revenue and expense, calculate profit margin trend
    if revenue_cols and expense_cols:
        revenue_col = revenue_cols[0]
        expense_col = expense_cols[0]
        
        # Calculate profit margin for each period
        profit_margins = []
        for i in range(len(data)):
            revenue = data[revenue_col].iloc[i]
            expense = data[expense_col].iloc[i]
            
            if revenue != 0:
                profit_margin = (revenue - expense) / revenue
            else:
                profit_margin = 0
            
            profit_margins.append(profit_margin)
        
        # Calculate profit margin trend
        x = np.arange(len(profit_margins)).reshape(-1, 1)
        model = LinearRegression().fit(x, profit_margins)
        profit_margin_trend = model.coef_[0]
        
        features.append(profit_margin_trend * 100)  # Scale up for similar magnitude
        feature_importances.append(0.3)  # Profit margin trend is important
    
    # For other numeric columns, calculate volatility
    volatility_scores = []
    for col in [c for c in numeric_columns if c not in revenue_cols + expense_cols]:
        values = data[col].values
        if len(values) > 0 and np.mean(values) != 0:
            volatility = np.std(values) / np.mean(values)
            volatility_scores.append(volatility)
    
    if volatility_scores:
        avg_volatility = np.mean(volatility_scores)
        features.append(-avg_volatility)  # Negative because lower volatility is better
        feature_importances.append(0.1)  # Volatility is less important
    
    # If we don't have enough features, return None
    if not features:
        return {
            'health_score': None,
            'description': 'Insufficient financial data for health prediction'
        }
    
    # Normalize feature importances
    feature_importances = np.array(feature_importances)
    feature_importances = feature_importances / np.sum(feature_importances)
    
    # Calculate weighted score
    features = np.array(features)
    features = np.clip(features, -1, 1)  # Clip to range [-1, 1]
    
    weighted_score = np.sum(features * feature_importances)
    
    # Convert to 0-100 scale
    health_score = int((weighted_score + 1) * 50)
    health_score = max(0, min(100, health_score))  # Ensure within 0-100
    
    # Generate description
    if health_score >= 80:
        description = "Excellent financial health with strong positive trends"
    elif health_score >= 60:
        description = "Good financial health with generally positive indicators"
    elif health_score >= 40:
        description = "Moderate financial health with mixed indicators"
    elif health_score >= 20:
        description = "Concerning financial health with several negative trends"
    else:
        description = "Poor financial health with significant negative indicators"
    
    return {
        'health_score': health_score,
        'description': description,
        'feature_contributions': dict(zip(['Revenue Trend', 'Expense Trend', 'Profit Margin Trend', 'Volatility'], 
                                        features * feature_importances))
    }
