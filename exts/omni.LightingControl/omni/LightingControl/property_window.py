import asyncio
import time
from functools import partial
from typing import List, Optional
from datetime import datetime

import omni.ui as ui
import omni.kit.commands
import omni.usd
from pxr import Sdf

from .sunpath import SunpathData, SunlightManipulator
from .material_manager import MaterialManager
from .light_manager import LightManager
from .ui_components import (
    main_window_style, ColorWidget, CustomCollsableFrame, 
    build_collapsable_header, _get_search_glyph,
    cl_text_gray, cl_text, cls_button_gradient,
    cl_attribute_red, build_gradient_image
)


class PropertyWindowExample(ui.Window):

    def __init__(self, title: str, delegate=None, **kwargs):
        self.__label_width = 120
        self.light_manager = LightManager()
        
        # 状态变量
        self.color_temperature_enabled = True
        self.current_color = [1.0, 1.0, 1.0]
        self.current_intensity = 15000
        self.current_exposure = 1.0
        self.current_specular = 1.0
        self.current_temperature = 6500.0
        
        # UI控件引用
        self.room_combobox = None
        self.lighting_combobox = None
        self.path_field = None
        self.room_combobox_model = None
        self.lighting_combobox_model = None
        self.color_widget = None
        self.temperature_checkbox_image = None
        
        # 滑块引用
        self.intensity_slider = None
        self.exposure_slider = None
        self.specular_slider = None
        self.temperature_slider = None

        # 输入框引用
        self.intensity_field = None
        self.exposure_field = None
        self.specular_field = None
        self.temperature_field = None

        # 状态标签
        self.group_status_label = None
        self.selection_count_label = None

        # 重置按钮引用
        self.top_reset_button = None

        # 选项列表存储
        self.current_room_options = []
        self.current_lighting_options = []
        
        # 默认值相关状态和控件引用
        self.has_recorded_defaults = False
        self.record_defaults_button = None
        self.reset_to_defaults_button = None

        # 太阳路径相关
        self.sunpath_data = SunpathData(172, 12, 0, 112.94, 28.12)
        self.sunlight_manipulator = SunlightManipulator(self.sunpath_data)
        
        # 太阳路径UI控件引用
        self.sun_light_combobox = None
        self.sun_info_label = None
        self.sun_status_label = None
        
        # 太阳属性控件
        self.sun_intensity_slider = None
        self.sun_temperature_slider = None
        self.sun_exposure_slider = None
        self.sun_angle_slider = None
        self.sun_color_widget = None

        # 刷新相关状态
        self._last_refresh_time = 0
        self.sun_light_refresh_button = None
        self._refreshing_sun_lights = False

        # 日期时间选择器字段引用
        self.year_field = None
        self.month_field = None
        self.day_field = None
        self.hour_field = None
        self.minute_field = None
        self.second_field = None

        # 材质管理相关
        self.material_manager = MaterialManager()
        self.material_checkboxes = {}  # 存储材质复选框引用

        super().__init__(title, **kwargs)

        self.frame.style = main_window_style
        self.frame.set_build_fn(self._build_fn)

    def destroy(self):
        """销毁窗口及其所有子控件"""
        self.material_checkboxes.clear()
        super().destroy()

    @property
    def label_width(self):
        """属性标签的宽度"""
        return self.__label_width

    @label_width.setter
    def label_width(self, value):
        """设置属性标签的宽度"""
        self.__label_width = value
        self.frame.rebuild()

    def _on_search_clicked(self):
        """搜索按钮点击事件"""
        try:
            search_path = self.path_field.model.get_value_as_string() if self.path_field else "/World/lights/"
            
            if not self.light_manager.check_path_exists(search_path):
                self._show_warning_message(f"路径 '{search_path}' 不存在")
                return
            
            room_names = self.light_manager.get_room_names(search_path)
            
            if not room_names:
                self._show_warning_message(f"路径 '{search_path}' 下没有找到房间")
                return
            
            self._update_room_combobox(room_names)
            
            if room_names:
                self._on_room_selected(room_names[0])
            
            self._show_success_message(f"找到 {len(room_names)} 个房间")
            
        except Exception as e:
            self._show_error_message(f"搜索时发生错误: {str(e)}")

    def _show_warning_message(self, message):
        """显示警告消息"""
        print(f"警告: {message}")
        if self.group_status_label:
            self.group_status_label.text = message

    def _show_success_message(self, message):
        """显示成功消息"""
        print(f"成功: {message}")
        if self.group_status_label:
            self.group_status_label.text = message

    def _show_error_message(self, message):
        """显示错误消息"""
        print(f"错误: {message}")
        if self.group_status_label:
            self.group_status_label.text = message

    def _show_sun_success_message(self, message):
        """显示太阳路径成功消息"""
        print(f"太阳路径成功: {message}")
        if hasattr(self, 'sun_status_label') and self.sun_status_label:
            self.sun_status_label.text = message

    def _show_sun_error_message(self, message):
        """显示太阳路径错误消息"""
        print(f"太阳路径错误: {message}")
        if hasattr(self, 'sun_status_label') and self.sun_status_label:
            self.sun_status_label.text = message

    def _show_sun_warning_message(self, message):
        """显示太阳路径警告消息"""
        print(f"太阳路径警告: {message}")
        if hasattr(self, 'sun_status_label') and self.sun_status_label:
            self.sun_status_label.text = message

    def _update_room_combobox(self, room_names):
        """更新房间下拉框选项"""
        if not self.room_combobox or not self.room_combobox_model:
            return
            
        self.current_room_options = room_names.copy()
        
        children = self.room_combobox_model.get_item_children()
        for i in range(len(children) - 1, -1, -1):
            self.room_combobox_model.remove_item(children[i])
        
        for name in room_names:
            self.room_combobox_model.append_child_item(None, ui.SimpleStringModel(name))
        
        if room_names:
            self.room_combobox.model.get_item_value_model().set_value(0)

    def _update_lighting_combobox(self, lighting_names):
        """更新灯光下拉框选项"""
        if not self.lighting_combobox or not self.lighting_combobox_model:
            return
            
        self.current_lighting_options = lighting_names.copy()
        
        children = self.lighting_combobox_model.get_item_children()
        for i in range(len(children) - 1, -1, -1):
            self.lighting_combobox_model.remove_item(children[i])
        
        for name in lighting_names:
            self.lighting_combobox_model.append_child_item(None, ui.SimpleStringModel(name))
        
        if lighting_names:
            self.lighting_combobox.model.get_item_value_model().set_value(0)

    def _on_room_selected(self, room_name):
        """房间选择回调"""
        try:
            self.light_manager.current_room = room_name
            
            lights_path = self.path_field.model.get_value_as_string() if self.path_field else "/World/lights/"
            room_path = f"{lights_path.rstrip('/')}/{room_name}"
            
            lighting_names = self.light_manager.get_lighting_names(room_path)
            
            if not lighting_names:
                self._show_warning_message(f"房间 '{room_name}' 中没有找到灯光组")
                self._update_lighting_combobox([])
                self.light_manager.selected_lights = []
                self._reset_ui_to_defaults()
                self._update_defaults_buttons_state()
                return
            
            self._update_lighting_combobox(lighting_names)
            
            if lighting_names:
                self._on_lighting_selected(lighting_names[0])
            
        except Exception as e:
            self._show_error_message(f"选择房间时发生错误: {str(e)}")

    def _on_lighting_selected(self, lighting_name):
        """灯光组选择回调"""
        try:
            self.light_manager.current_lighting = lighting_name
            
            lights_path = self.path_field.model.get_value_as_string() if self.path_field else "/World/lights/"
            room_path = f"{lights_path.rstrip('/')}/{self.light_manager.current_room}"
            lighting_path = f"{room_path}/{lighting_name}"
            
            lights = self.light_manager.get_lights_in_lighting_group(lighting_path)
            
            if not lights:
                self._show_warning_message(f"灯光组 '{lighting_name}' 中没有找到灯光")
                self.light_manager.selected_lights = []
                self._reset_ui_to_defaults()
                self._update_defaults_buttons_state()
                return
            
            self.light_manager.selected_lights = lights
            
            self._on_record_defaults()
            
            if lights:
                self._update_ui_with_light_properties(lights[0])
            
            if self.selection_count_label:
                self.selection_count_label.text = f"Selected: {len(lights)} lights"
            
            self._update_defaults_buttons_state()
            
        except Exception as e:
            self._show_error_message(f"选择灯光组时发生错误: {str(e)}")

    def _update_ui_with_light_properties(self, light_prim):
        """使用灯光属性更新UI"""
        try:
            if not light_prim:
                self._reset_ui_to_defaults()
                return
                
            color = self.light_manager.get_light_color(light_prim)
            intensity = self.light_manager.get_light_intensity(light_prim)
            exposure = self.light_manager.get_light_exposure(light_prim)
            temperature = self.light_manager.get_light_color_temperature(light_prim)
            temp_enabled = self.light_manager.is_color_temperature_enabled(light_prim)
            specular = self.light_manager.get_light_specular(light_prim)
            
            self.current_color = color
            self.current_intensity = intensity
            self.current_exposure = exposure
            self.current_temperature = temperature
            self.color_temperature_enabled = temp_enabled
            self.current_specular = specular
            
            async def update_ui_async():
                await asyncio.sleep(0.1)
                if self.color_widget:
                    self.color_widget.set_color(color)
                
                if self.intensity_slider:
                    self.intensity_slider.model.set_value(intensity)
                if self.intensity_field:
                    self.intensity_field.model.set_value(intensity)
                
                if self.exposure_slider:
                    self.exposure_slider.model.set_value(exposure)
                if self.exposure_field:
                    self.exposure_field.model.set_value(exposure)
                
                if self.temperature_slider:
                    self.temperature_slider.model.set_value(temperature)
                if self.temperature_field:
                    self.temperature_field.model.set_value(temperature)
                
                if self.specular_slider:
                    self.specular_slider.model.set_value(specular)
                if self.specular_field:
                    self.specular_field.model.set_value(specular)
                
                if self.temperature_checkbox_image:
                    self.temperature_checkbox_image.name = "checked" if temp_enabled else "unchecked"
            
            asyncio.ensure_future(update_ui_async())
            
        except Exception as e:
            self._show_error_message(f"更新UI属性时发生错误: {str(e)}")

    def _reset_ui_to_defaults(self):
        """重置UI到默认值"""
        self.current_color = [1.0, 1.0, 1.0]
        self.current_intensity = 15000
        self.current_exposure = 1.0
        self.current_specular = 1.0
        self.current_temperature = 6500.0
        self.color_temperature_enabled = True
        
        if self.color_widget:
            self.color_widget.set_color(self.current_color)
        if self.intensity_slider:
            self.intensity_slider.model.set_value(self.current_intensity)
        if self.intensity_field:
            self.intensity_field.model.set_value(self.current_intensity)
        if self.exposure_slider:
            self.exposure_slider.model.set_value(self.current_exposure)
        if self.exposure_field:
            self.exposure_field.model.set_value(self.current_exposure)
        if self.temperature_slider:
            self.temperature_slider.model.set_value(self.current_temperature)
        if self.temperature_field:
            self.temperature_field.model.set_value(self.current_temperature)
        if self.specular_slider:
            self.specular_slider.model.set_value(self.current_specular)
        if self.specular_field:
            self.specular_field.model.set_value(self.current_specular)
        if self.temperature_checkbox_image:
            self.temperature_checkbox_image.name = "checked"

    def _on_color_changed(self, color):
        """颜色改变回调"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_light_color(light_prim, color)
        except Exception as e:
            self._show_error_message(f"设置颜色时发生错误: {str(e)}")

    def _on_intensity_changed(self, intensity):
        """强度改变回调"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_light_intensity(light_prim, intensity)
        except Exception as e:
            self._show_error_message(f"设置强度时发生错误: {str(e)}")

    def _on_exposure_changed(self, exposure):
        """曝光改变回调"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_exposure(light_prim, exposure)
        except Exception as e:
            self._show_error_message(f"设置曝光时发生错误: {str(e)}")

    def _on_specular_changed(self, specular):
        """高光改变回调"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_specular(light_prim, specular)
        except Exception as e:
            self._show_error_message(f"设置高光时发生错误: {str(e)}")

    def _on_temperature_changed(self, temperature):
        """色温改变回调"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_color_temperature(light_prim, temperature)
        except Exception as e:
            self._show_error_message(f"设置色温时发生错误: {str(e)}")

    def _on_temperature_toggled(self, enabled):
        """色温开关回调"""
        try:
            self.color_temperature_enabled = enabled
            
            success_count = 0
            total_lights = len(self.light_manager.selected_lights)
            
            for light_prim in self.light_manager.selected_lights:
                if self.light_manager.enable_color_temperature(light_prim, enabled):
                    success_count += 1
            
            if total_lights > 0:
                if success_count == total_lights:
                    self._show_success_message(f"成功设置 {success_count} 个灯光的色温启用状态")
                else:
                    self._show_warning_message(f"部分设置成功: {success_count}/{total_lights} 个灯光")
            else:
                self._show_warning_message("没有选中的灯光可以设置")
                
        except Exception as e:
            self._show_error_message(f"切换色温时发生错误: {str(e)}")

    def _on_turn_on_lights(self):
        """打开所有灯光"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_light_enabled(light_prim, True)
            self._show_success_message(f"已打开 {len(self.light_manager.selected_lights)} 个灯光")
        except Exception as e:
            self._show_error_message(f"打开灯光时发生错误: {str(e)}")

    def _on_turn_off_lights(self):
        """关闭所有灯光"""
        try:
            for light_prim in self.light_manager.selected_lights:
                self.light_manager.set_light_enabled(light_prim, False)
            self._show_success_message(f"已关闭 {len(self.light_manager.selected_lights)} 个灯光")
        except Exception as e:
            self._show_error_message(f"关闭灯光时发生错误: {str(e)}")

    def _on_reset_all(self):
        """重置所有灯光"""
        try:
            self.light_manager.reset_all_lights()
            self.current_color = [1.0, 1.0, 1.0]
            self.current_intensity = 15000
            self.current_exposure = 1.0
            self.current_specular = 1.0
            self.current_temperature = 6500.0
            self.color_temperature_enabled = True
            
            if self.light_manager.selected_lights:
                self._update_ui_with_light_properties(self.light_manager.selected_lights[0])
            
            self._show_success_message(f"已重置 {len(self.light_manager.selected_lights)} 个灯光")
        except Exception as e:
            self._show_error_message(f"重置灯光时发生错误: {str(e)}")

    def _on_reset_vision_sync(self):
        """重置Vision Sync页面到默认值"""
        try:
            if self.path_field:
                self.path_field.model.set_value("/World/lights/")
            
            if self.room_combobox and self.room_combobox_model:
                children = self.room_combobox_model.get_item_children()
                for i in range(len(children) - 1, -1, -1):
                    self.room_combobox_model.remove_item(children[i])
                self.room_combobox.model.get_item_value_model().set_value(0)
            
            if self.lighting_combobox and self.lighting_combobox_model:
                children = self.lighting_combobox_model.get_item_children()
                for i in range(len(children) - 1, -1, -1):
                    self.lighting_combobox_model.remove_item(children[i])
                self.lighting_combobox.model.get_item_value_model().set_value(0)
            
            self.light_manager.selected_lights = []
            self.light_manager.clear_recorded_defaults()
            self._update_defaults_buttons_state()
            
            if self.group_status_label:
                self.group_status_label.text = "Enter path and click 'Search' to discover lights"
            
            if self.selection_count_label:
                self.selection_count_label.text = "Selected: 0 lights"
            
            self._show_success_message("Vision Sync页面已重置")
        except Exception as e:
            self._show_error_message(f"重置Vision Sync页面时发生错误: {str(e)}")

    def _on_record_defaults(self):
        """记录当前值为默认值"""
        try:
            if not self.light_manager.selected_lights:
                self._show_warning_message("没有选中的灯光，无法记录默认值")
                return
            
            if self.light_manager.record_current_values_as_defaults():
                self.has_recorded_defaults = True
                self._update_defaults_buttons_state()
                self._show_success_message(f"已记录 {len(self.light_manager.selected_lights)} 个灯光的当前值为默认值")
            else:
                self._show_error_message("记录默认值失败")
                
        except Exception as e:
            self._show_error_message(f"记录默认值时发生错误: {str(e)}")

    def _on_reset_to_defaults(self):
        """重置到记录的默认值"""
        try:
            if not self.light_manager.has_recorded_defaults():
                self._show_warning_message("没有记录的默认值，请先记录默认值")
                return
            
            if self.light_manager.reset_to_recorded_defaults():
                if self.light_manager.selected_lights:
                    self._update_ui_with_light_properties(self.light_manager.selected_lights[0])
                self._show_success_message("已重置到记录的默认值")
            else:
                self._show_error_message("重置到默认值失败")
                
        except Exception as e:
            self._show_error_message(f"重置到默认值时发生错误: {str(e)}")

    def _update_defaults_buttons_state(self):
        """更新默认值相关按钮的状态"""
        has_lights = len(self.light_manager.selected_lights) > 0
        has_defaults = self.light_manager.has_recorded_defaults()
        
        if self.record_defaults_button:
            self.record_defaults_button.enabled = has_lights
        
        if self.reset_to_defaults_button:
            self.reset_to_defaults_button.enabled = has_lights and has_defaults

    # ==============================================================================
    # 材质管理相关方法
    # ==============================================================================

    def _build_material_properties(self):
        """构建'材质管理'组的控件"""
        with CustomCollsableFrame("Materials").collapsable_frame:
            with ui.VStack(height=0, spacing=10):
                ui.Spacer(height=10)
                
                with ui.HStack():
                    ui.Spacer(width=30)
                    ui.Label("Material Utilities", name="header_attribute_name")
                
                # 操作按钮
                with ui.HStack(spacing=10, height=35):
                    scan_btn = ui.Button("Scan Unused", name="turn_on_off")
                    scan_btn.set_clicked_fn(self._on_material_scan_clicked)
                    
                    self.delete_selected_btn = ui.Button("Delete Selected", name="turn_on_off")
                    self.delete_selected_btn.set_clicked_fn(self._on_delete_selected_materials)
                    self.delete_selected_btn.visible = False
                    
                    self.delete_all_btn = ui.Button("Delete All", name="turn_on_off")
                    self.delete_all_btn.set_clicked_fn(self._on_delete_all_materials)
                    self.delete_all_btn.visible = False
                    
                    self.material_undo_btn = ui.Button("Undo Last", name="turn_on_off")
                    self.material_undo_btn.set_clicked_fn(self._on_undo_material_delete)
                    self.material_undo_btn.enabled = self.material_manager.has_deletion_history()
                    self.material_undo_btn.visible = False
                
                # 选择操作栏
                self.selection_actions_frame = ui.HStack(spacing=10, height=25)
                with self.selection_actions_frame:
                    self.select_all_btn = ui.Button("Select All", name="turn_on_off", width=80)
                    self.select_all_btn.set_clicked_fn(self._on_select_all_materials)
                    
                    self.clear_selection_btn = ui.Button("Clear Selection", name="turn_on_off", width=100)
                    self.clear_selection_btn.set_clicked_fn(self._on_clear_material_selection)
                    
                    ui.Spacer()
                    
                    # 选中计数标签
                    self.material_selection_count_label = ui.Label("Selected: 0 / 0", width=120,
                                                                  style={"font_size": 10, "color": cl_text_gray})
                self.selection_actions_frame.visible = False
                
                # 材质列表容器
                self.material_list_container = ui.Frame(height=200)
                with self.material_list_container:
                    with ui.ScrollingFrame():
                        self.material_list_widget = ui.VStack(spacing=2)
                        # 初始状态显示提示信息
                        with self.material_list_widget:
                            with ui.HStack():
                                ui.Spacer(width=10)
                                ui.Label("Click 'Scan Unused Materials' to start", 
                                        style={"color": cl_text_gray, "font_size": 12})
                self.material_list_container.visible = False
                
                # 状态栏
                with ui.HStack(height=25):
                    self.material_status_label = ui.Label("Click 'Scan Unused Materials' to start", 
                                                         word_wrap=True, alignment=ui.Alignment.LEFT_CENTER,
                                                         style={"font_size": 11, "color": cl_text_gray})

    def _show_material_controls(self, show=True):
        """显示或隐藏材质控制控件"""
        has_unused_materials = len(self.material_manager.unused_materials) > 0
        
        self.delete_selected_btn.visible = show and has_unused_materials
        self.delete_all_btn.visible = show and has_unused_materials
        self.material_undo_btn.visible = show
        self.selection_actions_frame.visible = show and has_unused_materials
        self.material_list_container.visible = show

    def _update_material_list(self):
        """更新材质列表显示"""
        if not hasattr(self, 'material_list_widget') or not self.material_list_widget:
            return
        
        # 清空复选框引用
        self.material_checkboxes.clear()
        
        # 清空现有列表
        self.material_list_widget.clear()
        
        unused_materials = self.material_manager.unused_materials
        selected_count = self.material_manager.get_selection_count()
        
        # 更新选中计数
        if hasattr(self, 'material_selection_count_label') and self.material_selection_count_label:
            self.material_selection_count_label.text = f"Selected: {selected_count} / {len(unused_materials)}"
        
        # 更新撤销按钮状态
        self._update_undo_button_state()
        
        # 更新按钮显示状态
        self._show_material_controls(True)
        
        # 如果没有未使用的材质，显示提示信息
        if not unused_materials:
            with self.material_list_widget:
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label("No unused materials found", style={"color": cl_text_gray})
            return
        
        # 显示材质列表
        with self.material_list_widget:
            for mat_info in unused_materials:
                self._create_material_item(mat_info)

    def _create_material_item(self, mat_info):
        """创建材质列表项"""
        is_selected = mat_info['path'] in self.material_manager.selected_materials
        can_delete = not mat_info.get('is_ancestral', False)
        
        with ui.HStack(spacing=5, height=25):
            # 创建复选框
            checkbox = ui.CheckBox(width=20)
            checkbox.checked = is_selected
            
            # 确保模型值也同步
            try:
                checkbox.model.set_value(is_selected)
            except:
                pass
            
            # 回调函数
            def on_checkbox_changed(model, path=mat_info['path']):
                selected = model.get_value_as_bool()
                self._on_material_selection_changed(path, selected)
            
            checkbox.model.add_value_changed_fn(on_checkbox_changed)
            
            # 材质名称 - 如果不能删除，用灰色显示
            name_style = {"font_size": 11}
            if not can_delete:
                name_style["color"] = cl_text_gray
            
            ui.Label(mat_info['name'], width=150, alignment=ui.Alignment.LEFT_CENTER,
                    style=name_style)
            
            # 材质路径
            path_style = {"color": cl_text_gray, "font_size": 10}
            if not can_delete:
                path_style["color"] = ui.color("#505050")
            
            ui.Label(str(mat_info['path']), alignment=ui.Alignment.LEFT_CENTER, 
                style=path_style)
            
            # 材质类型
            type_style = {"color": cl_text_gray, "font_size": 10}
            if not can_delete:
                type_style["color"] = ui.color("#505050")
            
            ui.Label(mat_info['type'], width=80, alignment=ui.Alignment.LEFT_CENTER,
                style=type_style)
            
            # 添加状态指示器
            if not can_delete:
                ui.Label("(ancestral)", width=60, alignment=ui.Alignment.LEFT_CENTER,
                    style={"color": cl_attribute_red, "font_size": 9})
            
            # 存储复选框引用以便后续更新
            self.material_checkboxes[mat_info['path']] = checkbox

    def _on_material_selection_changed(self, material_path, selected):
        """材质选中状态改变回调"""
        self.material_manager.toggle_material_selection(material_path, selected)
        self._update_material_selection_count()
        
        # 立即更新对应的复选框状态
        if material_path in self.material_checkboxes:
            checkbox = self.material_checkboxes[material_path]
            checkbox.checked = selected
            try:
                checkbox.model.set_value(selected)
            except:
                pass

    def _update_material_selection_count(self):
        """更新材质选中计数显示"""
        if hasattr(self, 'material_selection_count_label') and self.material_selection_count_label:
            selected_count = self.material_manager.get_selection_count()
            deletable_count = self.material_manager.get_deletable_count()
            total_count = self.material_manager.get_unused_count()
            self.material_selection_count_label.text = f"Selected: {selected_count} / {deletable_count} deletable of {total_count} total"

    def _on_material_scan_clicked(self):
        """材质扫描按钮点击事件"""
        try:
            unused_materials = self.material_manager.scan_unused_materials()
            
            # 显示其他控件
            self._show_material_controls(True)
            
            # 更新材质列表
            self._update_material_list()
            
            deletable_count = self.material_manager.get_deletable_count()
            total_count = len(unused_materials)
            
            if total_count > 0:
                if deletable_count > 0:
                    self._update_material_status(f"Found {total_count} unused materials ({deletable_count} deletable)")
                else:
                    self._update_material_status(f"Found {total_count} unused materials (all are ancestral, cannot delete)")
            else:
                self._update_material_status("No unused materials found")
                
        except Exception as e:
            self._update_material_status(f"Scan error: {str(e)}")

    def _on_delete_selected_materials(self):
        """删除选中材质按钮点击事件"""
        selected_count = self.material_manager.get_selection_count()
        if selected_count == 0:
            self._update_material_status("Please select materials to delete")
            return
        
        try:
            deleted_count, deleted_names, error_msg = self.material_manager.delete_selected_materials()
            self._update_material_list()
            self._update_undo_button_state()
            self._update_material_status(f"Deleted {deleted_count} materials: {', '.join(deleted_names[:3])}" + 
                                    ("..." if len(deleted_names) > 3 else "") + error_msg)
        except Exception as e:
            self._update_material_status(f"Delete error: {str(e)}")

    def _on_delete_all_materials(self):
        """删除所有材质按钮点击事件"""
        unused_count = self.material_manager.get_unused_count()
        if unused_count == 0:
            self._update_material_status("No unused materials to delete")
            return
        
        try:
            deleted_count, deleted_names, error_msg = self.material_manager.delete_all_unused_materials()
            self._update_material_list()
            self._update_undo_button_state()
            self._update_material_status(f"Deleted all {deleted_count} unused materials" + error_msg)
        except Exception as e:
            self._update_material_status(f"Delete all error: {str(e)}")

    def _on_undo_material_delete(self):
        """撤销材质删除按钮点击事件"""
        try:
            success, message = self.material_manager.undo_last_delete()
            self._update_material_status(message)
            
            if success:
                # 重新扫描以更新列表
                self.material_manager.scan_unused_materials()
                self._update_material_list()
                self._update_undo_button_state()
            
        except Exception as e:
            self._update_material_status(f"Undo error: {str(e)}")

    def _on_select_all_materials(self):
        """全选材质按钮点击事件"""
        self.material_manager.select_all_materials()
        # 更新所有复选框状态
        for path, checkbox in self.material_checkboxes.items():
            if path in self.material_manager.selected_materials:
                checkbox.checked = True
                try:
                    checkbox.model.set_value(True)
                except:
                    pass
        self._update_material_selection_count()
        self._update_material_status("Selected all materials")

    def _on_clear_material_selection(self):
        """清空材质选择按钮点击事件"""
        self.material_manager.clear_selection()
        # 更新所有复选框状态
        for checkbox in self.material_checkboxes.values():
            checkbox.checked = False
            try:
                checkbox.model.set_value(False)
            except:
                pass
        self._update_material_selection_count()
        self._update_material_status("Selection cleared")

    def _update_material_status(self, message):
        """更新材质状态栏消息"""
        if hasattr(self, 'material_status_label') and self.material_status_label:
            self.material_status_label.text = message
        print(f"Material Manager: {message}")

    def _update_undo_button_state(self):
        """更新撤销按钮状态"""
        if hasattr(self, 'material_undo_btn') and self.material_undo_btn:
            self.material_undo_btn.enabled = self.material_manager.has_deletion_history()

    # ==============================================================================
    # 太阳路径相关方法
    # ==============================================================================
    
    async def _refresh_sun_light_combobox_async(self):
        """异步刷新太阳光下拉框"""
        try:
            if self._refreshing_sun_lights:
                return
                
            self._refreshing_sun_lights = True
            
            if hasattr(self, 'sun_light_combobox'):
                self.sun_light_combobox.enabled = False
            
            def get_distant_lights():
                try:
                    return self.sunlight_manipulator.get_all_distant_lights()
                except Exception as e:
                    print(f"获取远光灯列表失败: {e}")
                    return []
            
            distant_lights = await asyncio.get_event_loop().run_in_executor(
                None, get_distant_lights
            )
            
            await omni.kit.app.get_app().next_update_async()
            
            options = ["Select DistantLight"] + distant_lights
            
            if self.sun_light_combobox and hasattr(self, 'sun_light_combobox_model'):
                children = self.sun_light_combobox_model.get_item_children()
                for i in range(len(children) - 1, -1, -1):
                    self.sun_light_combobox_model.remove_item(children[i])
                
                for option in options:
                    self.sun_light_combobox_model.append_child_item(None, ui.SimpleStringModel(option))
                
                current_path = self.sunlight_manipulator.path
                if current_path and current_path in options:
                    try:
                        index = options.index(current_path)
                        self.sun_light_combobox.model.get_item_value_model().set_value(index)
                    except ValueError:
                        self.sun_light_combobox.model.get_item_value_model().set_value(0)
                else:
                    self.sun_light_combobox.model.get_item_value_model().set_value(0)
            
            self._show_sun_success_message(f"太阳光列表已刷新，找到 {len(distant_lights)} 个远光灯")
            
        except Exception as e:
            self._show_sun_error_message(f"刷新太阳光列表时发生错误: {str(e)}")
        finally:
            if hasattr(self, 'sun_light_combobox'):
                self.sun_light_combobox.enabled = True
            self._refreshing_sun_lights = False

    def _refresh_sun_light_combobox(self):
        """同步包装方法"""
        asyncio.ensure_future(self._refresh_sun_light_combobox_async())
    
    def _on_sun_light_refresh_clicked(self, x, y, button, modifier):
        """太阳光刷新按钮点击事件"""
        current_time = time.time()
        
        if current_time - self._last_refresh_time < 1.0:
            return
        
        self._last_refresh_time = current_time
        
        if self.sun_light_refresh_button:
            original_name = self.sun_light_refresh_button.name
            self.sun_light_refresh_button.name = "on_off"
        
        self._show_sun_success_message("正在刷新太阳光列表...")
        
        try:
            self._refresh_sun_light_combobox()
        except Exception as e:
            self._show_sun_error_message(f"刷新失败: {str(e)}")
        
        async def restore_button_style():
            await asyncio.sleep(0.5)
            if self.sun_light_refresh_button:
                self.sun_light_refresh_button.name = "reset"
        
        asyncio.ensure_future(restore_button_style())
    
    def _on_sun_light_selected(self, light_path):
        """太阳光选择回调"""
        try:
            if not light_path or light_path == "Select DistantLight":
                self.sunlight_manipulator.path = None
                return
                
            self.sunlight_manipulator.set_selected_light(light_path)
            self.sunlight_manipulator.change_sun()
            self._update_sun_properties_ui()
                
            self._show_sun_success_message(f"已选择太阳光: {light_path}")
            
        except Exception as e:
            self._show_sun_error_message(f"选择太阳光时发生错误: {str(e)}")
    
    def _on_datetime_changed(self, model=None):
        """日期时间改变回调"""
        try:
            year = self.year_field.model.get_value_as_int()
            month = self.month_field.model.get_value_as_int()
            day = self.day_field.model.get_value_as_int()
            hour = self.hour_field.model.get_value_as_int()
            minute = self.minute_field.model.get_value_as_int()
            second = self.second_field.model.get_value_as_int()
            
            try:
                selected_date = datetime(year, month, day, hour, minute, second)
            except ValueError:
                now = datetime.now()
                self.year_field.model.set_value(now.year)
                self.month_field.model.set_value(now.month)
                self.day_field.model.set_value(now.day)
                self._show_sun_warning_message("无效的日期时间，已恢复为当前时间")
                return
            
            day_of_year = selected_date.timetuple().tm_yday
            self.sunpath_data.set_date(day_of_year)
            self.sunpath_data.set_hour(hour)
            self.sunpath_data.set_min(minute)
            
            self.sunlight_manipulator.change_sun()
            self._update_sun_info()
            
        except Exception as e:
            self._show_sun_error_message(f"设置日期时间时发生错误: {str(e)}")

    def _set_to_current_time(self):
        """设置为当前时间"""
        now = datetime.now()
        self.year_field.model.set_value(now.year)
        self.month_field.model.set_value(now.month)
        self.day_field.model.set_value(now.day)
        self.hour_field.model.set_value(now.hour)
        self.minute_field.model.set_value(now.minute)
        self.second_field.model.set_value(now.second)
        self._on_datetime_changed()
        self._show_sun_success_message("已设置为当前时间")

    def _set_to_sunrise_time(self):
        """设置为日出时间"""
        try:
            sunrise_time = self.sunpath_data.get_sunrise_time()
            year = self.year_field.model.get_value_as_int()
            month = self.month_field.model.get_value_as_int()
            day = self.day_field.model.get_value_as_int()
            
            self.hour_field.model.set_value(sunrise_time.hour)
            self.minute_field.model.set_value(sunrise_time.minute)
            self.second_field.model.set_value(sunrise_time.second)
            self._on_datetime_changed()
            
            self._show_sun_success_message("已设置为日出时间")
        except Exception as e:
            self._show_sun_error_message(f"设置日出时间时发生错误: {str(e)}")

    def _set_to_sunset_time(self):
        """设置为日落时间"""
        try:
            sunset_time = self.sunpath_data.get_sunset_time()
            year = self.year_field.model.get_value_as_int()
            month = self.month_field.model.get_value_as_int()
            day = self.day_field.model.get_value_as_int()
            
            self.hour_field.model.set_value(sunset_time.hour)
            self.minute_field.model.set_value(sunset_time.minute)
            self.second_field.model.set_value(sunset_time.second)
            self._on_datetime_changed()
            
            self._show_sun_success_message("已设置为日落时间")
        except Exception as e:
            self._show_sun_error_message(f"设置日落时间时发生错误: {str(e)}")
    
    def _on_longitude_changed(self, longitude_value):
        """经度改变回调"""
        try:
            self.sunpath_data.set_longitude(longitude_value)
            self.sunlight_manipulator.change_sun()
            self._update_sun_info()
            self._show_sun_success_message(f"经度已设置为: {longitude_value}")
        except Exception as e:
            self._show_sun_error_message(f"设置经度时发生错误: {str(e)}")
    
    def _on_latitude_changed(self, latitude_value):
        """纬度改变回调"""
        try:
            self.sunpath_data.set_latitude(latitude_value)
            self.sunlight_manipulator.change_sun()
            self._update_sun_info()
            self._show_sun_success_message(f"纬度已设置为: {latitude_value}")
        except Exception as e:
            self._show_sun_error_message(f"设置纬度时发生错误: {str(e)}")
    
    def _on_sun_intensity_changed(self, intensity):
        """太阳强度改变回调"""
        try:
            self.sunlight_manipulator.set_sun_intensity(intensity)
            self._show_sun_success_message(f"太阳强度已设置为: {intensity}")
        except Exception as e:
            self._show_sun_error_message(f"设置太阳强度时发生错误: {str(e)}")
    
    def _on_sun_temperature_changed(self, temperature):
        """太阳色温改变回调"""
        try:
            self.sunlight_manipulator.set_sun_color_temperature(temperature)
            self._show_sun_success_message(f"太阳色温已设置为: {temperature}")
        except Exception as e:
            self._show_sun_error_message(f"设置太阳色温时发生错误: {str(e)}")
    
    def _on_sun_exposure_changed(self, exposure):
        """太阳曝光改变回调"""
        try:
            self.sunlight_manipulator.set_sun_exposure(exposure)
            self._show_sun_success_message(f"太阳曝光已设置为: {exposure}")
        except Exception as e:
            self._show_sun_error_message(f"设置太阳曝光时发生错误: {str(e)}")
    
    def _on_sun_angle_changed(self, angle):
        """太阳角度改变回调"""
        try:
            self.sunlight_manipulator.set_sun_angle(angle)
            self._show_sun_success_message(f"太阳角度已设置为: {angle}")
        except Exception as e:
            self._show_sun_error_message(f"设置太阳角度时发生错误: {str(e)}")
    
    def _on_sun_color_changed(self, color):
        """太阳颜色改变回调"""
        try:
            if self.sunlight_manipulator.set_sun_color(color):
                self._show_sun_success_message(f"太阳颜色已设置为: {color}")
            else:
                self._show_sun_warning_message("设置太阳颜色失败，请检查太阳光是否存在")
        except Exception as e:
            self._show_sun_error_message(f"设置太阳颜色时发生错误: {str(e)}")
    
    def _hide_sun(self):
        """隐藏太阳"""
        try:
            if not self.sunlight_manipulator.path:
                self._show_sun_warning_message("请先选择太阳光")
                return
                
            self.sunlight_manipulator.hide_sun()
            self._show_sun_success_message("太阳已隐藏")
            
        except Exception as e:
            self._show_sun_error_message(f"隐藏太阳时发生错误: {str(e)}")
    
    def _show_sun(self):
        """显示太阳"""
        try:
            if not self.sunlight_manipulator.path:
                self._show_sun_warning_message("请先选择太阳光")
                return
                
            self.sunlight_manipulator.show_sun()
            self._show_sun_success_message("太阳已显示")
            
        except Exception as e:
            self._show_sun_error_message(f"显示太阳时发生错误: {str(e)}")
    
    def _update_sun_info(self):
        """更新太阳信息显示"""
        try:
            if self.sun_info_label:
                sunrise_time = self.sunpath_data.get_sunrise_time()
                sunset_time = self.sunpath_data.get_sunset_time()
                current_time = self.sunpath_data.get_cur_time()
                
                year = self.year_field.model.get_value_as_int()
                month = self.month_field.model.get_value_as_int()
                day = self.day_field.model.get_value_as_int()
                hour = self.hour_field.model.get_value_as_int()
                minute = self.minute_field.model.get_value_as_int()
                
                selected_datetime = datetime(year, month, day, hour, minute)
                
                info_text = f"选择的日期时间: {selected_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                info_text += f"日出时间: {sunrise_time.strftime('%H:%M:%S')}  日落时间: {sunset_time.strftime('%H:%M:%S')}\n"
                info_text += f"当前太阳位置计算时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.sun_info_label.text = info_text
        except Exception as e:
            print(f"更新太阳信息时发生错误: {str(e)}")
    
    def _update_sun_properties_ui(self):
        """更新太阳属性UI"""
        try:
            properties = self.sunlight_manipulator.get_sun_properties()
            
            if properties:
                if self.sun_intensity_slider and "intensity" in properties:
                    self.sun_intensity_slider.model.set_value(properties["intensity"])
                
                if self.sun_temperature_slider and "colorTemperature" in properties:
                    self.sun_temperature_slider.model.set_value(properties["colorTemperature"])
                
                if self.sun_exposure_slider and "exposure" in properties:
                    self.sun_exposure_slider.model.set_value(properties["exposure"])
                
                if self.sun_angle_slider and "angle" in properties:
                    self.sun_angle_slider.model.set_value(properties["angle"])
                
                if self.sun_color_widget and "color" in properties:
                    self.sun_color_widget.set_color(properties["color"])
                    
        except Exception as e:
            print(f"更新太阳属性UI时发生错误: {str(e)}")

    def _build_light_properties(self):
        """构建'灯光属性'组的控件"""
        with CustomCollsableFrame("Light").collapsable_frame:
            with ui.VStack(height=0, spacing=10):
                ui.Spacer(height=10)
                
                with ui.HStack():
                    ui.Spacer(width=10)
                    self.group_status_label = ui.Label("Enter path and click 'Search' to discover lights", 
                                                     word_wrap=True, alignment=ui.Alignment.LEFT,
                                                     style={"font_size": 11, "color": cl_text_gray})
                
                with ui.HStack(spacing=10, height=35):
                    self.record_defaults_button = ui.Button("Record Defaults", name="turn_on_off")
                    self.record_defaults_button.set_clicked_fn(self._on_record_defaults)
                    
                    self.reset_to_defaults_button = ui.Button("Reset to Defaults", name="reset_button")
                    self.reset_to_defaults_button.set_clicked_fn(self._on_reset_to_defaults)
                    self.reset_to_defaults_button.enabled = False
                
                self._build_color_temperature()

                # 使用统一的带输入框滑块构建方法
                self._build_gradient_float_slider_with_input("Exposure", "exposure", 0, -5, 5)
                self._build_gradient_float_slider_with_input("Intensity", "intensity", 15000, 0, 100000)
                self._build_gradient_float_slider_with_input("Specular", "specular", 1.0, 0, 2)

                with ui.VStack(spacing=10):
                    with ui.HStack(spacing=10, height=35):
                        turn_on_btn = ui.Button("Turn On", name="turn_on_off")
                        turn_on_btn.set_clicked_fn(self._on_turn_on_lights)
                        
                        turn_off_btn = ui.Button("Turn Off", name="turn_on_off")
                        turn_off_btn.set_clicked_fn(self._on_turn_off_lights)

                        reset_btn = ui.Button("Reset all", name="reset_button")
                        reset_btn.set_clicked_fn(self._on_reset_all)

                    with ui.HStack():
                        ui.Spacer(width=10)
                        self.selection_count_label = ui.Label("Selected: 0 lights", 
                                                            style={"font_size": 10, "color": cl_text_gray})
    
    def _build_sun_path_properties(self):
        """构建'太阳路径'组的控件"""
        with CustomCollsableFrame("SunPath").collapsable_frame:
            with ui.VStack(height=0, spacing=10):
                ui.Spacer(height=10)
                
                # 太阳路径状态标签
                with ui.HStack():
                    ui.Spacer(width=10)
                    self.sun_status_label = ui.Label("Please click refresh button to update sun lights list", word_wrap=True, alignment=ui.Alignment.LEFT,
                                                   style={"font_size": 11, "color": cl_text_gray})
                
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label("Sun Light", name="attribute_name", width=self.label_width)
                    with ui.HStack(width=ui.Fraction(1)):
                        self._build_sun_light_combobox()
                
                self._build_datetime_selector()
                
                self._build_gradient_float_slider_with_input("Longitude", "longitude", 118.1868, -180, 180)
                self._build_gradient_float_slider_with_input("Latitude", "latitude", 24.485408, -90, 90)
                
                ui.Spacer(height=5)
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label("Sun Properties", name="header_attribute_name")
                
                self._build_gradient_float_slider_with_input("Intensity", "sun_intensity", 1, -10, 100)
                self._build_gradient_float_slider_with_input("Color Temperature", "sun_temperature", 7250, 100, 15000)
                self._build_gradient_float_slider_with_input("Exposure", "sun_exposure", 10, -10, 50)
                self._build_gradient_float_slider_with_input("Angle", "sun_angle", 1, 0, 50)
                
                # 太阳控制按钮
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label("Sun Control", name="attribute_name", width=self.label_width)
                    with ui.HStack(width=ui.Fraction(1), spacing=5):
                        hide_sun_btn = ui.Button("Hide Sun", name="turn_on_off", width=80)
                        hide_sun_btn.set_clicked_fn(self._hide_sun)
                        
                        show_sun_btn = ui.Button("Show Sun", name="turn_on_off", width=80)
                        show_sun_btn.set_clicked_fn(self._show_sun)
                
                with ui.HStack():
                    ui.Spacer(width=10)
                    self.sun_info_label = ui.Label("", word_wrap=True, alignment=ui.Alignment.LEFT,
                                                 style={"font_size": 11, "color": cl_text_gray})
                    self._update_sun_info()

    def _build_datetime_selector(self):
        """构建日期时间选择器"""
        now = datetime.now()
        
        with ui.VStack(spacing=5):
            with ui.HStack():
                ui.Spacer(width=75)
                
                with ui.HStack():
                    ui.Label("Year:", name="attribute_name", width=60)
                    self.year_field = ui.IntField(
                        min=2000, 
                        max=2100,
                        height=0,
                        width=70,
                        style={"color": cl_text}
                    )
                    self.year_field.model.set_value(now.year)
                    self.year_field.model.add_value_changed_fn(self._on_datetime_changed)
                
                with ui.HStack():
                    ui.Label("Month:", name="attribute_name", width=60)
                    self.month_field = ui.IntField(
                        min=1, 
                        max=12,
                        height=0,
                        width=50,
                        style={"color": cl_text}
                    )
                    self.month_field.model.set_value(now.month)
                    self.month_field.model.add_value_changed_fn(self._on_datetime_changed)
                
                with ui.HStack():
                    ui.Label("Day:", name="attribute_name", width=40)
                    self.day_field = ui.IntField(
                        min=1, 
                        max=31,
                        height=0,
                        width=50,
                        style={"color": cl_text}
                    )
                    self.day_field.model.set_value(now.day)
                    self.day_field.model.add_value_changed_fn(self._on_datetime_changed)
            
            with ui.HStack():
                ui.Spacer(width=75)
                
                with ui.HStack():
                    ui.Label("Hour:", name="attribute_name", width=60)
                    self.hour_field = ui.IntField(
                        min=0, 
                        max=23,
                        height=0,
                        width=50,
                        style={"color": cl_text}
                    )
                    self.hour_field.model.set_value(now.hour)
                    self.hour_field.model.add_value_changed_fn(self._on_datetime_changed)
                
                with ui.HStack():
                    ui.Label("Minute:", name="attribute_name", width=60)
                    self.minute_field = ui.IntField(
                        min=0, 
                        max=59,
                        height=0,
                        width=50,
                        style={"color": cl_text}
                    )
                    self.minute_field.model.set_value(now.minute)
                    self.minute_field.model.add_value_changed_fn(self._on_datetime_changed)
                
                with ui.HStack():
                    ui.Label("Second:", name="attribute_name", width=60)
                    self.second_field = ui.IntField(
                        min=0, 
                        max=59,
                        height=0,
                        width=50,
                        style={"color": cl_text}
                    )
                    self.second_field.model.set_value(now.second)
                    self.second_field.model.add_value_changed_fn(self._on_datetime_changed)
            
            with ui.HStack():
                ui.Spacer(width=10)
                ui.Label("Quick Set", name="attribute_name", width=self.label_width)
                with ui.HStack(spacing=5):
                    now_btn = ui.Button("Now", name="turn_on_off", width=60)
                    now_btn.set_clicked_fn(self._set_to_current_time)
                    
                    sunrise_btn = ui.Button("Sunrise", name="turn_on_off", width=60)
                    sunrise_btn.set_clicked_fn(self._set_to_sunrise_time)
                    
                    sunset_btn = ui.Button("Sunset", name="turn_on_off", width=60)
                    sunset_btn.set_clicked_fn(self._set_to_sunset_time)

    def _build_sun_light_combobox(self):
        """构建太阳光下拉框"""
        try:
            distant_lights = self.sunlight_manipulator.get_all_distant_lights()
            options = ["Select DistantLight"] + distant_lights
            
            with ui.HStack(width=ui.Fraction(1)):
                with ui.ZStack(width=ui.Fraction(1)):
                    ui.Image(name="combobox", fill_policy=ui.FillPolicy.STRETCH, height=35)
                    with ui.HStack():
                        ui.Spacer(width=6)
                        with ui.VStack(width=ui.Fraction(1)):
                            ui.Spacer(height=10)
                            self.sun_light_combobox = ui.ComboBox(0, *options, name="dropdown_menu")
                            self.sun_light_combobox_model = self.sun_light_combobox.model
                            
                            def on_sun_light_changed(model, item):
                                try:
                                    index = model.get_item_value_model().get_value_as_int()
                                    if 0 <= index < len(options):
                                        selected_option = options[index]
                                        self._on_sun_light_selected(selected_option)
                                except Exception as e:
                                    print(f"太阳光选择回调错误: {e}")
                            
                            self.sun_light_combobox.model.add_item_changed_fn(on_sun_light_changed)
                
                with ui.VStack(width=35, height=35):
                    ui.Spacer()
                    self.sun_light_refresh_button = ui.Image(
                        name="reset", 
                        width=16, 
                        height=16,
                        tooltip="刷新太阳光列表"
                    )
                    ui.Spacer()
                
                self.sun_light_refresh_button.set_mouse_pressed_fn(self._on_sun_light_refresh_clicked)
                
        except Exception as e:
            print(f"构建太阳光下拉框时出错: {e}")
            with ui.HStack():
                ui.Label("构建太阳光选择器失败", style={"color": cl_attribute_red})
    
    def _build_gradient_float_slider_with_input(self, label_name, param_type, default_value, min_val, max_val):
        """为灯光属性构建渐变浮点滑块（带数值输入框）"""
        def _on_value_changed(model, rect_changed, rect_default):
            if model.as_float == default_value:
                rect_changed.visible = False
                rect_default.visible = True
            else:
                rect_changed.visible = True
                rect_default.visible = False

        def _restore_default(slider, input_field):
            slider.model.set_value(default_value)
            input_field.model.set_value(default_value)
        
        def _on_input_changed(value, slider):
            try:
                float_value = float(value)
                float_value = max(min_val, min(float_value, max_val))
                slider.model.set_value(float_value)
            except ValueError:
                pass

        with ui.HStack():
            ui.Label(label_name, name=f"attribute_name", width=self.label_width)
            with ui.ZStack():
                with ui.VStack():
                    ui.Spacer(height=1.5)
                    with ui.HStack():
                        slider = ui.FloatSlider(name="float_slider", height=0, min=min_val, max=max_val)
                        slider.model.set_value(default_value)
                        ui.Spacer(width=10)
                        input_field = ui.FloatField(
                            min=min_val, 
                            max=max_val,
                            height=0,
                            width=60,
                            style={"color": cl_text}
                        )
                        input_field.model.set_value(default_value)

                        # 同步滑块和输入框
                        slider.model.add_value_changed_fn(
                            lambda model, field=input_field: field.model.set_value(model.as_float)
                        )
                        input_field.model.add_value_changed_fn(
                            lambda model, s=slider: _on_input_changed(model.as_string, s)
                        )
                        
                        # 根据参数类型设置回调函数
                        if param_type == "exposure":
                            self.exposure_slider = slider
                            self.exposure_field = input_field
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_exposure_changed(s.model.as_float))
                        elif param_type == "intensity":
                            self.intensity_slider = slider
                            self.intensity_field = input_field
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_intensity_changed(s.model.as_float))
                        elif param_type == "specular":
                            self.specular_slider = slider
                            self.specular_field = input_field
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_specular_changed(s.model.as_float))
                        elif param_type == "temperature":
                            self.temperature_slider = slider
                            self.temperature_field = input_field
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_temperature_changed(s.model.as_float))
                        elif param_type == "longitude":
                            self.longitude_slider = slider
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_longitude_changed(s.model.as_float))
                        elif param_type == "latitude":
                            self.latitude_slider = slider
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_latitude_changed(s.model.as_float))
                        elif param_type == "sun_intensity":
                            self.sun_intensity_slider = slider
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_sun_intensity_changed(s.model.as_float))
                        elif param_type == "sun_temperature":
                            self.sun_temperature_slider = slider
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_sun_temperature_changed(s.model.as_float))
                        elif param_type == "sun_exposure":
                            self.sun_exposure_slider = slider
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_sun_exposure_changed(s.model.as_float))
                        elif param_type == "sun_angle":
                            self.sun_angle_slider = slider
                            slider.model.add_value_changed_fn(
                                lambda model, s=slider: self._on_sun_angle_changed(s.model.as_float))
                        
                        ui.Spacer(width=1.5)
            
            ui.Spacer(width=4)
            rect_changed, rect_default = self.__build_value_changed_widget()
            slider.model.add_value_changed_fn(lambda model: _on_value_changed(model, rect_changed, rect_default))
            
            rect_changed.set_mouse_pressed_fn(lambda x, y, b, m: _restore_default(slider, input_field))
        return None

    def _build_line_dot(self, line_width, height):
        """构建线点装饰元素"""
        with ui.HStack():
            ui.Spacer(width=10)
            with ui.VStack(width=line_width):
                ui.Spacer(height=height)
                ui.Line(name="group_line", alignment=ui.Alignment.TOP)
            with ui.VStack(width=6):
                ui.Spacer(height=height-2)
                ui.Circle(name="group_circle", width=6, height=6, alignment=ui.Alignment.BOTTOM)          

    def _build_color_temperature(self):
        """构建色温控件"""
        with ui.ZStack():
            with ui.HStack():
                ui.Spacer(width=10)
                with ui.VStack():
                    ui.Spacer(height=8)
                    ui.Line(name="group_line", alignment=ui.Alignment.RIGHT, width=0)
            with ui.VStack(height=0, spacing=10):
                with ui.HStack():
                    self._build_line_dot(10, 8)
                    ui.Label("Enable Color Temperature", name="attribute_name", width=0)
                    ui.Spacer()
                    with ui.HStack(width=0):
                        self._build_checkbox("", self.color_temperature_enabled, self._on_temperature_toggled)

                # 使用统一的带输入框滑块构建方法
                self._build_gradient_float_slider_with_input(
                    "    Color Temperature", "temperature", 2700.0, 1000, 15000)

                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Line(name="group_line", alignment=ui.Alignment.TOP)

    def _build_color_widget(self, widget_name):
        """构建颜色控件"""
        with ui.ZStack():
            with ui.HStack():
                ui.Spacer(width=10)
                with ui.VStack():
                    ui.Spacer(height=8)
                    ui.Line(name="group_line", alignment=ui.Alignment.RIGHT, width=0)
            with ui.VStack(height=0, spacing=10):
                with ui.HStack():
                    self._build_line_dot(40, 9)
                    ui.Label(widget_name, name="attribute_name", width=0)
                    self.color_widget = ColorWidget(1.0, 1.0, 1.0, on_color_changed=self._on_color_changed)
                    ui.Spacer(width=10)
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Line(name="group_line", alignment=ui.Alignment.TOP)

    def _build_fn(self):
        """构建所有UI的主要方法"""
        with ui.ScrollingFrame(name="main_frame"):
            with ui.VStack(height=0, spacing=10):
                self._build_head()
                self._build_light_properties()
                self._build_sun_path_properties()
                self._build_material_properties()
                ui.Spacer(height=30)

    def _build_head(self):
        """构建窗口头部"""
        with ui.ZStack():
            ui.Image(name="header_frame", height=180,  fill_policy=ui.FillPolicy.STRETCH)
            with ui.HStack():
                ui.Spacer(width=12)
                with ui.VStack(spacing=8):
                    self._build_tabs()
                    ui.Spacer(height=1)
                    self._build_selection_widget()
                    self._build_stage_path_widget()
                    self._build_search_field()
                ui.Spacer(width=12)

    def _build_tabs(self):
        """构建标签页"""
        with ui.HStack(height=35):
            ui.Label("Vision Sync", width=ui.Percent(17), name="details")
            with ui.ZStack():
                ui.Image(name="combobox", fill_policy=ui.FillPolicy.STRETCH, height=35)
                with ui.HStack():
                    ui.Spacer(width=15)

    def _build_selection_widget(self):
        """构建选择控件"""
        with ui.HStack(height=20):
            add_button = ui.Button(f"{_get_search_glyph()} Search", width=60, name="search")
            add_button.set_clicked_fn(self._on_search_clicked)
            
            ui.Spacer(width=14)
            
            self.path_field = ui.StringField(name="path")
            self.path_field.model.set_value("/World/lights/")
            
            ui.Spacer(width=8)
            self.top_reset_button = ui.Image(name="reset", width=20)
            self.top_reset_button.set_mouse_pressed_fn(lambda x, y, b, m: self._on_reset_vision_sync())

    def _build_stage_path_widget(self):
        """构建舞台路径控件"""
        with ui.HStack(height=20):
            with ui.VStack():
                self._build_combobox("Select Room", [], self._on_room_selected)

    def _build_search_field(self):
        """构建搜索字段"""
        with ui.HStack():
            ui.Spacer(width=2)
            self._build_combobox("Select Lighting", [], self._on_lighting_selected)

    def _build_checkbox(self, label_name, default_value=True, on_changed=None):
        """构建复选框"""
        def _restore_default(rect_changed, rect_default, current_state):
            image.name = "checked" if default_value else "unchecked"
            rect_changed.visible = False
            rect_default.visible = True
            
            if on_changed:
                on_changed(default_value)

        def _on_value_changed(image, rect_changed, rect_default):
            new_state = (image.name != "checked")
            image.name = "checked" if new_state else "unchecked"
            
            if (default_value and not new_state) or (not default_value and new_state):
                rect_changed.visible = True
                rect_default.visible = False
            else:
                rect_changed.visible = False
                rect_default.visible = True
            
            if on_changed:
                try:
                    on_changed(new_state)
                except Exception as e:
                    print(f"回调函数调用失败: {str(e)}")

        with ui.HStack():
            ui.Label(label_name, name=f"attribute_bool", width=self.label_width, height=20)
            
            initial_name = "checked" if default_value else "unchecked"
            image = ui.Image(name=initial_name, fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT, height=18, width=18)
            
            if label_name == "" and "temperature" in str(on_changed):
                self.temperature_checkbox_image = image
            
            ui.Spacer()
            
            rect_changed, rect_default = self.__build_value_changed_widget()
            
            image.set_mouse_pressed_fn(lambda x, y, b, m: _on_value_changed(image, rect_changed, rect_default))
            rect_changed.set_mouse_pressed_fn(
                lambda x, y, b, m: _restore_default(rect_changed, rect_default, default_value)
            )

    def __build_value_changed_widget(self):
        """构建值更改指示器控件"""
        with ui.VStack(width=20):
            ui.Spacer(height=3)
            rect_changed = ui.Rectangle(name="attribute_changed", width=15, height=15, visible= False)
            ui.Spacer(height=4)
            with ui.HStack():
                ui.Spacer(width=3)
                rect_default = ui.Rectangle(name="attribute_default", width=5, height=5, visible= True)
        return rect_changed, rect_default    

    def _build_combobox(self, label_name, options, on_selected=None):
        """构建下拉框"""
        def _on_value_changed(model, rect_changed, rect_defaul):
            index = model.get_item_value_model().get_value_as_int()
            if index == 0:
                rect_changed.visible = False
                rect_defaul.visible = True
            else:
                rect_changed.visible = True
                rect_defaul.visible = False
            
            current_options = []
            if label_name == "Select Room":
                current_options = self.current_room_options
            elif label_name == "Select Lighting":
                current_options = self.current_lighting_options
            
            if on_selected and index < len(current_options):
                on_selected(current_options[index])
        
        def _restore_default(combo_box):
            combo_box.model.get_item_value_model().set_value(0)
        
        with ui.HStack():
            ui.Label(label_name, name=f"attribute_name", width=self.label_width)
            with ui.ZStack():
                ui.Image(name="combobox", fill_policy=ui.FillPolicy.STRETCH, height=35)
                with ui.HStack():
                    ui.Spacer(width=10)
                    with ui.VStack():
                        ui.Spacer(height=10)
                        option_list = list(options)
                        combo_box = ui.ComboBox(0, *option_list, name="dropdown_menu")
                        
                        if label_name == "Select Room":
                            self.room_combobox = combo_box
                            self.room_combobox_model = combo_box.model
                        elif label_name == "Select Lighting":
                            self.lighting_combobox = combo_box
                            self.lighting_combobox_model = combo_box.model
                            
            with ui.VStack(width=0):
                ui.Spacer(height=10)
                rect_changed, rect_default = self.__build_value_changed_widget()
            combo_box.model.add_item_changed_fn(lambda m, i: _on_value_changed(m, rect_changed, rect_default))
            rect_changed.set_mouse_pressed_fn(lambda x, y, b, m: _restore_default(combo_box))