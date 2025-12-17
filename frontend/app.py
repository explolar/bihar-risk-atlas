import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

# --- 1. LOAD DATA ---
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "final_risk_atlas_bihar.geojson")
    
    if not os.path.exists(file_path):
        st.error(f"❌ File not found: {file_path}")
        st.stop()
    
    gdf = gpd.read_file(file_path)
    
    # Standardize Column Names
    rename_map = {
        "flood_pressure": "Flood_Risk_Score", 
        "gw_stress_index": "GW_Stress_Score",
        "compound_class": "Risk_Category",
        "compound_risk": "Compound_Score",
        "stress_slope": "Degradation_Rate",
        "block": "block_name"
    }
    gdf = gdf.rename(columns=rename_map)
    gdf["block_name"] = gdf["block_name"].astype(str)
    
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    elif gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
        
    return gdf

gdf = load_data()

# --- 2. MAP COLOR LOGIC ---
def get_color(value, layer_type):
    """Helper function to determine color based on value and layer type."""
    if layer_type == 'risk':
        colors = {'Critical': '#b2182b', 'High': '#ef8a62', 'Moderate': '#fddbc7', 'Low': '#67a9cf'}
        return colors.get(value, '#f7f7f7')
    
    # For numeric layers (Flood/GW), use a 0-1 scale
    if value is None or pd.isna(value): return '#f7f7f7'
    if value > 0.8: return '#b2182b' # Dark Red
    if value > 0.6: return '#ef8a62' # Orange
    if value > 0.4: return '#fddbc7' # Peach
    return '#67a9cf' # Blue

# --- 3. SIDEBAR & DASHBOARD ---
with st.sidebar:
    st.header("🔍 Controls")
    selected_block = st.selectbox("Search Block", options=["All Blocks"] + sorted(gdf["block_name"].unique().tolist()))
    st.divider()
    st.info("💡 Use the **Layer Icon** on the map (top right) to switch between Risk, Flood, and Groundwater views.")

st.title("🌊 Bihar Hydro-Climatic Risk Atlas")
col1, col2 = st.columns([3, 1.3])

with col1:
    # Set Map Center
    center = [25.8, 85.5]
    zoom = 7
    if selected_block != "All Blocks":
        block_geom = gdf[gdf["block_name"] == selected_block].geometry.centroid.iloc[0]
        center, zoom = [block_geom.y, block_geom.x], 10

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

    # Layer 1: Compound Risk
    fg1 = folium.FeatureGroup(name="Compound Risk Class", show=True)
    folium.GeoJson(
        gdf,
        style_function=lambda f: {
            'fillColor': get_color(f['properties']['Risk_Category'], 'risk'),
            'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'], aliases=['Block:', 'Risk:'])
    ).add_to(fg1)

    # Layer 2: Flood Pressure
    fg2 = folium.FeatureGroup(name="Flood Pressure Index", show=False)
    folium.GeoJson(
        gdf,
        style_function=lambda f: {
            'fillColor': get_color(f['properties']['Flood_Risk_Score'], 'numeric'),
            'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Flood_Risk_Score'], aliases=['Block:', 'Flood Score:'])
    ).add_to(fg2)

    # Layer 3: Groundwater Stress
    fg3 = folium.FeatureGroup(name="GW Stress Index", show=False)
    folium.GeoJson(
        gdf,
        style_function=lambda f: {
            'fillColor': get_color(f['properties']['GW_Stress_Score'], 'numeric'),
            'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(fields=['block_name', 'GW_Stress_Score'], aliases=['Block:', 'GW Stress:'])
    ).add_to(fg3)

    # Add all layers and the control widget
    fg1.add_to(m)
    fg2.add_to(m)
    fg3.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width="100%", height=600, key="bihar_map")

with col2:
    if selected_block != "All Blocks":
        row = gdf[gdf["block_name"] == selected_block].iloc[0]
        st.subheader(f"📊 {row['block_name']}")
        
        # Display Metrics
        c1, c2 = st.columns(2)
        c1.metric("Flood Risk", f"{row['Flood_Risk_Score']:.2f}")
        c2.metric("GW Stress", f"{row['GW_Stress_Score']:.2f}")
        
        # Trend Chart (Simulated from Degradation Rate)
        years = [2021, 2022, 2023, 2024, 2025]
        scores = [row['Compound_Score'] - (row['Degradation_Rate'] * (2025-y)) for y in years]
        fig = px.line(x=years, y=scores, title="Risk Trajectory", markers=True)
        fig.update_layout(height=250, margin=dict(l=0,r=0,b=0,t=40))
        st.plotly_chart(fig, use_container_width=True)
        
        # Download
        csv = pd.DataFrame([row.drop('geometry')]).to_csv().encode('utf-8')
        st.download_button("📥 Download Report", csv, f"{selected_block}.csv", use_container_width=True)
    else:
        st.info("Select a block to view specific trends. Use the map layers to explore different risk factors.")