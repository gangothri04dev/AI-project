import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64

def create_line_chart(data, date_column, value_column, title=None):
    """
    Create a line chart for time series financial data using Matplotlib.
    """
    if title is None:
        title = f"{value_column} Over Time"
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(data[date_column], data[value_column], marker='o', linestyle='-', markersize=4)
    
    # Add trend line using numpy polyfit
    try:
        x = np.arange(len(data))
        y = data[value_column].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        ax.plot(data[date_column], p(x), "r--", alpha=0.8, label="Trend Line")
    except:
        pass
        
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(value_column)
    ax.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def create_bar_chart(data, category_column, value_column, title=None):
    """
    Create a bar chart for categorical financial data using Matplotlib.
    """
    if title is None:
        title = f"{value_column} by {category_column}"
    
    grouped_data = data.groupby(category_column)[value_column].sum().sort_values(ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    grouped_data.plot(kind='bar', ax=ax, color=plt.cm.Paired(np.arange(len(grouped_data))))
    
    ax.set_title(title)
    ax.set_xlabel(category_column)
    ax.set_ylabel(value_column)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def create_pie_chart(data, category_column, value_column, title=None):
    """
    Create a pie chart for categorical financial data using Matplotlib.
    """
    if title is None:
        title = f"{value_column} Distribution by {category_column}"
    
    grouped_data = data.groupby(category_column)[value_column].sum().sort_values(ascending=False)
    
    if len(grouped_data) > 10:
        top_data = grouped_data.iloc[:9]
        other_sum = grouped_data.iloc[9:].sum()
        grouped_data = pd.concat([top_data, pd.Series({'Other': other_sum})])
    
    fig, ax = plt.subplots(figsize=(10, 8))
    grouped_data.plot(kind='pie', ax=ax, autopct='%1.1f%%', startangle=90, counterclock=False)
    
    ax.set_title(title)
    ax.set_ylabel('') # Remove 'None' label
    plt.tight_layout()
    
    return fig

def fig_to_html(fig):
    """
    Convert Matplotlib figure to HTML img tag with base64 data.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f'<img src="data:image/png;base64,{data}" style="max-width:100%; height:auto; display:block; margin:auto;"/>'
