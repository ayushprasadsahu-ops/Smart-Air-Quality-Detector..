
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import requests
from streamlit_lottie import st_lottie
import random
import geocoder
import socket
import qrcode
from io import BytesIO

# --- Backend Logic Functions ---

def get_current_location():
    """
    Detects the current location based on IP.
    Returns: (lat, lon, city_name) or None if failed.
    """
    try:
        g = geocoder.ip('me')
        if g.ok:
            return g.lat, g.lng, g.city
    except Exception as e:
        print(f"Geolocation error: {e}")
    return None

def get_coordinates(city_name):
    """
    Fetches coordinates for a given city name using Open-Meteo Geocoding API.
    Returns: (lat, lon, city_name_formatted) or None if failed.
    """
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            'name': city_name,
            'count': 1,
            'language': 'en',
            'format': 'json'
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if 'results' in data and data['results']:
            item = data['results'][0]
            lat = item['latitude']
            lon = item['longitude']
            name = item['name']
            country = item.get('country', '')
            display_name = f"{name}, {country}" if country else name
            return lat, lon, display_name
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None

def get_aqi_data(lat, lon):
    """
    Fetches AQI data from Open-Meteo API.
    """
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
            "hourly": "us_aqi",
            "timezone": "auto",
            "forecast_days": 1
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data
    except Exception as e:
        print(f"AQI API Error: {e}")
        return None

def process_aqi_data(api_data, city_name):
    """
    Processes raw API data into a structure suitable for the frontend.
    """
    if not api_data:
        return {
            "error": "Could not fetch data. Please try again later.",
            "city": city_name
        }

    current = api_data.get('current', {})
    base_aqi = current.get('us_aqi', 0)
    
    pollutants = {
        "PM2.5": current.get('pm2_5', 0),
        "PM10": current.get('pm10', 0),
        "O3": current.get('ozone', 0),
        "NO2": current.get('nitrogen_dioxide', 0),
        "CO": current.get('carbon_monoxide', 0)
    }

    # Hourly Forecast
    hourly = api_data.get('hourly', {})
    hourly_aqi = hourly.get('us_aqi', [])
    hourly_time = hourly.get('time', [])
    
    trend_data = pd.DataFrame()
    if hourly_time and hourly_aqi:
         trend_data = pd.DataFrame({
            "Time": [t.split('T')[1][:5] for t in hourly_time[:24]],
            "AQI": hourly_aqi[:24]
        })

    # Status & Color Logic
    if base_aqi <= 50:
        status = "Good"
        color = "#2ecc71"
        desc = "Air quality is satisfactory. Enjoy the outdoors!"
    elif base_aqi <= 100:
        status = "Moderate"
        color = "#f1c40f"
        desc = "Air quality is acceptable. Sensitive groups should watch out."
    elif base_aqi <= 150:
        status = "Unhealthy for Sensitive Groups"
        color = "#e67e22"
        desc = "Members of sensitive groups may experience health effects."
    elif base_aqi <= 200:
        status = "Unhealthy"
        color = "#e74c3c"
        desc = "Everyone may begin to experience health effects."
    else:
        status = "Very Unhealthy / Hazardous"
        color = "#8e44ad"
        desc = "Health warnings of emergency conditions. Stay indoors."

    return {
        "city": city_name,
        "aqi": base_aqi,
        "status": status,
        "color": color,
        "description": desc,
        "lat": api_data.get('latitude'),
        "lon": api_data.get('longitude'),
        "pollutants": pollutants,
        "trend_data": trend_data
    }

