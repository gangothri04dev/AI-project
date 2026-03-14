import pandas as pd
import numpy as np

def get_summary_statistics(data, numeric_columns):
    """
    Calculate summary statistics for numeric columns.
    
    Args:
        data (pd.DataFrame): The financial data
        numeric_columns (list): List of numeric column names
    
    Returns:
        pd.DataFrame: Summary statistics
    """
    # Check if we have data and numeric columns
    if data is None or len(data) == 0 or not numeric_columns:
        # Return empty DataFrame with appropriate columns if no data
        return pd.DataFrame(columns=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', 'median', 'skew', 'kurtosis'])
    
    # Select only numeric columns for summary
    numeric_data = data[numeric_columns]
    
    # Calculate basic statistics
    summary = numeric_data.describe().T
    
    # Add additional statistics
    summary['median'] = numeric_data.median()
    summary['skew'] = numeric_data.skew()
    summary['kurtosis'] = numeric_data.kurtosis()
    
    # Format the summary
    summary = summary.round(2)
    
    return summary

def calculate_financial_metrics(data, numeric_columns):
    if data is None or len(data) == 0:
        return {}
    
    # Filter out empty or invalid numeric columns
    valid_numeric_cols = []
    for col in (numeric_columns or []):
        try:
            # Skip if column doesn't exist
            if col not in data.columns:
                continue
            col_data = pd.to_numeric(data[col], errors='coerce')
            if col_data.notna().sum() > 0:  # At least one non-null value
                valid_numeric_cols.append(col)
        except:
            continue
    
    # If still no valid columns, try all columns
    if not valid_numeric_cols:
        for col in data.columns:
            try:
                col_data = pd.to_numeric(data[col], errors='coerce')
                if col_data.notna().sum() > 0:
                    valid_numeric_cols.append(col)
            except:
                continue
    
    if not valid_numeric_cols:
        return {}
        
    metrics = {}
    
    try:
        # Calculate global sums/means once for speed
        stats = data[valid_numeric_cols].agg(['sum', 'mean', 'std'])
        
        for col in valid_numeric_cols:
            try:
                # Only add metrics if the value is numeric and not NaN
                mean_val = stats.loc['mean', col]
                std_val = stats.loc['std', col]
                
                if pd.notna(mean_val) and not np.isnan(mean_val) and mean_val != 0:
                    metrics[f"Avg {col}"] = mean_val
                if pd.notna(std_val) and not np.isnan(std_val) and std_val != 0:
                    metrics[f"{col} Volatility"] = std_val
                
                # Fast growth calculation using first/last valid
                col_series = data[col].dropna()
                if len(col_series) > 1:
                    first, last = col_series.iloc[0], col_series.iloc[-1]
                    if first != 0 and pd.notna(first) and pd.notna(last) and not np.isnan(first) and not np.isnan(last):
                        change = ((last - first) / first) * 100
                        if not np.isnan(change) and abs(change) > 0.01:
                            metrics[f"{col} Change %"] = change
            except Exception as col_error:
                continue
        
        # Quick keyword-based aggregation
        col_map = {c.lower(): c for c in valid_numeric_cols}
        def get_first_match(keywords):
            for k in keywords:
                for cl, c in col_map.items():
                    if k in cl: return c
            return None

        rev_col = get_first_match(['revenue', 'income', 'sales'])
        if rev_col:
            try:
                rev_sum = stats.loc['sum', rev_col]
                if pd.notna(rev_sum) and not np.isnan(rev_sum):
                    metrics["Total Revenue"] = rev_sum
            except:
                pass
        
        exp_col = get_first_match(['expense', 'cost', 'spend'])
        if exp_col:
            try:
                exp_sum = stats.loc['sum', exp_col]
                if pd.notna(exp_sum) and not np.isnan(exp_sum):
                    metrics["Total Expenses"] = exp_sum
            except:
                pass
        
        if "Total Revenue" in metrics and "Total Expenses" in metrics:
            metrics["Net Profit"] = metrics["Total Revenue"] - metrics["Total Expenses"]
            if metrics["Total Revenue"] != 0:
                profit_margin = (metrics["Net Profit"] / metrics["Total Revenue"]) * 100
                if not np.isnan(profit_margin):
                    metrics["Profit Margin %"] = profit_margin
    except Exception as e:
        print(f"Error calculating metrics: {str(e)}")
        return {}
            
    return metrics

def analyze_trends(data, date_column, value_column):
    """
    Analyze trends in a time series financial data.
    
    Args:
        data (pd.DataFrame): The financial data
        date_column (str): Name of the date column
        value_column (str): Name of the value column to analyze
    
    Returns:
        dict: Dictionary of trend analysis results
    """
    # Ensure data is sorted by date
    data = data.sort_values(by=date_column)
    
    # Extract the value series
    series = data[value_column].dropna()
    
    if len(series) < 2:
        return {
            "trend": "Unknown",
            "description": "Not enough data points for trend analysis",
            "change_pct": 0
        }
    
    # Calculate basic trend metrics
    first_value = series.iloc[0]
    last_value = series.iloc[-1]
    change = last_value - first_value
    
    if first_value != 0:
        change_pct = (change / first_value) * 100
    else:
        change_pct = 0
    
    # Determine trend direction
    if change_pct > 5:
        trend = "Increasing"
        description = f"Strong upward trend with {change_pct:.2f}% growth"
    elif change_pct > 0:
        trend = "Slightly Increasing"
        description = f"Slight upward trend with {change_pct:.2f}% growth"
    elif change_pct < -5:
        trend = "Decreasing"
        description = f"Strong downward trend with {abs(change_pct):.2f}% decline"
    elif change_pct < 0:
        trend = "Slightly Decreasing"
        description = f"Slight downward trend with {abs(change_pct):.2f}% decline"
    else:
        trend = "Stable"
        description = "Stable with minimal change over time"
    
    # Calculate volatility
    if len(series) > 2:
        volatility = series.std() / series.mean() if series.mean() != 0 else 0
        
        if volatility > 0.2:
            volatility_desc = "High volatility"
        elif volatility > 0.1:
            volatility_desc = "Moderate volatility"
        else:
            volatility_desc = "Low volatility"
            
        description += f" with {volatility_desc}"
    
    return {
        "trend": trend,
        "description": description,
        "change_pct": change_pct
    }
