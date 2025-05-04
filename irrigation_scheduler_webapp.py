import streamlit as st
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from streamlit_folium import st_folium
import folium

st.set_page_config(page_title="Irrigation Scheduler", layout="centered")
st.title("Smart Irrigation Scheduler 🌱")
st.write("""
    Smart Irrigation Scheduler helps you plan efficient irrigation schedules 
    based on weather data, crop type, location, and soil type. 
    Select your location, crop, schedule duration, and soil to generate a tailored plan.
""")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Lato&family=Poppins:wght@500;700&display=swap" rel="stylesheet">

    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #b7d5f0 !important;
        font-family: 'Lato', sans-serif !important;
    }
            
     h1, h2, h3 {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
    }

    /* Title styling */
    .css-1v0mbdj h1 {
        font-size: 2.5rem !important;
        font-weight: 600 !important;
        text-align: center !important;
        margin-top: 3rem !important;
        margin-bottom: 1rem !important;
        color: #203069 !important;
    }

    /* Header background customization */
    .css-1d391kg {
        background-color: #203069 !important;
        color: white !important;
    }

    /* Button customization */
    .stButton > button, .stDownloadButton > button {
        background-color: #203069 !important;
        color: white !important;
        font-weight: bold;
        border: none;
        border-radius: 12px;
        padding: 0.5rem 1rem;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        transition: background-color 0.3s ease;
    }

    .stButton > button:hover, .stDownloadButton > button:hover,
    .stButton > button:focus, .stDownloadButton > button:focus,
    .stButton > button:active, .stDownloadButton > button:active {
        background-color: #132669 !important;
        box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.2);
    }

    /* Folium Map styling */
    .streamlit-folium {
        padding: 0 !important;
        margin-top: 1rem !important;
        height: 100% !important;
        border-radius: 12px;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
    }

    /* Focus effect for input fields */
    .stTextInput input:focus, 
    .stNumberInput input:focus, 
    .stSelectbox select:focus, 
    .stDateInput input:focus, 
    .stTextArea textarea:focus {
        box-shadow: 0px 0px 5px rgba(19, 38, 105, 0.5) !important;  
    }
            
    /* Add space above the map section */
    .css-ffhzg2 {
        margin-top: 2rem !important;
    }

    /* Adjust spacing between map and button */
    .css-1v3fvcr, .css-ffhzg2, .stApp {
        margin-top: 1.5rem !important;
        padding-top: 0 !important;
    }

    /* Adjust the spacing above the main content */
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 5rem !important;
    }

    /* General page layout adjustments */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        margin-top: 2rem !important;
    }
    </style>
""", unsafe_allow_html=True)


geolocator = Nominatim(user_agent="irrigation_app")

API_KEY = st.secrets["tomorrow_io"]["tomorrow_io_api_key"]         # Replace with your Tomorrow.io API key
BASE_URL = "https://api.tomorrow.io/v4/weather/forecast"

def fetch_weather_data(lat, lon, start_date, end_date):
    url = f"https://api.tomorrow.io/v4/weather/forecast"
    params = {
        "location": f"{lat},{lon}",
        "apikey": API_KEY,
        "units": "metric",
        "startTime": start_date.isoformat(),
        "endTime": end_date.isoformat(),
        "fields": ["temperatureAvg", "rainAccumulationAvg"]
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        days = data.get("timelines", {}).get("daily", [])

        dates = []
        et0_vals = []
        rain_vals = []

        for day in days:
            date = day["time"][:10]
            temp = day["values"].get("temperatureAvg", 25)
            rain = day["values"].get("rainAccumulationAvg", 0)
            dates.append(pd.to_datetime(date))
            et0_vals.append(round(temp * 0.7, 2))
            rain_vals.append(round(rain, 2))

        return pd.DataFrame({
            "date": dates,
            "et0": et0_vals,
            "rain": rain_vals
        })
    else:
        st.error(f"API Error {response.status_code}: {response.text}")
        return pd.DataFrame()

st.subheader("⚙️ Schedule Settings")
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Start Date", datetime.today())

with col2:
    end_date = st.date_input(
        "End Date",
        datetime.today() + timedelta(days=3),
        min_value=start_date,
        max_value=start_date + timedelta(days=5)
    )

# Adjust end date if the user selects a range greater than 5 days
if (end_date - start_date).days > 5:
    end_date = start_date + timedelta(days=5)
    st.warning("Forecast limited to 5 days ahead due to Tomorrow.io free plan limitations.")

crop = st.selectbox("Crop Type", ["Wheat", "Rice", "Corn", "Soybean", "Barley", "Sugarcane", "Cotton", "Potato", "Tomato", "Custom"])

soil_type = st.selectbox("Soil Type", ["Loamy", "Sandy", "Clay", "Silt", "Black Soil", "Red Soil"])
SOIL_MULTIPLIER = {
    "Loamy": 1.0,
    "Sandy": 1.4,
    "Clay": 0.8,
    "Silt": 0.9,
    "Black Soil": 1.2,
    "Red Soil": 1.1
}
soil_multiplier = SOIL_MULTIPLIER.get(soil_type, 1.0)

CROP_ET0 = {
    "Wheat": 5.5,
    "Rice": 6.0,
    "Corn": 5.0,
    "Soybean": 4.8,
    "Barley": 4.3,
    "Sugarcane": 7.0,
    "Cotton": 6.2,
    "Potato": 4.5,
    "Tomato": 4.7
}
custom_et0 = None
if crop == "Custom":
    st.text_input("Custom Crop Name")
    custom_et0 = st.number_input("ET0 for your crop (mm/day):", min_value=0.0, step=0.1)

st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
st.subheader("📍 Select Your Location on the Map")
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

@st.cache_data
def generate_irrigation_schedule(weather_df, multiplier):
    results = []
    for _, row in weather_df.iterrows():
        adjusted_et0 = row["et0"] * multiplier
        irrigation = max(0, adjusted_et0 - row["rain"])
        results.append({
            "date": row["date"],
            "et0": round(adjusted_et0, 2),
            "rain": row["rain"],
            "irrigation": round(irrigation, 2)
        })
    return pd.DataFrame(results)

if st.button("Generate Irrigation Schedule") and lat and lon:
    with st.spinner("Generating schedule..."):
        if crop == "Custom" and custom_et0 is not None:
            dates = pd.date_range(start_date, end_date)
            weather = pd.DataFrame({
                'date': dates,
                'et0': [custom_et0] * len(dates),
                'rain': [0.0] * len(dates)
            })
        else:
            weather = fetch_weather_data(lat, lon, start_date, end_date)

        if not weather.empty:
            schedule = generate_irrigation_schedule(weather, soil_multiplier)

            schedule = schedule.rename(columns={
                "et0": "ET₀ (mm/day)",
                "rain": "Rain (mm)",
                "irrigation": "Irrigation Needed (mm)"
            })

            st.subheader("✅ Irrigation Schedule")
            st.data_editor(schedule, use_container_width=True, num_rows="dynamic", disabled=True)

            st.subheader("📊 Irrigation and Weather Trends")
            chart_data = schedule.set_index("date")
            st.line_chart(chart_data[["ET₀ (mm/day)", "Rain (mm)", "Irrigation Needed (mm)"]])


            csv = schedule.to_csv(index=False)
            st.download_button(
                label="Download Schedule as CSV",
                data=csv,
                file_name="irrigation_schedule.csv",
                mime="text/csv"
            )
        else:
            st.error("Failed to fetch weather data.")
elif not lat or not lon:
    st.info("🗺️ Click a location on the map to continue.")