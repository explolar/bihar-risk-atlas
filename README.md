# 🌊 Bihar Hydro-Climatic Risk Atlas
### An Integrated Decision Support System for Flood & Groundwater Risk Assessment

**🔴 Live Demo:** [https://bihar-risk-atlas-ankit.streamlit.app/](https://bihar-risk-atlas-ankit.streamlit.app/)

## 📋 Project Overview
Bihar faces a hydrological paradox known as **"Double Jeopardy"**: the same administrative blocks often suffer from acute **floods** during the monsoon and severe **groundwater depletion** during the dry season.

This project creates a unified **Compound Risk Index** to identify these overlapping hazard zones. It leverages satellite data, machine learning, and explainable AI to provide policymakers with a transparent, data-driven tool for prioritizing interventions like Managed Aquifer Recharge (MAR).

---

## 🧠 Methodology: Hydro-Climatic Risk Assessment

The core of this project lies in quantifying two opposing hydrological extremes—**Flood Pressure** (Surface Excess) and **Groundwater Stress** (Subsurface Deficit)—using machine learning models trained on satellite-derived climatic variables.

### **1. Flood Pressure Assessment**
**Objective:** To quantify the probability of surface water accumulation exceeding the natural drainage capacity of a block.

* **Model Used:** Random Forest Regressor ($R^2 > 0.85$)
* **Target Variable:** `Flood_Pressure_Index` (Derived from historical flood extent data).
* **Key Input Features (Predictors):**
    * **`rain_3m` (3-Month Cumulative Rainfall):** Captures long-term soil saturation. Saturated soil cannot absorb new rainfall, leading to immediate runoff.
    * **`rain_anomaly` (Rainfall Deviation):** The deviation of current rainfall from the 30-year long-term average (LTA). Positive anomalies indicate potential flood triggers.
    * **`NDVI` (Vegetation Health):** Used as a proxy for surface roughness and water retention capacity.
* **Risk Logic:**
    $$\text{Flood Risk} \propto f(\text{Saturated Soil} + \text{Heavy Rainfall Anomaly})$$

### **2. Groundwater (GW) Stress Assessment**
**Objective:** To estimate the "thirst" of the atmosphere versus the available subsurface water supply, identifying zones of potential aquifer depletion.

* **Model Used:** Random Forest Regressor
* **Target Variable:** `GW_Stress_Index` (Proxy derived from GRACE satellite gravity anomalies downscaled using MODIS/Sentinel data).
* **Key Input Features (Predictors):**
    * **`ET` (Evapotranspiration):** The amount of water lost to the atmosphere from soil and crops. High ET represents high water demand.
    * **`Rainfall`:** The primary source of aquifer recharge.
    * **`ET_Rain_Ratio` (Interaction Term):** The ratio of Demand (ET) to Supply (Rain).
* **SHAP Analysis Finding:**
    Our Explainable AI (SHAP) analysis revealed a critical **"Tipping Point"**: when the `ET-to-Rainfall Ratio` exceeds **~7.0**, groundwater stress spikes exponentially.

### **3. Compound Risk Index (The "Double Jeopardy" Metric)**
To identify blocks facing *both* risks simultaneously, we normalized and combined the individual indices.

* **Step A: Normalization** (Min-Max Scaling 0–1)
  $$\text{Norm}_x = \frac{x - x_{min}}{x_{max} - x_{min}}$$
* **Step B: Composite Scoring**
  $$\text{Compound Score} = (0.5 \times \text{Flood}_{\text{norm}}) + (0.5 \times \text{GW}_{\text{norm}})$$
* **Step C: Classification**
  Blocks in the **Top 20%** of scores are classified as **🔴 Critical**.

### **4. Temporal Trend Analysis (Degradation Rate)**
To move beyond a static snapshot, we analyzed the *direction* of change over 5 years (2019–2024).

* **Method:** Ordinary Least Squares (OLS) Linear Regression on annual stress indices.
* **Equation:** $y = mx + c$ (where $m$ is the **Degradation Rate**).
* **Interpretation:**
    * **Positive Slope ($m > 0$):** Stress is increasing (Aquifer Depletion).
    * **Negative Slope ($m < 0$):** Stress is decreasing (Recovery).

---

## ⚙️ The Workflow

1.  **🛰️ Data Acquisition (Google Earth Engine):**
    * Extracted multi-year time-series data (2019–2024) for every block.
    * **Sources:** CHIRPS Daily (Rainfall), MODIS (ET), Sentinel-2 (NDVI).
2.  **🧠 Machine Learning & Risk Modeling:**
    * Trained Random Forest models to predict stress indices based on climatic drivers.
3.  **🔍 Explainable AI (SHAP):**
    * Used SHAP (Shapley Additive Explanations) to validate models and explain *why* specific blocks are critical.
4.  **💻 Web Application (Streamlit):**
    * Built an interactive dashboard to visualize maps, filter data, and display trend metrics.

---

## 🛠️ Tools & Technologies
This project was built using a robust stack of open-source geospatial and machine learning tools.

| Category | Technologies Used |
| :--- | :--- |
| **Remote Sensing & GIS** | Google Earth Engine (GEE), Geopandas, Folium, Rasterio, Shapely |
| **Machine Learning** | Scikit-Learn (Random Forest), SHAP (Explainable AI), SciPy |
| **Web Development** | Streamlit, Python 3.10+ |
| **Data Processing** | Pandas, NumPy, Matplotlib, Seaborn |
| **Version Control & Deploy** | Git, GitHub, Streamlit Community Cloud |

## 📬 Author & Contact

Developed by **Ankit Kumar** with the help of LLM.

* 📧 **Email:** [Ankituday123@gmail.com](mailto:Ankituday123@gmail.com)
* 💼 **LinkedIn:** [Ankit Kumar](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)
* 💻 **GitHub:** [explolar](https://github.com/explolar)

---

## 📂 Repository Structure

```text
bihar-risk-atlas/
├── frontend/
│   └── app.py                  # Main Dashboard Application
├── data/
│   └── final_risk_atlas_bihar.geojson  # The processed geospatial database
├── gee_scripts/
│   └── extraction_script.js    # Raw Google Earth Engine (JS) code
├── notebooks/
│   ├── 01_prepare_boundaries.ipynb     # Pre-processing administrative maps
│   └── 03_merge_features.ipynb         # Data fusion and risk calculation
├── .gitignore                  # Files to exclude from Git
├── LICENSE                     # MIT License
├── README.md                   # Project Documentation
└── requirements.txt            # Python dependencies for deployment
