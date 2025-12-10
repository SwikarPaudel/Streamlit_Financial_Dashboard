import requests, pandas as pd, streamlit as st 
#  custom exception handler for st.secrets
from streamlit.errors import StreamlitAPIException 


try:
    #  ATTEMPT CLOUD DEPLOYMENT METHOD (st.secrets)
    # This will work when deployed on Streamlit Community Cloud
    api_key = st.secrets["alphavantage"]["api_key"]
    st.caption(" Running with Streamlit Secrets (Cloud)")
except (StreamlitAPIException, KeyError):
    #  LOCAL DEVELOPMENT METHOD
    # This will work when running 'streamlit run' locally
    try:
        from API_KEY import api_key 
        st.caption(" Running with local API_KEY.py")
    except ImportError:
        #  FAILURE STATE (Key not found anywhere)
        st.error("ERROR: API key not found. Please create an API_KEY.py file for local testing or configure secrets for cloud deployment.")
        st.stop()

financial_functions = {
    "Time Series": [
        "TIME_SERIES_DAILY", 
        "GLOBAL_QUOTE",      
        "SYMBOL_SEARCH"      
    ],

    "Fundamentals": [
        "OVERVIEW",          
        "INCOME_STATEMENT",  
        "EARNINGS"           
    ],

    "Forex (FX)": [
        "CURRENCY_EXCHANGE_RATE", 
        "FX_DAILY"
    ],

    "Technical Indicators": [
        "SMA", 
        "RSI", 
    ]
}

# Main Dashboard Layout
st.title('Financial Data Dashboard (Alpha Vantage)')
st.markdown("---") 

#  Sidebar UI (The control panel)
st.sidebar.header('Settings')

# Pick a group of functions
func_group = st.sidebar.selectbox(
    "Choose a Data Category",
    list(financial_functions.keys())
)

# Pick the specific function (endpoint)
the_endpoint = st.sidebar.selectbox(
    "What kind of data are we fetching?",
    financial_functions[func_group]
)

# Helper Function 

def fetch_alpha_vantage_data(my_url, spin_text):
    """
    Tries to grab data from Alpha Vantage. If it fails, it
    shows an error and returns None.
    """
    with st.spinner(f'Working on it... {spin_text}'):
        try:
            req = requests.get(my_url)
            req.raise_for_status() # Catches 404s, 500s, etc.
            data_json = req.json()
            return data_json
        except requests.exceptions.RequestException as err:
            st.error(f"Ouch! An error happened while fetching data: {err}")
            return None


# Endpoint Logic 

if the_endpoint == 'TIME_SERIES_DAILY':
    st.subheader(f'Stock Price History: **{the_endpoint}**')
    stock_sym = st.sidebar.text_input('Stock Symbol', 'IBM').upper() 
    size_opt = st.sidebar.radio('Data Amount', ['compact']) 
    url_str = (f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={stock_sym}'
               f'&outputsize={size_opt}&apikey={api_key}')
    
    raw_data = fetch_alpha_vantage_data(url_str, f'Getting daily prices for {stock_sym}')

    if raw_data:
        if 'Time Series (Daily)' in raw_data:
            time_series = raw_data["Time Series (Daily)"]
            
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index.name = 'Date'
            
            # Clean up those weird prefixes (e.g., '4. close' becomes 'close')
            df.columns = [c.split('. ')[1] for c in df.columns] 
            df = df.apply(pd.to_numeric, errors='coerce') 

            st.dataframe(df.head(20))
            
            # CRITICAL FIX: Use the cleaned column name 'close' for plotting ---
            st.line_chart(df['close']) 
            
        else:
            st.warning("Data structure was weird. Maybe the symbol is wrong?")
            st.json(raw_data)

elif the_endpoint == 'GLOBAL_QUOTE':
    st.subheader(f'Current Quote: **{the_endpoint}**')
    stock_sym = st.sidebar.text_input('Stock Symbol', 'AAPL').upper()
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={stock_sym}&apikey={api_key}'

    data = fetch_alpha_vantage_data(url, f'Fetching real-time quote for {stock_sym}')

    if data:
        quote = data.get('Global Quote', {})

        if quote:
            df = pd.DataFrame([quote]).T
            df.columns = ['Value']
            st.table(df)
        else:
            st.error("Could not fetch quote. Check symbol.")
            st.json(data)
            
