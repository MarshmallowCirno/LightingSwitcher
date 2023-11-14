# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import bpy.utils.previews
from bpy.props import EnumProperty, IntProperty, CollectionProperty, PointerProperty, StringProperty
from bpy.types import AddonPreferences, Operator, Panel, PropertyGroup, UIList, Scene


bl_info = {
    "name": "Lighting Switcher",
    "author": "MarshmallowCirno",
    "blender": (3, 3, 1),
    "version": (1, 0),
    "location": "3D View > Sidebar > View",
    "description": "Fast switching between viewport shading lights with Ctrl+Wheel",
    "category": "3D View",
    "doc_url": "https://gumroad.com/l/trkzz",
    "tracker_url": "https://blenderartists.org/t/lighting-switcher/1422996",
}

PREVIEW_COLLECTIONS = {}


class LSWITCH_UL_lights(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        icon_id = -1
        pcoll = PREVIEW_COLLECTIONS.get("thumbnail_previews")
        if pcoll is not None:
            preview = pcoll.get(item.name)
            if preview is not None:
                icon_id = preview.icon_id

        layout.label(text=item.label, icon_value=icon_id)


class LSWITCH_OT_reload(Operator):
    bl_idname = "lighting_switcher.reload"
    bl_label = "Reload Themes"
    bl_description = "Reload list of themes"
    bl_options = {'INTERNAL'}

    def invoke(self, context, _):
        scene = context.scene
        addon_prefs = context.preferences.addons[__name__].preferences

        # Clear previews.
        for pcoll in PREVIEW_COLLECTIONS.values():
            bpy.utils.previews.remove(pcoll)
        PREVIEW_COLLECTIONS.clear()

        # Clear addon prefs props.
        addon_prefs.studio_lights.clear()
        addon_prefs.matcap_lights.clear()
        addon_prefs.hdri_lights.clear()

        # Add lights to scene collection.
        import_light()

        # Generate previews.
        generate_previews()

        shading = context.space_data.shading
        curr_light = shading.studio_light

        # Sync props with scene light and light type.
        studio_idx = 0
        matcap_idx = 0
        hdri_idx = 0

        if shading.type == 'SOLID':
            if shading.light == 'STUDIO':
                scene.lighting_switcher["active_light_type"] = 0
                idx = addon_prefs.studio_lights.find(curr_light)
                studio_idx = max(idx, 0)
            elif shading.light == 'MATCAP':
                scene.lighting_switcher["active_light_type"] = 1
                idx = addon_prefs.matcap_lights.find(curr_light)
                matcap_idx = max(idx, 0)
        elif shading.type == 'MATERIAL':
            scene.lighting_switcher["active_light_type"] = 2
            idx = addon_prefs.hdri_lights.find(curr_light)
            hdri_idx = max(idx, 0)

        scene.lighting_switcher["active_studio_light_index"] = studio_idx
        scene.lighting_switcher["active_matcap_light_index"] = matcap_idx
        scene.lighting_switcher["active_hdri_light_index"] = hdri_idx

        return {'FINISHED'}


def import_light():
    """Fill props collection with studio lights in prefs."""
    addon_prefs = bpy.context.preferences.addons[__name__].preferences

    for light in bpy.context.preferences.studio_lights:
        match light.type:
            case 'STUDIO':
                prop = addon_prefs.studio_lights.add()
            case 'MATCAP':
                prop = addon_prefs.matcap_lights.add()
            case 'WORLD':
                prop = addon_prefs.hdri_lights.add()
            case _:
                continue

        prop.name = light.name

        # Underscores to whitespaces.
        label = light.name.replace("_", " ")
        # CamelCase.
        label = label.title()
        # Remove extension.
        partition = label.rpartition(".")
        if partition[-1] in {"Sl", "Exr", "Hdr"}:
            label = partition[0]

        prop.label = label
        prop.path = light.path


def generate_previews():
    """Generate previews for props, rendering their path as images."""
    pcoll = bpy.utils.previews.new()
    addon_prefs = bpy.context.preferences.addons[__name__].preferences

    for light in addon_prefs.matcap_lights:
        pcoll.load(light.name, light.path, 'IMAGE')

    for light in addon_prefs.hdri_lights:
        pcoll.load(light.name, light.path, 'IMAGE')

    PREVIEW_COLLECTIONS["thumbnail_previews"] = pcoll


class LSWITCH_OT_edit(Operator):
    bl_idname = "lighting_switcher.edit"
    bl_label = "Edit Lighting"
    bl_description = "Open lighting editor"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        context.preferences.active_section = 'LIGHTS'
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        return {'FINISHED'}


# noinspection PyTypeChecker
class LSWITCH_PT_sidebar(Panel):
    bl_label = "Lighting"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "View"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        scene = context.scene
        shading = context.space_data.shading
        addon_prefs = context.preferences.addons[__name__].preferences

        row = col.row(align=True)
        row.prop(scene.lighting_switcher, "active_light_type", expand=True)

        match scene.lighting_switcher.active_light_type:
            case 'STUDIO':
                col.template_list("LSWITCH_UL_lights", "",
                                  addon_prefs, "studio_lights",
                                  scene.lighting_switcher, "active_studio_light_index")

                row = col.row(align=True)
                row.prop(shading, "use_world_space_lighting", text="", icon='WORLD', toggle=True)

                sub = row.row(align=True)
                sub.active = shading.use_world_space_lighting
                sub.prop(shading, "studiolight_rotate_z", text="Rotation")

            case 'MATCAP':
                col.template_list("LSWITCH_UL_lights", "",
                                  addon_prefs, "matcap_lights",
                                  scene.lighting_switcher, "active_matcap_light_index")

                row = col.row(align=True)
                row.operator("view3d.toggle_matcap_flip", icon='ARROW_LEFTRIGHT', text="Flip")

            case 'WORLD':
                col.template_list("LSWITCH_UL_lights", "",
                                  addon_prefs, "hdri_lights",
                                  scene.lighting_switcher, "active_hdri_light_index")

                row = col.row(align=True)
                row.prop(shading, "use_studiolight_view_rotation", text="", icon='WORLD', toggle=True)
                row.prop(shading, "studiolight_rotate_z", text="Rotation")
                col.prop(shading, "studiolight_intensity")

        row = col.row(align=True)
        row.operator("lighting_switcher.reload", icon='FILE_REFRESH', text="Reload")
        row.operator("lighting_switcher.edit", icon='SHADING_TEXTURE', text="Edit")


def set_viewport_shading_light(self, context):
    """Set viewport shading light to active light in props."""
    shading = context.space_data.shading
    addon_prefs = context.preferences.addons[__name__].preferences

    match self.active_light_type:
        case 'STUDIO':
            i = self.active_studio_light_index
            shading.studio_light = addon_prefs.studio_lights[i].name
        case 'MATCAP':
            i = self.active_matcap_light_index
            shading.studio_light = addon_prefs.matcap_lights[i].name
        case 'WORLD':
            i = self.active_hdri_light_index
            shading.studio_light = addon_prefs.hdri_lights[i].name


def set_viewport_shading_type(self, context):
    """Set viewport shading type to active type in props."""
    shading = context.space_data.shading

    match self.active_light_type:
        case 'STUDIO':
            shading.type = 'SOLID'
            shading.light = 'STUDIO'
        case 'MATCAP':
            shading.type = 'SOLID'
            shading.light = 'MATCAP'
        case 'WORLD':
            shading.type = 'MATERIAL'
            shading.use_scene_world = False


def sync_active_light_index(self, context):
    """Set current light in props to current light in viewport shading."""
    shading = context.space_data.shading
    curr_light = shading.studio_light
    addon_prefs = context.preferences.addons[__name__].preferences

    if shading.type == 'SOLID':
        if shading.light == 'STUDIO':
            idx = addon_prefs.studio_lights.find(curr_light)
            self["active_studio_light_index"] = max(idx, 0)
        elif shading.light == 'MATCAP':
            idx = addon_prefs.matcap_lights.find(curr_light)
            self["active_matcap_light_index"] = max(idx, 0)
    elif shading.type == 'MATERIAL':
        idx = addon_prefs.hdri_lights.find(curr_light)
        self["active_hdri_light_index"] = max(idx, 0)


class LSWITCH_PG_light(PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    label: StringProperty()
    path: StringProperty()


def update_active_light_type(self, context):
    set_viewport_shading_type(self, context)
    sync_active_light_index(self, context)


def update_active_studio_light(self, context):
    set_viewport_shading_type(self, context)
    set_viewport_shading_light(self, context)


class LSWITCH_PG_scene(PropertyGroup):
    # name = StringProperty() -> Instantiated by default
    # noinspection PyTypeChecker
    active_light_type: EnumProperty(
        name="Active Light Type",
        description="Lighting Method",
        items=[
            ('STUDIO', "Studio", "Display using studio lighting"),
            ('MATCAP', "MatCap", "Display using matcap material and lighting"),
            ('WORLD', "HDRI", "Display using hdri lighting"),
        ],
        default='STUDIO',
        update=update_active_light_type,
    )
    active_studio_light_index: IntProperty(
        name="Active Index",
        description="Index of the active studio light",
        default=0,
        update=update_active_studio_light,
    )
    active_matcap_light_index: IntProperty(
        name="Active Index",
        description="Index of the active matcap light",
        default=0,
        update=update_active_studio_light,
    )
    active_hdri_light_index: IntProperty(
        name="Active Index",
        description="Index of the active hdri light",
        default=0,
        update=update_active_studio_light,
    )


def update_sidebar_category(self, _):
    is_panel = hasattr(bpy.types, 'LSWITCH_PT_sidebar')
    if is_panel:
        try:
            bpy.utils.unregister_class(LSWITCH_PT_sidebar)
        except:  # noqa
            pass
    LSWITCH_PT_sidebar.bl_category = self.sidebar_category
    bpy.utils.register_class(LSWITCH_PT_sidebar)


class LSWITCH_preferences(AddonPreferences):
    bl_idname = __name__

    studio_lights: CollectionProperty(type=LSWITCH_PG_light)
    matcap_lights: CollectionProperty(type=LSWITCH_PG_light)
    hdri_lights: CollectionProperty(type=LSWITCH_PG_light)

    sidebar_category: StringProperty(
        name="Sidebar Category",
        description="Name for the tab in the sidebar panel",
        default="View",
        update=update_sidebar_category,
    )

    def draw(self, _):
        layout = self.layout

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False

        col.prop(self, "sidebar_category")


classes = (
    LSWITCH_UL_lights,
    LSWITCH_PT_sidebar,
    LSWITCH_OT_reload,
    LSWITCH_OT_edit,
    LSWITCH_PG_light,
    LSWITCH_PG_scene,
    LSWITCH_preferences,
)


def reload_previews_and_props():
    # Clear previews.
    for pcoll in PREVIEW_COLLECTIONS.values():
        bpy.utils.previews.remove(pcoll)
    PREVIEW_COLLECTIONS.clear()

    # Clear addon prefs props.
    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    addon_prefs.studio_lights.clear()
    addon_prefs.matcap_lights.clear()
    addon_prefs.hdri_lights.clear()

    # Add lights to scene collection.
    import_light()

    # Generate previews.
    generate_previews()


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    Scene.lighting_switcher = PointerProperty(type=LSWITCH_PG_scene)

    reload_previews_and_props()


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.lighting_switcher

    for pcoll in PREVIEW_COLLECTIONS.values():
        bpy.utils.previews.remove(pcoll)
    PREVIEW_COLLECTIONS.clear()


if __name__ == "__main__":
    register()