def get_health_recommendations(aqi):
    """
    Returns personalized health recommendations based on AQI.
    Returns a dict of dicts: {Group: {'action': '...', 'risk': '...'}}
    """
    recommendations = {
        "General": {},
        "Children": {},
        "Elderly": {},
        "Sensitive": {}
    }

    if aqi <= 50:
        recommendations["General"] = {
            "action": "Great air! Go outside and enjoy.",
            "risk": "No health risks.",
            "precaution": "None needed. Enjoy the outdoors!"
        }
        recommendations["Children"] = {
            "action": "Safe to play outside.",
            "risk": "No risk.",
            "precaution": "Encourage outdoor play."
        }
        recommendations["Elderly"] = {
            "action": "Perfect for walking.",
            "risk": "No risk.",
            "precaution": "Great time for a walk."
        }
        recommendations["Sensitive"] = {
            "action": "Air is clean. Enjoy!",
            "risk": "No symptoms expected.",
            "precaution": "None. Keep rescue inhaler just in case."
        }
        
    elif aqi <= 100:
        recommendations["General"] = {
            "action": "Air is okay. Have a good day.",
            "risk": "Very low risk for most people.",
            "precaution": "No special precautions."
        }
        recommendations["Children"] = {
            "action": "Safe for outdoor play.",
            "risk": "Minimal risk.",
            "precaution": "Monitor for coughing if they have asthma."
        }
        recommendations["Elderly"] = {
            "action": "Good for walking.",
            "risk": "Minimal risk.",
            "precaution": "Monitor for any breathing issues."
        }
        recommendations["Sensitive"] = {
            "action": "Limit long outdoor exercise.",
            "risk": "Possible minor breathing discomfort.",
            "precaution": "Carry your inhaler. Take breaks."
        }
        
    elif aqi <= 150:
        recommendations["General"] = {
            "action": "Take breaks if exercising outside.",
            "risk": "Possible throat irritation or coughing.",
            "precaution": "Reduce intensity of outdoor workouts."
        }
        recommendations["Children"] = {
            "action": "Play less outside.",
            "risk": "Risk of coughing and shortness of breath.",
            "precaution": "Take frequent breaks indoors. Drink water."
        }
        recommendations["Elderly"] = {
            "action": "Take it easy outside.",
            "risk": "Risk of respiratory irritation.",
            "precaution": "Shorten walks. Avoid busy roads."
        }
        recommendations["Sensitive"] = {
            "action": "Unhealthy. Stay indoors more.",
            "risk": "High risk of asthma attacks and wheezing.",
            "precaution": "Wear a mask (N95) if outside. Close windows."
        }
        
    elif aqi <= 200:
        recommendations["General"] = {
            "action": "Avoid hard exercise outside.",
            "risk": "Risk of inflammation and reduced lung function.",
            "precaution": "Wear a mask if you must be outside."
        }
        recommendations["Children"] = {
            "action": "Play inside today.",
            "risk": "Lungs are developing; high risk of damage.",
            "precaution": "Keep windows closed. Use air purifier."
        }
        recommendations["Elderly"] = {
            "action": "Stay inside if you can.",
            "risk": "Increased risk of heart/lung complications.",
            "precaution": "Use air purifier. Avoid exertion."
        }
        recommendations["Sensitive"] = {
            "action": "DANGER: Stay indoors.",
            "risk": "Severe respiratory distress likely.",
            "precaution": "Strictly avoid outdoor exposure. Use oxygen if prescribed."
        }
        
    elif aqi <= 300:
        recommendations["General"] = {
            "action": "Do NOT exercise outside.",
            "risk": "Significant heart and lung aggravation.",
            "precaution": "Stay indoors. Use air purifier."
        }
        recommendations["Children"] = {
            "action": "Keep children indoors.",
            "risk": "Serious risk of long-term health effects.",
            "precaution": "No outdoor play. Seal windows."
        }
        recommendations["Elderly"] = {
            "action": "Stay indoors. Safe air only.",
            "risk": "Severe risk of heart attack or stroke.",
            "precaution": "Keep medication handy. Stay in clean air."
        }
        recommendations["Sensitive"] = {
            "action": "DANGER: Do not go outside.",
            "risk": "Life-threatening conditions possible.",
            "precaution": "Emergency plan ready. Contact doctor if needed."
        }
        
    else: # > 300 Hazardous
        recommendations["General"] = {
            "action": "EMERGENCY: Stay inside.",
            "risk": "Serious risk of respiratory failure.",
            "precaution": "Seal room. Use high-efficiency air filter."
        }
        recommendations["Children"] = {
            "action": "Keep children inside!",
            "risk": "Extreme danger to developing lungs.",
            "precaution": "Do not open windows/doors."
        }
        recommendations["Elderly"] = {
            "action": "Do NOT go outside.",
            "risk": "High mortality risk.",
            "precaution": "Use oxygen if needed. Monitor vitals."
        }
        recommendations["Sensitive"] = {
            "action": "EMERGENCY: Seek help if needed.",
            "risk": "Emergency health warnings for everyone.",
            "precaution": "Immediate medical attention if symptoms worsen."
        }

    return recommendations

