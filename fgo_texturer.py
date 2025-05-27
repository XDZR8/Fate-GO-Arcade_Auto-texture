# FATE GRAND ORDER AUTO-TEXTURE
bl_info = {
    "name": "FGO Arcade Auto Texturer",
    "blender": (3, 0, 0),
    "category": "Import-Export",
    "author": "OpenAI Assistant",
    "description": "Aplica automáticamente texturas para personajes de FGO Arcade por ascensión y nombre.",
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


class FGOTexturePreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    texture_path: bpy.props.StringProperty(
        name="Carpeta de personajes",
        subtype='DIR_PATH',
        default="",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "texture_path")


class FGOToolsPanel(bpy.types.Panel):
    bl_label = "🎨 FGO Arcade Texturizer"
    bl_idname = "VIEW3D_PT_fgo_arcade_texturer_final"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FGO Tools'

    def draw(self, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        layout = self.layout
        scn = context.scene

        if not os.path.exists(prefs.texture_path):
            layout.label(text="⚠ Por favor, define la ruta en las preferencias del addon", icon="ERROR")
            return

        layout.label(text="🔍 Buscar personaje:")
        layout.prop(scn, "fgo_character_name", text="Nombre")
        layout.operator("fgo.search_character", text="🔎 Buscar carpeta")

        if scn.get("fgo_folder_choices"):
            layout.prop(scn, "fgo_character_folder", text="Carpeta encontrada")

        layout.label(text="🎭 Stage / Ascensión:")
        layout.prop(scn, "fgo_stage", expand=True)
        layout.prop(scn, "fgo_invert_uvs", text="Invertir UV de faceback")
        layout.operator("fgo.apply_textures", text="🎨 Aplicar Texturas")


class FGO_OT_SearchCharacter(bpy.types.Operator):
    bl_idname = "fgo.search_character"
    bl_label = "Buscar personaje"

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        folder = prefs.texture_path
        keyword = context.scene.fgo_character_name.lower()
        if not os.path.isdir(folder):
            self.report({'ERROR'}, "Ruta no válida.")
            return {'CANCELLED'}
        matches = [f for f in os.listdir(folder) if keyword in f.lower()]
        context.scene["fgo_folder_choices"] = matches
        if matches:
            context.scene.fgo_character_folder = matches[0]
        return {'FINISHED'}


class FGO_OT_ApplyTextures(bpy.types.Operator):
    bl_idname = "fgo.apply_textures"
    bl_label = "Aplicar texturas al modelo"

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        folder = prefs.texture_path
        char_folder = context.scene.fgo_character_folder
        stage = context.scene.fgo_stage
        invert_uvs = context.scene.fgo_invert_uvs

        texture_dir = os.path.join(folder, char_folder)
        if not os.path.exists(texture_dir):
            self.report({'ERROR'}, "No se encontró la carpeta de texturas.")
            return {'CANCELLED'}

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
                self.report({'INFO'}, f"Textura aplicada: {base_match}")
            else:
                print(f"[WARN] No se encontró textura para {mat.name}")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(FGOTexturePreferences)
    bpy.utils.register_class(FGOToolsPanel)
    bpy.utils.register_class(FGO_OT_SearchCharacter)
    bpy.utils.register_class(FGO_OT_ApplyTextures)
    bpy.types.Scene.fgo_character_name = bpy.props.StringProperty(name="Nombre del personaje")
    bpy.types.Scene.fgo_character_folder = bpy.props.EnumProperty(name="Carpeta", items=lambda self, context: [
        (c, c, "") for c in context.scene.get("fgo_folder_choices", [])
    ])
    bpy.types.Scene.fgo_stage = bpy.props.EnumProperty(
        name="Ascensión", items=[('s01', 'Stage 1', ''), ('s02', 'Stage 2', ''), ('s03', 'Stage 3', '')], default='s03')
    bpy.types.Scene.fgo_invert_uvs = bpy.props.BoolProperty(name="Invertir UV de faceback", default=False)


def unregister():
    bpy.utils.unregister_class(FGOTexturePreferences)
    bpy.utils.unregister_class(FGOToolsPanel)
    bpy.utils.unregister_class(FGO_OT_SearchCharacter)
    bpy.utils.unregister_class(FGO_OT_ApplyTextures)
    del bpy.types.Scene.fgo_character_name
    del bpy.types.Scene.fgo_character_folder
    del bpy.types.Scene.fgo_stage
    del bpy.types.Scene.fgo_invert_uvs


if __name__ == "__main__":
    register()
