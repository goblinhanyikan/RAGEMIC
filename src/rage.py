#aşağıdaki kod ttkbootstrap suçu

# tek yaptığı şey, ttkbootstrap'un varsayılan dil ayarlarını geçersiz kılmak
# Bu, ttkbootstrap'un bazı dillerdeki tarih ve saat biçimlendirmelerini bozabilir.
# Bu kodu kaldırarak, ttkbootstrap'un dil ayarlarını kullanabilirsiniz.
# ki onuda çözdüm merak etmeyin. Eğer hala hata varsa büyük ihtimalle kulanılan cihazda dil paketi yoktur.
# 3/15/2025 - BayEggex

import os
os.environ["LANG"] = "C"
os.environ["LC_ALL"] = "C"

import locale
try:
    locale.setlocale(locale.LC_ALL, locale.setlocale(locale.LC_TIME, ""))
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "C")
    except:
        pass
    
#Yukarıdaki kod ttkbootstrap suçu

import pyaudio
import numpy as np
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
import keyboard
import json

class AudioProcessor:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.gain = 1.0
        self.distortion = 1.0
        self.clipping = 1.0
        self.effects_enabled = False
        self.latest_amplitude = 0.0

    def get_device_list(self, device_type):
        devices = []
        seen_devices = set()
        host_api_count = self.p.get_host_api_count()
        host_api_names = {}
        for i in range(host_api_count):
            host_api_info = self.p.get_host_api_info_by_index(i)
            host_api_names[i] = host_api_info['name']
        for i in range(self.p.get_device_count()):
            dev_info = self.p.get_device_info_by_index(i)
            host_api = host_api_names.get(dev_info['hostApi'], 'Unknown API')
            if host_api != "MME":
                continue
            device_name = dev_info['name']
            device_key = (device_name, host_api)
            if device_key in seen_devices:
                continue
            seen_devices.add(device_key)
            if device_type == 'input' and dev_info['maxInputChannels'] > 0:
                devices.append(f"{i}: {device_name} ({host_api})")
            elif device_type == 'output' and dev_info['maxOutputChannels'] > 0:
                devices.append(f"{i}: {device_name} ({host_api})")
        return devices

    def process_audio(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        if self.effects_enabled:
            audio_data = audio_data * (self.gain ** 2)
            audio_data = np.tanh(audio_data * self.distortion * 10)
            audio_data = np.tanh(audio_data * 2)
            audio_data = np.clip(audio_data, -self.clipping, self.clipping)
        self.latest_amplitude = np.max(np.abs(audio_data))
        return (audio_data.tobytes(), pyaudio.paContinue)

    def start_stream(self, input_device_index, output_device_index):
        if self.stream is not None:
            self.stop_stream()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=44100,
            input=True,
            output=True,
            input_device_index=input_device_index,
            output_device_index=output_device_index,
            stream_callback=self.process_audio,
            frames_per_buffer=1024
        )
        self.stream.start_stream()

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def cleanup(self):
        self.stop_stream()
        self.p.terminate()


