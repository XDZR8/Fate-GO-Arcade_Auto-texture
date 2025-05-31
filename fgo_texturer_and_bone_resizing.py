bl_info = {
    "name": "FGO Character Texture Assigner",
    "author": "XDZR8 (assisted by ChatGPT)",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Tool Shelf",
    "description": "Asigna texturas automáticamente según el personaje de FGO Arcade seleccionado.",
    "category": "Material",
}


# Importación del registro de los personajes
from .fgo_data import character_enum_items, character_mappings

import bpy
import os
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import StringProperty, EnumProperty, PointerProperty

from .fgo_data import character_mappings, character_enum_items

class FGOTexSettings(PropertyGroup):
    texture_folder: StringProperty(
        name="Carpeta de Texturas",
        subtype='DIR_PATH'
    )
    character_id: EnumProperty(
        name="Personaje",
        description="Selecciona el personaje",
        items=character_enum_items
    )

class FGO_OT_AssignTextures(Operator):
    bl_idname = "fgo.assign_textures"
    bl_label = "Asignar Texturas"
    bl_description = "Asigna las texturas automáticamente al personaje seleccionado"

    def execute(self, context):
        settings = context.scene.fgo_tex_settings
        char_id = settings.character_id
        tex_dir = settings.texture_folder

        if not char_id or not tex_dir:
            self.report({'WARNING'}, "Selecciona personaje y carpeta de texturas")
            return {'CANCELLED'}

        mapping = character_mappings.get(char_id, {})
        if not mapping:
            self.report({'WARNING'}, f"No hay mapeo para {char_id}")
            return {'CANCELLED'}

        valid_exts = [".dds", ".png", ".tga"]
        all_textures = {}
        for file in os.listdir(tex_dir):
            name, ext = os.path.splitext(file)
            if ext.lower() in valid_exts:
                all_textures[name.lower()] = os.path.join(tex_dir, file)

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

        for mat in bpy.data.materials:
            matname = mat.name.lower()
            matched = False

            for key, base in mapping.items():
                if matname.startswith(key.lower()):
                    matched = True
                    if base == "solid_black":
                        mat.use_nodes = True
                        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                        if bsdf:
                            bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
                            bsdf.inputs["Roughness"].default_value = 1
                        break

                    if base.lower() in all_textures:
                        assign_texture(mat, all_textures[base.lower()], "Base Color")
                    if base.lower() + "_n" in all_textures:
                        assign_texture(mat, all_textures[base.lower() + "_n"], "Normal", is_normal=True)
                    if base.lower() + "_s" in all_textures:
                        assign_texture(mat, all_textures[base.lower() + "_s"], "Roughness")
                    if base.lower() + "_a" in all_textures:
                        assign_texture(mat, all_textures[base.lower() + "_a"], "Alpha", use_alpha=True)
                    break

            if not matched:
                print(f"[WARN] Sin mapeo para material: {mat.name}")

        return {'FINISHED'}

class FGO_PT_TexturePanel(Panel):
    bl_label = "FGO Texture Assigner"
    bl_idname = "FGO_PT_TexturePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FGO Tools'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.fgo_tex_settings

        layout.prop(settings, "character_id")
        layout.prop(settings, "texture_folder")
        layout.operator("fgo.assign_textures")

classes = [
    FGOTexSettings,
    FGO_OT_AssignTextures,
    FGO_PT_TexturePanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fgo_tex_settings = PointerProperty(type=FGOTexSettings)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.fgo_tex_settings

if __name__ == "__main__":
    register()
