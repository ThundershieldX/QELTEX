import sys
import os
import multiprocessing
import requests
import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt

class WeatherMatrixWindow(QMainWindow):
    def __init__(self, city, weather_data):
        super().__init__()
        self.setWindowTitle("qeltex_weather_matrix")
        self.setGeometry(150, 150, 650, 450)
        self.setStyleSheet("background-color: #0b111e; border: 1px solid #1f3a60;")
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        header_layout = QHBoxLayout()
        self.title_label = QLabel("WEATHER · " + str(city).upper())
        self.title_label.setStyleSheet("color: #ffffff; font-family: 'Consolas', 'Segoe UI'; font-size: 18px; font-weight: bold; letter-spacing: 1px; border: none;")
        header_layout.addWidget(self.title_label)
        
        live_label = QLabel("● LIVE")
        live_label.setStyleSheet("color: #ff3333; font-family: 'Consolas'; font-size: 11px; font-weight: bold; border: none;")
        live_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(live_label)
        main_layout.addLayout(header_layout)
        
        self.sub_label = QLabel("qeltex Meteorological Grid Link Enabled")
        self.sub_label.setStyleSheet("color: #5275a1; font-family: 'Consolas'; font-size: 11px; border: none;")
        main_layout.addWidget(self.sub_label)
        
        main_layout.addSpacing(25)
        
        mid_layout = QHBoxLayout()
        
        current_layout = QVBoxLayout()
        self.icon_label = QLabel(weather_data["current_icon"])
        self.icon_label.setStyleSheet("font-size: 64px; color: #ffffff; border: none;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.temp_label = QLabel(str(weather_data["current_temp"]) + "°")
        self.temp_label.setStyleSheet("color: #ffffff; font-family: 'Segoe UI', Arial; font-size: 72px; font-weight: 300; border: none;")
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.desc_label = QLabel(str(weather_data["current_desc"]).upper())
        self.desc_label.setStyleSheet("color: #8ab4f8; font-family: 'Consolas'; font-size: 12px; font-weight: bold; letter-spacing: 1px; border: none;")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        current_layout.addWidget(self.icon_label)
        current_layout.addWidget(self.temp_label)
        current_layout.addWidget(self.desc_label)
        mid_layout.addLayout(current_layout, stretch=1)
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #0e1726; border: 1px solid #1c2b42; border-radius: 6px; padding: 15px;")
        stats_layout = QVBoxLayout(stats_frame)
        
        def create_stat_line(label, value):
            line = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #5275a1; font-family: 'Consolas'; font-size: 12px; border: none;")
            val = QLabel(value)
            val.setStyleSheet("color: #ffffff; font-family: 'Consolas'; font-size: 13px; font-weight: bold; border: none;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            line.addWidget(lbl)
            line.addWidget(val)
            return line
            
        stats_layout.addLayout(create_stat_line("HUMIDITY:", str(weather_data["humidity"]) + "%"))
        stats_layout.addLayout(create_stat_line("PRESSURE:", str(weather_data["pressure"]) + " hPa"))
        stats_layout.addLayout(create_stat_line("WIND SPEED:", str(weather_data["wind"]) + " m/s"))
        stats_layout.addLayout(create_stat_line("FEELS LIKE:", str(weather_data["feels_like"]) + "°C"))
        
        mid_layout.addWidget(stats_frame, stretch=1)
        main_layout.addLayout(mid_layout)
        
        main_layout.addSpacing(30)
        
        forecast_title = QLabel("3-DAY ATMOSPHERIC FORECAST (12:00)")
        forecast_title.setStyleSheet("color: #5275a1; font-family: 'Consolas'; font-size: 10px; font-weight: bold; letter-spacing: 1px; border: none;")
        main_layout.addWidget(forecast_title)
        main_layout.addSpacing(5)
        
        forecast_layout = QHBoxLayout()
        for day in weather_data["forecast"]:
            day_box = QFrame()
            day_box.setStyleSheet("background-color: #0e1726; border: 1px solid #1c2b42; border-radius: 4px; padding: 10px;")
            day_box_layout = QVBoxLayout(day_box)
            day_box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            d_lbl = QLabel(str(day["day"]).upper())
            d_lbl.setStyleSheet("color: #5275a1; font-family: 'Consolas'; font-size: 11px; font-weight: bold; border: none;")
            d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            ico_lbl = QLabel(day["icon"])
            ico_lbl.setStyleSheet("font-size: 24px; color: #ffffff; margin: 5px 0; border: none;")
            ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            t_lbl = QLabel(str(day["temp"]) + "°")
            t_lbl.setStyleSheet("color: #ffffff; font-family: 'Consolas'; font-size: 14px; font-weight: bold; border: none;")
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            day_box_layout.addWidget(d_lbl)
            day_box_layout.addWidget(ico_lbl)
            day_box_layout.addWidget(t_lbl)
            forecast_layout.addWidget(day_box)
            
        main_layout.addLayout(forecast_layout)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

def get_auto_city() -> str:
    try:
        ip_host = "ip-api" + ".com"
        res = requests.get("http://" + ip_host + "/json/", timeout=3).json()
        if res.get("status") == "success" and res.get("city"):
            return res["city"]
    except Exception:
        pass
    return "Oslo"

def launch_weather_process(city, weather_data_dummy_not_used):
    lat, lon = 59.91, 10.75
    official_name = city
    
    geo_host = "geocoding-api.open-meteo" + ".com"
    met_host = "api.met" + ".no"
    
    try:
        geo_url = "https://" + geo_host + "/v1/search?name=" + requests.utils.quote(city) + "&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=4).json()
        if "results" in geo_res and len(geo_res["results"]) > 0:
            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            official_name = geo_res["results"][0]["name"]
    except Exception as e:
        print("[qeltex-GEO] Geokoding feilet: " + str(e))

    try:
        headers = {"User-Agent": "qeltexWeatherMatrix/2.0 (qeltex_system_link@domain.no)"}
        weather_url = "https://" + met_host + "/weatherapi/locationforecast/2.0/complete?lat=" + str(round(float(lat), 4)) + "&lon=" + str(round(float(lon), 4))
        res = requests.get(weather_url, headers=headers, timeout=5).json()
        
        timeseries = res["properties"]["timeseries"]
        
        current_entry = timeseries[0]
        current_details = current_entry["data"]["instant"]["details"]
        
        raw_current_symbol = current_entry["data"].get("next_1_hours", current_entry["data"].get("next_6_hours", {}))["summary"]["symbol_code"]

        def get_yr_meta(symbol_string, force_day=False):
            raw_sym = str(symbol_string).lower().strip()
            
            if force_day and "_night" in raw_sym:
                raw_sym = raw_sym.replace("_night", "_day")
            
            mapping = {
                "clearsky_day": ("☀️", "Clear Sky"),
                "clearsky_night": ("🌙", "Clear Sky"),
                "clearsky": ("☀️", "Clear Sky"),
                "fair_day": ("🌤️", "Fair"),
                "fair_night": ("☁️", "Fair"),
                "fair": ("🌤️", "Fair"),
                "partlycloudy_day": ("⛅", "Partly Cloudy"),
                "partlycloudy_night": ("☁️🌙", "Partly Cloudy"),
                "partlycloudy": ("⛅", "Partly Cloudy"),
                "cloudy": ("☁️", "Cloudy"),
                "fog": ("🌫️", "Fog"),
                "rainshowers_day": ("🌦️", "Rain Showers"),
                "rainshowers_night": ("🌧️", "Rain Showers"),
                "rainshowers": ("🌦️", "Rain Showers"),
                "lightrainshowers_day": ("🌦️", "Light Rain Showers"),
                "lightrainshowers_night": ("🌧️", "Light Rain Showers"),
                "lightrainshowers": ("🌦️", "Light Rain Showers"),
                "heavyrainshowers_day": ("🌦️", "Heavy Rain Showers"),
                "heavyrainshowers_night": ("🌧️", "Heavy Rain Showers"),
                "heavyrainshowers": ("🌦️", "Heavy Rain Showers"),
                "lightrain": ("🌧️", "Light Rain"),
                "rain": ("🌧️", "Rain"),
                "heavyrain": ("🌧️", "Heavy Rain"),
                "snow": ("❄️", "Snow"),
                "sleet": ("🌨️", "Sleet"),
                "thunder": ("⛈️", "Thunderstorm"),
                "rainandthunder": ("⛈️", "Rain & Thunder"),
                "rainshowersandthunder": ("⛈️", "Showers & Thunder")
            }
            
            if raw_sym in mapping:
                return mapping[raw_sym]
                
            base_sym = raw_sym.split("_")[0] if "_" in raw_sym else raw_sym
            return mapping.get(base_sym, ("☁️", "Cloudy"))

        c_icon, c_desc = get_yr_meta(raw_current_symbol, force_day=False)
        forecast_list = []
        
        now_dt = datetime.datetime.strptime(current_entry["time"][:10], "%Y-%m-%d")
        
        target_dates = [
            (now_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            (now_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
            (now_dt + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        ]
        
        for target_date in target_dates:
            found_entry = None
            
            for entry in timeseries:
                entry_time = entry["time"]
                if entry_time.startswith(target_date) and "T12:00:00" in entry_time:
                    found_entry = entry
                    break
                    
            if not found_entry:
                for entry in timeseries:
                    if entry["time"].startswith(target_date):
                        found_entry = entry
                        break

            if found_entry:
                dt_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d")
                day_name = dt_obj.strftime("%a")
                
                f_data = found_entry["data"]
                
                symbol_block = f_data.get("next_1_hours", f_data.get("next_6_hours", f_data.get("next_12_hours", {})))
                raw_f_symbol = symbol_block.get("summary", {}).get("symbol_code", "cloudy")
                
                dag_ikon, _ = get_yr_meta(raw_f_symbol, force_day=True)
                
                f_temp = f_data["instant"]["details"]["air_temperature"]
                
                forecast_list.append({
                    "day": day_name,
                    "icon": dag_ikon,
                    "temp": str(int(round(float(f_temp))))
                })

        weather_data = {
            "current_temp": str(int(round(float(current_details["air_temperature"])))),
            "current_icon": c_icon,
            "current_desc": c_desc,
            "humidity": str(int(round(float(current_details["relative_humidity"])))),
            "pressure": str(int(round(float(current_details["air_pressure_at_sea_level"])))),
            "wind": str(int(round(float(current_details["wind_speed"])))),
            "feels_like": str(int(round(float(current_details.get("apparent_air_temperature", current_details["air_temperature"]))))),
            "forecast": forecast_list
        }

    except Exception as e:
        print("[qeltex-ERROR] API-utpakking feilet: " + str(e))
        weather_data = {
            "current_temp": "N/A", "current_icon": "☁️", "current_desc": "N/A",
            "humidity": "N/A", "pressure": "N/A", "wind": "N/A", "feels_like": "N/A",
            "forecast": [
                {"day": "N/A", "icon": "☁️", "temp": "N/A"},
                {"day": "N/A", "icon": "☁️", "temp": "N/A"},
                {"day": "N/A", "icon": "☁️", "temp": "N/A"}
            ]
        }

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = WeatherMatrixWindow(official_name, weather_data)
    window.show()
    sys.exit(app.exec())

def weather_report(parameters: dict = None, player=None) -> str:
    params = parameters if isinstance(parameters, dict) else {}
    city = params.get("city")
    if not city or not isinstance(city, str) or not city.strip():
        city = get_auto_city()
        
    city = city.strip()

    try:
        p = multiprocessing.Process(target=launch_weather_process, args=(city, None))
        p.start()
        return "[WEATHER CONTROL] Weather matrix overlay deployed for " + city + ", sir."
    except Exception as e:
        return "Hardware matrix overlay failure: " + str(e)