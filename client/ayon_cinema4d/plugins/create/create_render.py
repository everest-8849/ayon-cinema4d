from ayon_cinema4d.api import (
    lib,
    plugin
)
from ayon_core.lib import EnumDef, BoolDef, UISeparatorDef
from ayon_core.pipeline.template_data import get_template_data_with_names
from ayon_core.pipeline import Anatomy, get_current_host_name
from ayon_core.lib import StringTemplate

class CreateRender(plugin.Cinema4DCreator):
    """Render"""
    identifier = "io.ayon.creators.cinema4d.render"
    label = "Render"
    description = "Create Render"
    product_type = "render"
    icon = "eye"

    # TODO: Enable this once it is implemented
    enabled = True

    # default render target
    render_target = "farm"

    default_variants = ["Main"]
    instance_attributes = ["review"]

    def get_instance_attr_defs(self):
        defs = lib.collect_animation_defs(self.create_context)

        self.log.debug(f"[RenderCreate] get_instance_attr_defs: {defs}")

        render_target_items = {
            "local": "Local",
            "farm": "Farm",
            "farm_split": "Farm - Split export & render jobs"
        }

        defs.append(
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render Target",
                    default="farm")
        )

        defs.append(
            BoolDef("review",
                    label="Mark for Review",
                    default=True)
        )

        return defs

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection",
                    tooltip="Attach instance to selected camera/null.",
                    default=True,
                    label="Use Selection"),
            UISeparatorDef(),
            EnumDef("render_target",
                    items={
                        "local": "Local",
                        "farm": "Farm",
                        "farm_split": "Farm - Split export & render jobs"
                    },
                    label="Render Target",
                    default="farm"),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=True,
            )
        ]

    # def create(self, product_name, instance_data, pre_create_data):
    #     project_name = self.create_context.get_current_project_name()
    #     anatomy = Anatomy(project_name)
    #
    #     self.log.debug(f"[RenderCreate] project_name: {project_name}")
    #
    #     data = get_template_data_with_names(
    #         project_name,
    #         self.create_context.get_current_folder_path(),
    #         self.create_context.get_current_task_name(),
    #         get_current_host_name()
    #     )
    #     data.update({
    #         "subset": product_name,
    #         "family": self.product_type,
    #         "product": {
    #             "name": product_name,
    #             "type": self.product_type
    #         },
    #         "frame": "#" * anatomy.templates_obj.frame_padding
    #     })
    #
    #     self.log.debug(f"[RenderCreate] template input data: {data}")
    #
    #     instance_data["fpath_template"] = anatomy.get_template_item(
    #         "work", "render", "file"
    #     ).raw_template
    #
    #     self.log.debug(f"[RenderCreate] fpath_template: {instance_data['fpath_template']}")
    #
    #     work_template = anatomy.get_template_item("work", "default", "directory")
    #     data["work"] = work_template.format_strict(data).normalized().replace("\\", "/")
    #
    #     self.log.debug(f"[RenderCreate] resolved work path: {data['work']}")
    #
    #     path = StringTemplate(instance_data["fpath_template"]).format_strict(data)
    #     instance_data["path_preview"] = path
    #
    #     self.log.debug(f"[RenderCreate] preview path: {path}")
    #
    #     return super().create(product_name, instance_data, pre_create_data)



