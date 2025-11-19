# material_manager.py
from datetime import datetime
import omni.kit.commands
from pxr import UsdShade, Sdf, Usd, UsdGeom
from typing import List, Optional, Set, Dict
import omni.usd


class MaterialManager:
    """材质管理器，负责处理USD场景中的材质操作"""
    
    def __init__(self):
        self.unused_materials = []  # 未使用的材质列表
        self.deleted_materials_history = []  # 删除历史记录列表 - 修复：改为列表存储所有历史
        self.selected_materials = set()  # 用户选中的材质
        self.last_deleted_materials = None  # 最近一次删除的材质
    
    def scan_unused_materials(self):
        """扫描未使用的材质 - 主方法"""
        return self._scan_unused_materials_enhanced()
    
    def _scan_unused_materials_enhanced(self):
        """增强版的未使用材质扫描"""
        try:
            used_materials = set()
            all_materials = []
            stage = omni.usd.get_context().get_stage()
            
            if not stage:
                print("无法获取USD舞台")
                return []
            
            print("=== 开始增强版材质扫描 ===")
            
            # 首先收集所有材质
            for prim in stage.Traverse():
                try:
                    if prim.IsA(UsdShade.Material):
                        is_ancestral = self._is_ancestral_prim(prim)
                        
                        material_info = {
                            'path': str(prim.GetPath()),
                            'name': prim.GetName(),
                            'type': prim.GetTypeName(),
                            'is_ancestral': is_ancestral,
                            'can_delete': not is_ancestral
                        }
                        all_materials.append(material_info)
                        print(f"找到材质: {prim.GetPath()} - Ancestral: {is_ancestral}")
                except Exception as e:
                    print(f"检查材质图元时出错: {str(e)}")
                    continue
            
            print(f"总共找到材质: {len(all_materials)}")
            
            # 增强的使用检测逻辑
            for prim in stage.Traverse():
                try:
                    # 跳过材质本身
                    if prim.IsA(UsdShade.Material):
                        continue
                        
                    # 检查直接材质绑定
                    if prim.IsA(UsdGeom.Imageable):
                        binding_api = UsdShade.MaterialBindingAPI(prim)
                        
                        # 检查直接绑定
                        direct_binding = binding_api.GetDirectBinding()
                        material_path = direct_binding.GetMaterialPath()
                        if material_path:
                            used_materials.add(str(material_path))
                            print(f"材质被直接绑定使用: {material_path} -> {prim.GetPath()}")
                        
                        # 检查集合绑定
                        collection_bindings = binding_api.GetCollectionBindings()
                        for collection_binding in collection_bindings:
                            material_path = collection_binding.GetMaterialPath()
                            if material_path:
                                used_materials.add(str(material_path))
                                print(f"材质被集合绑定使用: {material_path} -> {prim.GetPath()}")
                    
                    # 检查所有可能的材质绑定属性
                    material_attrs = [
                        "material:binding", 
                        "inputs:material:binding",
                        "primvars:material:binding"
                    ]
                    
                    for attr_name in material_attrs:
                        if prim.HasAttribute(attr_name):
                            material_attr = prim.GetAttribute(attr_name)
                            if material_attr and material_attr.HasAuthoredValue():
                                # 获取连接的目标
                                if material_attr.HasAuthoredConnections():
                                    connections = material_attr.GetConnections()
                                    for connection in connections:
                                        used_materials.add(str(connection))
                                        print(f"材质被属性连接使用: {connection} -> {prim.GetPath()}")
                                # 获取直接值
                                else:
                                    try:
                                        target_path = material_attr.Get()
                                        if target_path:
                                            used_materials.add(str(target_path))
                                            print(f"材质被属性值使用: {target_path} -> {prim.GetPath()}")
                                    except:
                                        pass
                    
                    # 检查材质关系(relationships)
                    for rel in prim.GetRelationships():
                        try:
                            targets = rel.GetTargets()
                            for target in targets:
                                target_prim = stage.GetPrimAtPath(target)
                                if target_prim and target_prim.IsA(UsdShade.Material):
                                    used_materials.add(str(target))
                                    print(f"材质被关系使用: {target} -> {prim.GetPath()}")
                        except:
                            pass
                            
                except Exception as e:
                    print(f"处理图元 {prim.GetPath()} 时出错: {str(e)}")
                    continue
            
            print(f"已使用的材质数量: {len(used_materials)}")
            if used_materials:
                print("使用的材质路径示例:")
                for used_mat in list(used_materials)[:5]:  # 只显示前5个
                    print(f"  - {used_mat}")
            
            # 找出未使用的材质
            self.unused_materials = [
                mat for mat in all_materials 
                if mat['path'] not in used_materials
            ]
            
            # 统计信息
            ancestral_count = sum(1 for mat in self.unused_materials if mat['is_ancestral'])
            deletable_count = sum(1 for mat in self.unused_materials if not mat['is_ancestral'])
            
            print(f"未使用的材质总数: {len(self.unused_materials)}")
            print(f"  - 可删除的材质: {deletable_count}")
            print(f"  - Ancestral 材质 (不能删除): {ancestral_count}")
            print("=== 材质扫描完成 ===")
            
            # 重置选中状态
            self.selected_materials.clear()
            
            return self.unused_materials
            
        except Exception as e:
            print(f"扫描未使用材质时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_ancestral_prim(self, prim):
        """改进的祖先材质检测逻辑"""
        try:
            # 只检测真正不能删除的情况
            # 检查是否在原型或实例中
            if prim.IsInPrototype() or prim.IsInstance():
                return True
                
            # 检查是否有外部引用
            if prim.HasAuthoredReferences():
                # 进一步检查引用是否来自只读层
                stage = prim.GetStage()
                if stage:
                    root_layer = stage.GetRootLayer()
                    # 如果根层不是可读写的，可能是引用场景
                    if hasattr(root_layer, 'permission') and root_layer.permission != Sdf.LayerPermission.PublicReadWrite:
                        return True
            
            # 检查是否在系统路径中（可选，更宽松的判断）
            prim_path = str(prim.GetPath())
            system_paths = ["/Looks/", "/Materials/", "/_class/"]
            if any(prim_path.startswith(path) for path in system_paths):
                return True
                
            return False
            
        except Exception as e:
            print(f"检查ancestral prim时出错: {str(e)}")
            return False  # 出错时允许删除，避免误判
    
    def delete_selected_materials(self):
        """删除选中的材质"""
        if not self.selected_materials:
            return 0, [], "没有选中的材质"
        
        try:
            materials_to_delete = []
            deletable_materials = []
            
            # 只收集可删除的材质
            for mat_info in self.unused_materials:
                if mat_info['path'] in self.selected_materials and not mat_info['is_ancestral']:
                    materials_to_delete.append(mat_info['path'])
                    deletable_materials.append(mat_info)
            
            # 检查是否有选中的 ancestral 材质
            ancestral_selected = [
                mat_info for mat_info in self.unused_materials 
                if mat_info['path'] in self.selected_materials and mat_info['is_ancestral']
            ]
            
            if materials_to_delete:
                # 记录删除历史 - 修复：保存所有删除的材质
                deleted_info = {
                    'paths': materials_to_delete.copy(),
                    'names': [Sdf.Path(path).name for path in materials_to_delete],
                    'material_infos': [mat for mat in self.unused_materials if mat['path'] in materials_to_delete],
                    'timestamp': datetime.now()
                }
                # 修复：添加到历史列表而不是覆盖
                self.deleted_materials_history.append(deleted_info)
                self.last_deleted_materials = deleted_info
                
                # 执行删除 - 修复：使用批量删除而不是循环
                success_count = 0
                failed_paths = []
                
                try:
                    # 批量删除所有选中的材质
                    omni.kit.commands.execute('DeletePrims', paths=materials_to_delete)
                    success_count = len(materials_to_delete)
                    print(f"成功批量删除 {success_count} 个材质")
                except Exception as e:
                    print(f"批量删除失败: {str(e)}")
                    # 如果批量删除失败，尝试逐个删除
                    for material_path in materials_to_delete:
                        try:
                            omni.kit.commands.execute('DeletePrims', paths=[material_path])
                            success_count += 1
                            print(f"成功删除材质: {material_path}")
                        except Exception as e:
                            print(f"删除材质 {material_path} 失败: {str(e)}")
                            failed_paths.append(material_path)
                
                # 从当前列表中移除成功删除的材质
                self.unused_materials = [
                    mat for mat in self.unused_materials 
                    if mat['path'] not in materials_to_delete or mat['path'] in failed_paths
                ]
                
                # 清空选中状态
                self.selected_materials.clear()
                
                # 准备返回消息
                message = ""
                if success_count > 0:
                    message = f"成功删除 {success_count} 个材质"
                if failed_paths:
                    message += f"，{len(failed_paths)} 个删除失败"
                if ancestral_selected:
                    message += f"，跳过 {len(ancestral_selected)} 个 ancestral 材质"
                
                return success_count, deleted_info['names'], message
            
            elif ancestral_selected:
                return 0, [], f"无法删除 ancestral 材质，请选择可删除的材质"
            else:
                return 0, [], "没有选中的可删除材质"
            
        except Exception as e:
            print(f"删除选中材质时发生错误: {str(e)}")
            return 0, [], f"错误: {str(e)}"
    
    def delete_all_unused_materials(self):
        """删除所有未使用的材质"""
        if not self.unused_materials:
            return 0, [], "没有未使用的材质"
        
        try:
            # 只收集可删除的材质
            materials_to_delete = [mat['path'] for mat in self.unused_materials if not mat['is_ancestral']]
            material_names = [mat['name'] for mat in self.unused_materials if not mat['is_ancestral']]
            material_infos = [mat for mat in self.unused_materials if not mat['is_ancestral']]
            
            # 统计 ancestral 材质数量
            ancestral_count = sum(1 for mat in self.unused_materials if mat['is_ancestral'])
            
            if not materials_to_delete:
                if ancestral_count > 0:
                    return 0, [], f"没有可删除的材质，有 {ancestral_count} 个 ancestral 材质无法删除"
                else:
                    return 0, [], "没有可删除的材质"
            
            # 记录删除历史
            deleted_info = {
                'paths': materials_to_delete.copy(),
                'names': material_names.copy(),
                'material_infos': material_infos.copy(),
                'timestamp': datetime.now()
            }
            self.deleted_materials_history.append(deleted_info)
            self.last_deleted_materials = deleted_info
            
            # 执行删除
            success_count = 0
            failed_paths = []
            
            try:
                # 批量删除所有可删除的材质
                omni.kit.commands.execute('DeletePrims', paths=materials_to_delete)
                success_count = len(materials_to_delete)
                print(f"成功批量删除 {success_count} 个材质")
            except Exception as e:
                print(f"批量删除失败: {str(e)}")
                # 如果批量删除失败，尝试逐个删除
                for material_path in materials_to_delete:
                    try:
                        omni.kit.commands.execute('DeletePrims', paths=[material_path])
                        success_count += 1
                        print(f"成功删除材质: {material_path}")
                    except Exception as e:
                        print(f"删除材质 {material_path} 失败: {str(e)}")
                        failed_paths.append(material_path)
            
            # 清空列表（只保留删除失败的）
            self.unused_materials = [mat for mat in self.unused_materials if mat['path'] in failed_paths or mat['is_ancestral']]
            self.selected_materials.clear()
            
            # 准备返回消息
            message = f"成功删除 {success_count} 个材质"
            if failed_paths:
                message += f"，{len(failed_paths)} 个删除失败"
            if ancestral_count > 0:
                message += f"，跳过 {ancestral_count} 个 ancestral 材质"
            
            return success_count, material_names, message
            
        except Exception as e:
            print(f"删除所有未使用材质时发生错误: {str(e)}")
            return 0, [], f"错误: {str(e)}"
    
    def undo_last_delete(self):
        """撤销上一次删除操作"""
        if not self.deleted_materials_history:
            return False, "没有可撤销的删除操作"
        
        try:
            # 获取最后一次删除的历史记录
            last_delete = self.deleted_materials_history.pop()
            
            if not last_delete or 'material_infos' not in last_delete:
                return False, "删除历史记录不完整"
            
            restored_count = 0
            stage = omni.usd.get_context().get_stage()
            
            # 恢复所有被删除的材质
            for mat_info in last_delete['material_infos']:
                try:
                    # 重新创建材质prim
                    prim_path = mat_info['path']
                    prim = stage.DefinePrim(prim_path, mat_info['type'])
                    
                    # 重新添加到未使用材质列表
                    if prim.IsValid():
                        self.unused_materials.append(mat_info)
                        restored_count += 1
                        print(f"成功恢复材质: {prim_path}")
                        
                except Exception as e:
                    print(f"恢复材质 {mat_info['path']} 失败: {str(e)}")
            
            # 更新last_deleted_materials
            if self.deleted_materials_history:
                self.last_deleted_materials = self.deleted_materials_history[-1]
            else:
                self.last_deleted_materials = None
            
            # 重新扫描材质以更新完整列表
            self.scan_unused_materials()
            
            return True, f"已撤销上次删除操作，恢复了 {restored_count} 个材质"
            
        except Exception as e:
            print(f"撤销操作失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"撤销操作失败: {str(e)}"
    
    def toggle_material_selection(self, material_path, selected):
        """切换材质选中状态"""
        if selected:
            self.selected_materials.add(material_path)
        else:
            self.selected_materials.discard(material_path)
    
    def select_all_materials(self):
        """选中所有材质"""
        self.selected_materials.clear()
        for mat in self.unused_materials:
            if not mat['is_ancestral']:  # 只选择可删除的材质
                self.selected_materials.add(mat['path'])
    
    def clear_selection(self):
        """清空选中状态"""
        self.selected_materials.clear()
    
    def get_selection_count(self):
        """获取选中材质数量"""
        return len(self.selected_materials)
    
    def get_unused_count(self):
        """获取未使用材质数量"""
        return len(self.unused_materials)
    
    def get_deletable_count(self):
        """获取可删除的材质数量"""
        return sum(1 for mat in self.unused_materials if not mat['is_ancestral'])
    
    def has_deletion_history(self):
        """检查是否有删除历史"""
        return len(self.deleted_materials_history) > 0
    
    def clear_deletion_history(self):
        """清空删除历史"""
        self.deleted_materials_history.clear()
        self.last_deleted_materials = None
    
    def get_deletion_history_count(self):
        """获取删除历史记录数量"""
        return len(self.deleted_materials_history)