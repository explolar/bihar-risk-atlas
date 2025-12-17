import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import plotly.express as px

# 1. Page Config
st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

# 2. Enhanced Styling
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    h1, h2, h3 { color: #0f172a; font-family: 'Segoe UI', sans-serif; }
    
    /* Card Styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-top: 4px solid #1e3a8a;
        text-align: center;
    }
    
    /* Custom Sidebar */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#1e3a8a, #1e40af);
        color: white;
    }
    
    /* Glassmorphism Footer */
    .footer {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        color: #64748b;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "final_risk_atlas_bihar.geojson")
    if not os.path.exists(file_path):
        file_path = os.path.join(os.path.dirname(base_dir), "data", "final_risk_atlas_bihar.geojson")
    
    gdf = gpd.read_file(file_path)
    rename_map = {
        "flood_pressure": "Flood_Risk_Score", "gw_stress_index": "GW_Stress_Score",
        "compound_class": "Risk_Category", "compound_risk": "Compound_Score",
        "stress_slope": "Degradation_Rate", "block": "block_name"
    }
    gdf = gdf.rename(columns=rename_map)
    
    # Force lat/lon projection
    if gdf.crs is None or gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    return gdf

gdf = load_data()

# --- COLOR LOGIC ---
def get_color(feature, layer_type):
    if layer_type == 'risk':
        val = feature['properties'].get('Risk_Category', 'Low')
        return {'Critical': '#991b1b', 'High': '#d97706', 'Moderate': '#fcd34d', 'Low': '#059669'}.get(val, '#9ca3af')
    
    val = feature['properties'].get(layer_type, 0)
    if pd.isna(val): return '#9ca3af'
    return '#7f1d1d' if val > 0.7 else '#f59e0b' if val > 0.4 else '#10b981'

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/water-unbalanced.png", width=60)
    st.title("Atlas Navigator")
    selected_block = st.selectbox("Search District/Block", ["Bihar State View"] + sorted(gdf["block_name"].unique().tolist()))
    
    st.divider()
    st.subheader("State Vitality")
    st.metric("Blocks Analyzed", len(gdf))
    criticals = len(gdf[gdf["Risk_Category"] == "Critical"])
    st.metric("Critical Hotspots", criticals, delta=f"{(criticals/len(gdf)*100):.1f}%", delta_color="inverse")

# --- MAIN DASHBOARD ---
st.title("🌊 Bihar Hydro-Climatic Risk Atlas")

col_map, col_stats = st.columns([2.5, 1])

with col_map:
    # 1. Map Control Logic
    m_center = [25.8, 85.5]
    m_zoom = 7
    if selected_block != "Bihar State View":
        centroid = gdf[gdf["block_name"] == selected_block].geometry.centroid.iloc[0]
        m_center, m_zoom = [centroid.y, centroid.x], 10

    m = folium.Map(location=m_center, zoom_start=m_zoom, tiles="CartoDB positron", zoom_control=True)
    
    # 2. Add Layers
    layers = [("Risk Category", "risk", True), ("Flood Pressure", "Flood_Risk_Score", False), ("GW Stress", "GW_Stress_Score", False)]
    for name, key, show in layers:
        folium.GeoJson(
            gdf,
            name=name,
            show=show,
            style_function=lambda x, k=key: {
                'fillColor': get_color(x, k),
                'color': 'white', 'weight': 0.8, 'fillOpacity': 0.7
            },
            tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'], aliases=['Block:', 'Status:'])
        ).add_to(m)

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # 3. RENDER MAP (With fixed key to prevent flickering)
    st_folium(m, width="100%", height=600, key=f"map_{selected_block}")

with col_stats:
    if selected_block != "Bihar State View":
        data = gdf[gdf["block_name"] == selected_block].iloc[0]
        
        # Banner
        risk_color = get_color({'properties': data.to_dict()}, 'risk')
        st.markdown(f"""
            <div style="background:{risk_color}; padding:20px; border-radius:15px; color:white; text-align:center;">
                <h2 style="color:white; margin:0">{data['block_name']}</h2>
                <small>{data['Risk_Category'].upper()} PRIORITY</small>
            </div>
        """, unsafe_allow_html=True)
        
        # Grid Metrics
        st.write("")
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="metric-card"><small>Flood</small><br><b>{data["Flood_Risk_Score"]:.2f}</b></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><small>GW Stress</small><br><b>{data["GW_Stress_Score"]:.2f}</b></div>', unsafe_allow_html=True)
        
        # Trend
        st.markdown("### 📈 Risk Trajectory")
        years = [2021, 2022, 2023, 2024, 2025]
        scores = [data['Compound_Score'] - (data['Degradation_Rate'] * (2025-y)) for y in years]
        fig = px.line(x=years, y=scores, template="plotly_white", markers=True)
        fig.update_traces(line_color=risk_color, line_width=4)
        fig.update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig, use_container_width=True)

        csv = pd.DataFrame([data.drop('geometry')]).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", csv, f"{data['block_name']}.csv", use_container_width=True)
    else:
        st.markdown("### 🗺️ State Profile")
        fig_pie = px.pie(gdf, names='Risk_Category', hole=0.5,
                         color='Risk_Category',
                         color_discrete_map={'Critical': '#991b1b', 'High': '#d97706', 'Moderate': '#fcd34d', 'Low': '#059669'})
        fig_pie.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=350, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)

# --- 4. DATA EXPLORER TABLE ---
st.markdown("### 🔎 Regional Comparison Table")
search_query = st.text_input("Quick Search Blocks...", placeholder="e.g. Patna")
table_df = gdf.drop(columns='geometry')
if search_query:
    table_df = table_df[table_df['block_name'].str.contains(search_query, case=False)]

st.dataframe(
    table_df.sort_values("Compound_Score", ascending=False),
    column_config={
        "Compound_Score": st.column_config.ProgressColumn("Risk Intensity", min_value=0, max_value=1),
        "Risk_Category": "Classification"
    },
    use_container_width=True,
    hide_index=True
)

st.markdown("""
    <div class="footer">
        Bihar Hydro-Climatic Risk Atlas © 2025 | Data provided by Water Resources Dept.
    </div>
""", unsafe_allow_html=True)