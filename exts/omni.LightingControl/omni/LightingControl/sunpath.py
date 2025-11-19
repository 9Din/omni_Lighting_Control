import math
from datetime import datetime
import omni.kit.commands  # 确保这行存在
from pxr import Gf, Sdf
from typing import List, Optional
import omni.usd  # 添加这行导入

# 安装pyephem-sunpath包
omni.kit.pipapi.install("pyephem-sunpath", None, False, False, None, True, True, None)
from pyephem_sunpath.sunpath import sunpos, sunrise, sunset

class SunpathData:
    """太阳路径数据计算类"""
    
    def __init__(self, datevalue, hour, min, lon, lat):
        self.datevalue = datevalue
        self.year = datetime.now().year
        self.hour = hour
        self.lat = lat
        self.lon = lon
        self.min = min
        
        # 计算时区
        self.tz = round(self.lon / 15)
    
    def set_date(self, value):
        """设置日期参数"""
        self.datevalue = value
    
    def set_hour(self, value):
        """设置小时参数"""
        self.hour = value
    
    def set_min(self, value):
        """设置分钟参数"""
        self.min = value
    
    def set_longitude(self, value):
        """设置经度参数"""
        self.lon = value
    
    def set_latitude(self, value):
        """设置纬度参数"""
        self.lat = value
    
    @staticmethod
    def calc_xyz(alt, azm):
        """将球坐标转换为笛卡尔坐标"""
        x_val = math.sin((azm - 180) * math.pi / 180)
        y_val = math.cos((azm - 180) * math.pi / 180)
        z_val = math.tan(alt * math.pi / 180)
        length = (x_val**2 + y_val**2 + z_val**2) ** 0.5
        return [-x_val / length, z_val / length, y_val / length]
    
    def dome_rotate_angle(self):
        """计算圆顶旋转角度"""
        month, day = self.slider_to_datetime(self.datevalue)
        thetime = datetime(self.year, month, day, self.hour, self.min)
        alt, azm = sunpos(thetime, self.lat, self.lon, self.tz, dst=False)
        return -alt, 180 - azm
    
    def get_sun_position(self, thetime, lat, lon, tz):
        """获取指定时间的太阳位置"""
        alt, azm = sunpos(thetime, lat, lon, tz, dst=False)
        position = self.calc_xyz(alt, azm)
        return position
    
    def cur_sun_position(self):
        """获取当前时间的太阳位置"""
        month, day = self.slider_to_datetime(self.datevalue)
        thetime = datetime(self.year, month, day, self.hour, self.min)
        return self.get_sun_position(thetime, self.lat, self.lon, self.tz)
    
    def get_cur_time(self):
        """获取当前日期时间"""
        month, day = self.slider_to_datetime(self.datevalue)
        thetime = datetime(self.year, month, day, self.hour, self.min)
        return thetime
    
    def get_sunrise_time(self):
        """获取日出时间"""
        month, day = self.slider_to_datetime(self.datevalue)
        thetime = datetime(self.year, month, day, self.hour, self.min)
        return sunrise(thetime, self.lat, self.lon, self.tz, dst=False).time()
    
    def get_sunset_time(self):
        """获取日落时间"""
        month, day = self.slider_to_datetime(self.datevalue)
        thetime = datetime(self.year, month, day, self.hour, self.min)
        return sunset(thetime, self.lat, self.lon, self.tz, dst=False).time()
    
    @staticmethod
    def slider_to_datetime(datevalue):
        """将滑块值转换为日期时间"""
        if datevalue <= 31:
            return [1, datevalue]
        if datevalue > 31 and datevalue <= 59:
            return [2, datevalue - 31]
        if datevalue > 59 and datevalue <= 90:
            return [3, datevalue - 59]
        if datevalue > 90 and datevalue <= 120:
            return [4, datevalue - 90]
        if datevalue > 120 and datevalue <= 151:
            return [5, datevalue - 120]
        if datevalue > 151 and datevalue <= 181:
            return [6, datevalue - 151]
        if datevalue > 181 and datevalue <= 212:
            return [7, datevalue - 181]
        if datevalue > 212 and datevalue <= 243:
            return [8, datevalue - 212]
        if datevalue > 243 and datevalue <= 273:
            return [9, datevalue - 243]
        if datevalue > 273 and datevalue <= 304:
            return [10, datevalue - 273]
        if datevalue > 304 and datevalue <= 334:
            return [11, datevalue - 304]
        if datevalue > 334 and datevalue <= 365:
            return [12, datevalue - 334]


