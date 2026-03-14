import pandas as pd
import numpy as np

def calculate_portfolio_metrics(data, numeric_columns):
    """
    Calculate key metrics for each numeric column (asset).
    
    Args:
        data (pd.DataFrame): The financial data
        numeric_columns (list): List of numeric column names
    
    Returns:
        dict: Portfolio metrics including returns, volatility, and Sharpe ratios
    """
    if not numeric_columns or len(numeric_columns) == 0:
        return {}
    
    metrics = {}
    
    for col in numeric_columns:
        try:
            values = pd.to_numeric(data[col], errors='coerce').dropna()
            
            if len(values) < 2:
                continue
            
            # Calculate returns (percentage change)
            returns = values.pct_change().dropna()
            
            if len(returns) == 0:
                continue
            
            # Calculate metrics
            avg_return = returns.mean()
            volatility = returns.std()
            sharpe_ratio = avg_return / volatility if volatility != 0 else 0
            
            metrics[col] = {
                'return': avg_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'current_value': values.iloc[-1] if len(values) > 0 else 0,
                'min': values.min(),
                'max': values.max()
            }
        except:
            continue
    
    return metrics

def optimize_portfolio(metrics):
    """
    Generate portfolio optimization suggestions based on Sharpe ratio.
    
    Args:
        metrics (dict): Portfolio metrics from calculate_portfolio_metrics
    
    Returns:
        dict: Optimization suggestions including weights and recommendations
    """
    if not metrics:
        return {}
    
    suggestions = {}
    
    # Calculate weights based on Sharpe ratios (higher Sharpe = higher allocation)
    sharpe_ratios = [m['sharpe_ratio'] for m in metrics.values()]
    sharpe_sum = sum(sharpe_ratios)
    
    if sharpe_sum <= 0:
        # If all Sharpe ratios are negative, use inverse volatility weighting
        volatilities = [m['volatility'] for m in metrics.values()]
        volatility_sum = sum(volatilities)
        weights = {col: (1 / m['volatility']) / (volatility_sum / len(metrics)) 
                  for col, m in metrics.items() if m['volatility'] > 0}
    else:
        # Weight by Sharpe ratio
        weights = {col: m['sharpe_ratio'] / sharpe_sum for col, m in metrics.items()}
    
    # Normalize weights
    total_weight = sum(weights.values())
    weights = {col: (w / total_weight * 100) for col, w in weights.items()}
    
    suggestions['weights'] = weights
    suggestions['metrics'] = metrics
    
    return suggestions

def generate_recommendations(metrics, weights):
    """
    Generate actionable recommendations for portfolio optimization.
    
    Args:
        metrics (dict): Portfolio metrics
        weights (dict): Suggested weights for each asset
    
    Returns:
        list: List of recommendations
    """
    recommendations = []
    
    if not metrics or not weights:
        return recommendations
    
    # Find best and worst performers
    best_asset = max(metrics.items(), key=lambda x: x[1]['sharpe_ratio'])
    worst_asset = min(metrics.items(), key=lambda x: x[1]['sharpe_ratio'])
    
    recommendations.append({
        'type': 'top_performer',
        'asset': best_asset[0],
        'reason': f"Best risk-adjusted returns (Sharpe: {best_asset[1]['sharpe_ratio']:.2f})",
        'action': f"Consider increasing allocation to {best_asset[0]}"
    })
    
    recommendations.append({
        'type': 'caution',
        'asset': worst_asset[0],
        'reason': f"Lowest risk-adjusted returns (Sharpe: {worst_asset[1]['sharpe_ratio']:.2f})",
        'action': f"Consider reducing exposure to {worst_asset[0]} or monitor closely"
    })
    
    # Volatility recommendations
    high_vol_assets = [col for col, m in metrics.items() if m['volatility'] > np.mean([m['volatility'] for m in metrics.values()])]
    if high_vol_assets:
        recommendations.append({
            'type': 'volatility',
            'assets': high_vol_assets,
            'reason': f"High volatility assets ({', '.join(high_vol_assets[:2])})",
            'action': "Balance with lower volatility assets for portfolio stability"
        })
    
    # Diversification recommendation
    num_assets = len(metrics)
    recommendations.append({
        'type': 'diversification',
        'asset_count': num_assets,
        'reason': f"Portfolio contains {num_assets} assets",
        'action': f"Current diversification level is {'adequate' if num_assets >= 3 else 'limited'}"
    })
    
    return recommendations