elif the_endpoint == 'INCOME_STATEMENT':
    st.subheader(f'Company Financials: **{the_endpoint}**')
    fund_sym = st.sidebar.text_input('Company Ticker', 'MSFT').upper()
    url = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={fund_sym}&apikey={api_key}'
    data_fund = fetch_alpha_vantage_data(url, f'Downloading income statements for {fund_sym}')

    if data_fund and 'annualReports' in data_fund:
        reports = data_fund['annualReports']
        df_income = pd.DataFrame(reports)
        df_income = df_income.set_index('fiscalDateEnding') 
        st.table(df_income.T)

        st.caption(f"Showing the last {len(reports)} annual income statements.")
    elif data_fund:
        st.error(f"Could not find annual reports for {fund_sym}. Check the ticker.")
        st.json(data_fund)
        
elif the_endpoint == 'SMA':
    st.subheader(f'Technical Indicator: **{the_endpoint}** (Simple Moving Average)')
    sym = st.sidebar.text_input('Symbol', 'TSLA').upper()
    interval = st.sidebar.selectbox('Interval', ['daily', 'weekly', 'monthly'])
    time_period = st.sidebar.number_input('Time Period', min_value=1, value=20)
    series_type = st.sidebar.selectbox('Series Type', ['close', 'open', 'high', 'low'])
    
    url = (f'https://www.alphavantage.co/query?function=SMA&symbol={sym}&interval={interval}&time_period={time_period}'
           f'&series_type={series_type}&apikey={api_key}')

    data = fetch_alpha_vantage_data(url, f'Calculating {time_period}-period SMA for {sym}')

    if data:
        indicator_key = f'Technical Analysis: {the_endpoint}'
        ts = data.get(indicator_key, {})

        if ts:
            df = pd.DataFrame.from_dict(ts, orient='index')
            df.index.name = 'Date'
            df.columns = [the_endpoint]
            df = df.apply(pd.to_numeric, errors='coerce')
            
            st.dataframe(df.head(20))
            st.line_chart(df)
            st.caption(f"The chart shows the {time_period}-day Simple Moving Average.")
        else:
            st.error(f"Could not calculate {the_endpoint}. Check parameters.")
            st.json(data)

elif the_endpoint == 'RSI':
    st.subheader(f'Technical Indicator: **{the_endpoint}** (Relative Strength Index)')
    sym = st.sidebar.text_input('Symbol', 'GOOGL').upper()
    interval = st.sidebar.selectbox('Interval', ['daily', 'weekly', 'monthly'])
    time_period = st.sidebar.number_input('Time Period', min_value=1, value=14)
    series_type = st.sidebar.selectbox('Series Type', ['close'])
    
    url = (f'https://www.alphavantage.co/query?function=RSI&symbol={sym}&interval={interval}&time_period={time_period}'
           f'&series_type={series_type}&apikey={api_key}')

    data = fetch_alpha_vantage_data(url, f'Calculating {time_period}-period RSI for {sym}')

    if data:
        indicator_key = f'Technical Analysis: {the_endpoint}'
        ts = data.get(indicator_key, {})

        if ts:
            df = pd.DataFrame.from_dict(ts, orient='index')
            df.index.name = 'Date'
            df.columns = [the_endpoint]
            df = df.apply(pd.to_numeric, errors='coerce')
            
            st.dataframe(df.head(20))
            st.line_chart(df)
            st.caption("RSI values typically range from 0 to 100. Values below 30 suggest the asset might be **oversold**, and values above 70 suggest it might be **overbought**.")
        else:
            st.error(f"Could not calculate {the_endpoint}. Check parameters.")
            st.json(data)
            
elif the_endpoint == 'OVERVIEW':
    st.subheader(f'Company Fundamentals: **{the_endpoint}**')
    sym = st.sidebar.text_input('Symbol', 'MSFT').upper()
    
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={sym}&apikey={api_key}'
    
    data = fetch_alpha_vantage_data(url, f'Fetching overview for {sym}')

    if data and data.get('Symbol') == sym:
        # Create a single-row DataFrame from the overview dictionary and transpose it
        df = pd.DataFrame([data]).T
        df.columns = ['Value']
        st.table(df)
        
        st.markdown('***')
        st.caption('Company Description:')
        st.write(data.get('Description', 'No description available.'))
        
    else:
        st.error("Could not fetch company overview. Check the symbol and API key.")
        if data: st.json(data)


# Placeholder for others
else:
    # This handles all currently unimplemented endpoints (SYMBOL_SEARCH, EARNINGS, FX_DAILY, CURRENCY_EXCHANGE_RATE)
    st.info(f"The **{the_endpoint}** endpoint is not yet fully implemented in this script. Please select one of the following: TIME_SERIES_DAILY, GLOBAL_QUOTE, OVERVIEW, INCOME_STATEMENT, SMA, or RSI.")

st.markdown("---")

st.caption("Powered by Alpha Vantage and a tired coder.")
