import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import plotly.express as px

# 1. Page Config - Essential for responsiveness
st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

# 2. Refined Styling - Fixed contrast issues for visibility
st.markdown("""
    <style>
    /* Force dark blue sidebar and dark text for main area headers */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; color: white; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    h1, h2, h3 { color: #0f172a !important; }
    
    /* Metric Card Styling */
    .metric-card {
        background: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        color: #0f172a;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA LOADING (Optimized with simpler pathing) ---
@st.cache_data(show_spinner="Loading Spatial Data...")
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "final_risk_atlas_bihar.geojson")
    
    if not os.path.exists(file_path):
        # Alternative path check
        file_path = os.path.join(os.path.dirname(base_dir), "data", "final_risk_atlas_bihar.geojson")
    
    gdf = gpd.read_file(file_path)
    
    # Critical: Simplify geometry to speed up map rendering
    gdf['geometry'] = gdf['geometry'].simplify(0.001, preserve_topology=True)
    
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

# --- 4. COLOR LOGIC ---
def get_color(feature, layer_type):
    if layer_type == 'risk':
        val = feature['properties'].get('Risk_Category', 'Low')
        return {'Critical': '#991b1b', 'High': '#d97706', 'Moderate': '#fcd34d', 'Low': '#059669'}.get(val, '#9ca3af')
    return '#10b981' # Default

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("Atlas Navigator")
    selected_block = st.selectbox("Search District/Block", ["Bihar State View"] + sorted(gdf["block_name"].unique().tolist()))
    st.divider()
    st.metric("Blocks Analyzed", len(gdf))
    criticals = len(gdf[gdf["Risk_Category"] == "Critical"])
    st.metric("Critical Hotspots", criticals)

# --- 6. MAIN CONTENT ---
st.title("🌊 Bihar Hydro-Climatic Risk Atlas")

col_map, col_stats = st.columns([2.5, 1])

with col_map:
    # Logic for map view
    m_center, m_zoom = [25.8, 85.5], 7
    if selected_block != "Bihar State View":
        block_data = gdf[gdf["block_name"] == selected_block]
        if not block_data.empty:
            c = block_data.geometry.centroid.iloc[0]
            m_center, m_zoom = [c.y, c.x], 10

    # Initialize map
    m = folium.Map(location=m_center, zoom_start=m_zoom, tiles="CartoDB positron")

    # Add single layer for speed
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': get_color(x, 'risk'),
            'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'], aliases=['Block:', 'Status:'])
    ).add_to(m)

    # Use a simplified st_folium call for performance
    st_folium(m, width="100%", height=500, key=f"map_{selected_block}")

with col_stats:
    if selected_block != "Bihar State View":
        data = gdf[gdf["block_name"] == selected_block].iloc[0]
        st.subheader(data['block_name'])
        
        # Display as cards
        st.markdown(f'<div class="metric-card">Risk: {data["Risk_Category"]}</div>', unsafe_allow_html=True)
        st.write("")
        st.metric("Flood Score", f"{data['Flood_Risk_Score']:.2f}")
        st.metric("GW Stress", f"{data['GW_Stress_Score']:.2f}")
    else:
        st.info("Select a block to see detailed metrics.")
        # Summary chart
        fig = px.pie(gdf, names='Risk_Category', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True)