import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd

# Try-except block for Plotly to prevent hard crashes
try:
    import plotly.express as px
except ImportError:
    st.error("Missing Plotly library. Please add 'plotly' to your requirements.txt")

st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

# --- 1. DATA LOADING ---
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Adjust path if app.py is inside a 'frontend' folder
    file_path = os.path.join(os.path.dirname(base_dir), "data", "final_risk_atlas_bihar.geojson")
    
    if not os.path.exists(file_path):
        # Fallback for different folder structures
        file_path = os.path.join(base_dir, "data", "final_risk_atlas_bihar.geojson")
        
    gdf = gpd.read_file(file_path)
    
    rename_map = {
        "flood_pressure": "Flood_Risk_Score", 
        "gw_stress_index": "GW_Stress_Score",
        "compound_class": "Risk_Category",
        "compound_risk": "Compound_Score",
        "stress_slope": "Degradation_Rate",
        "block": "block_name"
    }
    gdf = gdf.rename(columns=rename_map)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    return gdf

gdf = load_data()

# --- 2. MAP LAYERS ---
def get_color(val, layer_type='numeric'):
    if layer_type == 'risk':
        return {'Critical': '#b2182b', 'High': '#ef8a62', 'Moderate': '#fddbc7', 'Low': '#67a9cf'}.get(val, '#f7f7f7')
    
    if pd.isna(val): return '#f7f7f7'
    if val > 0.7: return '#b2182b' # High Stress (Red)
    if val > 0.4: return '#fddbc7' # Moderate (Orange)
    return '#67a9cf' # Low (Blue)

# --- 3. UI LAYOUT ---
st.title("🌊 Bihar Hydro-Climatic Risk Atlas")

with st.sidebar:
    st.header("🔍 Controls")
    selected_block = st.selectbox("Select Block", ["All Blocks"] + sorted(gdf["block_name"].unique().tolist()))
    st.divider()
    st.info("Use the layer control icon on the map to switch views.")

col1, col2 = st.columns([3, 1.2])

with col1:
    # Map Centering
    m_center = [25.8, 85.5]
    m_zoom = 7
    if selected_block != "All Blocks":
        centroid = gdf[gdf["block_name"] == selected_block].geometry.centroid.iloc[0]
        m_center, m_zoom = [centroid.y, centroid.x], 10

    m = folium.Map(location=m_center, zoom_start=m_zoom, tiles="CartoDB positron")

    # Group 1: Risk Category
    fg1 = folium.FeatureGroup(name="Compound Risk", show=True)
    folium.GeoJson(gdf, style_function=lambda x: {
        'fillColor': get_color(x['properties']['Risk_Category'], 'risk'),
        'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
    }).add_to(fg1)

    # Group 2: Flood Pressure
    fg2 = folium.FeatureGroup(name="Flood Pressure", show=False)
    folium.GeoJson(gdf, style_function=lambda x: {
        'fillColor': get_color(x['properties']['Flood_Risk_Score']),
        'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
    }).add_to(fg2)

    fg1.add_to(m)
    fg2.add_to(m)
    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=550)

with col2:
    if selected_block != "All Blocks":
        data = gdf[gdf["block_name"] == selected_block].iloc[0]
        st.subheader(data['block_name'])
        
        # Risk Metric
        st.metric("Compound Risk", f"{data['Compound_Score']:.2f}")
        
        # Simple Trend Chart
        try:
            years = [2021, 2022, 2023, 2024, 2025]
            vals = [data['Compound_Score'] - (data['Degradation_Rate'] * (2025-y)) for y in years]
            fig = px.line(x=years, y=vals, labels={'x':'Year', 'y':'Risk Score'})
            fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.warning("Trend chart unavailable.")

        # Download
        csv = pd.DataFrame([data.drop('geometry')]).to_csv().encode('utf-8')
        st.download_button("📥 Download Data", csv, f"{selected_block}.csv")
    else:
        st.write("Click a block or use the sidebar to begin analysis.")