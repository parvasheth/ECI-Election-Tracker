import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import os

st.set_page_config(page_title="WB Election 2026 Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Inject Custom CSS for aesthetics
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        font-family: 'Inter', sans-serif;
    }
    h1 {
        color: #ff4b4b;
        text-align: center;
        font-weight: 800;
        margin-bottom: 30px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00d2ff;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #a0a0a0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    /* Style the dataframe slightly */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Check for Streamlit Secrets first (for Cloud deployment)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Fallback to local file
        creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'service_account.json')
        if not os.path.exists(creds_path):
            st.error("Credentials not found in st.secrets or local path.")
            st.stop()
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("1mTnwDbsvtq0WcKsfgjJALY8ajoGM_ZOAD72yTmZcGmM")
    
    sheet = spreadsheet.sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Clean Margin column if it exists
    if 'Margin' in df.columns:
        df['Margin'] = pd.to_numeric(df['Margin'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
    # Load Vote Share data
    try:
        vs_sheet = spreadsheet.worksheet("Vote_Share")
        vs_data = vs_sheet.get_all_records()
        vs_df = pd.DataFrame(vs_data)
        if 'Vote %' in vs_df.columns:
            vs_df['Vote %'] = pd.to_numeric(vs_df['Vote %'].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
    except Exception:
        vs_df = pd.DataFrame()
    
    return df, vs_df

st.markdown("<h1>🗳️ West Bengal Election 2026 - Live Dashboard</h1>", unsafe_allow_html=True)

with st.spinner("Fetching Live Data from Google Sheets..."):
    try:
        df, vs_df = load_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.stop()

if df.empty:
    st.warning("No data available in the Google Sheet. Please run `python scraper.py` first to populate data.")
    st.stop()

# Identify correct columns robustly
party_col = next((col for col in df.columns if 'Leading Party' in col or 'Party' in col), None)
constituency_col = next((col for col in df.columns if 'Constituency' in col), None)
candidate_col = next((col for col in df.columns if 'Leading Candidate' in col or 'Candidate' in col), None)

if not party_col:
    st.error("Could not find a 'Party' column in the data.")
    st.dataframe(df)
    st.stop()

# Top Metrics
col1, col2, col3 = st.columns(3)
total_seats = len(df)
party_counts = df[party_col].value_counts()
leading_party = party_counts.index[0] if not party_counts.empty else "N/A"
leading_seats = party_counts.iloc[0] if not party_counts.empty else 0

with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Total Constituencies Declared/Leading</div><div class="metric-value">{total_seats}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Leading Party</div><div class="metric-value">{leading_party}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Seats for {leading_party}</div><div class="metric-value">{leading_seats}</div></div>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Charts Section
c1, c2 = st.columns(2)

with c1:
    st.subheader("📊 Party-wise Seat Share")
    fig_pie = px.pie(
        values=party_counts.values, 
        names=party_counts.index, 
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True)

    if not vs_df.empty and 'Party' in vs_df.columns and 'Vote %' in vs_df.columns:
        st.subheader("📈 State Vote Share %")
        # Filter out tiny shares for cleaner chart
        chart_vs_df = vs_df[vs_df['Vote %'] > 0.5]
        fig_vs_pie = px.pie(
            chart_vs_df,
            values='Vote %', 
            names='Party', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_vs_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_vs_pie, use_container_width=True)

with c2:
    if 'Margin' in df.columns and candidate_col and constituency_col:
        st.subheader("🔥 Top 10 Highest Margins")
        top_margins = df.nlargest(10, 'Margin')
        top_margins['Label'] = top_margins[candidate_col] + " (" + top_margins[constituency_col] + ")"
        fig_bar = px.bar(
            top_margins, 
            y='Label', 
            x='Margin', 
            orientation='h',
            color='Margin',
            color_continuous_scale='Reds'
        )
        fig_bar.update_layout(
            yaxis={'categoryorder':'total ascending'},
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)", 
            font_color="white"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Margin data not available for plotting.")

st.markdown("<hr>", unsafe_allow_html=True)

st.subheader("⚖️ Swing Seat & Scenario Analysis")
margin_threshold = st.slider("Define 'Swing Seat' Margin Threshold", min_value=100, max_value=20000, value=5000, step=100)

valid_margin_df = df[df['Margin'] > 0]
swing_seats_df = valid_margin_df[valid_margin_df['Margin'] <= margin_threshold]

st.markdown(f"**Total Swing Seats Identified:** {len(swing_seats_df)}")

if not swing_seats_df.empty:
    # Safely get Trailing Party column if it exists
    trailing_party_col = next((col for col in df.columns if 'Trailing Party' in col), None)
    
    if trailing_party_col:
        all_parties = pd.concat([df[party_col], df[trailing_party_col]]).unique()
        all_parties = [p for p in all_parties if pd.notna(p) and str(p).strip() != ""]
        
        selected_party = st.selectbox("Analyze Scenarios For Party:", all_parties, index=all_parties.index(leading_party) if leading_party in all_parties else 0)
        
        # Safe seats: Leading and margin > threshold (or no margin reported yet)
        safe_leads = len(df[(df[party_col] == selected_party) & ((df['Margin'] > margin_threshold) | (df['Margin'] == 0))])
        
        # Vulnerable leads: Leading but margin is tight
        vuln_leads = len(swing_seats_df[swing_seats_df[party_col] == selected_party])
        
        # Opportunities: Trailing but margin is tight
        opportunities = len(swing_seats_df[swing_seats_df[trailing_party_col] == selected_party])
        
        current_total = safe_leads + vuln_leads
        best_case = safe_leads + vuln_leads + opportunities
        worst_case = safe_leads
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Worst Case (Lose all swings)</div><div class="metric-value" style="color:#ff4b4b;">{worst_case}</div></div>', unsafe_allow_html=True)
        with sc2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Current Standings</div><div class="metric-value" style="color:#f39c12;">{current_total}</div></div>', unsafe_allow_html=True)
        with sc3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Best Case (Win all swings)</div><div class="metric-value" style="color:#2ecc71;">{best_case}</div></div>', unsafe_allow_html=True)
            
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### 🛡️ Vulnerable Seats (Currently Leading)")
            vuln_df = swing_seats_df[swing_seats_df[party_col] == selected_party][['Constituency', trailing_party_col, 'Margin']].sort_values('Margin')
            st.dataframe(vuln_df, use_container_width=True)
        
        with col_b:
            st.write("### 🎯 Opportunities (Currently Trailing)")
            opp_df = swing_seats_df[swing_seats_df[trailing_party_col] == selected_party][['Constituency', party_col, 'Margin']].sort_values('Margin')
            st.dataframe(opp_df, use_container_width=True)
    else:
        st.info("Trailing Party column not found, cannot calculate opportunities.")

st.markdown("<hr>", unsafe_allow_html=True)

st.subheader("📋 Detailed Results Explorer")
search_term = st.text_input("🔍 Search by Constituency, Candidate, or Party")

filtered_df = df.copy()
if search_term:
    mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
    filtered_df = filtered_df[mask]

st.dataframe(filtered_df, use_container_width=True, height=500)
