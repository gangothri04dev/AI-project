import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

# Import custom modules
from data_processor import process_data, validate_financial_data
from financial_analysis import calculate_financial_metrics, get_summary_statistics, analyze_trends
from visualization import create_line_chart, create_bar_chart, create_pie_chart
from ai_predictions import predict_future_values
from portfolio_optimizer import calculate_portfolio_metrics, optimize_portfolio, generate_recommendations
from auth import register_user, login_user, get_user_data, save_analysis, get_user_analysis_history, get_analysis_by_id
import sqlite3
# Set page configuration
st.set_page_config(
    page_title="An AI That Converts Chaos into Clarity",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'data' not in st.session_state:
    st.session_state.data = None
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'columns' not in st.session_state:
    st.session_state.columns = []
if 'date_column' not in st.session_state:
    st.session_state.date_column = None
if 'numeric_columns' not in st.session_state:
    st.session_state.numeric_columns = []
if 'categorical_columns' not in st.session_state:
    st.session_state.categorical_columns = []
if 'show_recovery' not in st.session_state:
    st.session_state.show_recovery = False
if 'recovery_step' not in st.session_state:
    st.session_state.recovery_step = 1
if 'recovery_email_val' not in st.session_state:
    st.session_state.recovery_email_val = ""
if 'view_history' not in st.session_state:
    st.session_state.view_history = False
if 'viewing_analysis_id' not in st.session_state:
    st.session_state.viewing_analysis_id = None

# Authentication Section
if not st.session_state.logged_in:
    st.title("An AI That Converts Chaos into Clarity - Authentication")
    
    if st.session_state.show_recovery:
        st.subheader("Recover Your Password")
        
        if st.session_state.recovery_step == 1:
            recovery_email = st.text_input("Enter your registered email", key="recovery_email")
            if st.button("Send Recovery Code", key="recovery_button"):
                if recovery_email:
                    from auth import reset_password_request
                    success, message = reset_password_request(recovery_email)
                    if success:
                        st.session_state.recovery_email_val = recovery_email
                        st.session_state.recovery_step = 2
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter your email address.")
        
        elif st.session_state.recovery_step == 2:
            st.info(f"Recovery code sent to {st.session_state.recovery_email_val}")
            recovery_code = st.text_input("Enter 6-digit recovery code", key="recovery_code")
            new_password = st.text_input("Enter new password", type="password", key="new_password")
            confirm_password = st.text_input("Confirm new password", type="password", key="confirm_password")
            
            if st.button("Reset Password", key="reset_button"):
                if not recovery_code or not new_password or not confirm_password:
                    st.warning("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    from auth import verify_code_and_reset_password
                    success, message = verify_code_and_reset_password(
                        st.session_state.recovery_email_val, 
                        recovery_code, 
                        new_password
                    )
                    if success:
                        st.success(message)
                        st.session_state.recovery_step = 1
                        st.session_state.show_recovery = False
                        st.rerun()
                    else:
                        st.error(message)
        
        if st.button("Back to Login", key="back_to_login"):
            st.session_state.show_recovery = False
            st.session_state.recovery_step = 1
            st.rerun()
            
    else:
        auth_tab1, auth_tab2 = st.tabs(["Login", "Sign Up"])
        
        with auth_tab1:
            st.subheader("Login to Your Account")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Login", key="login_button"):
                    if login_username and login_password:
                        success, message, user_data = login_user(login_username, login_password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_info = user_data  # Contains id, username, email
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Please enter both username and password.")
            
            with col2:
                if st.button("Forgot Password?", key="forgot_password"):
                    st.session_state.show_recovery = True
                    st.rerun()
        
        with auth_tab2:
            st.subheader("Create a New Account")
            signup_username = st.text_input("Choose a username", key="signup_username")
            signup_email = st.text_input("Email address", key="signup_email")
            signup_password = st.text_input("Create a password (min 6 characters)", type="password", key="signup_password")
            signup_confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            
            if st.button("Sign Up", key="signup_button"):
                if not signup_username or not signup_email or not signup_password:
                    st.warning("Please fill in all fields.")
                elif signup_password != signup_confirm:
                    st.error("Passwords do not match.")
                else:
                    success, message = register_user(signup_username, signup_email, signup_password)
                    if success:
                        st.success(message)
                        st.info("Please go to the Login tab and sign in with your credentials.")
                    else:
                        st.error(message)
else:
    # Load and display a specific analysis if viewing
    if st.session_state.viewing_analysis_id:
        st.title("Analysis Preview")
        if st.button("Back to History"):
            st.session_state.viewing_analysis_id = None
            st.rerun()
        
        st.divider()
        
        result = get_analysis_by_id(st.session_state.viewing_analysis_id)
        success, file_data, file_name, date_column, numeric_columns, predictions = result
        
        if success and file_data is not None:
            st.subheader(f"📊 {file_name}")
            st.info(f"Rows: {len(file_data)} | Columns: {len(file_data.columns)} | Date Column: {date_column}")
            
            # Use tabs for better organization
            tabs = st.tabs(["Data Preview", "Statistics", "Visualizations", "AI Predictions"])
            tab1, tab2, tab3, tab4 = tabs
            
            with tab1:
                st.dataframe(file_data.head(20), use_container_width=True)
            
            with tab2:
                if numeric_columns:
                    st.subheader("Summary Statistics")
                    summary = get_summary_statistics(file_data, numeric_columns)
                    st.dataframe(summary, use_container_width=True)
                    
                    # Show top metrics only (not all)
                    st.subheader("Key Metrics")
                    metrics = calculate_financial_metrics(file_data, numeric_columns)
                    if metrics:
                        top_metrics = dict(list(metrics.items())[:6])  # Show only top 6 metrics
                        col1, col2, col3 = st.columns(3)
                        for i, (metric, value) in enumerate(top_metrics.items()):
                            if i % 3 == 0:
                                col1.metric(metric, f"{value:,.2f}")
                            elif i % 3 == 1:
                                col2.metric(metric, f"{value:,.2f}")
                            else:
                                col3.metric(metric, f"{value:,.2f}")
                    else:
                        st.info("No metrics calculated for this analysis")
            
            with tab3:
                if numeric_columns and len(numeric_columns) > 0:
                    st.subheader("Trend Analysis")
                    # Create line chart for first numeric column
                    chart_col = numeric_columns[0]
                    try:
                        fig = create_line_chart(file_data, date_column, [chart_col], f"{chart_col} Over Time")
                        st.pyplot(fig)
                    except:
                        st.info("Could not generate visualization")
                else:
                    st.info("No numeric columns available for visualization")
            
            if tab4:
                with tab4:
                    if predictions is not None:
                        st.subheader("AI Predictions")
                        if isinstance(predictions, pd.DataFrame):
                            st.dataframe(predictions.head(20), use_container_width=True)
                        else:
                            st.json(predictions)
                    else:
                        st.info("No AI predictions saved for this analysis")
        else:
            st.error("Could not load analysis data")
        st.stop()
    
    # Show history view if requested
    if st.session_state.view_history:
        st.title("Your Analysis History")
        
        if st.button("Back to Dashboard"):
            st.session_state.view_history = False
            st.rerun()
        
        st.divider()
        
        if st.session_state.user_info:
            history = get_user_analysis_history(st.session_state.user_info['id'])
            
            if history:
                st.subheader(f"Past Analyses ({len(history)} total)")
                
                for idx, analysis in enumerate(history, 1):
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{idx}. {analysis['file_name']}**")
                            st.caption(f"Uploaded: {analysis['created_at']}")
                            st.text(f"Rows: {analysis['num_rows']} | Columns: {analysis['num_columns']}")
                        
                        with col2:
                            if analysis['date_column']:
                                st.caption(f"📅 Date: {analysis['date_column']}")
                        
                        with col3:
                            if st.button("View", key=f"view_analysis_{idx}"):
                                st.session_state.viewing_analysis_id = analysis['id']
                                st.session_state.view_history = False
                                st.rerun()
            else:
                st.info("No analyses saved yet. Start by uploading and analyzing a file!")
        else:
            st.error("User information not available")
        st.stop()
    
    # Title and introduction
    st.title("An AI That Converts Chaos into Clarity")
    st.markdown("""
    This dashboard helps you efficiently process and analyze CSV and Excel files up to 50 MB in size. 
    It transforms raw data into interactive Matplotlib visualizations and AI-powered insights.
    """)

    # Sidebar for data upload and filtering
    with st.sidebar:
        st.header("User Profile")
        if st.session_state.user_info:
            st.write(f"**Logged in as:** {st.session_state.user_info['username']}")
            st.write(f"**Email:** {st.session_state.user_info['email']}")
        else:
            st.write("User profile not available")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View History"):
                st.session_state.view_history = True
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_info = None
                st.session_state.data = None
                st.session_state.filtered_data = None
                st.session_state.view_history = False
                st.rerun()
        
        st.divider()
        st.header("Data Import")
        uploaded_file = st.file_uploader("Upload your financial data", type=["csv", "xlsx", "xls"])
        
        if uploaded_file is not None:
            try:
                # Show loading progress
                with st.spinner("Reading file..."):
                    # Determine file type and read accordingly
                    if uploaded_file.name.endswith('.csv'):
                        # Try different encodings for CSV files
                        data = None
                        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
                        for encoding in encodings:
                            try:
                                data = pd.read_csv(uploaded_file, engine='c', low_memory=True, encoding=encoding)
                                break
                            except (UnicodeDecodeError, UnicodeError):
                                continue
                        
                        if data is None:
                            st.error("Could not read CSV file - unsupported encoding. Please save your file as UTF-8 and try again.")
                            st.stop()
                    else:
                        # Read Excel file - handle multiple sheet support
                        try:
                            data = pd.read_excel(uploaded_file)
                        except:
                            # Try with different engine
                            data = pd.read_excel(uploaded_file, engine='openpyxl')
                
                # Show basic info
                st.info(f"File loaded: {data.shape[0]} rows, {data.shape[1]} columns")
                
                # Validate if the data looks like financial data
                is_valid, message = validate_financial_data(data)
                
                if is_valid:
                    with st.spinner("Processing data..."):
                        # Process data
                        processed_data, date_column, numeric_columns, categorical_columns = process_data(data)
                    
                    # Store in session state
                    st.session_state.data = processed_data
                    st.session_state.filtered_data = processed_data
                    st.session_state.columns = processed_data.columns.tolist()
                    st.session_state.date_column = date_column
                    st.session_state.numeric_columns = numeric_columns
                    st.session_state.categorical_columns = categorical_columns
                    
                    st.success("Data successfully loaded!")
                    st.info(f"Detected: {len(numeric_columns)} numeric columns, {len(categorical_columns)} categorical columns, date column: {date_column}")
                    
                    # Save to analysis history
                    if st.session_state.user_info and st.session_state.user_info.get('id'):
                        try:
                            summary_stats = {}
                            if numeric_columns and len(numeric_columns) > 0:
                                summary_stats = get_summary_statistics(processed_data, numeric_columns)
                            
                            success, msg = save_analysis(
                                user_id=st.session_state.user_info['id'],
                                file_name=uploaded_file.name,
                                file_size=uploaded_file.size,
                                num_rows=len(processed_data),
                                num_columns=len(processed_data.columns),
                                date_column=date_column,
                                numeric_columns=numeric_columns,
                                summary_stats=summary_stats,
                                file_data=processed_data
                            )
                            if success:
                                st.info("✓ Analysis saved to your history")
                            else:
                                st.warning(f"Could not save to history: {msg}")
                        except Exception as save_err:
                            st.warning(f"Error saving analysis: {str(save_err)}")
                else:
                    st.error(f"⚠️ Data validation issue: {message}")
                    st.warning("The system will still attempt to analyze the data.")
                    # Try to process anyway even if validation failed
                    try:
                        with st.spinner("Attempting to process data..."):
                            processed_data, date_column, numeric_columns, categorical_columns = process_data(data)
                        
                        st.session_state.data = processed_data
                        st.session_state.filtered_data = processed_data
                        st.session_state.columns = processed_data.columns.tolist()
                        st.session_state.date_column = date_column
                        st.session_state.numeric_columns = numeric_columns
                        st.session_state.categorical_columns = categorical_columns
                        
                        st.success("Data processed (with warnings)")
                        st.info(f"Detected: {len(numeric_columns)} numeric columns, {len(categorical_columns)} categorical columns")
                    except Exception as process_error:
                        st.error(f"Could not process data: {str(process_error)}")
            except Exception as e:
                st.error(f"❌ Error loading file: {str(e)}")
                st.error("Try uploading a CSV or Excel file with proper formatting.")
        
        # Data filtering (only show if data is loaded)
        if st.session_state.data is not None:
            st.header("Data Filtering")
            
            # Date range filter (if date column exists)
            if st.session_state.date_column:
                st.subheader("Date Range")
                min_date = st.session_state.data[st.session_state.date_column].min()
                max_date = st.session_state.data[st.session_state.date_column].max()
                
                date_range = st.date_input(
                    "Select date range",
                    [min_date, max_date],
                    min_value=min_date,
                    max_value=max_date
                )
                
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    # Ensure start_date and end_date are datetime objects for comparison
                    start_datetime = pd.to_datetime(start_date)
                    end_datetime = pd.to_datetime(end_date)
                    
                    # Convert column to datetime if not already
                    if not pd.api.types.is_datetime64_any_dtype(st.session_state.data[st.session_state.date_column]):
                        st.session_state.data[st.session_state.date_column] = pd.to_datetime(st.session_state.data[st.session_state.date_column], errors='coerce')
                    
                    # Handle timezone mismatch - remove timezone if present
                    date_col = st.session_state.data[st.session_state.date_column]
                    if date_col.dt.tz is not None:
                        date_col = date_col.dt.tz_localize(None)
                    
                    # Ensure comparison datetimes are also timezone-naive
                    if start_datetime.tz is not None:
                        start_datetime = start_datetime.tz_localize(None)
                    if end_datetime.tz is not None:
                        end_datetime = end_datetime.tz_localize(None)
                    
                    filtered_data = st.session_state.data[
                        (date_col >= start_datetime) & 
                        (date_col <= end_datetime)
                    ]
                    st.session_state.filtered_data = filtered_data
            
            # Category filter (if categorical columns exist)
            if st.session_state.categorical_columns:
                st.subheader("Category Filters")
                selected_category_column = st.selectbox(
                    "Select category column",
                    st.session_state.categorical_columns
                )
                
                if selected_category_column and st.session_state.filtered_data is not None:
                    unique_categories = st.session_state.filtered_data[selected_category_column].unique()
                    selected_categories = st.multiselect(
                        "Select categories",
                        unique_categories,
                        default=unique_categories
                    )
                    
                    if selected_categories:
                        st.session_state.filtered_data = st.session_state.filtered_data[
                            st.session_state.filtered_data[selected_category_column].isin(selected_categories)
                        ]

    # Main content area
    if st.session_state.filtered_data is not None:
        if st.session_state.user_info['username'] == "gangothri9":
            st.header("Project Database Viewer")

            if st.button("Show Users Database"):
                try:
                    conn = sqlite3.connect("users.db")  # change if your DB name is different
                    df = pd.read_sql_query("SELECT * FROM users", conn)
                    st.dataframe(df)
                    conn.close()
                except Exception as e:
                    st.error(f"Database error: {str(e)}")

        st.header("Data Overview")
        with st.expander("Data Preview"):
            st.dataframe(st.session_state.filtered_data.head(10))
        
        # Summary Statistics
        st.header("Financial Summary Statistics")
        summary_stats = get_summary_statistics(st.session_state.filtered_data, st.session_state.numeric_columns)
        st.dataframe(summary_stats)
        
        # Financial Metrics
        st.header("Key Financial Metrics")
        metrics = calculate_financial_metrics(st.session_state.filtered_data, st.session_state.numeric_columns)
        
        # Display metrics in columns
        if metrics:
            col1, col2, col3, col4 = st.columns(4)
            for i, (metric, value) in enumerate(metrics.items()):
                if i % 4 == 0:
                    col1.metric(metric, f"{value:,.2f}")
                elif i % 4 == 1:
                    col2.metric(metric, f"{value:,.2f}")
                elif i % 4 == 2:
                    col3.metric(metric, f"{value:,.2f}")
                else:
                    col4.metric(metric, f"{value:,.2f}")
        else:
            st.info("No financial metrics could be calculated. This may happen if no numeric columns were detected or data is insufficient.")
        
        # Visualization Section
        st.header("Data Visualization")
        
        # Tabs for different chart types
        viz_tab1, viz_tab2, viz_tab3 = st.tabs(["Time Series", "Bar Charts", "Pie Charts"])
        
        with viz_tab1:
            st.subheader("Time Series Analysis")
            if st.session_state.date_column and st.session_state.numeric_columns:
                time_series_column = st.selectbox(
                    "Select value to plot over time",
                    st.session_state.numeric_columns,
                    key="time_series"
                )
                
                if not st.session_state.filtered_data.empty:
                    try:
                        line_chart = create_line_chart(
                            st.session_state.filtered_data,
                            st.session_state.date_column,
                            time_series_column
                        )
                        st.pyplot(line_chart)
                    except Exception as e:
                        st.error(f"Could not create time series chart: {str(e)}")
                        st.info("Try selecting different columns or check your data format.")
                else:
                    st.info("No data available for time series visualization. Please upload data or adjust filters.")
        
        with viz_tab2:
            st.subheader("Bar Chart Analysis")
            if st.session_state.numeric_columns:
                bar_value_column = st.selectbox(
                    "Select value for bar chart",
                    st.session_state.numeric_columns,
                    key="bar_value"
                )
                
                if st.session_state.categorical_columns:
                    bar_category_column = st.selectbox(
                        "Group by category",
                        st.session_state.categorical_columns,
                        key="bar_category"
                    )
                    
                    if not st.session_state.filtered_data.empty:
                        try:
                            bar_chart = create_bar_chart(
                                st.session_state.filtered_data,
                                bar_category_column,
                                bar_value_column
                            )
                            st.pyplot(bar_chart)
                        except Exception as e:
                            st.error(f"Could not create bar chart: {str(e)}")
                            st.info("Try selecting different columns or check your data format.")
                    else:
                        st.info("No data available for bar chart visualization. Please upload data or adjust filters.")
                else:
                    st.info("No categorical columns available for bar chart grouping.")
            else:
                st.info("No numeric columns available for bar chart values.")
        
        with viz_tab3:
            st.subheader("Pie Chart Analysis")
            if st.session_state.categorical_columns and st.session_state.numeric_columns:
                pie_value_column = st.selectbox(
                    "Select value for pie chart",
                    st.session_state.numeric_columns,
                    key="pie_value"
                )
                
                pie_category_column = st.selectbox(
                    "Group by category",
                    st.session_state.categorical_columns,
                    key="pie_category"
                )
                
                if not st.session_state.filtered_data.empty:
                    try:
                        pie_chart = create_pie_chart(
                            st.session_state.filtered_data,
                            pie_category_column,
                            pie_value_column
                        )
                        st.pyplot(pie_chart)
                    except Exception as e:
                        st.error(f"Could not create pie chart: {str(e)}")
                        st.info("Try selecting different columns or check your data format.")
                else:
                    st.info("No data available for pie chart visualization. Please upload data or adjust filters.")
            else:
                st.info("Pie charts require both categorical and numeric columns.")
        
        
        # AI Predictions
        st.header("AI-Powered Predictions")
        
        if st.session_state.date_column and st.session_state.numeric_columns:
            prediction_column = st.selectbox(
                "Select financial metric to predict",
                st.session_state.numeric_columns,
                key="prediction_column"
            )
            
            prediction_days = st.slider(
                "Number of days to predict",
                min_value=7,
                max_value=90,
                value=30,
                step=7
            )
            
            if st.button("Generate Prediction"):
                with st.spinner("Generating AI predictions..."):
                    try:
                        # Initialize html_content if it's not already in session state or accessible
                        # This ensures the variable exists even if the Export section hasn't run
                        html_content = "" 
                        
                        # Get prediction and figure
                        prediction_result, prediction_fig = predict_future_values(
                            st.session_state.filtered_data,
                            st.session_state.date_column,
                            prediction_column,
                            prediction_days
                        )
                        
                        # Store prediction result in session state for the export feature
                        st.session_state.prediction_result = prediction_result
                        st.session_state.prediction_fig = prediction_fig
                        st.session_state.last_prediction_column = prediction_column
                        
                        st.success(f"Prediction generated for the next {prediction_days} days")
                        st.pyplot(prediction_fig)
                        
                        # Show prediction summary
                        st.subheader("Prediction Summary")
                        st.write(f"Predicted average {prediction_column}: {prediction_result['average_prediction']:.2f}")
                        st.write(f"Predicted trend: {prediction_result['trend_description']}")
                        
                    except Exception as e:
                        st.error(f"Error generating prediction: {str(e)}")
                        st.info("Prediction requires sufficient historical data. Try a different metric or adjust date range.")
        
        # Download section
        st.header("Export Dashboard")
        
        col1_exp, col2_exp = st.columns(2)
        
        with col1_exp:
            if st.button("Export Dashboard as HTML", key="btn_export_html"):
                try:
                    import plotly.io as pio
                    
                    html_content = f"""
                    <html>
                    <head>
                        <title>AI FINANCIAL TRACKER Report</title>
                        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                        <style>
                            body {{ font-family: sans-serif; padding: 20px; }}
                            .chart {{ margin-bottom: 40px; border: 1px solid #eee; padding: 10px; }}
                            h1 {{ color: #1f77b4; }}
                            .table {{ border-collapse: collapse; width: 100%; }}
                            .table th, .table td {{ border: 1px solid #ddd; padding: 8px; }}
                            .table tr:nth-child(even){{background-color: #f2f2f2;}}
                        </style>
                    </head>
                    <body>
                        <h1>An AI That Converts Chaos into Clarity - Summary Report</h1>
                        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <hr>
                        
                        <h2>Financial Summary Statistics</h2>
                        {summary_stats.to_html(classes='table')}
                        
                        <h2>Key Financial Metrics</h2>
                        <ul>
                            {"".join([f"<li><strong>{k}:</strong> {v:,.2f}</li>" for k, v in metrics.items()])}
                        </ul>
                    </body>
                    </html>
                    """
                    
                    # Add charts to HTML if they exist in the UI state
                    if st.session_state.date_column and st.session_state.numeric_columns:
                        # We use the currently selected columns from session state
                        current_ts = st.session_state.get("time_series", st.session_state.numeric_columns[0])
                        line_chart = create_line_chart(st.session_state.filtered_data, st.session_state.date_column, current_ts)
                        from visualization import fig_to_html
                        html_content = html_content.replace("</body>", f"<h2>Time Series Analysis ({current_ts})</h2><div class='chart'>{fig_to_html(line_chart)}</div></body>")
                    html_content = html_content.replace("<title>AI FINANCIAL TRACKER Report</title>", "<title>An AI That Converts Chaos into Clarity Report</title>")
                    
                    if st.session_state.numeric_columns and st.session_state.categorical_columns:
                        from visualization import fig_to_html
                        current_bar_v = st.session_state.get("bar_value", st.session_state.numeric_columns[0])
                        current_bar_c = st.session_state.get("bar_category", st.session_state.categorical_columns[0])
                        bar_chart = create_bar_chart(st.session_state.filtered_data, current_bar_c, current_bar_v)
                        html_content = html_content.replace("</body>", f"<h2>Bar Chart Analysis ({current_bar_v} by {current_bar_c})</h2><div class='chart'>{fig_to_html(bar_chart)}</div></body>")
                        
                        current_pie_v = st.session_state.get("pie_value", st.session_state.numeric_columns[0])
                        current_pie_c = st.session_state.get("pie_category", st.session_state.categorical_columns[0])
                        pie_chart = create_pie_chart(st.session_state.filtered_data, current_pie_c, current_pie_v)
                        html_content = html_content.replace("</body>", f"<h2>Pie Chart Analysis ({current_pie_v} by {current_pie_c})</h2><div class='chart'>{fig_to_html(pie_chart)}</div></body>")

                    # Add AI prediction if it was generated
                    if 'prediction_result' in st.session_state and 'prediction_fig' in st.session_state:
                        from visualization import fig_to_html
                        pred_col = st.session_state.get('last_prediction_column', 'Value')
                        html_content = html_content.replace("</body>", f"<h2>AI Prediction ({pred_col})</h2><div class='chart'>{fig_to_html(st.session_state.prediction_fig)}</div></body>")

                    html_content = html_content.replace("</body>", "</html>")
                    
                    st.download_button(
                        label="Click here to download dashboard",
                        data=html_content,
                        file_name="financial_dashboard_report.html",
                        mime="text/html"
                    )
                except Exception as e:
                    st.error(f"Error creating HTML report: {str(e)}")

        with col2_exp:
            if st.button("Export Data (CSV)", key="btn_export_csv"):
                csv = st.session_state.filtered_data.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="financial_data_export.csv",
                    mime="text/csv"
                )
        
        if st.button("Export Summary Text Report", key="btn_export_txt"):
            # Create a simple summary report
            buffer = io.StringIO()
            buffer.write("# An AI That Converts Chaos into Clarity - Summary Report\n\n")
            buffer.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            buffer.write("## Data Summary\n")
            buffer.write(f"Records: {len(st.session_state.filtered_data)}\n")
            
            if st.session_state.date_column and not st.session_state.filtered_data.empty:
                min_date = st.session_state.filtered_data[st.session_state.date_column].min()
                max_date = st.session_state.filtered_data[st.session_state.date_column].max()
                buffer.write(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}\n\n")
            else:
                buffer.write("Date range: Not available\n\n")
            
            buffer.write("## Key Metrics\n")
            if metrics:
                for metric, value in metrics.items():
                    buffer.write(f"{metric}: {value:,.2f}\n")
            else:
                buffer.write("No metrics available\n")
            
            # Add Graph Analysis section
            buffer.write("\n## Graph Analysis\n")
            
            # Time series analysis
            if st.session_state.date_column and not st.session_state.filtered_data.empty:
                time_series_metrics = []
                
                for value_column in st.session_state.numeric_columns[:3]:
                    try:
                        trend_results = analyze_trends(
                            st.session_state.filtered_data,
                            st.session_state.date_column,
                            value_column
                        )
                        
                        if trend_results:
                            time_series_metrics.append(f"### {value_column} Time Series\n")
                            time_series_metrics.append(f"Trend: {trend_results.get('trend', 'Not available')}\n")
                            time_series_metrics.append(f"Average: {trend_results.get('average', 0):.2f}\n")
                            time_series_metrics.append(f"Volatility: {trend_results.get('volatility', 0):.2f}\n")
                            time_series_metrics.append(f"Change rate: {trend_results.get('change_rate', 0):.2f}%\n\n")
                    except:
                        continue
                
                if time_series_metrics:
                    buffer.write("".join(time_series_metrics))
                else:
                    buffer.write("No time series analysis available.\n\n")
            
            # Categorical analysis if available
            if st.session_state.categorical_columns and not st.session_state.filtered_data.empty:
                buffer.write("### Categorical Analysis\n")
                
                try:
                    cat_column = st.session_state.categorical_columns[0]
                    num_column = st.session_state.numeric_columns[0]
                    
                    category_counts = st.session_state.filtered_data[cat_column].value_counts()
                    total = category_counts.sum()
                    
                    buffer.write(f"Distribution for {cat_column}:\n")
                    for category, count in category_counts.items():
                        percentage = (count / total) * 100
                        buffer.write(f"- {category}: {count} ({percentage:.1f}%)\n")
                    
                    buffer.write("\n")
                except:
                    buffer.write("Error generating categorical analysis.\n\n")
            
            # Add AI predictions if generated
            if 'prediction_result' in st.session_state and st.session_state.prediction_result:
                prediction_result = st.session_state.prediction_result
                buffer.write("## AI Predictions\n")
                if 'prediction_column' in st.session_state:
                    buffer.write(f"Predicted average {st.session_state.get('prediction_column', 'Value')}: {prediction_result['average_prediction']:.2f}\n")
                buffer.write(f"Predicted trend: {prediction_result['trend_description']}\n\n")
            
            report_text = buffer.getvalue()
            
            st.download_button(
                label="Download Text Report",
                data=report_text,
                file_name="financial_summary_report.txt",
                mime="text/plain"
            )
    
    else:
        # Display instructions when no data is loaded
        st.info("👈 Please upload your financial data file using the sidebar to get started.")
        
        # Sample dashboard preview
        st.header("Dashboard Preview")
        st.image("https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4c8.svg", width=100)
        st.markdown("""
        ## What you can do with this dashboard:
        
        - **Visualize financial trends** with interactive time series charts
        - **Compare financial metrics** using bar and pie charts
        - **Filter data** by date ranges and categories
        - **Get AI-powered predictions** for future financial performance
        - **Export data and reports** for further analysis
        
        Supported file formats: CSV and Excel (.xlsx, .xls)
        """)
