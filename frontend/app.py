import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import plotly.express as px
import numpy as np

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
    gdf["block_name"] = gdf["block_name"].astype(str)
    
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    elif gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
        
    return gdf

try:
    gdf = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🔍 Controls")
    all_blocks = ["All Blocks"] + sorted(gdf["block_name"].unique().tolist())
    selected_block = st.selectbox("Search Block", options=all_blocks)
    
    st.divider()
    st.metric("Total Blocks Analysed", len(gdf))
    
    if "Risk_Category" in gdf.columns:
        critical_count = len(gdf[gdf["Risk_Category"] == "Critical"])
        st.metric("Critical Hotspots", critical_count, delta="High Risk", delta_color="inverse")

# --- 3. MAIN DASHBOARD ---
st.title("🌊 Bihar Hydro-Climatic Risk Atlas")

col1, col2 = st.columns([3, 1.3])

with col1:
    if selected_block != "All Blocks":
        block_gdf = gdf[gdf["block_name"] == selected_block]
        center = [block_gdf.geometry.centroid.y.iloc[0], block_gdf.geometry.centroid.x.iloc[0]]
        zoom = 10
    else:
        center = [25.8, 85.5]
        zoom = 7

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")
    
    def style_function(feature):
        risk = feature['properties'].get('Risk_Category', 'Low')
        colors = {'Critical': '#b2182b', 'High': '#ef8a62', 'Moderate': '#fddbc7', 'Low': '#67a9cf'}
        return {'fillColor': colors.get(risk, '#f7f7f7'), 'color': 'white', 'weight': 0.8, 'fillOpacity': 0.7}

    folium.GeoJson(
        gdf,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['block_name', 'Risk_Category'], aliases=['Block:', 'Risk:']),
        popup=folium.GeoJsonPopup(fields=['block_name', 'Risk_Category', 'Compound_Score'])
    ).add_to(m)
    
    st_folium(m, width="100%", height=600, key="bihar_map")

with col2:
    st.subheader("Analysis Panel")
    
    if selected_block != "All Blocks":
        row = gdf[gdf["block_name"] == selected_block].iloc[0]
        
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "🌊 Flood", "💧 GW"])
        
        with tab1:
            st.markdown(f"### {row['block_name']}")
            risk = row.get('Risk_Category', 'Unknown')
            color = "#d73027" if risk == 'Critical' else "#fc8d59" if risk == 'High' else "#1a9850"
            st.markdown(f'<div style="background-color:{color};padding:12px;color:white;text-align:center;border-radius:8px;font-size:18px;font-weight:bold;">{risk} Risk Level</div>', unsafe_allow_html=True)
            
            # --- TREND CHART ---
            st.write("#### 📈 Risk Trajectory")
            if 'Compound_Score' in row and 'Degradation_Rate' in row:
                # Generate synthetic trend data: current_score - (rate * year_offset)
                years = [2021, 2022, 2023, 2024, 2025]
                rate = row['Degradation_Rate'] if pd.notnull(row['Degradation_Rate']) else 0
                current_score = row['Compound_Score']
                
                scores = [current_score - (rate * (2025 - y)) for y in years]
                trend_df = pd.DataFrame({"Year": years, "Score": scores})
                
                fig_trend = px.line(trend_df, x="Year", y="Score", markers=True, 
                                    color_discrete_sequence=[color])
                fig_trend.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0),
                                        yaxis_title="Risk Score", xaxis_title=None)
                st.plotly_chart(fig_trend, use_container_width=True)

            # Download Button
            report_df = pd.DataFrame([row.drop('geometry')]).T
            csv = report_df.to_csv().encode('utf-8')
            st.download_button("📥 Download Report", csv, f"{row['block_name']}_report.csv", "text/csv", use_container_width=True)

        with tab2:
            st.markdown("#### Surface Water Risk")
            if 'Flood_Risk_Score' in row and pd.notnull(row['Flood_Risk_Score']):
                st.metric("Flood Pressure Index", f"{row['Flood_Risk_Score']:.2f}")
            else:
                st.info("No flood data available.")

        with tab3:
            st.markdown("#### Aquifer Dynamics")
            if 'GW_Stress_Score' in row and pd.notnull(row['GW_Stress_Score']):
                st.metric("Current Stress Index", f"{float(row['GW_Stress_Score']):.2f}")
            
            if 'Degradation_Rate' in row and pd.notnull(row['Degradation_Rate']):
                rate = float(row['Degradation_Rate'])
                st.metric("Trend", "Depleting" if rate > 0 else "Recharging", 
                          delta=f"{rate:.3f}", delta_color="inverse" if rate > 0 else "normal")

    else:
        st.info("Select a block for analysis.")
        # Summary Distribution Chart
        fig = px.pie(gdf, names='Risk_Category', color='Risk_Category',
                     color_discrete_map={'Critical': '#b2182b', 'High': '#ef8a62', 'Moderate': '#fddbc7', 'Low': '#67a9cf'},
                     hole=0.4)
        fig.update_layout(showlegend=False, height=250, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)