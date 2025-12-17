import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd

st.set_page_config(layout="wide", page_title="Bihar Risk Atlas", page_icon="🌊")

# --- 1. LOAD DATA ---
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        "trend_class": "Trend_Status",
        "stress_slope": "Degradation_Rate",
        "block": "block_name"
    }
    gdf = gdf.rename(columns=rename_map)
    
    # Ensure Block Name is string
    if "block_name" in gdf.columns:
        gdf["block_name"] = gdf["block_name"].astype(str)
    else:
        gdf["block_name"] = gdf.index.astype(str)
        
    return gdf

try:
    gdf = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔍 Controls")
    all_blocks = ["None"] + sorted(gdf["block_name"].unique().tolist())
    selected_block = st.selectbox("Search Block", options=all_blocks)
    
    st.divider()
    st.metric("Total Blocks", len(gdf))
    if "Risk_Category" in gdf.columns:
        critical_count = len(gdf[gdf["Risk_Category"] == "Critical"])
        st.metric("Critical Hotspots", critical_count, delta_color="inverse")

# --- 3. MAIN DASHBOARD ---
st.title("🌊 Bihar Hydro-Climatic Risk Atlas")

col1, col2 = st.columns([3, 1.2])

with col1:
    st.subheader("Interactive Map")
    m = folium.Map(location=[25.5, 85.8], zoom_start=7, tiles="CartoDB positron")
    
    def style_function(feature):
        risk = feature['properties'].get('Risk_Category', 'Low')
        colors = {'Critical': '#d73027', 'High': '#fc8d59', 'Moderate': '#fee08b', 'Low': '#1a9850'}
        return {'fillColor': colors.get(risk, 'gray'), 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.7}

    def highlight_function(feature):
        return {'weight': 3, 'color': 'blue', 'fillOpacity': 0.9}

    folium.GeoJson(
        gdf,
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'], aliases=['Block:', 'Risk:']),
        popup=folium.GeoJsonPopup(fields=['block_name'])
    ).add_to(m)
    st_folium(m, width="100%", height=600)

with col2:
    st.subheader("Block Details")
    
    if selected_block != "None":
        row = gdf[gdf["block_name"] == selected_block].iloc[0]
        
        tab1, tab2, tab3 = st.tabs(["⚠️ Overview", "🌊 Flood", "💧 Groundwater"])
        
        with tab1:
            st.markdown(f"### {row['block_name']}")
            risk = row.get('Risk_Category', 'Unknown')
            color = "#d73027" if risk == 'Critical' else "#fc8d59" if risk == 'High' else "#1a9850"
            st.markdown(f'<div style="background-color:{color};padding:10px;color:white;text-align:center;border-radius:5px;font-weight:bold;">{risk}</div>', unsafe_allow_html=True)
            if 'Compound_Score' in row:
                st.write("")
                st.progress(float(row['Compound_Score']), text=f"Composite Risk: {row['Compound_Score']:.2f}")

        with tab2:
            st.markdown("#### Surface Water")
            if 'Flood_Risk_Score' in row and pd.notnull(row['Flood_Risk_Score']):
                val = float(row['Flood_Risk_Score'])
                st.metric("Flood Pressure Index", f"{val:.2f}", help="Higher is worse")
                if val > 0.6: st.error("⚠️ High Saturation")
                else: st.success("✅ Normal Drainage")
            else:
                st.warning("Data Missing")

        with tab3:
            st.markdown("#### Aquifer Status")
            
            # 1. Current Stress
            if 'GW_Stress_Score' in row and pd.notnull(row['GW_Stress_Score']):
                val = float(row['GW_Stress_Score'])
                st.metric("Current Stress Index", f"{val:.2f}")
            
            st.divider()