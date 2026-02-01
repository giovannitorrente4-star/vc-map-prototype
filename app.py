import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np

# -----------------------
# App config
# -----------------------
st.set_page_config(page_title="VC Map", layout="wide")
st.title("🇺🇸 VC Map MVP")

# -----------------------
# Load embedded CSV
# -----------------------
DATA_PATH = "VC_Map_Final_Reliable.csv"

try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    st.error(f"Data file not found: {DATA_PATH}. Please upload the 'VC_Map_Final_Reliable.csv' file.")
    st.stop()

# Clean column names
df.columns = df.columns.str.strip()

# Normalize column names
df = df.rename(columns={
    "Name": "name",
    "Lat": "latitude",
    "Long": "longitude",
    "Latitude": "latitude",
    "Longitude": "longitude"
})

# Validate coordinates
if "latitude" not in df.columns or "longitude" not in df.columns:
    st.error("CSV must contain 'latitude' and 'longitude' columns.")
    st.stop()

# Force numeric coords
df["latitude"] = pd.to_numeric(df["latitude"], errors='coerce')
df["longitude"] = pd.to_numeric(df["longitude"], errors='coerce')
df = df.dropna(subset=["latitude", "longitude"])

# Add jitter
df["lat_jitter"] = df["latitude"] + np.random.uniform(-0.002, 0.002, len(df))
df["lon_jitter"] = df["longitude"] + np.random.uniform(-0.002, 0.002, len(df))

# -----------------------
# Clean Stage and Sector
# -----------------------
df["Stage"] = df["Stage"].astype(str).apply(lambda x: [s.strip() for s in x.split(",") if s.strip()])
df["Sector"] = df["Sector"].astype(str).apply(lambda x: [s.strip() for s in x.split(",") if s.strip()])

# -----------------------
# Sidebar filters
# -----------------------
st.sidebar.header("🔍 Filters")

all_sectors = sorted({s for sublist in df["Sector"] for s in sublist})
selected_sectors = st.sidebar.multiselect("Sector", options=all_sectors, default=all_sectors)

all_stages = sorted({s for sublist in df["Stage"] for s in sublist})
selected_stages = st.sidebar.multiselect("Stage", options=all_stages, default=all_stages)

# Toggle for Heatmap
show_heatmap = st.sidebar.checkbox("Show Heatmap Layer", value=True)

# --- Add this section ---
st.sidebar.markdown("---")
st.sidebar.markdown("📄 **Dataset:** US VCs v1.0")
st.sidebar.markdown("🗓️ **Last updated:** Feb 2026")
# ------------------------

# -----------------------
# Filtering logic
# -----------------------
if not selected_sectors or not selected_stages:
    st.warning("Please select at least one Sector and Stage.")
    filtered_df = pd.DataFrame(columns=df.columns)
else:
    filtered_df = df[
        df["Sector"].apply(lambda sectors: any(s in selected_sectors for s in sectors)) &
        df["Stage"].apply(lambda stages: any(s in selected_stages for s in stages))
    ]

# -----------------------
# Table
# -----------------------
st.subheader(f"VC Firms ({len(filtered_df)})")

display_df = filtered_df.copy()
display_df["Stage_Str"] = display_df["Stage"].apply(lambda x: ", ".join(x))
display_df["Sector_Str"] = display_df["Sector"].apply(lambda x: ", ".join(x))

st.dataframe(
    display_df[["name", "Address", "City", "Sector_Str", "Stage_Str", "Website"]],
    use_container_width=True
)

# -----------------------
# Map
# -----------------------
st.subheader("🗺️ VC Map")

if not filtered_df.empty:
    mid_lat = filtered_df["latitude"].mean()
    mid_lon = filtered_df["longitude"].mean()

    # 1. Heatmap Layer (Density)
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=filtered_df,
        get_position='[longitude, latitude]',
        opacity=0.9,
        radius=30,  # Radius of the heat blur
        intensity=1,
        threshold=0.05,
    )

    # 2. Scatterplot Layer (Clickable Dots)
    scatterplot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=display_df,
        get_position='[lon_jitter, lat_jitter]',
        get_radius=1000,
        get_fill_color='[0, 180, 255, 200]', # Cyan/Blue glowing color
        pickable=True,
        auto_highlight=True,
        stroked=True,
        get_line_color='[255, 255, 255, 100]', # White outline for contrast
        line_width_min_pixels=1,
    )

    layers = [scatterplot_layer]
    if show_heatmap:
        layers.insert(0, heatmap_layer) # Add heatmap below dots

    view_state = pdk.ViewState(
        latitude=mid_lat,
        longitude=mid_lon,
        zoom=3.5,
        pitch=0
    )

    # Dark Map Style for "Glowing" effect
    deck = pdk.Deck(
        map_provider="carto",
        map_style="dark", 
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{name}</b><br>"
                    "City: {City}<br>"
                    "Stage: {Stage_Str}<br>"
                    "Sector: {Sector_Str}"
        }
    )

    st.pydeck_chart(deck)
else:
    st.info("No VCs found matching your filters.")

# -----------------------
# VC Detail
# -----------------------
st.subheader("📌 Selected VC")

if not filtered_df.empty:
    selected_vc = st.selectbox("Choose a VC", options=display_df["name"].sort_values())
    
    if selected_vc:
        vc_info = display_df[display_df["name"] == selected_vc].iloc[0]
        st.markdown(f"### {vc_info['name']}")
        st.write(f"**City:** {vc_info['City']}")
        st.write(f"**Stage:** {vc_info['Stage_Str']}")
        st.write(f"**Sector:** {vc_info['Sector_Str']}")
        
        if pd.notna(vc_info.get("Website", "")) and str(vc_info["Website"]).lower() != "nan":
            st.markdown(f"[Visit Website]({vc_info['Website']})")
