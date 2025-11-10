import bpy
import os
import subprocess
import platform
import winreg

class THERMRunner:
    def __init__(self):
        pass
    
    def find_therm_executable(self):
        """Znajduje ścieżkę do THERM7.exe"""
        # Sprawdź ręcznie wskazaną ścieżkę
        manual_path = bpy.context.scene.therm_props.therm_executable_path
        if manual_path and os.path.exists(manual_path):
            return manual_path
        
        # Sprawdź w typowych lokalizacjach
        therm_paths = [
            r"C:\Program Files\THERM\THERM7.exe",
            r"C:\Program Files (x86)\THERM\THERM7.exe",
            r"C:\THERM\THERM7.exe",
            os.path.join(os.path.expanduser("~"), "THERM", "THERM7.exe"),
            "THERM7.exe",
        ]
        
        for path in therm_paths:
            if path and os.path.exists(path):
                return path
        
        # Sprawdź w rejestrze Windows
        return self.find_therm_in_registry()
    
    def find_therm_in_registry(self):
        """Próbuje znaleźć THERM w rejestrze Windows"""
        try:
            if platform.system() == "Windows":
                registry_paths = [
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\THERM"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\THERM"),
                    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\THERM"),
                ]
                
                for root, path in registry_paths:
                    try:
                        key = winreg.OpenKey(root, path)
                        try:
                            therm_path = winreg.QueryValueEx(key, "InstallPath")[0]
                            exe_path = os.path.join(therm_path, "THERM7.exe")
                            if os.path.exists(exe_path):
                                return exe_path
                        finally:
                            winreg.CloseKey(key)
                    except WindowsError:
                        continue
        except:
            pass
        
        return None
    
    def run_calculation_thmx(self, context):
        """Uruchamia obliczenia THERM z plikiem .thmx"""
        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            return {'ERROR'}, "Zapisz plik Blender przed uruchomieniem obliczeń"
        
        # Sprawdź czy plik .thmx istnieje
        blend_filename = os.path.splitext(os.path.basename(blend_filepath))[0]
        therm_thmx_path = os.path.join(os.path.dirname(blend_filepath), f"{blend_filename}.thmx")
        
        if not os.path.exists(therm_thmx_path):
            return {'ERROR'}, f"Plik {therm_thmx_path} nie istnieje. Najpierw wyeksportuj do THERM."
        
        # Uruchom obliczenia
        if self._run_therm_calculation_thmx(therm_thmx_path):
            return {'INFO'}, f"Uruchomiono obliczenia THERM: {therm_thmx_path}"
        else:
            return {'ERROR'}, "Nie można uruchomić obliczeń THERM. Sprawdź instalację."
    
    def _run_therm_calculation_thmx(self, thmx_filepath):
        """Uruchamia obliczenia THERM - poprawiona wersja"""
        try:
            therm_exe = self.find_therm_executable()
            
            if not therm_exe:
                print("❌ Nie znaleziono THERM.exe")
                return False
            
            print(f"Znaleziono THERM: {therm_exe}")
            
            thmx_filepath_raw = os.path.normpath(thmx_filepath)
            directory = os.path.dirname(thmx_filepath_raw)
            basename = os.path.splitext(os.path.basename(thmx_filepath_raw))[0]
            
            # Sprawdź czy pliki wynikowe już istnieją (usuń stare)
            expected_output_files = [
                os.path.join(directory, f"{basename}.thm"),
                os.path.join(directory, f"{basename}.o"),
                os.path.join(directory, f"{basename}.tdf")
            ]
            
            # Usuń stare pliki wynikowe
            for file_path in expected_output_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Usunięto stary plik: {file_path}")
                    except:
                        pass
            
            # Komenda dla trybu CLI
            cmd = [
                therm_exe,
                '-pw', 'thmCLA',
                '-thmx', thmx_filepath_raw,
                '-calc',
                '-exit'
            ]
            
            print(f"Uruchamianie THERM: {' '.join(cmd)}")
            
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        cmd, 
                        shell=False,
                        capture_output=True, 
                        text=True,
                        timeout=300,  # 5 minut na obliczenia
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True,
                        timeout=300
                    )
                
                print(f"THERM stdout: {result.stdout}")
                print(f"THERM stderr: {result.stderr}")
                print(f"THERM return code: {result.returncode}")
                
                # SPRAWDŹ CZY PLIKI WYNIKOWE POWSTAŁY
                output_files_created = []
                for file_path in expected_output_files:
                    if os.path.exists(file_path):
                        output_files_created.append(file_path)
                        print(f"✓ Utworzono plik: {os.path.basename(file_path)}")
                
                if output_files_created:
                    print("✅ OBLICZENIA THERM ZAKOŃCZONE SUKCESEM!")
                    print(f"Utworzone pliki: {[os.path.basename(f) for f in output_files_created]}")
                    return True
                elif result.returncode == 0:
                    print("✅ THERM zakończony kodem 0 (sukces)")
                    return True
                else:
                    print(f"❌ THERM zakończony kodem {result.returncode} i brak plików wynikowych")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("❌ Przekroczono czas oczekiwania na THERM (5 minut)")
                # Sprawdź czy mimo timeoutu pliki powstały
                output_files_created = []
                for file_path in expected_output_files:
                    if os.path.exists(file_path):
                        output_files_created.append(file_path)
                
                if output_files_created:
                    print("✅ Mimo timeoutu, obliczenia zostały wykonane!")
                    print(f"Utworzone pliki: {[os.path.basename(f) for f in output_files_created]}")
                    return True
                else:
                    return False
            except Exception as e:
                print(f"❌ Błąd uruchamiania THERM: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Krytyczny błąd: {e}")
            return False
    
    
    
    def run_calculation_thm(self, context):
        """Uruchamia obliczenia THERM z plikiem .thm"""
        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            return {'ERROR'}, "Zapisz plik Blender przed uruchomieniem obliczeń"
        
        # Sprawdź czy plik .thm istnieje
        blend_filename = os.path.splitext(os.path.basename(blend_filepath))[0]
        therm_thm_path = os.path.join(os.path.dirname(blend_filepath), f"{blend_filename}.thm")
        
        if not os.path.exists(therm_thm_path):
            return {'ERROR'}, f"Plik {therm_thm_path} nie istnieje."
        
        # Uruchom obliczenia
        if self._run_therm_calculation_thm(therm_thm_path):
            return {'INFO'}, f"Uruchomiono obliczenia THERM: {therm_thm_path}"
        else:
            return {'ERROR'}, "Nie można uruchomić obliczeń THERM. Sprawdź instalację."
    
    def _run_therm_calculation_thm(self, thm_filepath):
        """Uruchamia obliczenia THERM z plikiem .thm"""
        try:
            therm_exe = self.find_therm_executable()
            
            if not therm_exe:
                return False
            
            print(f"Znaleziono THERM: {therm_exe}")
            
            thm_filepath_raw = thm_filepath.replace('/', '\\')
            cmd = [therm_exe, thm_filepath_raw]
            
            print(f"Uruchamianie THERM: {' '.join(cmd)}")
            
            if platform.system() == "Windows":
                result = subprocess.run(
                    cmd, 
                    shell=True,
                    capture_output=True, 
                    text=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            print(f"THERM stdout: {result.stdout}")
            print(f"THERM stderr: {result.stderr}")
            print(f"THERM return code: {result.returncode}")
            
            if result.returncode == 0:
                print("THERM uruchomiony pomyślnie")
                return True
            else:
                print(f"Błąd uruchamiania THERM: {result.stderr}")
                try:
                    subprocess.Popen([therm_exe, thm_filepath_raw], shell=True)
                    print("Uruchomiono THERM w trybie okienkowym")
                    return True
                except:
                    return False
                
        except Exception as e:
            print(f"Błąd uruchamiania THERM: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def open_therm_folder(self, context):
        """Otwórz folder z plikami THERM"""
        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            return {'ERROR'}, "Zapisz plik Blender przed otwarciem folderu"
        
        folder_path = os.path.dirname(blend_filepath)
        
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            
            return {'INFO'}, f"Otwarto folder: {folder_path}"
        except Exception as e:
            return {'ERROR'}, f"Nie można otworzyć folderu: {e}"