class AudioEffectGUI:
    def __init__(self):
        # JSON dosyaları aynı klasörde saklanıyor.
        self.config_file = "audio_config.json"
        self.device_file = "device_selection.json"
        self.load_config()
        self.profile_settings = self.config.get("presets", {
            "Normal": {"gain": 1.0, "distortion": 1.0, "clipping": 1.0},
            "Boost": {"gain": 5.0, "distortion": 20.0, "clipping": 0.5},
            "Extreme": {"gain": 10.0, "distortion": 35.0, "clipping": 0.3}
        })
        self.night_mode = self.config.get("night_mode", False)
        self.theme_name = "darkly" if self.night_mode else "flatly"
        self.root = ttk.Window(themename=self.theme_name)
        self.root.title("RAGE MIC!")
        self.root.geometry("800x900")
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, "icon.png")
            self.icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(False, self.icon)
        except Exception as e:
            print("Icon yüklenemedi:", e)

        self.processor = AudioProcessor()
        self.toggle_key = "F6"  # Efekt için

        self.setup_ui()
        self.load_device_selection()
        self.setup_hotkey()
        self.update_volume_meter()

        last_preset = self.config.get("last_preset")
        if last_preset and last_preset in self.profile_settings:
            self.profile_var.set(last_preset)
            self.apply_profile()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Config dosyası hatası: {e}")
                self.config = {}
        else:
            self.config = {}

    def save_config(self):
        self.config["presets"] = self.profile_settings
        self.config["night_mode"] = self.night_mode
        self.config["last_preset"] = self.profile_var.get()
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def load_device_selection(self):
        if os.path.exists(self.device_file):
            try:
                with open(self.device_file, "r") as f:
                    device_config = json.load(f)
                    input_device = device_config.get("input_device", "")
                    output_device = device_config.get("output_device", "")
                    input_list = self.processor.get_device_list('input')
                    output_list = self.processor.get_device_list('output')
                    if input_device in input_list:
                        self.input_device_var.set(input_device)
                    elif input_list:
                        self.input_device_var.set(input_list[0])
                    if output_device in output_list:
                        self.output_device_var.set(output_device)
                    elif output_list:
                        self.output_device_var.set(output_list[0])
            except Exception as e:
                print(f"Cihaz seçim yükleme hatası: {e}")

    def save_device_selection(self):
        device_config = {
            "input_device": self.input_device_var.get(),
            "output_device": self.output_device_var.get()
        }
        with open(self.device_file, "w") as f:
            json.dump(device_config, f, indent=4)

    def on_closing(self):
        self.save_config()
        self.save_device_selection()
        self.processor.cleanup()
        self.root.destroy()

    def update_ui_mode(self):
        self.theme_name = "darkly" if self.night_mode else "flatly"
        self.root.style.theme_use(self.theme_name)

    def toggle_ui_mode(self):
        self.night_mode = not self.night_mode
        self.update_ui_mode()

    def add_new_preset(self):
        preset_win = ttk.Toplevel(self.root)
        preset_win.title("Yeni Preset Ekle")
        preset_win.geometry("300x370")
        try:
            preset_win.iconphoto(False, self.icon)
        except Exception as e:
            print("Preset penceresi için icon yüklenemedi:", e)
        
        ttk.Label(preset_win, text="Preset Adı:").pack(pady=5)
        preset_name_entry = ttk.Entry(preset_win)
        preset_name_entry.pack(pady=5)
        
        ttk.Label(preset_win, text="Gain:").pack(pady=5)
        gain_entry = ttk.Entry(preset_win)
        gain_entry.pack(pady=5)
        
        ttk.Label(preset_win, text="Distorsiyon:").pack(pady=5)
        distortion_entry = ttk.Entry(preset_win)
        distortion_entry.pack(pady=5)
        
        ttk.Label(preset_win, text="Klip Seviyesi:").pack(pady=5)
        clipping_entry = ttk.Entry(preset_win)
        clipping_entry.pack(pady=5)
        
        def save_preset():
            name = preset_name_entry.get().strip()
            try:
                gain = float(gain_entry.get())
                distortion = float(distortion_entry.get())
                clipping = float(clipping_entry.get())
            except:
                ttk.Messagebox.show_error("Hata", "Lütfen geçerli sayısal değerler girin!")
                return
            if not name:
                ttk.Messagebox.show_error("Hata", "Preset adı boş olamaz!")
                return
            self.profile_settings[name] = {"gain": gain, "distortion": distortion, "clipping": clipping}
            self.profile_combo['values'] = list(self.profile_settings.keys())
            preset_win.destroy()
        
        ttk.Button(preset_win, text="Kaydet", command=save_preset).pack(pady=10)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        device_frame = ttk.Labelframe(main_frame, text="Ses Aygıtları")
        device_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(device_frame, text="Mikrofon:").pack(pady=2)
        self.input_device_var = tk.StringVar()
        self.input_device_combo = ttk.Combobox(device_frame, textvariable=self.input_device_var, state="readonly")
        input_devices = self.processor.get_device_list('input')
        self.input_device_combo['values'] = input_devices
        self.input_device_combo.pack(padx=5, pady=5, fill="x")
        if not self.input_device_var.get() and input_devices:
            self.input_device_var.set(input_devices[0])

        ttk.Label(device_frame, text="Çıkış:").pack(pady=2)
        self.output_device_var = tk.StringVar()
        self.output_device_combo = ttk.Combobox(device_frame, textvariable=self.output_device_var, state="readonly")
        output_devices = self.processor.get_device_list('output')
        self.output_device_combo['values'] = output_devices
        self.output_device_combo.pack(padx=5, pady=5, fill="x")
        if not self.output_device_var.get() and output_devices:
            self.output_device_var.set(output_devices[0])

        # Profil Seçimi
        profile_frame = ttk.Labelframe(main_frame, text="Profil Seçimi")
        profile_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(profile_frame, text="Ön ayarlar:").pack(pady=2)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly")
        self.profile_combo['values'] = list(self.profile_settings.keys())
        self.profile_combo.current(0)
        self.profile_combo.pack(padx=5, pady=5, fill="x")
        self.profile_combo.bind("<<ComboboxSelected>>", self.apply_profile)
        
        ttk.Button(profile_frame, text="Yeni Preset Ekle", command=self.add_new_preset).pack(pady=5, fill="x")
        
        # UI Modu Değiştirme
        ttk.Button(main_frame, text="UI Modunu Değiştir (Sabah/Akşam)", command=self.toggle_ui_mode).pack(padx=5, pady=5, fill="x")

        # Efekt Ayarları
        effects_frame = ttk.Labelframe(main_frame, text="Efekt Ayarları")
        effects_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(effects_frame, text="Ses seviyesi (Gain):").pack(pady=2)
        self.gain_scale = ttk.Scale(effects_frame, from_=0, to=20, orient="horizontal", command=self.update_gain)
        self.gain_scale.set(self.profile_settings[self.profile_var.get()]["gain"])
        self.gain_scale.pack(fill="x", padx=5, pady=5)
        ttk.Label(effects_frame, text="Distorsiyon:").pack(pady=2)
        self.distortion_scale = ttk.Scale(effects_frame, from_=1, to=50, orient="horizontal", command=self.update_distortion)
        self.distortion_scale.set(self.profile_settings[self.profile_var.get()]["distortion"])
        self.distortion_scale.pack(fill="x", padx=5, pady=5)
        ttk.Label(effects_frame, text="Klip seviyesi:").pack(pady=2)
        self.clipping_scale = ttk.Scale(effects_frame, from_=0.01, to=1, orient="horizontal", command=self.update_clipping)
        self.clipping_scale.set(self.profile_settings[self.profile_var.get()]["clipping"])
        self.clipping_scale.pack(fill="x", padx=5, pady=5)

        # Ses Seviyesi Göstergesi
        meter_frame = ttk.Labelframe(main_frame, text="Ses Seviyesi Göstergesi")
        meter_frame.pack(padx=5, pady=5, fill="both", expand=True)
        self.canvas = tk.Canvas(meter_frame, bg="black", height=150)
        self.canvas.pack(padx=5, pady=5, fill="x")
        self.meter_rect = self.canvas.create_rectangle(0, 0, 0, 150, fill="green")

        # Butonlar
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(padx=5, pady=5, fill="x")
        self.toggle_button = ttk.Button(button_frame, text="Efektleri Aç/Kapa (" + self.toggle_key + ")", command=self.toggle_processing)
        self.toggle_button.pack(pady=5, fill="x")
        self.stop_button = ttk.Button(button_frame, text="Stream Durdur", command=self.stop_processing)
        self.stop_button.pack(pady=5, fill="x")
        self.info_button = ttk.Button(button_frame, text="Yardım & Bilgi", command=self.show_info)
        self.info_button.pack(pady=5, fill="x")
        self.status_label = ttk.Label(main_frame, text="Durum: Efektler Kapalı", anchor="center")
        self.status_label.pack(pady=10, fill="x")

    def apply_profile(self, event=None):
        profile = self.profile_var.get()
        settings = self.profile_settings.get(profile, {})
        self.gain_scale.set(settings.get("gain", 1.0))
        self.distortion_scale.set(settings.get("distortion", 1.0))
        self.clipping_scale.set(settings.get("clipping", 1.0))
        self.processor.gain = float(settings.get("gain", 1.0))
        self.processor.distortion = float(settings.get("distortion", 1.0))
        self.processor.clipping = float(settings.get("clipping", 1.0))

    def setup_hotkey(self):
        keyboard.on_press_key(self.toggle_key.lower(), lambda e: self.toggle_processing())

    def show_info(self):
        info_win = ttk.Toplevel(self.root)
        info_win.title("Yardım & Bilgi")
        info_win.geometry("700x700")
        try:
            info_win.iconphoto(False, self.icon)
        except Exception as e:
            print("Bilgi penceresi için icon yüklenemedi:", e)
        text_box = ttk.Label(info_win, text="""
            Uygulama çalışmıyorsa:\n\n
            - Doğru ses aygıtlarını seçtiğinizden emin olun.\n
            - 'CABLE INPUT' gibi sanal ses aygıtlarını doğru kurduğunuzu kontrol edin.\n
            - Global hotkey (F6) antivirüs tarafından yanlış algılanabilir.\n\n
            Herhangi bir sorunla karşılaşırsanız, lütfen geri bildirimde bulunun.
        """)
        text_box.pack(padx=10, pady=10)

    def toggle_processing(self):
        if not self.processor.stream:
            try:
                input_device = self.input_device_var.get()
                input_idx = int(input_device.split(':')[0]) if ':' in input_device else 0
                output_device = self.output_device_var.get()
                output_idx = int(output_device.split(':')[0]) if ':' in output_device else 0
            except (ValueError, IndexError) as e:
                self.status_label.config(text=f"Hata: Geçersiz cihaz formatı ({str(e)})")
                return
            try:
                self.processor.start_stream(input_idx, output_idx)
                self.processor.effects_enabled = True
                self.status_label.config(text="Durum: Efektler Açık")
                self.toggle_button.config(text="Efektleri Kapat (" + self.toggle_key + ")")
            except Exception as err:
                self.status_label.config(text=f"Hata: {str(err)}")
        else:
            self.processor.effects_enabled = not self.processor.effects_enabled
            if self.processor.effects_enabled:
                self.status_label.config(text="Durum: Efektler Açık")
                self.toggle_button.config(text="Efektleri Kapat (" + self.toggle_key + ")")
            else:
                self.status_label.config(text="Durum: Efektler Kapalı")
                self.toggle_button.config(text="Efektleri Aç (" + self.toggle_key + ")")

    def stop_processing(self):
        self.processor.stop_stream()
        self.status_label.config(text="Durum: Stream Durduruldu")
        self.toggle_button.config(text="Efektleri Aç (" + self.toggle_key + ")")

    def update_gain(self, value):
        self.processor.gain = float(value)

    def update_distortion(self, value):
        self.processor.distortion = float(value)

    def update_clipping(self, value):
        self.processor.clipping = float(value)

    def update_volume_meter(self):
        amp = self.processor.latest_amplitude
        meter_width = int(self.canvas.winfo_width() * amp)
        meter_width = max(0, min(self.canvas.winfo_width(), meter_width))
        self.canvas.coords(self.meter_rect, 0, 0, meter_width, 150)
        color = "green" if amp < 0.3 else "yellow" if amp < 0.7 else "red"
        self.canvas.itemconfig(self.meter_rect, fill=color)
        self.root.after(50, self.update_volume_meter)

    def run(self):
        self.root.mainloop()
        self.processor.cleanup()


if __name__ == "__main__":
    try:
        app = AudioEffectGUI()
        app.run()
    except Exception as e:
        print("Uygulama başlatılamadı bu hata kodu ile @bayeggex'e ulaşın veya Issue açın:", e)
        input("Çıkmak için ENTER tuşuna basın...")   
    #app = AudioEffectGUI()
    #app.run()

# -----------------------------------------------------
# Bay Eggex'den not:
# - Build dosyasında ben zaten buildledim ancak siz yine de buildlemek istiyorsanız aşağıdaki araçları kullanarak yapabilirsiniz:
#   PyInstaller gibi araçlar kullanabilirsiniz:
#   > pyinstaller --onefile --hidden-import=ttkbootstrap.constants --hidden-import=keyboard --hidden-import=pyaudio rage.py
#
# - Alternatif olarak, .bat dosyası oluşturarak da yapabilirsiniz.:
#   @echo off
#   python rage.py
#   pause
# -----------------------------------------------------