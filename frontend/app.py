import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import plotly.express as px

# Setting page to wide for a professional dashboard look
st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

# --- 1. ROBUST DATA LOADING ---
@st.cache_data
def load_data():
    # Detects if app is running locally or on Streamlit Cloud
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check common paths for the data folder
    possible_paths = [
        os.path.join(base_dir, "data", "final_risk_atlas_bihar.geojson"),
        os.path.join(os.path.dirname(base_dir), "data", "final_risk_atlas_bihar.geojson")
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        st.error("❌ Data file not found. Please ensure 'data/final_risk_atlas_bihar.geojson' exists.")
        st.stop()
    
    gdf = gpd.read_file(file_path)
    
    # Mapping original columns to user-friendly names
    rename_map = {
        "flood_pressure": "Flood_Risk_Score", 
        "gw_stress_index": "GW_Stress_Score",
        "compound_class": "Risk_Category",
        "compound_risk": "Compound_Score",
        "stress_slope": "Degradation_Rate",
        "block": "block_name"
    }
    gdf = gdf.rename(columns=rename_map)
    
    # Ensure spatial projection is correct for Folium (Lat/Long)
    if gdf.crs is None or gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    
    return gdf

gdf = load_data()

# --- 2. COLOR PALETTES ---
def get_color(feature, layer_type):
    """Returns hex colors based on risk levels or numeric scores."""
    if layer_type == 'risk':
        val = feature['properties'].get('Risk_Category', 'Low')
        return {'Critical': '#b2182b', 'High': '#ef8a62', 'Moderate': '#fddbc7', 'Low': '#67a9cf'}.get(val, '#f7f7f7')
    
    # Numeric scaling for Flood/GW Stress (0 to 1)
    val = feature['properties'].get(layer_type, 0)
    if pd.isna(val) or val is None: return '#f7f7f7'
    if val > 0.7: return '#7f0000' # Deep Red
    if val > 0.5: return '#d73027' # Red
    if val > 0.3: return '#fdae61' # Orange
    return '#abd9e9' # Light Blue

# --- 3. DASHBOARD UI ---
st.title("🌊 Bihar Hydro-Climatic Risk Atlas")
st.markdown("---")

with st.sidebar:
    st.header("🔍 Controls")
    selected_block = st.selectbox("Search/Select Block", ["All Blocks"] + sorted(gdf["block_name"].unique().tolist()))
    
    st.divider()
    st.write("### Quick Summary")
    st.metric("Total Blocks Analysed", len(gdf))
    if "Risk_Category" in gdf.columns:
        critical_count = len(gdf[gdf["Risk_Category"] == "Critical"])
        st.metric("Critical Hotspots", critical_count, delta="Immediate Action", delta_color="inverse")

col1, col2 = st.columns([2.5, 1])

with col1:
    # Handle Map Centering and Zoom
    m_center = [25.8, 85.5]
    m_zoom = 7
    if selected_block != "All Blocks":
        # Get coordinates of the selected block to zoom in
        target = gdf[gdf["block_name"] == selected_block].geometry.centroid.iloc[0]
        m_center, m_zoom = [target.y, target.x], 10

    m = folium.Map(location=m_center, zoom_start=m_zoom, tiles="CartoDB positron")

    # Layer 1: Risk Category
    fg_risk = folium.FeatureGroup(name="Compound Risk Category", show=True)
    folium.GeoJson(gdf, style_function=lambda x: {
        'fillColor': get_color(x, 'risk'),
        'color': 'black', 'weight': 0.3, 'fillOpacity': 0.7
    }, tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'])).add_to(fg_risk)

    # Layer 2: Flood Pressure
    fg_flood = folium.FeatureGroup(name="Flood Pressure View", show=False)
    folium.GeoJson(gdf, style_function=lambda x: {
        'fillColor': get_color(x, 'Flood_Risk_Score'),
        'color': 'black', 'weight': 0.3, 'fillOpacity': 0.7
    }, tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Flood_Risk_Score'])).add_to(fg_flood)

    # Layer 3: GW Stress
    fg_gw = folium.FeatureGroup(name="Groundwater Stress View", show=False)
    folium.GeoJson(gdf, style_function=lambda x: {
        'fillColor': get_color(x, 'GW_Stress_Score'),
        'color': 'black', 'weight': 0.3, 'fillOpacity': 0.7
    }, tooltip=folium.GeoJsonTooltip(fields=['block_name', 'GW_Stress_Score'])).add_to(fg_gw)

    fg_risk.add_to(m)
    fg_flood.add_to(m)
    fg_gw.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width="100%", height=600, key="atlas_map")

with col2:
    if selected_block != "All Blocks":
        data = gdf[gdf["block_name"] == selected_block].iloc[0]
        st.subheader(f"📍 {data['block_name']}")
        
        # Risk Badge
        risk_color = get_color({'properties': data.to_dict()}, 'risk')
        st.markdown(f'<div style="background-color:{risk_color}; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;">{data["Risk_Category"]} RISK</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Metrics
        c1, c2 = st.columns(2)
        c1.metric("Flood Score", f"{data['Flood_Risk_Score']:.2f}")
        c2.metric("GW Stress", f"{data['GW_Stress_Score']:.2f}")
        
        # Trend Graph
        st.write("#### 📈 Trend Trajectory")
        years = [2021, 2022, 2023, 2024, 2025]
        # Calculate trend using Degradation Rate
        scores = [data['Compound_Score'] - (data['Degradation_Rate'] * (2025-y)) for y in years]
        fig = px.line(x=years, y=scores, markers=True)
        fig.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), yaxis_title="Risk Score", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

        # Download Feature
        st.divider()
        csv = pd.DataFrame([data.drop('geometry')]).to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Data Report", data=csv, file_name=f"{data['block_name']}_risk_report.csv", mime="text/csv", use_container_width=True)
        
    else:
        st.info("👈 Select a block from the sidebar or click on the map to view detailed risk trends and download reports.")
        # Summary Distribution Pie Chart
        st.write("#### State-wide Risk Profile")
        fig_pie = px.pie(gdf, names='Risk_Category', hole=0.4, color='Risk_Category',
                         color_discrete_map={'Critical': '#b2182b', 'High': '#ef8a62', 'Moderate': '#fddbc7', 'Low': '#67a9cf'})
        fig_pie.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)