# --- Frontend Logic ---

# --- Page Configuration ---
st.set_page_config(
    page_title="Smart Air Quality Detector",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Animations ---
def load_lottieurl(url: str):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Load Lottie Animations
lottie_good_air = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_j3uxlw5q.json") 
lottie_moderate_air = load_lottieurl("https://assets7.lottiefiles.com/packages/lf20_tzjuvg8y.json") 
lottie_unhealthy_air = load_lottieurl("https://assets10.lottiefiles.com/private_files/lf30_j3uxlw5q.json") 
lottie_loading = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_p8bfn5to.json") 

if not lottie_good_air:
    lottie_good_air = load_lottieurl("https://assets1.lottiefiles.com/packages/lf20_mjpaho66.json")

# --- Custom Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        color: #f0f2f5;
        font-size: 16px; 
    }

    /* Hide the top right toolbar (Deploy button, menu, etc.) */
    [data-testid="stToolbar"] {
        display: none;
    }
    
    /* Ensure the sidebar toggle remains visible if it was affected */
    [data-testid="collapsedControl"] {
        display: block;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(30, 30, 50) 0%, rgb(10, 10, 20) 90.2%);
        background-attachment: fixed;
    }

    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }

    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: clamp(10px, 2vw, 20px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        color: #e0e0e0;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.08);
    }
    
    .aqi-card {
        background: rgba(20, 20, 35, 0.6);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: clamp(1.5rem, 5vw, 3rem);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.25);
        text-align: center;
        margin-bottom: 2rem;
        transition: transform 0.3s ease;
        width: 100%;
    }
    
    .aqi-card:hover {
        transform: scale(1.02);
    }

    .aqi-value {
        font-size: clamp(3.5rem, 12vw, 6rem); 
        font-weight: 800;
        letter-spacing: -2px;
        line-height: 1.1;
        margin-bottom: 10px;
        text-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    .aqi-status {
        font-size: clamp(1.2rem, 4vw, 2rem);
        font-weight: 600;
        letter-spacing: 0.5px;
        color: #e0e0e0;
        margin-bottom: 15px;
        text-transform: uppercase;
    }

    .advice-container {
        background: rgba(30, 30, 45, 0.6);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: clamp(15px, 3vw, 24px);
        margin-top: 20px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 6px solid #2e8b57;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        color: #e0e0e0;
        transition: transform 0.2s;
    }
    .advice-container:hover {
        transform: translateY(-3px);
    }
    
    .stTextInput > div > div > input {
        background-color: rgba(255, 255, 255, 0.9);
        color: #1a1a1a;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 10px 15px;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4);
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(118, 75, 162, 0.6);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }

    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def get_pollutant_chart(pollutants):
    """Creates a donut chart for pollutants."""
    labels = list(pollutants.keys())
    values = list(pollutants.values())
    
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5)])
    fig.update_layout(
        title_text="Pollutant Distribution",
        annotations=[dict(text='Particles', x=0.5, y=0.5, font_size=20, showarrow=False)],
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", size=12, color="#ffffff")
    )
    return fig

# --- Main Layout ---

