import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import plotly.express as px

# 1. Page Config with Custom CSS for Styling
st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

st.markdown("""
    <style>
    /* Main Background and Typography */
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1e3a8a; font-family: 'Inter', sans-serif; font-weight: 800; }
    
    /* Custom Card Styling */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #1e3a8a;
        margin-bottom: 10px;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1e3a8a !important;
        color: white;
    }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] h2 {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA (Keep your robust logic) ---
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
    if gdf.crs is None or gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    return gdf

gdf = load_data()

# --- COLOR LOGIC (Enhanced Palette) ---
def get_color(feature, layer_type):
    if layer_type == 'risk':
        val = feature['properties'].get('Risk_Category', 'Low')
        return {'Critical': '#991b1b', 'High': '#d97706', 'Moderate': '#fcd34d', 'Low': '#059669'}.get(val, '#9ca3af')
    
    val = feature['properties'].get(layer_type, 0)
    if pd.isna(val): return '#9ca3af'
    if val > 0.7: return '#7f1d1d' 
    if val > 0.4: return '#f59e0b'
    return '#10b981'

# --- UI COMPONENTS ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/water-unbalanced.png", width=80)
    st.title("Atlas Controls")
    selected_block = st.selectbox("Search Territory", ["Bihar State View"] + sorted(gdf["block_name"].unique().tolist()))
    
    st.markdown("---")
    st.subheader("📊 Statistics")
    st.metric("Blocks Analyzed", len(gdf))
    criticals = len(gdf[gdf["Risk_Category"] == "Critical"])
    st.metric("Critical Zones", criticals, delta=f"{(criticals/len(gdf)*100):.1f}%", delta_color="inverse")

# --- MAIN DASHBOARD ---
st.title("🌊 Hydro-Climatic Risk Atlas: Bihar")
st.caption("Real-time composite monitoring of groundwater stress and surface flood pressure.")

col_map, col_stats = st.columns([2.2, 1])

with col_map:
    # Set Map Center
    m_center = [25.8, 85.5]
    m_zoom = 7.2
    if selected_block != "Bihar State View":
        target = gdf[gdf["block_name"] == selected_block].geometry.centroid.iloc[0]
        m_center, m_zoom = [target.y, target.x], 10

    m = folium.Map(location=m_center, zoom_start=m_zoom, tiles="CartoDB positron", zoom_control=False)
    
    # Stylized Layers
    for name, key, show in [("Risk Category", "risk", True), ("Flood Pressure", "Flood_Risk_Score", False), ("GW Stress", "GW_Stress_Score", False)]:
        folium.GeoJson(
            gdf,
            name=name,
            show=show,
            style_function=lambda x, k=key: {
                'fillColor': get_color(x, k),
                'color': 'white', 'weight': 1, 'fillOpacity': 0.7
            },
            tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'], aliases=['Block', 'Risk Status'])
        ).add_to(m)

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    st_folium(m, width="100%", height=650, key="main_atlas")

with col_stats:
    if selected_block != "Bihar State View":
        data = gdf[gdf["block_name"] == selected_block].iloc[0]
        
        # Stylized Header
        risk_color = get_color({'properties': data.to_dict()}, 'risk')
        st.markdown(f"""
            <div style="background:{risk_color}; padding:20px; border-radius:15px; color:white; margin-bottom:20px">
                <h2 style="color:white; margin:0">{data['block_name']}</h2>
                <p style="margin:0; opacity:0.9; font-weight:bold">{data['Risk_Category'].upper()} RISK ZONE</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Metrics Cards
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f'<div class="metric-card"><strong>Flood</strong><br><span style="font-size:24px">{data["Flood_Risk_Score"]:.2f}</span></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><strong>GW Stress</strong><br><span style="font-size:24px">{data["GW_Stress_Score"]:.2f}</span></div>', unsafe_allow_html=True)
        
        # Trend Graph with stylish theme
        st.markdown("### 📈 Risk Trajectory")
        years = [2021, 2022, 2023, 2024, 2025]
        scores = [data['Compound_Score'] - (data['Degradation_Rate'] * (2025-y)) for y in years]
        df_trend = pd.DataFrame({"Year": years, "Score": scores})
        
        fig = px.line(df_trend, x="Year", y="Score", template="plotly_white", markers=True)
        fig.update_traces(line_color=risk_color, line_width=4)
        fig.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis_showgrid=False, yaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

        # Download
        csv = pd.DataFrame([data.drop('geometry')]).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Technical Report", csv, f"{data['block_name']}_report.csv", "text/csv", use_container_width=True)
        
    else:
        st.markdown("### 🗺️ State Overview")
        st.info("Select a specific block on the map or search bar to view temporal trends and local vulnerability scores.")
        
        # Stylish Pie Chart
        fig_pie = px.pie(gdf, names='Risk_Category', hole=0.6,
                         color='Risk_Category',
                         color_discrete_map={'Critical': '#991b1b', 'High': '#d97706', 'Moderate': '#fcd34d', 'Low': '#059669'})
        fig_pie.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2), height=400, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")
st.caption("Data Source: Hydro-Climatic Research Division | Updated: 2025")