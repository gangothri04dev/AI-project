import pandas as pd
import numpy as np
from datetime import datetime

def validate_financial_data(data):
    """
    Validate if the uploaded data looks like financial data.
    
    Args:
        data (pd.DataFrame): The uploaded data frame
    
    Returns:
        tuple: (is_valid, message) - Boolean indicating if valid and explanation message
    """
    # Check if data exists
    if data is None:
        return False, "No data was provided."
    
    # Check if dataframe is empty
    if data.empty:
        return False, "The uploaded file contains no data."
    
    # Check column count
    if len(data.columns) < 1:
        return False, "The data must have at least one column."
    
    # Look for invalid or problematic values (but allow some null)
    if data.isnull().all().all():
        return False, "All values in the dataset are missing (null)."
    
    # Check if there's at least one column that might be a date
    has_date_column = False
    date_column_name = None
    # For large datasets, use a more efficient approach for date detection
    for col in data.columns:
        # Skip numeric columns for date detection
        if pd.api.types.is_numeric_dtype(data[col]):
            continue
            
        try:
            # Check if column is already datetime
            if pd.api.types.is_datetime64_any_dtype(data[col]):
                has_date_column = True
                date_column_name = col
                break
            
            # For large datasets, sample the data to speed up validation
            sample_size = min(len(data), 1000)
            sample_data = data[col].sample(sample_size) if len(data) > 1000 else data[col]
            
            # Try to convert to datetime
            test_conversion = pd.to_datetime(sample_data, errors='coerce', utc=True)
            # Check if this really looks like a date column (at least 30% valid dates)
            valid_ratio = test_conversion.notna().mean()
            if valid_ratio >= 0.3:
                has_date_column = True
                date_column_name = col
                break
        except:
            continue
    
    # Even without a date column, we can still create a dashboard
    # We'll generate a dummy date or just use categorical analysis
    if not has_date_column:
        return True, "No specific date column found. Using record order for time-based analysis."
    
    # Check if there are numeric columns (potential financial values)
    numeric_columns = data.select_dtypes(include=['number']).columns
    # Much more lenient - accept files even with zero native numeric columns
    # because we try to convert them later
    if len(numeric_columns) == 0:
        return True, "No native numeric columns found, but system will attempt to convert text values to numbers."
    
    # Check for potential financial column names as an additional validation
    financial_keywords = ['amount', 'price', 'value', 'cost', 'revenue', 'income', 'expense', 
                         'balance', 'profit', 'sale', 'asset', 'liability', 'cash', 'fund', 
                         'tax', 'interest', 'dividend', 'payment']
    
    found_financial_cols = []
    for col in data.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in financial_keywords):
            found_financial_cols.append(col)
    
    if found_financial_cols:
        return True, f"Data appears to be valid financial data with date column '{date_column_name}' and financial columns: {', '.join(found_financial_cols)}"
    else:
        # Even without matching column names, if we have dates and numbers, it's probably financial data
        return True, f"Data contains dates and numeric values which might represent financial data."

