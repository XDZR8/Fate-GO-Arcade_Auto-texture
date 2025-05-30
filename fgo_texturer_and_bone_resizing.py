
bl_info = {
    "name": "FGO Arcade Toolkit (Full UI + Context Menu + Safe Check)",
    "blender": (3, 0, 0),
    "category": "Import-Export",
    "author": XDZR8 (con ayuda de ChatGPT)",
    "description": "Toolkit completo para FGO Arcade: auto texturas, redim. huesos, menú contextual y validación de carpeta.",
}

import bpy
import os

valid_exts = [".dds", ".png", ".tga"]

def assign_texture(mat, tex_path, input_name, is_normal=False, use_alpha=False):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        return
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = bpy.data.images.load(tex_path)
    bsdf.inputs["Metallic"].default_value = 0
    bsdf.inputs["Roughness"].default_value = 0.5

    if is_normal:
        normal_node = nodes.new('ShaderNodeNormalMap')
        links.new(tex_node.outputs["Color"], normal_node.inputs["Color"])
        links.new(normal_node.outputs["Normal"], bsdf.inputs[input_name])
    elif use_alpha:
        mat.blend_method = 'BLEND'
        tex_node.image.alpha_mode = 'CHANNEL_PACKED'
        links.new(tex_node.outputs["Alpha"], bsdf.inputs[input_name])
    else:
        links.new(tex_node.outputs["Color"], bsdf.inputs[input_name])

class FGO_OT_ApplyTextures(bpy.types.Operator):
    bl_idname = "fgo.apply_textures"
    bl_label = "Apply FGO Textures"

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        texture_dir = prefs.texture_path

        if not os.path.isdir(texture_dir):
            self.report({'ERROR'}, f"Selected path is not a valid folder:\n{texture_dir}")
            return {'CANCELLED'}

        stage = context.scene.fgo_stage
        char_folder = os.path.basename(texture_dir)
        all_textures = {}
        for file in os.listdir(texture_dir):
            name, ext = os.path.splitext(file)
            if ext.lower() in valid_exts:
                all_textures[name.lower()] = os.path.join(texture_dir, file)

        svt_id = char_folder.split("svt_")[-1]
        base_prefix = f"svt_{svt_id}_{stage}"

        for mat in bpy.data.materials:
            matname = mat.name.lower()
            base_match = None
            for key in all_textures:
                if key.startswith(base_prefix) and matname in key:
                    base_match = key
                    break

            if base_match:
                assign_texture(mat, all_textures[base_match], "Base Color")
                if base_match + "_n" in all_textures:
                    assign_texture(mat, all_textures[base_match + "_n"], "Normal", is_normal=True)
                if base_match + "_s" in all_textures:
                    assign_texture(mat, all_textures[base_match + "_s"], "Roughness")
                if base_match + "_a" in all_textures:
                    assign_texture(mat, all_textures[base_match + "_a"], "Alpha", use_alpha=True)
        return {'FINISHED'}

class FGO_OT_ScaleBones(bpy.types.Operator):
    bl_idname = "fgo.scale_bones"
    bl_label = "Resize Bones"

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an Armature object.")
            return {'CANCELLED'}

        scale_factor = context.scene.fgo_bone_scale_factor
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in obj.data.edit_bones:
            bone.length *= scale_factor
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Bones resized by {scale_factor:.2f}")
        return {'FINISHED'}

class FGOAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    texture_path: bpy.props.StringProperty(name="Character Folder Path", subtype='DIR_PATH', default="")
    def draw(self, context):
        self.layout.prop(self, "texture_path")

class FGO_PT_MainPanel(bpy.types.Panel):
    bl_label = "FGO Arcade Toolkit"
    bl_idname = "VIEW3D_PT_fgo_arcade_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FGO Tools'

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "fgo_stage")
        layout.prop(context.scene, "fgo_bone_scale_factor")
        layout.operator("fgo.apply_textures")
        layout.operator("fgo.scale_bones")

class FGO_MT_ContextMenu(bpy.types.Menu):
    bl_label = "FGO Tools"
    bl_idname = "FGO_MT_context_menu"
    def draw(self, context):
        layout = self.layout
        obj = context.object
        if obj and obj.type == 'MESH':
            layout.operator("fgo.apply_textures", text="🎨 Apply FGO Textures")
        if obj and obj.type == 'ARMATURE':
            layout.prop(context.scene, "fgo_bone_scale_factor")
            layout.operator("fgo.scale_bones", text="🦴 Resize Bones")

def draw_context_menu(self, context):
    self.layout.separator()
    self.layout.menu("FGO_MT_context_menu")

def register():
    bpy.utils.register_class(FGOAddonPreferences)
    bpy.utils.register_class(FGO_OT_ApplyTextures)
    bpy.utils.register_class(FGO_OT_ScaleBones)
    bpy.utils.register_class(FGO_PT_MainPanel)
    bpy.utils.register_class(FGO_MT_ContextMenu)
    bpy.types.Scene.fgo_stage = bpy.props.EnumProperty(
        name="Stage", items=[('s01', 'Stage 1', ''), ('s02', 'Stage 2', ''), ('s03', 'Stage 3', '')], default='s03')
    bpy.types.Scene.fgo_bone_scale_factor = bpy.props.FloatProperty(
        name="Bone Scale", default=0.1, min=0.01, max=10.0)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_context_menu)

def unregister():
    bpy.utils.unregister_class(FGOAddonPreferences)
    bpy.utils.unregister_class(FGO_OT_ApplyTextures)
    bpy.utils.unregister_class(FGO_OT_ScaleBones)
    bpy.utils.unregister_class(FGO_PT_MainPanel)
    bpy.utils.unregister_class(FGO_MT_ContextMenu)
    del bpy.types.Scene.fgo_stage
    del bpy.types.Scene.fgo_bone_scale_factor
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_context_menu)

if __name__ == "__main__":
    register()