class SunlightManipulator:
    """阳光操纵器"""
    
    def __init__(self, pathmodel: SunpathData):
        self.path = None
        self.pathmodel = pathmodel
        self.selected_light_path = None
    
    def get_all_distant_lights(self):
        """获取场景中所有的DistantLight"""
        stage = omni.usd.get_context().get_stage()  # 这里使用了 omni.usd
        distant_lights = []
        
        if not stage:
            print("无法获取USD舞台")
            return distant_lights
        
        try:
            prim_range = stage.Traverse()
            
            for prim in prim_range:
                try:
                    if prim.IsValid() and prim.GetTypeName() == "DistantLight":
                        prim_path = str(prim.GetPath())
                        distant_lights.append(prim_path)
                except Exception as e:
                    print(f"处理图元时出错: {e}")
                    continue
                    
        except Exception as e:
            print(f"遍历USD舞台时出错: {e}")
        
        distant_lights.sort()
        return distant_lights
    
    def set_selected_light(self, light_path):
        """设置选中的灯光路径"""
        self.selected_light_path = light_path
        if light_path and light_path != "Select DistantLight":
            self.path = light_path
    
    def change_sun(self):
        """改变远光灯属性（旋转）"""
        if not self.path:
            return
            
        xr, yr = self.pathmodel.dome_rotate_angle()
        
        try:
            omni.kit.commands.execute(
                "TransformPrimSRT",
                path=Sdf.Path(self.path),
                new_rotation_euler=Gf.Vec3d(xr, yr, 0),
            )
            
            # 获取太阳高度角
            alt, azm = self.pathmodel.dome_rotate_angle()
            sun_altitude = -alt  # 转换为实际高度角
            
            # 修改可见性判断逻辑：在日出日落时（高度角接近0）也显示太阳
            # 只有当太阳在地平线以下较深时才隐藏（例如-5度以下）
            if sun_altitude < -5.0:
                omni.kit.commands.execute(
                    "ChangeProperty", prop_path=Sdf.Path(f"{self.path}.visibility"), value="invisible", prev=None
                )
            else:
                omni.kit.commands.execute(
                    "ChangeProperty", prop_path=Sdf.Path(f"{self.path}.visibility"), value="inherited", prev=None
                )
                
                # 根据太阳高度调整太阳光的强度和颜色
                self._adjust_sun_for_time_of_day(sun_altitude)
                
        except Exception as e:
            print(f"改变太阳位置时出错: {e}")
    
    def _adjust_sun_for_time_of_day(self, altitude):
        """根据太阳高度调整太阳光属性"""
        if not self.path:
            return
            
        try:
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(self.path)
            
            if not prim:
                return
                
            # 根据太阳高度调整强度
            if altitude <= 0:
                # 日出日落时：较低强度，暖色调
                intensity = max(100, 1000 * (altitude + 5) / 5)  # 在-5到0度之间渐变
                color = [1.0, 0.6, 0.4]  # 暖红色调
                exposure = -2.0  # 较低曝光
            elif altitude < 10:
                # 早晨/傍晚：中等强度
                intensity = 5000 + 1000 * altitude
                color = [1.0, 0.8, 0.6]  # 暖黄色调
                exposure = -1.0
            else:
                # 白天：正常强度
                intensity = 30000
                color = [1.0, 1.0, 1.0]  # 白色
                exposure = 0.0
                
            # 设置属性
            intensity_attr = prim.GetAttribute("intensity")
            if not intensity_attr:
                intensity_attr = prim.CreateAttribute("intensity", Sdf.ValueTypeNames.Float)
            intensity_attr.Set(float(intensity))
            
            color_attrs = ["color", "inputs:color"]
            for attr_name in color_attrs:
                color_attr = prim.GetAttribute(attr_name)
                if color_attr:
                    try:
                        color_attr.Set(Gf.Vec3f(color[0], color[1], color[2]))
                        break
                    except Exception:
                        continue
            
            exposure_attr = prim.GetAttribute("exposure")
            if not exposure_attr:
                exposure_attr = prim.CreateAttribute("exposure", Sdf.ValueTypeNames.Float)
            exposure_attr.Set(float(exposure))
                
        except Exception as e:
            print(f"调整太阳光属性时出错: {e}")
    
    def show_sun(self):
        """显示太阳光"""
        if not self.path:
            return
        self.change_sun()
    
    def hide_sun(self):
        """隐藏太阳光"""
        if not self.path:
            return
        
        try:
            omni.kit.commands.execute(
                "ChangeProperty", prop_path=Sdf.Path(f"{self.path}.visibility"), value="invisible", prev=None
            )
        except Exception as e:
            print(f"隐藏太阳时出错: {e}")
    
    def set_sun_intensity(self, intensity):
        """设置太阳光强度"""
        if self.path:
            try:
                stage = omni.usd.get_context().get_stage()
                prim = stage.GetPrimAtPath(self.path)
                if prim:
                    attr = prim.GetAttribute("intensity")
                    if not attr:
                        attr = prim.CreateAttribute("intensity", Sdf.ValueTypeNames.Float)
                    attr.Set(float(intensity))
            except Exception as e:
                print(f"设置太阳光强度时出错: {e}")
    
    def set_sun_color_temperature(self, temperature):
        """设置太阳光色温"""
        if self.path:
            try:
                stage = omni.usd.get_context().get_stage()
                prim = stage.GetPrimAtPath(self.path)
                if prim:
                    enable_attr = prim.GetAttribute("enableColorTemperature")
                    if not enable_attr:
                        enable_attr = prim.CreateAttribute("enableColorTemperature", Sdf.ValueTypeNames.Bool)
                    enable_attr.Set(True)
                    
                    temp_attr = prim.GetAttribute("colorTemperature")
                    if not temp_attr:
                        temp_attr = prim.CreateAttribute("colorTemperature", Sdf.ValueTypeNames.Float)
                    temp_attr.Set(float(temperature))
            except Exception as e:
                print(f"设置太阳光色温时出错: {e}")
    
    def set_sun_exposure(self, exposure):
        """设置太阳光曝光"""
        if self.path:
            try:
                stage = omni.usd.get_context().get_stage()
                prim = stage.GetPrimAtPath(self.path)
                if prim:
                    attr = prim.GetAttribute("exposure")
                    if not attr:
                        attr = prim.CreateAttribute("exposure", Sdf.ValueTypeNames.Float)
                    attr.Set(float(exposure))
            except Exception as e:
                print(f"设置太阳光曝光时出错: {e}")
    
    def set_sun_angle(self, angle):
        """设置太阳光角度"""
        if self.path:
            try:
                stage = omni.usd.get_context().get_stage()
                prim = stage.GetPrimAtPath(self.path)
                if prim:
                    attr = prim.GetAttribute("angle")
                    if not attr:
                        attr = prim.CreateAttribute("angle", Sdf.ValueTypeNames.Float)
                    attr.Set(float(angle))
            except Exception as e:
                print(f"设置太阳光角度时出错: {e}")
    
    def set_sun_color(self, color):
        """设置太阳光颜色"""
        if self.path:
            try:
                stage = omni.usd.get_context().get_stage()
                prim = stage.GetPrimAtPath(self.path)
                if prim:
                    color_attrs = ["color", "inputs:color"]
                    for attr_name in color_attrs:
                        color_attr = prim.GetAttribute(attr_name)
                        if color_attr:
                            try:
                                color_attr.Set(Gf.Vec3f(color[0], color[1], color[2]))
                                return True
                            except Exception as e:
                                print(f"设置颜色失败 {attr_name}: {str(e)}")
                    
                    try:
                        color_attr = prim.CreateAttribute("inputs:color", Sdf.ValueTypeNames.Color3f)
                        color_attr.Set(Gf.Vec3f(color[0], color[1], color[2]))
                        return True
                    except Exception as e:
                        print(f"创建颜色属性失败: {str(e)}")
            except Exception as e:
                print(f"设置太阳光颜色时出错: {e}")
        return False
    
    def get_sun_properties(self):
        """获取太阳光属性"""
        if not self.path:
            return {}
            
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self.path)
        
        if not prim:
            return {}
        
        properties = {}
        try:
            intensity_attr = prim.GetAttribute("intensity")
            if intensity_attr and intensity_attr.HasAuthoredValue():
                properties["intensity"] = intensity_attr.Get()
            else:
                properties["intensity"] = 3000.0
            
            temp_attr = prim.GetAttribute("colorTemperature")
            if temp_attr and temp_attr.HasAuthoredValue():
                properties["colorTemperature"] = temp_attr.Get()
            else:
                properties["colorTemperature"] = 6500.0
            
            exposure_attr = prim.GetAttribute("exposure")
            if exposure_attr and exposure_attr.HasAuthoredValue():
                properties["exposure"] = exposure_attr.Get()
            else:
                properties["exposure"] = 0.0
            
            angle_attr = prim.GetAttribute("angle")
            if angle_attr and angle_attr.HasAuthoredValue():
                properties["angle"] = angle_attr.Get()
            else:
                properties["angle"] = 1.0
            
            color_attr = prim.GetAttribute("color")
            if color_attr and color_attr.HasAuthoredValue():
                color_value = color_attr.Get()
                properties["color"] = [color_value[0], color_value[1], color_value[2]]
            else:
                properties["color"] = [1.0, 1.0, 1.0]
                
        except Exception as e:
            print(f"获取太阳光属性时出错: {e}")
        
        return properties