def process_data(data):
    """
    Process the uploaded financial data:
    - Identify date columns
    - Identify numeric and categorical columns
    - Handle missing values
    - Convert date columns to datetime
    
    Args:
        data (pd.DataFrame): The uploaded data frame
    
    Returns:
        tuple: (processed_data, date_column, numeric_columns, categorical_columns)
    """
    # Basic validation
    if data is None or data.empty:
        return data, None, [], []
    
    # Create a copy to avoid modifying the original
    try:
        df = data.copy()
    except Exception as e:
        print(f"Error creating data copy: {str(e)}")
        return data, None, [], []
    
    # Identifiers for common financial/date column names to prioritize
    date_indicators = {'date', 'time', 'day', 'month', 'year', 'period', 'timestamp'}
    
    # Pre-calculate column names to avoid repeated lower() calls
    col_names_lower = {col: col.lower() for col in df.columns}
    
    # Identify date columns
    date_column = None
    for indicator in date_indicators:
        for col, col_lower in col_names_lower.items():
            if indicator in col_lower:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    if df[col].notna().any():
                        date_column = col
                        break
                except:
                    continue
        if date_column:
            break

    # Optimized search for date column if not found by name
    if date_column is None:
        # Only check non-numeric columns to save time
        potential_date_cols = [col for col in df.columns if not pd.api.types.is_numeric_dtype(df[col])]
        for col in potential_date_cols:
            sample_size = min(len(df), 500)
            sample = df[col].sample(sample_size) if len(df) > 500 else df[col]
            try:
                test_conv = pd.to_datetime(sample, errors='coerce')
                if test_conv.notna().mean() >= 0.4:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    date_column = col
                    break
            except:
                continue
    
    # If still no date column, create a synthetic one for time-series visualization
    if date_column is None:
        df['Index_Date'] = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
        date_column = 'Index_Date'
    
    # Identify numeric columns (excluding the date column)
    try:
        numeric_columns = [col for col in df.select_dtypes(include=['number']).columns if col != date_column]
        
        # If no numeric columns found, aggressively try to convert columns
        if not numeric_columns:
            for col in df.columns:
                if col != date_column and col not in ['Index_Date']:
                    try:
                        # Try converting to numeric
                        converted = pd.to_numeric(df[col], errors='coerce')
                        valid_count = converted.notna().sum()
                        # Lower threshold to 20% for better detection
                        if valid_count > 0 and valid_count / len(df) >= 0.2:
                            df[col] = converted
                            numeric_columns.append(col)
                    except:
                        continue
        
        # Force convert remaining columns with any numeric data
        if not numeric_columns:
            for col in df.columns:
                if col != date_column and col not in ['Index_Date']:
                    try:
                        # Try conversion
                        converted = pd.to_numeric(df[col], errors='coerce')
                        if converted.notna().sum() > 0:  # Has any numeric values
                            df[col] = converted
                            numeric_columns.append(col)
                    except:
                        continue
    except Exception as e:
        print(f"Error identifying numeric columns: {str(e)}")
        numeric_columns = []
    
    # Identify categorical columns
    try:
        categorical_columns = [col for col in df.columns 
                              if col != date_column and col not in numeric_columns]
    except Exception as e:
        print(f"Error identifying categorical columns: {str(e)}")
        categorical_columns = []
    
    # Handle missing values
    # For numeric columns, fill with mean or 0
    for col in numeric_columns:
        try:
            if df[col].isnull().any():
                # If more than 50% are missing, use 0 instead of mean to avoid skew
                if df[col].isnull().mean() > 0.5:
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = df[col].fillna(df[col].mean())
        except Exception as e:
            print(f"Error handling missing values in column {col}: {str(e)}")
            # Use a safe fallback
            df[col] = df[col].fillna(0)
    
    # For categorical columns, fill with 'Unknown'
    for col in categorical_columns:
        try:
            if df[col].isnull().any():
                df[col] = df[col].fillna('Unknown')
        except Exception as e:
            print(f"Error handling missing values in categorical column {col}: {str(e)}")
            df[col] = df[col].fillna('Unknown')
    
    # Sort by date column if available
    if date_column:
        try:
            df = df.sort_values(by=date_column)
        except Exception as e:
            print(f"Error sorting by date: {str(e)}")
    
    return df, date_column, numeric_columns, categorical_columns

def filter_data_by_date(data, date_column, start_date, end_date):
    """
    Filter the dataframe by date range.
    
    Args:
        data (pd.DataFrame): The data frame to filter
        date_column (str): Name of the date column
        start_date (datetime): Start date for filtering
        end_date (datetime): End date for filtering
    
    Returns:
        pd.DataFrame: Filtered dataframe
    """
    # Safety checks
    if data is None or data.empty:
        return data
    
    if date_column is None or date_column not in data.columns:
        return data
    
    try:
        filtered_data = data[(data[date_column] >= start_date) & (data[date_column] <= end_date)]
        # If filtering removed all data, return the original instead
        if filtered_data.empty and not data.empty:
            print(f"Date filtering resulted in empty dataframe. Using original data instead.")
            return data
        return filtered_data
    except Exception as e:
        print(f"Error filtering by date: {str(e)}")
        return data  # Return original data if error occurs

def filter_data_by_category(data, category_column, selected_categories):
    """
    Filter the dataframe by selected categories.
    
    Args:
        data (pd.DataFrame): The data frame to filter
        category_column (str): Name of the category column
        selected_categories (list): List of categories to include
    
    Returns:
        pd.DataFrame: Filtered dataframe
    """
    # Safety checks
    if data is None or data.empty:
        return data
    
    if category_column is None or category_column not in data.columns:
        return data
        
    if not selected_categories:
        return data
    
    try:
        filtered_data = data[data[category_column].isin(selected_categories)]
        # If filtering removed all data, return the original instead
        if filtered_data.empty and not data.empty:
            print(f"Category filtering resulted in empty dataframe. Using original data instead.")
            return data
        return filtered_data
    except Exception as e:
        print(f"Error filtering by category: {str(e)}")
        return data  # Return original data if error occurs