# Header Section
col_header, col_anim = st.columns([3, 1])
with col_header:
    st.markdown('<h1 class="gradient-text">🌿 Smart Air Quality Detector</h1>', unsafe_allow_html=True)
    st.markdown("### Real-time, AI-powered air quality monitoring.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown("Configure your preferences.")
    st.info("Data source: Public AQI APIs")


    st.markdown("---")


# Location Input Logic
st.markdown("<br>", unsafe_allow_html=True)

with st.expander("📱 **Share App (Scan QR Code)**", expanded=False):
    col_qr, col_info = st.columns([1, 2])
    
    # Robust IP Detection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external server to find the routeable interface
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()
        
    with col_qr:
        url = f"http://{local_ip}:8501" # Defaulting to 8501 for simplicity in main view, can add advanced options if needed
        img = qrcode.make(url)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        st.image(buffer, caption="Scan to open on Mobile", use_container_width=True)

    with col_info:
        st.markdown(f"### Access on Local Network")
        st.markdown(f"**URL:** `{url}`")
        st.info("Ensure your phone is on the same WiFi network as this computer.")
        st.warning("If it doesn't load, check your Windows Firewall settings to allow Python/Streamlit.")

# Session state for location to persist across re-runs
if 'location_data' not in st.session_state:
    st.session_state['location_data'] = None
if 'city_input_val' not in st.session_state:
    st.session_state['city_input_val'] = "San Francisco"

c1, c2 = st.columns([3, 1])
with c1:
    city_input = st.text_input("📍 Enter City Name", value=st.session_state.get('city_input_val', "San Francisco"))
with c2:
    st.write("")
    st.write("")
    if st.button("Detect Location", use_container_width=True):
        detect_location_result = get_current_location()
        if detect_location_result:
            lat, lon, city = detect_location_result
            st.session_state['location_data'] = (lat, lon, city)
            st.session_state['city_input_val'] = city 
            city_input = city
            st.rerun()
        else:
            st.error("Could not detect location.")

if not city_input:
    st.warning("Please enter a city or detect your location.")
    st.stop()

# Data Fetching Logic
with st.spinner(f"Analyzing air quality in {city_input}..."):
    lat, lon = 0, 0
    # Check if we already have lat/lon for this specific city input from detection
    if st.session_state['location_data'] and st.session_state['location_data'][2] == city_input:
        lat, lon, _ = st.session_state['location_data']
    else:
        # Geocode the input city
        geo_res = get_coordinates(city_input)
        if geo_res:
            lat, lon, formatted_name = geo_res
        else:
            st.error(f"Could not find coordinates for '{city_input}'. Please check the spelling.")
            st.stop()
            
    # Fetch AQI Data
    raw_data = get_aqi_data(lat, lon)
    if not raw_data:
        st.error("Failed to fetch AQI data from the API. Please try again later.")
        st.stop()
        
    data = process_aqi_data(raw_data, city_input)
    if "error" in data:
         st.error(data['error'])
         st.stop()

    # Determine animation based on status
    if data['aqi'] <= 50:
        anim = lottie_good_air
    elif data['aqi'] <= 100:
        anim = lottie_moderate_air
    elif data['aqi'] <= 150:
        anim = lottie_moderate_air
    else:
        anim = lottie_unhealthy_air

st.markdown("---")

# Hero Section: Left (AQI Card & Stats) | Right (Visuals)
hero_col1, hero_col2 = st.columns([1, 1], gap="large")

with hero_col1:
    # AQI Card
    st.markdown(f"""
        <div class="aqi-card">
            <h2 class="gradient-text" style="margin:0;">AQI Index</h2>
            <div class="aqi-value" style="-webkit-text-fill-color: {data['color']};">{data['aqi']}</div>
            <div class="aqi-status" style="color: {data['color']};">{data['status']}</div>
            <p style="margin-top:10px; font-size:1.1rem;">{data['description']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="advice-container">
        <h4>🩺 General Advice</h4>
        <p>{data['description']} Stay hydrated and keep an eye on changing conditions.</p>
    </div>
    """, unsafe_allow_html=True)

with hero_col2:
    tab1, tab2 = st.tabs(["Analysis", "Map View"])
    
    with tab1:
        st.plotly_chart(get_pollutant_chart(data['pollutants']), use_container_width=True)
        
    with tab2:
        map_df = pd.DataFrame({'lat': [data['lat']], 'lon': [data['lon']]})
        st.map(map_df, zoom=10)

# Metrics Grid
st.markdown("### 📊 Pollutant Breakdown")
m1, m2, m3, m4 = st.columns(4)
m1.metric("PM2.5", f"{data['pollutants']['PM2.5']} µg/m³")
m2.metric("PM10", f"{data['pollutants']['PM10']} µg/m³")
m3.metric("Ozone (O3)", f"{data['pollutants']['O3']} µg/m³")
m4.metric("NO2", f"{data['pollutants']['NO2']} µg/m³")

# --- Vertex AI Analysis Section ---
st.markdown("### 🧠 Vertex AI Health Analysis")

recommendations = get_health_recommendations(data['aqi'])

# Use colorful expanders or tabs for different groups
rec_tab1, rec_tab2, rec_tab3, rec_tab4 = st.tabs([
    "🏃 General Population", 
    "👶 Children", 
    "👴 Elderly", 
    "🫁 Sensitive Groups"
])

with rec_tab1:
    st.markdown(f"""
    <div class="advice-container" style="border-left-color: #3498db; margin-top:0;">
        <h4 style="color:#3498db;">General Population</h4>
        <p style="font-size:1.8rem; font-weight: 500; margin-bottom: 15px;">{recommendations['General']['action']}</p>
        <p style="font-size:1rem; color: #a0a0a0; margin-bottom: 5px;"><b>⚠️ Potential Health Issues:</b> {recommendations['General']['risk']}</p>
        <p style="font-size:1rem; color: #a0a0a0;"><b>🛡️ Precautions:</b> {recommendations['General']['precaution']}</p>
    </div>
    """, unsafe_allow_html=True)

with rec_tab2:
    st.markdown(f"""
    <div class="advice-container" style="border-left-color: #f1c40f; margin-top:0;">
        <h4 style="color:#f1c40f;">Children</h4>
        <p style="font-size:1.8rem; font-weight: 500; margin-bottom: 15px;">{recommendations['Children']['action']}</p>
        <p style="font-size:1rem; color: #a0a0a0; margin-bottom: 5px;"><b>⚠️ Potential Health Issues:</b> {recommendations['Children']['risk']}</p>
        <p style="font-size:1rem; color: #a0a0a0;"><b>🛡️ Precautions:</b> {recommendations['Children']['precaution']}</p>
    </div>
    """, unsafe_allow_html=True)

with rec_tab3:
    st.markdown(f"""
    <div class="advice-container" style="border-left-color: #9b59b6; margin-top:0;">
        <h4 style="color:#9b59b6;">Elderly</h4>
        <p style="font-size:1.8rem; font-weight: 500; margin-bottom: 15px;">{recommendations['Elderly']['action']}</p>
        <p style="font-size:1rem; color: #a0a0a0; margin-bottom: 5px;"><b>⚠️ Potential Health Issues:</b> {recommendations['Elderly']['risk']}</p>
        <p style="font-size:1rem; color: #a0a0a0;"><b>🛡️ Precautions:</b> {recommendations['Elderly']['precaution']}</p>
    </div>
    """, unsafe_allow_html=True)

with rec_tab4:
    st.markdown(f"""
    <div class="advice-container" style="border-left-color: #e74c3c; margin-top:0;">
        <h4 style="color:#e74c3c;">Sensitive Groups (Asthma/Lung Disease)</h4>
        <p style="font-size:1.8rem; font-weight: 500; margin-bottom: 15px;">{recommendations['Sensitive']['action']}</p>
        <p style="font-size:1rem; color: #a0a0a0; margin-bottom: 5px;"><b>⚠️ Potential Health Issues:</b> {recommendations['Sensitive']['risk']}</p>
        <p style="font-size:1rem; color: #a0a0a0;"><b>🛡️ Precautions:</b> {recommendations['Sensitive']['precaution']}</p>
    </div>
    """, unsafe_allow_html=True)

# Trend Graph
st.markdown("### 📉 24-Hour Forecast (Google Cloud Processing)")
if not data['trend_data'].empty:
    trend_df = data['trend_data']
    fig = px.area(trend_df, x="Time", y="AQI", title="", markers=True)
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="AQI",
        font=dict(family="Outfit, sans-serif", size=12, color="#e0e0e0"),
        hovermode="x unified"
    )
    fig.update_traces(line_color=data['color'], fillcolor=f"rgba{tuple(int(data['color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.2,)}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Forecast data unavailable for this location.")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='text-align: center; color: #a0a0a0; padding: 20px; font-size: 0.9rem;'>
        <b>Stay Safe & Breathe Healthy! 🌿</b> <br> We Care For Your Health
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("---")
