import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from streamlit_folium import st_folium
import folium
import plotly.express as px

st.set_page_config(page_title="Irrigation Scheduler", layout="centered")
st.title("Smart Irrigation Scheduler 💧")

st.markdown("""
    <style>
    /* Custom button styles */
    .stButton > button {
        background-color: #0099ff;
        color: white;
        font-weight: bold;
    }
    .stDownloadButton > button {
        background-color: #00cc66;
        color: white;
        font-weight: bold;
    }

    /* Custom map container styling */
    .streamlit-folium {
        padding: 0;
        margin-top: 0;
        margin-bottom: 10px;  /* Adjust space below the map */
    }

    /* Remove excess padding and margin for the entire page */
    .main .block-container {
        padding-top: 0rem;
        padding-bottom: 1rem;
    }

    /* Adjust margin below title */
    .css-1v3fvcr {
        margin-bottom: 0rem;
    }
    </style>
""", unsafe_allow_html=True)

# Geolocator for reverse lookup
geolocator = Nominatim(user_agent="irrigation_app")

st.sidebar.header("Schedule Settings")
start_date = st.sidebar.date_input("Start Date", datetime.today())
end_date = st.sidebar.date_input("End Date", datetime.today() + timedelta(days=7))
crop = st.sidebar.selectbox("Crop Type", ["Wheat", "Rice", "Corn", "Custom"])

# Map-based Location Picker
st.subheader("📍 Select Your Location on the Map")

# Setup folium map
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

lat, lon = None, None
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.success(f"📌 Selected Coordinates: {lat:.4f}, {lon:.4f}")
    
    try:
        location_name = geolocator.reverse((lat, lon), timeout=10)
        st.write(f"📍 Location: {location_name}")
    except Exception as e:
        st.warning(f"⚠️ Could not retrieve location name. ({e})")

# Dummy Weather & Irrigation Logic
def fetch_dummy_weather(start_date, end_date, crop_type):
    dates = pd.date_range(start_date, end_date)
    
    # Adjust ET₀ baseline based on crop type
    et0_base = {
        "Wheat": 3.5,
        "Rice": 4.0,
        "Corn": 4.5,
        "Custom": 3.0
    }.get(crop_type, 3.0)
    
    return pd.DataFrame({
        "date": dates,
        "et0": [round(et0_base + i * 0.1, 2) for i in range(len(dates))],
        "rain": [0.5 if i % 5 == 0 else 0.0 for i in range(len(dates))]
    })

def generate_irrigation_schedule(weather_df):
    results = []
    for _, row in weather_df.iterrows():
        irrigation = max(0, row["et0"] - row["rain"])
        results.append({
            "date": row["date"].date(),
            "et0": row["et0"],
            "rain": row["rain"],
            "irrigation": round(irrigation, 2)
        })
    return pd.DataFrame(results)

# Generate and Display Schedule
if st.button("Generate Irrigation Schedule", key="generate_schedule_button_1") and lat and lon:
    weather = fetch_dummy_weather(start_date, end_date, crop)
    with st.spinner("Generating schedule..."):
        schedule = generate_irrigation_schedule(weather)

    st.subheader("✅ Irrigation Schedule")
    st.data_editor(schedule, use_container_width=True, num_rows="dynamic", disabled=True)

    # Create line chart of ET0, Rain, and Irrigation
    chart_data = schedule.set_index("date")
    
    # Plot ET0, Rain, and Irrigation as Line Chart
    st.subheader("📊 Irrigation and Weather Trends")
    st.line_chart(chart_data[["et0", "rain", "irrigation"]])
    
    # Add download button for CSV
    csv = schedule.to_csv(index=False)
    st.download_button(
        label="Download Schedule as CSV",
        data=csv,
        file_name="irrigation_schedule.csv",
        mime="text/csv",
        key="download_csv_button_1" 
    )
elif not lat or not lon:
    st.info("🗺️ Click a location on the map to continue.")
